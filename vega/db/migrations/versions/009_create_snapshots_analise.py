"""create vega.snapshots_analise

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-16

"""
from alembic import op


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE vega.snapshots_analise (
          id                    BIGSERIAL PRIMARY KEY,
          carteira_id           BIGINT NOT NULL REFERENCES vega.carteiras(id),
          sessao_id             BIGINT REFERENCES vega.sessoes_analise(id),
          tenant_id             VARCHAR(120) NOT NULL,
          titulo                VARCHAR(300),
          versao_vega           VARCHAR(10) NOT NULL DEFAULT 'v4',
          metricas_diagnostico  JSONB NOT NULL DEFAULT '{}',
          metricas_scoring      JSONB NOT NULL DEFAULT '{}',
          metricas_safra        JSONB NOT NULL DEFAULT '{}',
          metricas_contactab    JSONB NOT NULL DEFAULT '{}',
          metricas_historico    JSONB NOT NULL DEFAULT '{}',
          metricas_cenarios     JSONB NOT NULL DEFAULT '{}',
          insights_jsonb        JSONB NOT NULL DEFAULT '[]',
          parametros_snapshot   JSONB NOT NULL,
          criado_por_id         BIGINT NOT NULL,
          criado_por_nome       VARCHAR(200),
          created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ON vega.snapshots_analise (carteira_id);")
    op.execute(
        "CREATE INDEX ON vega.snapshots_analise (carteira_id, created_at DESC);"
    )
    op.execute(
        "CREATE INDEX ON vega.snapshots_analise (tenant_id, created_at DESC);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vega.snapshots_analise;")
