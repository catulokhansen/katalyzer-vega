"""Etapa 2a — Higienização.

Referência: Pipeline_KatalyzerVega_v1.docx, seção 3.

Classifica cada CDA bruta como ativa (entra na análise) ou eliminada
(estoque morto). Para cada CDA eliminada, registra a causa.

Ordem de aplicação dos critérios (seção 3.2):
  1. Flag de prescrição interrompida (parcelado | protestado | ajuizado)
     — NÃO elimina, apenas levanta a flag.
  2. Valor irrisório — elimina (causa = irrisorio).
  3. Devedor inexistente — elimina (causa = devedor_inexistente).
  4. Prescrição — elimina SE não houver flag de interrupção
     (causa = prescricao).

Ao final, para CDAs ativas, também calcula os campos derivados da
segmentação (faixa_valor, faixa_idade, safra, padrao_densidade) e
persiste tudo em vega.cdas_higienizadas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Optional

import psycopg2.extras
from dateutil.relativedelta import relativedelta

from vega.db.connection import get_conn
from vega.pipeline.segmentacao import (
    calcular_padrao_densidade,
    classificar_faixa_idade,
    classificar_faixa_valor,
    classificar_safra,
)

import pandas as pd


# --- Critérios de eliminação ---------------------------------------------

STATUS_INEXISTENTE: frozenset[str] = frozenset(
    {"baixado", "cancelado", "inexistente", "inativo"}
)

# "ajuizado" também marca prescrição como interrompida (CTN art. 174).
STATUS_INTERROMPE_PRESCRICAO: frozenset[str] = frozenset(
    {"parcelado", "protestado", "ajuizado"}
)


@dataclass(frozen=True)
class ParametrosSessao:
    """Parâmetros de uma sessao_analise relevantes para a higienização."""

    valor_minimo_cents: int = 5_000
    prazo_prescricao_anos: int = 5


@dataclass
class CDABruta:
    """View leve de uma linha de vega.cdas_brutas usada pela higienização."""

    id: int
    contribuinte_id: str
    valor_total_cents: int
    data_inscricao: date
    status_da: Optional[str]
    # Campos opcionais usados pela segmentação + contactabilidade
    telefone: Optional[str] = None
    celular: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    logradouro: Optional[str] = None
    bairro: Optional[str] = None


@dataclass
class CDAAHigienizada:
    """Resultado da higienização + campos derivados da segmentação."""

    cda_bruta_id: int
    contribuinte_id: str
    ativa: bool
    causa_eliminacao: Optional[str]
    data_prescricao_estimada: date
    dias_para_prescricao: int
    prescricao_interrompida: bool
    valor_corrigido_cents: int
    data_inscricao: date
    # Campos da segmentação — preenchidos só para ativas
    faixa_valor: Optional[str] = None
    faixa_idade: Optional[str] = None
    safra: Optional[int] = None
    padrao_densidade: Optional[str] = None


@dataclass
class HigienizacaoResult:
    """Agregado dos resultados da higienização para exibição/KPI."""

    total: int
    ativas: int
    eliminadas: int
    prescricao_interrompida: int
    por_causa: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_resultados(cls, resultados: Iterable[CDAAHigienizada]) -> "HigienizacaoResult":
        total = 0
        ativas = 0
        eliminadas = 0
        prescricao_interrompida = 0
        por_causa: dict[str, int] = {}
        for r in resultados:
            total += 1
            if r.ativa:
                ativas += 1
                if r.prescricao_interrompida:
                    prescricao_interrompida += 1
            else:
                eliminadas += 1
                causa = r.causa_eliminacao or "desconhecida"
                por_causa[causa] = por_causa.get(causa, 0) + 1
        return cls(
            total=total,
            ativas=ativas,
            eliminadas=eliminadas,
            prescricao_interrompida=prescricao_interrompida,
            por_causa=por_causa,
        )


# --- Predicados dos critérios --------------------------------------------


def _verificar_irrisorio(cda: CDABruta, params: ParametrosSessao) -> bool:
    """Critério 1: valor total < valor mínimo configurado."""
    return cda.valor_total_cents < params.valor_minimo_cents


def _verificar_inexistente(cda: CDABruta) -> bool:
    """Critério 2: status_da indica contribuinte inativo/baixado."""
    if cda.status_da is None:
        return False
    return cda.status_da.lower() in STATUS_INEXISTENTE


def _verificar_prescricao_interrompida(cda: CDABruta) -> bool:
    """Critério 3 (flag): status_da com prescrição legalmente interrompida."""
    if cda.status_da is None:
        return False
    return cda.status_da.lower() in STATUS_INTERROMPE_PRESCRICAO


def _calcular_prescricao(
    cda: CDABruta, params: ParametrosSessao, hoje: Optional[date] = None
) -> tuple[date, int]:
    """Retorna (data_prescricao_estimada, dias_restantes)."""
    hoje = hoje or date.today()
    data_prescricao = cda.data_inscricao + relativedelta(years=params.prazo_prescricao_anos)
    dias_restantes = (data_prescricao - hoje).days
    return data_prescricao, dias_restantes


def _verificar_prescricao(dias_para_prescricao: int) -> bool:
    """Critério 4: dias_para_prescricao <= 0 significa já prescrita."""
    return dias_para_prescricao <= 0


# --- Processador ---------------------------------------------------------


def _processar_cda(
    cda: CDABruta, params: ParametrosSessao, hoje: Optional[date] = None
) -> CDAAHigienizada:
    """Aplica os 4 critérios na ordem documentada.

    A função é pura e determinística — exposta para os testes unitários.
    """
    hoje = hoje or date.today()

    # Pré-cálculo: prescrição sempre é calculada (campo NOT NULL na tabela).
    prescricao_interrompida = _verificar_prescricao_interrompida(cda)
    data_prescricao, dias_restantes = _calcular_prescricao(cda, params, hoje=hoje)

    # Critério 1: Valor irrisório (prioridade máxima — H-08).
    if _verificar_irrisorio(cda, params):
        return CDAAHigienizada(
            cda_bruta_id=cda.id,
            contribuinte_id=cda.contribuinte_id,
            ativa=False,
            causa_eliminacao="irrisorio",
            data_prescricao_estimada=data_prescricao,
            dias_para_prescricao=dias_restantes,
            prescricao_interrompida=False,
            valor_corrigido_cents=cda.valor_total_cents,
            data_inscricao=cda.data_inscricao,
        )

    # Critério 2: Devedor inexistente.
    if _verificar_inexistente(cda):
        return CDAAHigienizada(
            cda_bruta_id=cda.id,
            contribuinte_id=cda.contribuinte_id,
            ativa=False,
            causa_eliminacao="devedor_inexistente",
            data_prescricao_estimada=data_prescricao,
            dias_para_prescricao=dias_restantes,
            prescricao_interrompida=False,
            valor_corrigido_cents=cda.valor_total_cents,
            data_inscricao=cda.data_inscricao,
        )

    # Critério 4: Prescrição — CDAs com flag de interrupção NÃO são eliminadas.
    if _verificar_prescricao(dias_restantes) and not prescricao_interrompida:
        return CDAAHigienizada(
            cda_bruta_id=cda.id,
            contribuinte_id=cda.contribuinte_id,
            ativa=False,
            causa_eliminacao="prescricao",
            data_prescricao_estimada=data_prescricao,
            dias_para_prescricao=dias_restantes,
            prescricao_interrompida=False,
            valor_corrigido_cents=cda.valor_total_cents,
            data_inscricao=cda.data_inscricao,
        )

    # CDA ativa — campos derivados da segmentação são preenchidos depois.
    return CDAAHigienizada(
        cda_bruta_id=cda.id,
        contribuinte_id=cda.contribuinte_id,
        ativa=True,
        causa_eliminacao=None,
        data_prescricao_estimada=data_prescricao,
        dias_para_prescricao=dias_restantes,
        prescricao_interrompida=prescricao_interrompida,
        valor_corrigido_cents=cda.valor_total_cents,
        data_inscricao=cda.data_inscricao,
    )


# --- Acesso ao banco -----------------------------------------------------


_SELECT_CDAS_BRUTAS_SQL = """
    SELECT id, contribuinte_id, valor_total_cents, data_inscricao,
           status_da, telefone, celular, whatsapp, email, logradouro, bairro
    FROM vega.cdas_brutas
    WHERE carteira_id = %(carteira_id)s
    ORDER BY id
"""

_SELECT_PARAMS_SQL = """
    SELECT valor_minimo_cents, prazo_prescricao_anos
    FROM vega.sessoes_analise
    WHERE id = %(sessao_id)s
"""

_DELETE_ANTERIORES_SQL = """
    DELETE FROM vega.cdas_higienizadas
    WHERE carteira_id = %(carteira_id)s AND sessao_id = %(sessao_id)s
"""

_INSERT_HIGIENIZADA_SQL = """
    INSERT INTO vega.cdas_higienizadas (
        carteira_id, cda_bruta_id, sessao_id,
        ativa, causa_eliminacao,
        data_prescricao_estimada, dias_para_prescricao,
        prescricao_interrompida, valor_corrigido_cents,
        faixa_valor, faixa_idade, safra, padrao_densidade
    ) VALUES (
        %(carteira_id)s, %(cda_bruta_id)s, %(sessao_id)s,
        %(ativa)s, %(causa_eliminacao)s,
        %(data_prescricao_estimada)s, %(dias_para_prescricao)s,
        %(prescricao_interrompida)s, %(valor_corrigido_cents)s,
        %(faixa_valor)s, %(faixa_idade)s, %(safra)s, %(padrao_densidade)s
    )
"""


class Higienizador:
    """Processa CDAs brutas de uma carteira aplicando os critérios em sequência.

    Idempotente: executar de novo com os mesmos parâmetros produz o mesmo
    resultado. Para rodar com parâmetros diferentes, crie outra
    ``sessoes_analise`` — a tabela ``cdas_higienizadas`` é filtrada por
    ``(carteira_id, sessao_id)`` e os registros da sessão são substituídos.
    """

    def __init__(self, hoje: Optional[date] = None) -> None:
        # Data de referência — útil para testes determinísticos.
        self._hoje = hoje or date.today()

    # ---- API pública ----

    def processar(self, carteira_id: int, sessao_id: int) -> HigienizacaoResult:
        with get_conn() as conn:
            params = self._buscar_parametros(conn, sessao_id)
            brutas = self._carregar_brutas(conn, carteira_id)
            resultados = self._higienizar_e_segmentar(brutas, params)
            self._persistir(conn, carteira_id, sessao_id, resultados)
            conn.commit()
        return HigienizacaoResult.from_resultados(resultados)

    # ---- Passos internos ----

    def _buscar_parametros(self, conn, sessao_id: int) -> ParametrosSessao:
        with conn.cursor() as cur:
            cur.execute(_SELECT_PARAMS_SQL, {"sessao_id": sessao_id})
            linha = cur.fetchone()
        if linha is None:
            raise ValueError(f"Sessão {sessao_id} não encontrada em vega.sessoes_analise")
        valor_min, prazo = linha
        return ParametrosSessao(
            valor_minimo_cents=int(valor_min),
            prazo_prescricao_anos=int(prazo),
        )

    def _carregar_brutas(self, conn, carteira_id: int) -> list[CDABruta]:
        with conn.cursor() as cur:
            cur.execute(_SELECT_CDAS_BRUTAS_SQL, {"carteira_id": carteira_id})
            linhas = cur.fetchall()
        return [
            CDABruta(
                id=linha[0],
                contribuinte_id=linha[1],
                valor_total_cents=int(linha[2]),
                data_inscricao=linha[3],
                status_da=linha[4],
                telefone=linha[5],
                celular=linha[6],
                whatsapp=linha[7],
                email=linha[8],
                logradouro=linha[9],
                bairro=linha[10],
            )
            for linha in linhas
        ]

    def _higienizar_e_segmentar(
        self, brutas: list[CDABruta], params: ParametrosSessao
    ) -> list[CDAAHigienizada]:
        """Executa a classificação + segmentação em 2 passes.

        1) Aplica os critérios para cada CDA.
        2) Para as ativas, calcula padrão de densidade (precisa do conjunto
           completo de ativas) e as demais classificações.
        """
        resultados = [_processar_cda(cda, params, hoje=self._hoje) for cda in brutas]

        ativas = [r for r in resultados if r.ativa]
        if ativas:
            df_ativas = pd.DataFrame({
                "contribuinte_id": [r.contribuinte_id for r in ativas],
                "idx": list(range(len(ativas))),
            }).set_index("idx")
            densidades = calcular_padrao_densidade(df_ativas)

            for pos, r in enumerate(ativas):
                r.faixa_valor = classificar_faixa_valor(r.valor_corrigido_cents)
                r.faixa_idade = classificar_faixa_idade(r.dias_para_prescricao)
                r.safra = classificar_safra(r.data_inscricao)
                r.padrao_densidade = densidades.loc[pos]

        return resultados

    def _persistir(
        self, conn, carteira_id: int, sessao_id: int, resultados: list[CDAAHigienizada]
    ) -> None:
        with conn.cursor() as cur:
            # Idempotência: remove registros anteriores da MESMA sessão.
            cur.execute(_DELETE_ANTERIORES_SQL,
                        {"carteira_id": carteira_id, "sessao_id": sessao_id})

            if not resultados:
                return

            payload = [
                {
                    "carteira_id": carteira_id,
                    "cda_bruta_id": r.cda_bruta_id,
                    "sessao_id": sessao_id,
                    "ativa": r.ativa,
                    "causa_eliminacao": r.causa_eliminacao,
                    "data_prescricao_estimada": r.data_prescricao_estimada,
                    "dias_para_prescricao": r.dias_para_prescricao,
                    "prescricao_interrompida": r.prescricao_interrompida,
                    "valor_corrigido_cents": r.valor_corrigido_cents,
                    "faixa_valor": r.faixa_valor,
                    "faixa_idade": r.faixa_idade,
                    "safra": r.safra,
                    "padrao_densidade": r.padrao_densidade,
                }
                for r in resultados
            ]
            psycopg2.extras.execute_batch(cur, _INSERT_HIGIENIZADA_SQL, payload)
