"""create vega.cdas_higienizadas

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-16

"""
from alembic import op


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE vega.cdas_higienizadas (
          id                         BIGSERIAL PRIMARY KEY,
          carteira_id                BIGINT NOT NULL REFERENCES vega.carteiras(id),
          cda_bruta_id               BIGINT NOT NULL REFERENCES vega.cdas_brutas(id),
          sessao_id                  BIGINT REFERENCES vega.sessoes_analise(id),
          ativa                      BOOLEAN NOT NULL,
          causa_eliminacao           VARCHAR(30),
          data_prescricao_estimada   DATE NOT NULL,
          dias_para_prescricao       INTEGER NOT NULL,
          prescricao_interrompida    BOOLEAN NOT NULL DEFAULT false,
          valor_corrigido_cents      BIGINT NOT NULL,
          faixa_valor                VARCHAR(20),
          faixa_idade                VARCHAR(20),
          safra                      INTEGER,
          padrao_densidade           VARCHAR(20),
          created_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ON vega.cdas_higienizadas (carteira_id, ativa);")
    op.execute(
        "CREATE INDEX ON vega.cdas_higienizadas (carteira_id, causa_eliminacao) "
        "WHERE causa_eliminacao IS NOT NULL;"
    )
    op.execute(
        "CREATE INDEX ON vega.cdas_higienizadas (carteira_id, prescricao_interrompida);"
    )
    op.execute("CREATE INDEX ON vega.cdas_higienizadas (carteira_id, safra);")
    op.execute("CREATE INDEX ON vega.cdas_higienizadas (carteira_id, faixa_valor);")
    op.execute("CREATE INDEX ON vega.cdas_higienizadas (cda_bruta_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vega.cdas_higienizadas;")
