"""Seed de demonstração — cria carteira Beberibe CE e popula todas as tabelas.

Uso:
    python scripts/seed_demo.py

Requer DATABASE_URL no ambiente (ou .env na raiz do projeto).
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

import psycopg2.extras

from vega.db.connection import get_conn
from vega.ingestion.loader import load_csv
from vega.pipeline.higienizacao import Higienizador
from vega.pipeline.scoring import ParametrosScoring, ScorerV1


# ---------------------------------------------------------------------------
# 1. Carteira
# ---------------------------------------------------------------------------

_INSERT_CARTEIRA = """
    INSERT INTO vega.carteiras (
        tenant_id, municipio, uf, data_referencia, status_pipeline, origem
    ) VALUES (
        %(tenant_id)s, %(municipio)s, %(uf)s, %(data_referencia)s,
        %(status_pipeline)s, %(origem)s
    )
    RETURNING id
"""


def criar_carteira(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(_INSERT_CARTEIRA, {
            "tenant_id": "beberibe-ce",
            "municipio": "Beberibe",
            "uf": "CE",
            "data_referencia": date.today(),
            "status_pipeline": "aguardando",
            "origem": "csv",
        })
        return cur.fetchone()[0]


# ---------------------------------------------------------------------------
# 2. Sessão de análise
# ---------------------------------------------------------------------------

_INSERT_SESSAO = """
    INSERT INTO vega.sessoes_analise (
        carteira_id, usuario_id, usuario_nome,
        valor_minimo_cents, prazo_prescricao_anos,
        peso_dim_valor, peso_dim_urgencia,
        threshold_q1_prioridade, threshold_q1_recuperab,
        decay_rate_conservador, decay_rate_moderado, decay_rate_agressivo,
        desconto_otimo_pct, decay_calibrado
    ) VALUES (
        %(carteira_id)s, %(usuario_id)s, %(usuario_nome)s,
        %(valor_minimo_cents)s, %(prazo_prescricao_anos)s,
        %(peso_dim_valor)s, %(peso_dim_urgencia)s,
        %(threshold_q1_prioridade)s, %(threshold_q1_recuperab)s,
        %(decay_rate_conservador)s, %(decay_rate_moderado)s, %(decay_rate_agressivo)s,
        %(desconto_otimo_pct)s, %(decay_calibrado)s
    )
    RETURNING id
"""


def criar_sessao(conn, carteira_id: int) -> int:
    with conn.cursor() as cur:
        cur.execute(_INSERT_SESSAO, {
            "carteira_id": carteira_id,
            "usuario_id": 1,
            "usuario_nome": "Seed Demo",
            "valor_minimo_cents": 5_000,
            "prazo_prescricao_anos": 5,
            "peso_dim_valor": 30,
            "peso_dim_urgencia": 30,
            "threshold_q1_prioridade": 40,
            "threshold_q1_recuperab": 30,
            "decay_rate_conservador": "0.9000",
            "decay_rate_moderado": "0.5500",
            "decay_rate_agressivo": "0.3800",
            "desconto_otimo_pct": 25,
            "decay_calibrado": False,
        })
        return cur.fetchone()[0]


# ---------------------------------------------------------------------------
# 3. Scoring pipeline
# ---------------------------------------------------------------------------

_SELECT_ATIVAS = """
    SELECT
        h.id                        AS cda_higienizada_id,
        h.valor_corrigido_cents,
        h.padrao_densidade,
        b.data_inscricao,
        b.status_da,
        b.data_parcelamento,
        b.whatsapp, b.celular, b.email, b.telefone,
        b.logradouro, b.bairro,
        s.prazo_prescricao_anos
    FROM vega.cdas_higienizadas h
    JOIN vega.cdas_brutas b       ON b.id  = h.cda_bruta_id
    JOIN vega.sessoes_analise s   ON s.id  = h.sessao_id
    WHERE h.carteira_id = %(carteira_id)s
      AND h.sessao_id   = %(sessao_id)s
      AND h.ativa       = TRUE
"""

_SELECT_SCORING_PARAMS = """
    SELECT peso_dim_valor, peso_dim_urgencia,
           threshold_q1_prioridade, threshold_q1_recuperab
    FROM vega.sessoes_analise
    WHERE id = %(sessao_id)s
"""

_DELETE_SCORES = """
    DELETE FROM vega.scores
    WHERE carteira_id = %(carteira_id)s AND sessao_id = %(sessao_id)s
"""

_INSERT_SCORE = """
    INSERT INTO vega.scores (
        carteira_id, cda_higienizada_id, sessao_id,
        dim_valor, dim_urgencia, dim_contato, dim_comportamento,
        eixo_prioridade, eixo_recuperabilidade,
        quadrante, acao_sugerida, versao_score, pesos_usados
    ) VALUES (
        %(carteira_id)s, %(cda_higienizada_id)s, %(sessao_id)s,
        %(dim_valor)s, %(dim_urgencia)s, %(dim_contato)s, %(dim_comportamento)s,
        %(eixo_prioridade)s, %(eixo_recuperabilidade)s,
        %(quadrante)s, %(acao_sugerida)s, %(versao_score)s, %(pesos_usados)s
    )
"""


def rodar_scoring(conn, carteira_id: int, sessao_id: int) -> int:
    hoje = date.today()
    scorer = ScorerV1()

    with conn.cursor() as cur:
        cur.execute(_SELECT_SCORING_PARAMS, {"sessao_id": sessao_id})
        p = cur.fetchone()
    # peso_dim_contato e peso_dim_comportamento usam defaults do ParametrosScoring (25)
    # pois não foram adicionados à migration 002
    params = ParametrosScoring(
        peso_dim_valor=p[0],
        peso_dim_urgencia=p[1],
        threshold_q1_prioridade=p[2],
        threshold_q1_recuperab=p[3],
    )

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(_SELECT_ATIVAS, {"carteira_id": carteira_id, "sessao_id": sessao_id})
        ativas = cur.fetchall()

    payload = []
    for row in ativas:
        prazo_anos = int(row["prazo_prescricao_anos"])
        data_inscricao = row["data_inscricao"]
        dias_totais = prazo_anos * 365
        dias_decorridos = (hoje - data_inscricao).days

        row_scoring = dict(row)
        row_scoring["dias_decorridos"] = dias_decorridos
        row_scoring["dias_totais"] = dias_totais

        resultado = scorer.calcular_score(row_scoring, params)
        payload.append({
            "carteira_id": carteira_id,
            "cda_higienizada_id": row["cda_higienizada_id"],
            "sessao_id": sessao_id,
            "dim_valor": resultado.dim_valor,
            "dim_urgencia": resultado.dim_urgencia,
            "dim_contato": resultado.dim_contato,
            "dim_comportamento": resultado.dim_comportamento,
            "eixo_prioridade": resultado.eixo_prioridade,
            "eixo_recuperabilidade": resultado.eixo_recuperabilidade,
            "quadrante": resultado.quadrante,
            "acao_sugerida": resultado.acao_sugerida,
            "versao_score": resultado.versao_score,
            "pesos_usados": psycopg2.extras.Json(resultado.pesos_usados),
        })

    with conn.cursor() as cur:
        cur.execute(_DELETE_SCORES, {"carteira_id": carteira_id, "sessao_id": sessao_id})
        if payload:
            psycopg2.extras.execute_batch(cur, _INSERT_SCORE, payload)

    return len(payload)


# ---------------------------------------------------------------------------
# 4. Fluxo mensal — 12 meses mockados
# ---------------------------------------------------------------------------

_INSERT_FLUXO = """
    INSERT INTO vega.fluxo_mensal (
        carteira_id, tenant_id, ano_mes,
        cdas_inscritas, cdas_recuperadas,
        valor_inscrito_cents, valor_recuperado_cents,
        fonte_dados
    ) VALUES (
        %(carteira_id)s, %(tenant_id)s, %(ano_mes)s,
        %(cdas_inscritas)s, %(cdas_recuperadas)s,
        %(valor_inscrito_cents)s, %(valor_recuperado_cents)s,
        %(fonte_dados)s
    )
    ON CONFLICT (carteira_id, ano_mes) DO NOTHING
"""


def popular_fluxo_mensal(conn, carteira_id: int, tenant_id: str) -> None:
    hoje = date.today()
    payload = []
    for i in range(12, 0, -1):
        ano, mes = hoje.year, hoje.month - i
        while mes <= 0:
            mes += 12
            ano -= 1
        inscritas = 15 + (i % 5)
        recuperadas = 3 + (i % 3)
        payload.append({
            "carteira_id": carteira_id,
            "tenant_id": tenant_id,
            "ano_mes": date(ano, mes, 1),
            "cdas_inscritas": inscritas,
            "cdas_recuperadas": recuperadas,
            "valor_inscrito_cents": inscritas * 350_000,
            "valor_recuperado_cents": recuperadas * 180_000,
            "fonte_dados": "mock",
        })
    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, _INSERT_FLUXO, payload)


# ---------------------------------------------------------------------------
# 5. Cohorts de campanha — 4 programas mockados
# ---------------------------------------------------------------------------

_INSERT_COHORT = """
    INSERT INTO vega.cohorts_campanha (
        carteira_id, tenant_id, nome_programa, tipo_programa,
        data_inicio, data_encerramento,
        condicoes_desconto_pct, parcelas_maximas,
        aderiram, concluiram, quebraram, voltaram_carteira,
        reabordados_sucesso, perfil_dominante, fonte_dados
    ) VALUES (
        %(carteira_id)s, %(tenant_id)s, %(nome_programa)s, %(tipo_programa)s,
        %(data_inicio)s, %(data_encerramento)s,
        %(condicoes_desconto_pct)s, %(parcelas_maximas)s,
        %(aderiram)s, %(concluiram)s, %(quebraram)s, %(voltaram_carteira)s,
        %(reabordados_sucesso)s, %(perfil_dominante)s, %(fonte_dados)s
    )
"""


def popular_cohorts(conn, carteira_id: int, tenant_id: str) -> None:
    hoje = date.today()
    programas = [
        {
            "nome_programa": "Refis Municipal 2022",
            "tipo_programa": "refis",
            "data_inicio": date(hoje.year - 3, 3, 1),
            "data_encerramento": date(hoje.year - 3, 6, 30),
            "condicoes_desconto_pct": 30,
            "parcelas_maximas": 12,
            "aderiram": 280, "concluiram": 195, "quebraram": 55,
            "voltaram_carteira": 30, "reabordados_sucesso": 18,
            "perfil_dominante": "Q1",
        },
        {
            "nome_programa": "Campanha Regulariza 2023",
            "tipo_programa": "campanha",
            "data_inicio": date(hoje.year - 2, 1, 15),
            "data_encerramento": date(hoje.year - 2, 3, 31),
            "condicoes_desconto_pct": 20,
            "parcelas_maximas": 6,
            "aderiram": 142, "concluiram": 98, "quebraram": 30,
            "voltaram_carteira": 14, "reabordados_sucesso": 9,
            "perfil_dominante": "Q2",
        },
        {
            "nome_programa": "Parcelamento Especial IPTU 2023",
            "tipo_programa": "parcelamento",
            "data_inicio": date(hoje.year - 2, 8, 1),
            "data_encerramento": date(hoje.year - 2, 12, 31),
            "condicoes_desconto_pct": 15,
            "parcelas_maximas": 24,
            "aderiram": 87, "concluiram": 52, "quebraram": 25,
            "voltaram_carteira": 10, "reabordados_sucesso": 6,
            "perfil_dominante": "Q1",
        },
        {
            "nome_programa": "Campanha WhatsApp Q1 2024",
            "tipo_programa": "campanha",
            "data_inicio": date(hoje.year - 1, 2, 1),
            "data_encerramento": date(hoje.year - 1, 4, 30),
            "condicoes_desconto_pct": 25,
            "parcelas_maximas": 6,
            "aderiram": 63, "concluiram": 41, "quebraram": 14,
            "voltaram_carteira": 8, "reabordados_sucesso": 5,
            "perfil_dominante": "Q2",
        },
    ]
    payload = [
        {**p, "carteira_id": carteira_id, "tenant_id": tenant_id, "fonte_dados": "mock"}
        for p in programas
    ]
    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, _INSERT_COHORT, payload)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    csv_path = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "carteira_teste.csv"

    print("→ Conectando ao banco...")
    with get_conn() as conn:
        print("→ Criando carteira (Beberibe CE)...")
        carteira_id = criar_carteira(conn)
        conn.commit()
        print(f"  carteira_id = {carteira_id}")

        print("→ Criando sessão de análise (parâmetros default)...")
        sessao_id = criar_sessao(conn, carteira_id)
        conn.commit()
        print(f"  sessao_id   = {sessao_id}")

    print(f"→ Carregando CSV: {csv_path.name} ...")
    resultado = load_csv(csv_path, carteira_id, sessao_id)
    print(f"  total={resultado['total']}  válidas={resultado['validas']}  "
          f"rejeitadas={resultado['rejeitadas']}")
    if resultado["erros"]:
        print(f"  erros: {resultado['erros']}")

    print("→ Rodando higienização + segmentação...")
    hig = Higienizador().processar(carteira_id, sessao_id)
    print(f"  total={hig.total}  ativas={hig.ativas}  eliminadas={hig.eliminadas}")
    print(f"  por causa: {hig.por_causa}")

    print("→ Rodando scoring...")
    with get_conn() as conn:
        n_scores = rodar_scoring(conn, carteira_id, sessao_id)
        conn.commit()
    print(f"  scores inseridos: {n_scores}")

    print("→ Populando fluxo_mensal (12 meses mockados)...")
    with get_conn() as conn:
        popular_fluxo_mensal(conn, carteira_id, "beberibe-ce")
        conn.commit()

    print("→ Populando cohorts_campanha (4 programas mockados)...")
    with get_conn() as conn:
        popular_cohorts(conn, carteira_id, "beberibe-ce")
        conn.commit()

    print()
    print("✓ Seed concluído com sucesso.")
    print(f"  carteira_id = {carteira_id}")
    print(f"  sessao_id   = {sessao_id}")
    print()
    print("Próximos passos:")
    print("  1. Edite .env → DEMO_MODE=false")
    print("  2. python -m vega.app.app")
    print("     → http://localhost:8050")


if __name__ == "__main__":
    main()
