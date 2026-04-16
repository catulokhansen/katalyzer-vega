"""create vega.scores

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-16

"""
from alembic import op


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE vega.scores (
          id                    BIGSERIAL PRIMARY KEY,
          carteira_id           BIGINT NOT NULL REFERENCES vega.carteiras(id),
          cda_higienizada_id    BIGINT NOT NULL REFERENCES vega.cdas_higienizadas(id),
          sessao_id             BIGINT REFERENCES vega.sessoes_analise(id),
          dim_valor             SMALLINT NOT NULL CHECK (dim_valor BETWEEN 0 AND 30),
          dim_urgencia          SMALLINT NOT NULL CHECK (dim_urgencia BETWEEN 0 AND 30),
          dim_contato           SMALLINT NOT NULL CHECK (dim_contato BETWEEN 0 AND 25),
          dim_comportamento     SMALLINT NOT NULL CHECK (dim_comportamento BETWEEN 0 AND 25),
          eixo_prioridade       SMALLINT NOT NULL,
          eixo_recuperabilidade SMALLINT NOT NULL,
          quadrante             CHAR(2) NOT NULL,
          acao_sugerida         VARCHAR(200),
          versao_score          VARCHAR(10) NOT NULL DEFAULT 'v1',
          pesos_usados          JSONB NOT NULL,
          created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ON vega.scores (carteira_id, quadrante);")
    op.execute("CREATE INDEX ON vega.scores (carteira_id, eixo_prioridade);")
    op.execute("CREATE INDEX ON vega.scores (carteira_id, eixo_recuperabilidade);")
    op.execute("CREATE UNIQUE INDEX ON vega.scores (cda_higienizada_id);")
    op.execute("CREATE INDEX ON vega.scores (carteira_id, versao_score);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vega.scores;")
