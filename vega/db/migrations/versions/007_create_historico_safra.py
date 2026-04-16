"""create vega.historico_safra

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-16

"""
from alembic import op


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE vega.historico_safra (
          id                        BIGSERIAL PRIMARY KEY,
          carteira_id               BIGINT NOT NULL REFERENCES vega.carteiras(id),
          tenant_id                 VARCHAR(120) NOT NULL,
          safra                     INTEGER NOT NULL,
          meses_desde_inscricao     INTEGER NOT NULL,
          taxa_recuperacao_pct      NUMERIC(6,2) NOT NULL,
          valor_inscrito_cents      BIGINT,
          valor_recuperado_cents    BIGINT,
          fonte_dados               VARCHAR(30) NOT NULL DEFAULT 'calculado',
          created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX ON vega.historico_safra "
        "(carteira_id, safra, meses_desde_inscricao);"
    )
    op.execute("CREATE INDEX ON vega.historico_safra (carteira_id, safra);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vega.historico_safra;")
