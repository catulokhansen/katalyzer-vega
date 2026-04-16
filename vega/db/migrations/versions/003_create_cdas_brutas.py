"""create vega.cdas_brutas

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-16

"""
from alembic import op


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE vega.cdas_brutas (
          id                    BIGSERIAL PRIMARY KEY,
          carteira_id           BIGINT NOT NULL REFERENCES vega.carteiras(id),
          tenant_id             VARCHAR(120) NOT NULL,
          numero_cda            VARCHAR(100) NOT NULL,
          contribuinte_id       VARCHAR(100) NOT NULL,
          contribuinte_nome     VARCHAR(500),
          contribuinte_tipo     CHAR(2),
          tributo               VARCHAR(50) NOT NULL,
          valor_principal_cents BIGINT NOT NULL,
          valor_juros_cents     BIGINT NOT NULL DEFAULT 0,
          valor_multa_cents     BIGINT NOT NULL DEFAULT 0,
          valor_total_cents     BIGINT NOT NULL,
          data_inscricao        DATE NOT NULL,
          data_vencimento       DATE,
          exercicio             INTEGER,
          logradouro            VARCHAR(500),
          bairro                VARCHAR(200),
          municipio             VARCHAR(200),
          uf                    CHAR(2),
          cep                   VARCHAR(10),
          telefone              VARCHAR(20),
          celular               VARCHAR(20),
          whatsapp              VARCHAR(20),
          email                 VARCHAR(200),
          status_da             VARCHAR(50),
          data_parcelamento     DATE,
          data_protesto         DATE,
          raw_jsonb             JSONB,
          created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX ON vega.cdas_brutas (carteira_id, numero_cda) "
        "WHERE carteira_id IS NOT NULL;"
    )
    op.execute("CREATE INDEX ON vega.cdas_brutas (carteira_id, contribuinte_id);")
    op.execute("CREATE INDEX ON vega.cdas_brutas (carteira_id, tributo);")
    op.execute("CREATE INDEX ON vega.cdas_brutas (carteira_id, data_inscricao);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vega.cdas_brutas;")
