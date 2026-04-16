"""create vega.cohorts_campanha

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-16

"""
from alembic import op


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE vega.cohorts_campanha (
          id                        BIGSERIAL PRIMARY KEY,
          carteira_id               BIGINT NOT NULL REFERENCES vega.carteiras(id),
          tenant_id                 VARCHAR(120) NOT NULL,
          nome_programa             VARCHAR(200) NOT NULL,
          tipo_programa             VARCHAR(30),
          data_inicio               DATE,
          data_encerramento         DATE,
          condicoes_desconto_pct    INTEGER,
          parcelas_maximas          INTEGER,
          aderiram                  INTEGER NOT NULL DEFAULT 0,
          concluiram                INTEGER NOT NULL DEFAULT 0,
          quebraram                 INTEGER NOT NULL DEFAULT 0,
          voltaram_carteira         INTEGER NOT NULL DEFAULT 0,
          reabordados_sucesso       INTEGER NOT NULL DEFAULT 0,
          perfil_dominante          VARCHAR(30),
          observacoes               TEXT,
          fonte_dados               VARCHAR(30) NOT NULL DEFAULT 'manual',
          created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at                TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ON vega.cohorts_campanha (carteira_id);")
    op.execute("CREATE INDEX ON vega.cohorts_campanha (tenant_id, data_inicio);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vega.cohorts_campanha;")
