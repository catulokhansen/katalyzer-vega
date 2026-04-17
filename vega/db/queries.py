"""Queries analíticas do Vega — SQL puro + pandas.read_sql.

Regras (CLAUDE.md):
  - Toda query filtra por carteira_id, sem exceção.
  - Queries de scoring filtram também por sessao_id.
  - Sem SQLAlchemy. Sem ORM.
  - Valores monetários em centavos (bigint) — formatação só em utils/formatters.
"""
from __future__ import annotations

import pandas as pd

from vega.db.connection import get_conn


def metricas_diagnostico(carteira_id: int) -> pd.DataFrame:
    """KPIs da Aba 1: contagens e valores por grupo (ativa × causa_eliminacao).

    Retorna uma linha por (ativa, causa_eliminacao). O caller agrega os totais.
    """
    sql = """
        SELECT
            h.ativa,
            h.causa_eliminacao,
            SUM(h.valor_corrigido_cents)                AS valor_cents,
            COUNT(*)                                    AS total_cdas
        FROM vega.cdas_higienizadas h
        WHERE h.carteira_id = %(carteira_id)s
        GROUP BY h.ativa, h.causa_eliminacao
        ORDER BY h.ativa DESC, h.causa_eliminacao NULLS FIRST
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


def concentracao_risco(carteira_id: int) -> pd.DataFrame:
    """Contribuinte com maior participação na carteira ativa (RN-07).

    Retorna o contribuinte que mais concentra valor, junto com seu percentual
    em relação ao total ativo. Se nenhum contribuinte ultrapassa 10%, retorna
    DataFrame vazio (0 linhas).
    """
    sql = """
        WITH total_ativo AS (
            SELECT SUM(h.valor_corrigido_cents) AS total
            FROM vega.cdas_higienizadas h
            WHERE h.carteira_id = %(carteira_id)s
              AND h.ativa = TRUE
        ),
        por_contribuinte AS (
            SELECT
                b.contribuinte_id,
                b.contribuinte_nome,
                SUM(h.valor_corrigido_cents)                        AS valor_cents,
                SUM(h.valor_corrigido_cents)::FLOAT / NULLIF(t.total, 0) * 100 AS pct_carteira_ativa
            FROM vega.cdas_higienizadas h
            JOIN vega.cdas_brutas b ON b.id = h.cda_bruta_id
            CROSS JOIN total_ativo t
            WHERE h.carteira_id = %(carteira_id)s
              AND h.ativa = TRUE
            GROUP BY b.contribuinte_id, b.contribuinte_nome, t.total
        )
        SELECT contribuinte_id, contribuinte_nome, valor_cents, pct_carteira_ativa
        FROM por_contribuinte
        WHERE pct_carteira_ativa > %(threshold)s
        ORDER BY valor_cents DESC
        LIMIT 1
    """
    with get_conn() as conn:
        return pd.read_sql(
            sql,
            conn,
            params={"carteira_id": carteira_id, "threshold": 10.0},
        )


def top_contribuintes(
    carteira_id: int,
    sessao_id: int | None = None,
    limit: int = 10,
) -> pd.DataFrame:
    """Top contribuintes por valor ativo — consolida CDAs, densidade, score e NBA.

    Se sessao_id for None, usa o score da sessão mais recente da carteira.
    Retorna: contribuinte_id, contribuinte_nome, contribuinte_tipo,
             count_cdas, valor_total_cents, densidade_cents, padrao_densidade,
             quadrante, score_total, acao_sugerida.
    """
    sql = """
        WITH sessao AS (
            SELECT COALESCE(%(sessao_id)s::BIGINT,
                            (SELECT id FROM vega.sessoes_analise
                             WHERE carteira_id = %(carteira_id)s
                             ORDER BY created_at DESC LIMIT 1)) AS sid
        ),
        ativas AS (
            SELECT
                h.id                        AS hig_id,
                b.contribuinte_id,
                b.contribuinte_nome,
                b.contribuinte_tipo,
                h.valor_corrigido_cents,
                h.padrao_densidade
            FROM vega.cdas_higienizadas h
            JOIN vega.cdas_brutas b ON b.id = h.cda_bruta_id
            WHERE h.carteira_id = %(carteira_id)s
              AND h.ativa = TRUE
        ),
        scores_cda AS (
            SELECT
                s.cda_higienizada_id,
                s.eixo_prioridade + s.eixo_recuperabilidade   AS score_total,
                s.quadrante,
                s.acao_sugerida
            FROM vega.scores s
            CROSS JOIN sessao
            WHERE s.carteira_id = %(carteira_id)s
              AND (s.sessao_id = sessao.sid OR s.sessao_id IS NULL)
        )
        SELECT
            a.contribuinte_id,
            a.contribuinte_nome,
            a.contribuinte_tipo,
            COUNT(*)                                        AS count_cdas,
            SUM(a.valor_corrigido_cents)                    AS valor_total_cents,
            (SUM(a.valor_corrigido_cents) / COUNT(*))::BIGINT AS densidade_cents,
            MAX(a.padrao_densidade)                         AS padrao_densidade,
            MODE() WITHIN GROUP (ORDER BY sc.quadrante)     AS quadrante,
            ROUND(AVG(sc.score_total))::INT                 AS score_total,
            MODE() WITHIN GROUP (ORDER BY sc.acao_sugerida) AS acao_sugerida
        FROM ativas a
        LEFT JOIN scores_cda sc ON sc.cda_higienizada_id = a.hig_id
        GROUP BY a.contribuinte_id, a.contribuinte_nome, a.contribuinte_tipo
        ORDER BY valor_total_cents DESC
        LIMIT %(limit)s
    """
    with get_conn() as conn:
        return pd.read_sql(
            sql,
            conn,
            params={
                "carteira_id": carteira_id,
                "sessao_id": sessao_id,
                "limit": limit,
            },
        )


def fluxo_mensal_resumo(carteira_id: int) -> pd.DataFrame:
    """Últimos 12 meses de vega.fluxo_mensal.

    Retorna: ano_mes, cdas_inscritas, cdas_recuperadas,
             valor_inscrito_cents, valor_recuperado_cents.
    """
    sql = """
        SELECT
            ano_mes,
            cdas_inscritas,
            cdas_recuperadas,
            valor_inscrito_cents,
            valor_recuperado_cents
        FROM vega.fluxo_mensal
        WHERE carteira_id = %(carteira_id)s
          AND ano_mes >= (CURRENT_DATE - INTERVAL '12 months')
        ORDER BY ano_mes ASC
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


def pareto_curva(carteira_id: int) -> pd.DataFrame:
    """Curva de Pareto: % acumulado de contribuintes × % acumulado de valor.

    Retorna: pct_contribuintes (0–100), pct_valor_acumulado (0–100).
    """
    sql = """
        WITH contribuintes AS (
            SELECT
                b.contribuinte_id,
                SUM(h.valor_corrigido_cents) AS valor_cents
            FROM vega.cdas_higienizadas h
            JOIN vega.cdas_brutas b ON b.id = h.cda_bruta_id
            WHERE h.carteira_id = %(carteira_id)s
              AND h.ativa = TRUE
            GROUP BY b.contribuinte_id
            ORDER BY valor_cents DESC
        ),
        ranked AS (
            SELECT
                ROW_NUMBER() OVER ()        AS rn,
                COUNT(*) OVER ()            AS total_contrib,
                SUM(valor_cents) OVER ()    AS total_valor,
                SUM(valor_cents) OVER (ORDER BY valor_cents DESC
                                       ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                                            AS valor_acumulado
            FROM contribuintes
        )
        SELECT
            ROUND(rn::NUMERIC / total_contrib * 100, 1) AS pct_contribuintes,
            ROUND(valor_acumulado::NUMERIC / NULLIF(total_valor, 0) * 100, 1)
                                                        AS pct_valor_acumulado
        FROM ranked
        WHERE MOD(rn, GREATEST(total_contrib / 20, 1)) = 0
           OR rn = total_contrib
        ORDER BY pct_contribuintes
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


def composicao_tributo(carteira_id: int) -> pd.DataFrame:
    """Composição da carteira ativa por tributo.

    Retorna: tributo, valor_cents, pct_total.
    """
    sql = """
        WITH total AS (
            SELECT SUM(h.valor_corrigido_cents) AS total_cents
            FROM vega.cdas_higienizadas h
            WHERE h.carteira_id = %(carteira_id)s
              AND h.ativa = TRUE
        )
        SELECT
            b.tributo,
            SUM(h.valor_corrigido_cents)                        AS valor_cents,
            ROUND(
                SUM(h.valor_corrigido_cents)::NUMERIC / NULLIF(t.total_cents, 0) * 100,
                1
            )                                                   AS pct_total
        FROM vega.cdas_higienizadas h
        JOIN vega.cdas_brutas b ON b.id = h.cda_bruta_id
        CROSS JOIN total t
        WHERE h.carteira_id = %(carteira_id)s
          AND h.ativa = TRUE
        GROUP BY b.tributo, t.total_cents
        ORDER BY valor_cents DESC
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


def valor_por_idade_tributo(carteira_id: int) -> pd.DataFrame:
    """Valor ativo por faixa etária × tributo — alimenta o gráfico de barras empilhadas.

    Retorna: faixa_idade, tributo, valor_cents.
    faixa_idade segue a convenção de segmentacao.py (tempo restante até prescrição).
    """
    sql = """
        SELECT
            h.faixa_idade,
            b.tributo,
            SUM(h.valor_corrigido_cents) AS valor_cents
        FROM vega.cdas_higienizadas h
        JOIN vega.cdas_brutas b ON b.id = h.cda_bruta_id
        WHERE h.carteira_id = %(carteira_id)s
          AND h.ativa = TRUE
          AND h.faixa_idade IS NOT NULL
        GROUP BY h.faixa_idade, b.tributo
        ORDER BY h.faixa_idade, b.tributo
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


# ── Aba 2 — Segmentação ───────────────────────────────────────────────────────

def distribuicao_faixa_valor(carteira_id: int) -> pd.DataFrame:
    """Distribuição de CDAs ativas por faixa de valor.

    Retorna: faixa_valor, count_cdas, valor_cents, pct_count, pct_valor.
    """
    sql = """
        WITH total AS (
            SELECT COUNT(*)                       AS total_cdas,
                   SUM(valor_corrigido_cents)      AS total_cents
            FROM vega.cdas_higienizadas
            WHERE carteira_id = %(carteira_id)s AND ativa = TRUE
        )
        SELECT
            h.faixa_valor,
            COUNT(*)                                AS count_cdas,
            SUM(h.valor_corrigido_cents)            AS valor_cents,
            ROUND(COUNT(*)::NUMERIC
                  / NULLIF(t.total_cdas, 0) * 100, 1) AS pct_count,
            ROUND(SUM(h.valor_corrigido_cents)::NUMERIC
                  / NULLIF(t.total_cents, 0) * 100, 1) AS pct_valor
        FROM vega.cdas_higienizadas h
        CROSS JOIN total t
        WHERE h.carteira_id = %(carteira_id)s
          AND h.ativa = TRUE
          AND h.faixa_valor IS NOT NULL
        GROUP BY h.faixa_valor, t.total_cdas, t.total_cents
        ORDER BY
            CASE h.faixa_valor
                WHEN 'ate_500'    THEN 1
                WHEN '500_2k'     THEN 2
                WHEN '2k_10k'     THEN 3
                WHEN '10k_50k'    THEN 4
                WHEN 'acima_50k'  THEN 5
                ELSE 9
            END
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


def pf_vs_pj(carteira_id: int) -> pd.DataFrame:
    """PF vs PJ: contagem de CDAs, valor e número de contribuintes.

    Retorna: contribuinte_tipo, count_cdas, valor_cents, count_contrib.
    """
    sql = """
        SELECT
            b.contribuinte_tipo,
            COUNT(*)                           AS count_cdas,
            SUM(h.valor_corrigido_cents)       AS valor_cents,
            COUNT(DISTINCT b.contribuinte_id)  AS count_contrib
        FROM vega.cdas_higienizadas h
        JOIN vega.cdas_brutas b ON b.id = h.cda_bruta_id
        WHERE h.carteira_id = %(carteira_id)s
          AND h.ativa = TRUE
        GROUP BY b.contribuinte_tipo
        ORDER BY b.contribuinte_tipo
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


def matriz_segmentos(carteira_id: int) -> pd.DataFrame:
    """Matriz pivotada: tributo × faixa_valor (count CDAs ativas).

    Retorna DataFrame com colunas: tributo, ate_500, 500_2k, 2k_10k, 10k_50k, acima_50k.
    """
    sql = """
        SELECT
            b.tributo,
            h.faixa_valor,
            COUNT(*) AS count_cdas
        FROM vega.cdas_higienizadas h
        JOIN vega.cdas_brutas b ON b.id = h.cda_bruta_id
        WHERE h.carteira_id = %(carteira_id)s
          AND h.ativa = TRUE
          AND h.faixa_valor IS NOT NULL
        GROUP BY b.tributo, h.faixa_valor
        ORDER BY b.tributo, h.faixa_valor
    """
    with get_conn() as conn:
        df = pd.read_sql(sql, conn, params={"carteira_id": carteira_id})
    if df.empty:
        return df
    faixas = ["ate_500", "500_2k", "2k_10k", "10k_50k", "acima_50k"]
    pivot = df.pivot_table(
        index="tributo", columns="faixa_valor", values="count_cdas", fill_value=0
    )
    cols = [c for c in faixas if c in pivot.columns]
    return pivot[cols].reset_index()


# ── Aba 3 — Scoring ───────────────────────────────────────────────────────────

def distribuicao_quadrantes(
    carteira_id: int,
    sessao_id: int,
    thr_prioridade: int = 40,
    thr_recuperab: int = 30,
) -> pd.DataFrame:
    """Distribuição de CDAs pelos 4 quadrantes, calculada dinamicamente pelos thresholds.

    Retorna: quadrante, valor_cents, count_contrib, count_cdas, pct_valor.
    """
    sql = """
        WITH classificados AS (
            SELECT
                h.valor_corrigido_cents,
                b.contribuinte_id,
                CASE
                    WHEN s.eixo_prioridade >= %(thr_pri)s
                     AND s.eixo_recuperabilidade >= %(thr_rec)s THEN 'Q1'
                    WHEN s.eixo_prioridade < %(thr_pri)s
                     AND s.eixo_recuperabilidade >= %(thr_rec)s THEN 'Q2'
                    WHEN s.eixo_prioridade >= %(thr_pri)s
                     AND s.eixo_recuperabilidade < %(thr_rec)s  THEN 'Q3'
                    ELSE 'Q4'
                END AS quadrante
            FROM vega.scores s
            JOIN vega.cdas_higienizadas h ON h.id = s.cda_higienizada_id
            JOIN vega.cdas_brutas b ON b.id = h.cda_bruta_id
            WHERE s.carteira_id = %(carteira_id)s
              AND s.sessao_id   = %(sessao_id)s
        ),
        total_valor AS (
            SELECT SUM(valor_corrigido_cents) AS total_cents FROM classificados
        )
        SELECT
            c.quadrante,
            SUM(c.valor_corrigido_cents)                    AS valor_cents,
            COUNT(DISTINCT c.contribuinte_id)               AS count_contrib,
            COUNT(*)                                        AS count_cdas,
            ROUND(
                SUM(c.valor_corrigido_cents)::NUMERIC
                / NULLIF(t.total_cents, 0) * 100, 1
            )                                               AS pct_valor
        FROM classificados c
        CROSS JOIN total_valor t
        GROUP BY c.quadrante, t.total_cents
        ORDER BY c.quadrante
    """
    with get_conn() as conn:
        return pd.read_sql(
            sql,
            conn,
            params={
                "carteira_id": carteira_id,
                "sessao_id":   sessao_id,
                "thr_pri":     thr_prioridade,
                "thr_rec":     thr_recuperab,
            },
        )


def distribuicao_prioridade(carteira_id: int, sessao_id: int) -> pd.DataFrame:
    """Histograma de Score Prioridade em 12 bins de 5 pts (0–60).

    Retorna: bin_min, bin_label, count_cdas.
    """
    sql = """
        SELECT
            (eixo_prioridade / 5) * 5       AS bin_min,
            COUNT(*)                        AS count_cdas
        FROM vega.scores
        WHERE carteira_id = %(carteira_id)s
          AND sessao_id   = %(sessao_id)s
        GROUP BY bin_min
        ORDER BY bin_min
    """
    with get_conn() as conn:
        df = pd.read_sql(sql, conn, params={"carteira_id": carteira_id, "sessao_id": sessao_id})
    df["bin_label"] = df["bin_min"].apply(lambda x: f"{x}–{x + 5}")
    return df


def distribuicao_recuperabilidade(carteira_id: int, sessao_id: int) -> pd.DataFrame:
    """Histograma de Score Recuperabilidade em 10 bins de 5 pts (0–50).

    Retorna: bin_min, bin_label, count_cdas.
    """
    sql = """
        SELECT
            (eixo_recuperabilidade / 5) * 5 AS bin_min,
            COUNT(*)                        AS count_cdas
        FROM vega.scores
        WHERE carteira_id = %(carteira_id)s
          AND sessao_id   = %(sessao_id)s
        GROUP BY bin_min
        ORDER BY bin_min
    """
    with get_conn() as conn:
        df = pd.read_sql(sql, conn, params={"carteira_id": carteira_id, "sessao_id": sessao_id})
    df["bin_label"] = df["bin_min"].apply(lambda x: f"{x}–{x + 5}")
    return df


# ── Aba 4 — Safra & Aging ─────────────────────────────────────────────────────

def metricas_safra(carteira_id: int) -> pd.DataFrame:
    """KPIs da Aba 4: safras analisadas, melhor safra, prescrição bruta/líquida, idade média.

    Retorna uma única linha com: safras_analisadas, melhor_safra,
    prescricao_bruta_cents, prescricao_liquida_cents,
    idade_media_ponderada, mediana_idade.
    """
    sql = """
        WITH ativas AS (
            SELECT
                h.valor_corrigido_cents,
                h.safra,
                h.dias_para_prescricao,
                h.prescricao_interrompida,
                EXTRACT(EPOCH FROM (CURRENT_DATE - b.data_inscricao))
                    / 86400.0 / 365.25                       AS idade_anos
            FROM vega.cdas_higienizadas h
            JOIN vega.cdas_brutas b ON b.id = h.cda_bruta_id
            WHERE h.carteira_id = %(carteira_id)s
              AND h.ativa = TRUE
        ),
        melhor_safra_cte AS (
            SELECT safra
            FROM vega.historico_safra
            WHERE carteira_id = %(carteira_id)s
            GROUP BY safra
            ORDER BY MAX(taxa_recuperacao_pct) DESC
            LIMIT 1
        )
        SELECT
            COUNT(DISTINCT a.safra)                                        AS safras_analisadas,
            (SELECT safra FROM melhor_safra_cte)                           AS melhor_safra,
            SUM(CASE WHEN a.dias_para_prescricao <= 365
                 THEN a.valor_corrigido_cents ELSE 0 END)                  AS prescricao_bruta_cents,
            SUM(CASE WHEN a.dias_para_prescricao <= 365
                      AND a.prescricao_interrompida = FALSE
                 THEN a.valor_corrigido_cents ELSE 0 END)                  AS prescricao_liquida_cents,
            ROUND(
                SUM(a.valor_corrigido_cents * a.idade_anos)::NUMERIC
                / NULLIF(SUM(a.valor_corrigido_cents), 0),
                1
            )                                                              AS idade_media_ponderada,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY a.idade_anos)     AS mediana_idade
        FROM ativas a
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


def vintage_por_safra(carteira_id: int) -> pd.DataFrame:
    """Valor inscrito e taxa de recuperação por safra (duplo eixo Y).

    Retorna: safra, valor_inscrito_cents, taxa_recuperacao_pct.
    taxa_recuperacao_pct = taxa máxima registrada em historico_safra para cada safra.
    """
    sql = """
        WITH valor_por_safra AS (
            SELECT
                h.safra,
                SUM(h.valor_corrigido_cents)  AS valor_inscrito_cents
            FROM vega.cdas_higienizadas h
            WHERE h.carteira_id = %(carteira_id)s
              AND h.ativa = TRUE
              AND h.safra IS NOT NULL
            GROUP BY h.safra
        ),
        taxa_por_safra AS (
            SELECT
                safra,
                MAX(taxa_recuperacao_pct)     AS taxa_recuperacao_pct
            FROM vega.historico_safra
            WHERE carteira_id = %(carteira_id)s
            GROUP BY safra
        )
        SELECT
            v.safra,
            v.valor_inscrito_cents,
            COALESCE(t.taxa_recuperacao_pct, 0) AS taxa_recuperacao_pct
        FROM valor_por_safra v
        LEFT JOIN taxa_por_safra t ON t.safra = v.safra
        ORDER BY v.safra
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


def aging_por_faixa(carteira_id: int) -> pd.DataFrame:
    """Valor ativo por faixa etária, separado em normal × prescrição interrompida.

    Retorna: faixa_idade, valor_normal_cents, valor_interrompido_cents.
    """
    sql = """
        SELECT
            h.faixa_idade,
            SUM(CASE WHEN h.prescricao_interrompida = FALSE OR h.prescricao_interrompida IS NULL
                 THEN h.valor_corrigido_cents ELSE 0 END) AS valor_normal_cents,
            SUM(CASE WHEN h.prescricao_interrompida = TRUE
                 THEN h.valor_corrigido_cents ELSE 0 END) AS valor_interrompido_cents
        FROM vega.cdas_higienizadas h
        WHERE h.carteira_id = %(carteira_id)s
          AND h.ativa = TRUE
          AND h.faixa_idade IS NOT NULL
        GROUP BY h.faixa_idade
        ORDER BY
            CASE h.faixa_idade
                WHEN 'lt_6m'  THEN 1
                WHEN '6m_1a'  THEN 2
                WHEN '1a_2a'  THEN 3
                WHEN '2a_3a'  THEN 4
                WHEN '3a_4a'  THEN 5
                WHEN '4a_5a'  THEN 6
                ELSE 9
            END
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


def decay_por_safra(carteira_id: int) -> pd.DataFrame:
    """Curva de decay: taxa acumulada de recuperação por safra × meses desde inscrição.

    Retorna: safra, meses_desde_inscricao, taxa_recuperacao_pct.
    Retorna DataFrame vazio se historico_safra não tiver dados para esta carteira.
    """
    sql = """
        SELECT
            safra,
            meses_desde_inscricao,
            taxa_recuperacao_pct
        FROM vega.historico_safra
        WHERE carteira_id = %(carteira_id)s
        ORDER BY safra, meses_desde_inscricao
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


def sazonalidade(carteira_id: int) -> pd.DataFrame:
    """Média de CDAs inscritas e recuperadas por mês do ano (1–12).

    Retorna: mes, media_inscritas, media_recuperadas.
    """
    sql = """
        WITH inscricoes AS (
            SELECT
                EXTRACT(MONTH FROM b.data_inscricao)::INT   AS mes,
                COUNT(*)                                    AS total_inscritas,
                COUNT(DISTINCT
                    EXTRACT(YEAR FROM b.data_inscricao))    AS anos_distintos
            FROM vega.cdas_brutas b
            WHERE b.carteira_id = %(carteira_id)s
            GROUP BY EXTRACT(MONTH FROM b.data_inscricao)
        ),
        recuperacoes AS (
            SELECT
                EXTRACT(MONTH FROM f.ano_mes)::INT          AS mes,
                SUM(f.cdas_recuperadas)                     AS total_recuperadas,
                COUNT(*)                                    AS meses_count
            FROM vega.fluxo_mensal f
            WHERE f.carteira_id = %(carteira_id)s
            GROUP BY EXTRACT(MONTH FROM f.ano_mes)
        )
        SELECT
            i.mes,
            ROUND(i.total_inscritas::NUMERIC
                  / NULLIF(i.anos_distintos, 0), 1)         AS media_inscritas,
            COALESCE(
                ROUND(r.total_recuperadas::NUMERIC
                      / NULLIF(r.meses_count, 0), 1),
                0
            )                                               AS media_recuperadas
        FROM inscricoes i
        LEFT JOIN recuperacoes r ON r.mes = i.mes
        ORDER BY i.mes
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


# ── Aba 5 — Contactabilidade ──────────────────────────────────────────────────

def metricas_contactabilidade(carteira_id: int) -> pd.DataFrame:
    """KPIs da Aba 5: distribuição de contactabilidade e valor incontactável.

    Retorna uma linha com: pct_contactaveis, pct_so_endereco,
    pct_incontactaveis, valor_incontactavel_cents.
    """
    sql = """
        WITH ativas AS (
            SELECT
                h.valor_corrigido_cents,
                CASE
                    WHEN b.celular    IS NOT NULL
                      OR b.whatsapp   IS NOT NULL
                      OR b.email      IS NOT NULL
                      OR b.telefone   IS NOT NULL THEN 'contactavel'
                    WHEN b.logradouro IS NOT NULL  THEN 'so_endereco'
                    ELSE                                'incontactavel'
                END AS nivel
            FROM vega.cdas_higienizadas h
            JOIN vega.cdas_brutas b ON b.id = h.cda_bruta_id
            WHERE h.carteira_id = %(carteira_id)s
              AND h.ativa = TRUE
        ),
        totais AS (
            SELECT
                COUNT(*)                                                    AS n,
                SUM(CASE WHEN nivel = 'incontactavel'
                         THEN valor_corrigido_cents ELSE 0 END)             AS valor_incontactavel_cents
            FROM ativas
        )
        SELECT
            ROUND(100.0 * COUNT(*) FILTER (WHERE a.nivel = 'contactavel')
                  / NULLIF(t.n, 0), 1)                                      AS pct_contactaveis,
            ROUND(100.0 * COUNT(*) FILTER (WHERE a.nivel = 'so_endereco')
                  / NULLIF(t.n, 0), 1)                                      AS pct_so_endereco,
            ROUND(100.0 * COUNT(*) FILTER (WHERE a.nivel = 'incontactavel')
                  / NULLIF(t.n, 0), 1)                                      AS pct_incontactaveis,
            t.valor_incontactavel_cents
        FROM ativas a
        CROSS JOIN totais t
        GROUP BY t.n, t.valor_incontactavel_cents
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


def cobertura_por_canal(carteira_id: int) -> pd.DataFrame:
    """Cobertura de contacto por canal nas CDAs ativas.

    Retorna: canal, pct_cobertura (5 linhas: celular, whatsapp, email, telefone, endereco).
    """
    sql = """
        WITH ativas AS (
            SELECT
                (b.celular    IS NOT NULL)::INT AS tem_celular,
                (b.whatsapp   IS NOT NULL)::INT AS tem_whatsapp,
                (b.email      IS NOT NULL)::INT AS tem_email,
                (b.telefone   IS NOT NULL)::INT AS tem_telefone,
                (b.logradouro IS NOT NULL)::INT AS tem_endereco
            FROM vega.cdas_higienizadas h
            JOIN vega.cdas_brutas b ON b.id = h.cda_bruta_id
            WHERE h.carteira_id = %(carteira_id)s
              AND h.ativa = TRUE
        ),
        agg AS (
            SELECT
                COUNT(*)          AS n,
                SUM(tem_celular)  AS n_celular,
                SUM(tem_whatsapp) AS n_whatsapp,
                SUM(tem_email)    AS n_email,
                SUM(tem_telefone) AS n_telefone,
                SUM(tem_endereco) AS n_endereco
            FROM ativas
        )
        SELECT canal, pct_cobertura
        FROM agg
        CROSS JOIN LATERAL (
            VALUES
                ('celular',  ROUND(100.0 * n_celular  / NULLIF(n, 0), 1)),
                ('whatsapp', ROUND(100.0 * n_whatsapp / NULLIF(n, 0), 1)),
                ('email',    ROUND(100.0 * n_email    / NULLIF(n, 0), 1)),
                ('telefone', ROUND(100.0 * n_telefone / NULLIF(n, 0), 1)),
                ('endereco', ROUND(100.0 * n_endereco / NULLIF(n, 0), 1))
        ) AS t(canal, pct_cobertura)
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


def contactabilidade_por_faixa(carteira_id: int) -> pd.DataFrame:
    """Valor ativo por faixa_valor × nível de contacto agrupado.

    Retorna: faixa_valor, nivel_contato_agrupado, valor_cents.
    nivel_contato_agrupado: 'digital', 'so_endereco', 'incontactavel'.
    """
    sql = """
        SELECT
            h.faixa_valor,
            CASE
                WHEN b.celular    IS NOT NULL
                  OR b.whatsapp   IS NOT NULL
                  OR b.email      IS NOT NULL
                  OR b.telefone   IS NOT NULL THEN 'digital'
                WHEN b.logradouro IS NOT NULL  THEN 'so_endereco'
                ELSE                                'incontactavel'
            END                                   AS nivel_contato_agrupado,
            SUM(h.valor_corrigido_cents)           AS valor_cents
        FROM vega.cdas_higienizadas h
        JOIN vega.cdas_brutas b ON b.id = h.cda_bruta_id
        WHERE h.carteira_id = %(carteira_id)s
          AND h.ativa = TRUE
          AND h.faixa_valor IS NOT NULL
        GROUP BY h.faixa_valor, nivel_contato_agrupado
        ORDER BY
            CASE h.faixa_valor
                WHEN 'ate_500'   THEN 1
                WHEN '500_2k'    THEN 2
                WHEN '2k_10k'    THEN 3
                WHEN '10k_50k'   THEN 4
                WHEN 'acima_50k' THEN 5
                ELSE 9
            END,
            nivel_contato_agrupado
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


def heatmap_qualidade(carteira_id: int) -> pd.DataFrame:
    """Cobertura de contacto por canal × tributo.

    Retorna: tributo, canal, pct_cobertura.
    """
    sql = """
        WITH ativas AS (
            SELECT
                b.tributo,
                (b.celular    IS NOT NULL)::INT AS tem_celular,
                (b.whatsapp   IS NOT NULL)::INT AS tem_whatsapp,
                (b.email      IS NOT NULL)::INT AS tem_email,
                (b.telefone   IS NOT NULL)::INT AS tem_telefone,
                (b.logradouro IS NOT NULL)::INT AS tem_endereco
            FROM vega.cdas_higienizadas h
            JOIN vega.cdas_brutas b ON b.id = h.cda_bruta_id
            WHERE h.carteira_id = %(carteira_id)s
              AND h.ativa = TRUE
        ),
        agg AS (
            SELECT
                tributo,
                COUNT(*)          AS n,
                SUM(tem_celular)  AS n_celular,
                SUM(tem_whatsapp) AS n_whatsapp,
                SUM(tem_email)    AS n_email,
                SUM(tem_telefone) AS n_telefone,
                SUM(tem_endereco) AS n_endereco
            FROM ativas
            GROUP BY tributo
        )
        SELECT tributo, canal, pct_cobertura
        FROM agg
        CROSS JOIN LATERAL (
            VALUES
                ('celular',  ROUND(100.0 * n_celular  / NULLIF(n, 0), 1)),
                ('whatsapp', ROUND(100.0 * n_whatsapp / NULLIF(n, 0), 1)),
                ('email',    ROUND(100.0 * n_email    / NULLIF(n, 0), 1)),
                ('telefone', ROUND(100.0 * n_telefone / NULLIF(n, 0), 1)),
                ('endereco', ROUND(100.0 * n_endereco / NULLIF(n, 0), 1))
        ) AS t(canal, pct_cobertura)
        ORDER BY tributo, canal
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


# ── Aba 6 — Histórico ─────────────────────────────────────────────────────────

def metricas_historico(carteira_id: int) -> pd.DataFrame:
    """KPIs da Aba 6: reincidência e quebra de parcelamento.

    Retorna uma linha com: pct_reincidentes, valor_reincidentes_cents,
    taxa_quebra_media, parcela_media_quebra.

    Reincidente = CDA com data_parcelamento registrado (proxy: já voltou à carteira).
    taxa_quebra_media e parcela_media_quebra derivados de cohorts_campanha.
    """
    sql = """
        WITH ativas AS (
            SELECT
                h.valor_corrigido_cents,
                (b.data_parcelamento IS NOT NULL) AS reincidente
            FROM vega.cdas_higienizadas h
            JOIN vega.cdas_brutas b ON b.id = h.cda_bruta_id
            WHERE h.carteira_id = %(carteira_id)s
              AND h.ativa = TRUE
        ),
        totais AS (
            SELECT
                COUNT(*)                                                    AS n,
                COUNT(*) FILTER (WHERE reincidente)                         AS n_reincid,
                SUM(valor_corrigido_cents) FILTER (WHERE reincidente)       AS v_reincid
            FROM ativas
        ),
        quebras AS (
            SELECT
                COALESCE(
                    ROUND(AVG(quebraram::FLOAT / NULLIF(aderiram, 0)) * 100, 1),
                    0
                )                                       AS taxa_quebra_media,
                COALESCE(
                    ROUND(AVG(parcelas_maximas::FLOAT / 2.0), 1),
                    0
                )                                       AS parcela_media_quebra
            FROM vega.cohorts_campanha
            WHERE carteira_id = %(carteira_id)s
              AND quebraram > 0
        )
        SELECT
            ROUND(100.0 * t.n_reincid / NULLIF(t.n, 0), 1)  AS pct_reincidentes,
            COALESCE(t.v_reincid, 0)                          AS valor_reincidentes_cents,
            q.taxa_quebra_media,
            q.parcela_media_quebra
        FROM totais t
        CROSS JOIN quebras q
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


def reincidencia_por_tipo(carteira_id: int) -> pd.DataFrame:
    """Valor ativo por tipo de comportamento do devedor.

    Retorna: tipo, valor_cents.
    Tipos: reincidente_pagador, so_parcelou, primeiro_debito.
    """
    sql = """
        SELECT
            CASE
                WHEN b.data_parcelamento IS NOT NULL
                 AND b.data_protesto     IS NOT NULL THEN 'reincidente_pagador'
                WHEN b.data_parcelamento IS NOT NULL
                 AND b.data_protesto     IS NULL     THEN 'so_parcelou'
                ELSE                                      'primeiro_debito'
            END                           AS tipo,
            SUM(h.valor_corrigido_cents)  AS valor_cents
        FROM vega.cdas_higienizadas h
        JOIN vega.cdas_brutas b ON b.id = h.cda_bruta_id
        WHERE h.carteira_id = %(carteira_id)s
          AND h.ativa = TRUE
        GROUP BY tipo
        ORDER BY tipo
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


def sobrevivencia_parcelamento(carteira_id: int) -> list[float]:
    """% de parcelamentos ainda ativos por parcela (1ª a 12ª).

    Aproximado a partir de cohorts_campanha: assume decay linear entre
    100% (1ª parcela) e taxa_conclusao × 100 ao longo de parcelas_maximas.
    Retorna lista de 12 floats (0–100).
    """
    sql = """
        SELECT aderiram, concluiram, quebraram,
               COALESCE(parcelas_maximas, 12) AS parcelas
        FROM vega.cohorts_campanha
        WHERE carteira_id = %(carteira_id)s
          AND aderiram > 0
    """
    with get_conn() as conn:
        df = pd.read_sql(sql, conn, params={"carteira_id": carteira_id})
    if df.empty:
        return []
    total_aderiram   = int(df["aderiram"].sum())
    total_concluiram = int(df["concluiram"].sum())
    avg_parcelas     = max(int(df["parcelas"].mean()), 1)
    taxa_conclusao   = total_concluiram / total_aderiram if total_aderiram > 0 else 0
    resultado = []
    for i in range(1, 13):
        if i <= avg_parcelas:
            pct = 100.0 - (100.0 - taxa_conclusao * 100) * (i / avg_parcelas)
        else:
            pct = taxa_conclusao * 100
        resultado.append(round(max(pct, 0.0), 1))
    return resultado


def programas_historico(carteira_id: int) -> pd.DataFrame:
    """Histórico de programas de parcelamento.

    Retorna: nome_programa, aderiram, concluiram, quebraram, taxa_conclusao.
    """
    sql = """
        SELECT
            nome_programa,
            aderiram,
            concluiram,
            quebraram,
            ROUND(100.0 * concluiram / NULLIF(aderiram, 0), 1) AS taxa_conclusao
        FROM vega.cohorts_campanha
        WHERE carteira_id = %(carteira_id)s
        ORDER BY data_inicio DESC
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})


def concentracao_geografica(carteira_id: int, limit: int = 10) -> pd.DataFrame:
    """Top bairros por valor ativo.

    Retorna: bairro, contribuintes, valor_cents, pct_total.
    """
    sql = """
        WITH total AS (
            SELECT SUM(h.valor_corrigido_cents) AS total_cents
            FROM vega.cdas_higienizadas h
            WHERE h.carteira_id = %(carteira_id)s
              AND h.ativa = TRUE
        )
        SELECT
            COALESCE(b.bairro, 'Não informado')      AS bairro,
            COUNT(DISTINCT b.contribuinte_id)         AS contribuintes,
            SUM(h.valor_corrigido_cents)              AS valor_cents,
            ROUND(
                100.0 * SUM(h.valor_corrigido_cents)
                / NULLIF(t.total_cents, 0),
                1
            )                                         AS pct_total
        FROM vega.cdas_higienizadas h
        JOIN vega.cdas_brutas b ON b.id = h.cda_bruta_id
        CROSS JOIN total t
        WHERE h.carteira_id = %(carteira_id)s
          AND h.ativa = TRUE
        GROUP BY b.bairro, t.total_cents
        ORDER BY valor_cents DESC
        LIMIT %(limit)s
    """
    with get_conn() as conn:
        return pd.read_sql(
            sql, conn, params={"carteira_id": carteira_id, "limit": limit}
        )


# ── Aba 7 — Cenários ──────────────────────────────────────────────────────────

def base_cenarios(carteira_id: int, sessao_id: int) -> pd.DataFrame:
    """Base para os 3 cenários da Aba 7: Q1/Q2/Q3 por valor e contribuintes.

    Usa o campo quadrante já gravado em vega.scores (calculado no scoring).
    Retorna: quadrante, count_contrib, valor_cents (apenas Q1, Q2, Q3).
    Q4 é excluído — não faz parte de nenhum cenário de ação.
    """
    sql = """
        SELECT
            s.quadrante,
            COUNT(DISTINCT b.contribuinte_id)   AS count_contrib,
            SUM(h.valor_corrigido_cents)         AS valor_cents
        FROM vega.scores s
        JOIN vega.cdas_higienizadas h ON h.id = s.cda_higienizada_id
        JOIN vega.cdas_brutas b       ON b.id = h.cda_bruta_id
        WHERE s.carteira_id = %(carteira_id)s
          AND s.sessao_id   = %(sessao_id)s
          AND s.quadrante   IN ('Q1', 'Q2', 'Q3')
        GROUP BY s.quadrante
        ORDER BY s.quadrante
    """
    with get_conn() as conn:
        return pd.read_sql(
            sql, conn,
            params={"carteira_id": carteira_id, "sessao_id": sessao_id},
        )


def cohort_campanha(carteira_id: int) -> pd.DataFrame:
    """Todos os cohorts de campanha de uma carteira.

    Retorna campos relevantes de vega.cohorts_campanha.
    """
    sql = """
        SELECT
            nome_programa,
            tipo_programa,
            data_inicio,
            data_encerramento,
            condicoes_desconto_pct,
            parcelas_maximas,
            aderiram,
            concluiram,
            quebraram,
            voltaram_carteira,
            reabordados_sucesso,
            perfil_dominante,
            observacoes
        FROM vega.cohorts_campanha
        WHERE carteira_id = %(carteira_id)s
        ORDER BY data_inicio DESC
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})
