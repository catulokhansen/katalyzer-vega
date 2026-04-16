"""create vega.sessoes_analise

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-16

"""
from alembic import op


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE vega.sessoes_analise (
          id                         BIGSERIAL PRIMARY KEY,
          carteira_id                BIGINT NOT NULL REFERENCES vega.carteiras(id),
          usuario_id                 BIGINT NOT NULL,
          usuario_nome               VARCHAR(200),
          valor_minimo_cents         INTEGER NOT NULL DEFAULT 5000,
          prazo_prescricao_anos      INTEGER NOT NULL DEFAULT 5,
          peso_dim_valor             INTEGER NOT NULL DEFAULT 30,
          peso_dim_urgencia          INTEGER NOT NULL DEFAULT 30,
          threshold_q1_prioridade    INTEGER NOT NULL DEFAULT 40,
          threshold_q1_recuperab     INTEGER NOT NULL DEFAULT 30,
          decay_rate_conservador     NUMERIC(6,4) NOT NULL DEFAULT 0.9000,
          decay_rate_moderado        NUMERIC(6,4) NOT NULL DEFAULT 0.5500,
          decay_rate_agressivo       NUMERIC(6,4) NOT NULL DEFAULT 0.3800,
          desconto_otimo_pct         INTEGER NOT NULL DEFAULT 25,
          decay_calibrado            BOOLEAN NOT NULL DEFAULT false,
          parametros_extras          JSONB NOT NULL DEFAULT '{}',
          ultima_atividade_em        TIMESTAMPTZ,
          created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ON vega.sessoes_analise (carteira_id);")
    op.execute("CREATE INDEX ON vega.sessoes_analise (usuario_id);")
    op.execute("CREATE INDEX ON vega.sessoes_analise (carteira_id, usuario_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vega.sessoes_analise;")
