"""create vega.carteiras

Revision ID: 0001
Revises:
Create Date: 2026-04-16

"""
from alembic import op


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS vega;")
    op.execute(
        """
        CREATE TABLE vega.carteiras (
          id                    BIGSERIAL PRIMARY KEY,
          tenant_id             VARCHAR(120) NOT NULL,
          municipio             VARCHAR(200) NOT NULL,
          uf                    CHAR(2) NOT NULL,
          data_referencia       DATE NOT NULL,
          status_pipeline       VARCHAR(30) NOT NULL DEFAULT 'aguardando',
          etapa_atual           VARCHAR(30),
          total_cdas_brutas     INTEGER,
          total_cdas_ativas     INTEGER,
          valor_bruto_cents     BIGINT,
          valor_ativo_cents     BIGINT,
          origem                VARCHAR(20) NOT NULL DEFAULT 'csv',
          arquivo_original      VARCHAR(500),
          erro_mensagem         TEXT,
          parametros            JSONB NOT NULL DEFAULT '{}',
          carregado_por_id      BIGINT,
          created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ON vega.carteiras (tenant_id);")
    op.execute("CREATE INDEX ON vega.carteiras (tenant_id, data_referencia);")
    op.execute("CREATE INDEX ON vega.carteiras (status_pipeline);")
    op.execute("CREATE INDEX ON vega.carteiras (tenant_id, status_pipeline);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vega.carteiras;")
