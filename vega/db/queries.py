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
