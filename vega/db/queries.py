"""Queries analíticas do Vega.

Padrão único: SQL puro + pandas.read_sql.

    import pandas as pd
    from vega.db.connection import get_conn

    def metricas_diagnostico(carteira_id: int) -> pd.DataFrame:
        sql = '''
            SELECT ativa, causa_eliminacao,
                   SUM(valor_corrigido_cents) AS valor_cents,
                   COUNT(*) AS total_cdas
            FROM vega.cdas_higienizadas
            WHERE carteira_id = %(carteira_id)s
            GROUP BY ativa, causa_eliminacao
        '''
        with get_conn() as conn:
            return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})

Regras (CLAUDE_Vega.md):
    - Toda query filtra por carteira_id, sem exceção.
    - Queries de scoring filtram também por sessao_id.
    - Sem SQLAlchemy. Sem ORM.
    - Valores monetários permanecem em centavos (bigint) — formatação só em utils/formatters.
"""
