"""create vega.fluxo_mensal

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-16

"""
from alembic import op


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE vega.fluxo_mensal (
          id                        BIGSERIAL PRIMARY KEY,
          carteira_id               BIGINT NOT NULL REFERENCES vega.carteiras(id),
          tenant_id                 VARCHAR(120) NOT NULL,
          ano_mes                   DATE NOT NULL,
          cdas_inscritas            INTEGER NOT NULL DEFAULT 0,
          cdas_recuperadas          INTEGER NOT NULL DEFAULT 0,
          valor_inscrito_cents      BIGINT NOT NULL DEFAULT 0,
          valor_recuperado_cents    BIGINT NOT NULL DEFAULT 0,
          fonte_dados               VARCHAR(30) NOT NULL DEFAULT 'calculado',
          created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE UNIQUE INDEX ON vega.fluxo_mensal (carteira_id, ano_mes);")
    op.execute("CREATE INDEX ON vega.fluxo_mensal (carteira_id, ano_mes DESC);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vega.fluxo_mensal;")
