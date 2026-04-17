"""010 — Add ceiling columns to sessoes_analise, update decay rate defaults.

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-17

Benchmarks de DA municipal (C1.1): 15-40% do valor-alvo em 12 meses com
plataforma de protesto ativa. Os novos rates são velocidade de convergência
para o ceiling (modelo exponencial), não fração restante (modelo geométrico).

| Cenário     | Rate  | Ceiling | Recuperação ~12m |
|-------------|-------|---------|------------------|
| Conservador | 0.04  | 0.22    | ~8% valor-alvo   |
| Moderado    | 0.06  | 0.32    | ~16% valor-alvo  |
| Agressivo   | 0.08  | 0.42    | ~26% valor-alvo  |
"""
from alembic import op


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE vega.sessoes_analise
          ADD COLUMN IF NOT EXISTS ceiling_conservador NUMERIC(4,3) NOT NULL DEFAULT 0.22,
          ADD COLUMN IF NOT EXISTS ceiling_moderado    NUMERIC(4,3) NOT NULL DEFAULT 0.32,
          ADD COLUMN IF NOT EXISTS ceiling_agressivo   NUMERIC(4,3) NOT NULL DEFAULT 0.42;
    """)
    op.execute("""
        ALTER TABLE vega.sessoes_analise
          ALTER COLUMN decay_rate_conservador SET DEFAULT 0.04,
          ALTER COLUMN decay_rate_moderado    SET DEFAULT 0.06,
          ALTER COLUMN decay_rate_agressivo   SET DEFAULT 0.08;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE vega.sessoes_analise
          DROP COLUMN IF EXISTS ceiling_conservador,
          DROP COLUMN IF EXISTS ceiling_moderado,
          DROP COLUMN IF EXISTS ceiling_agressivo;
    """)
    op.execute("""
        ALTER TABLE vega.sessoes_analise
          ALTER COLUMN decay_rate_conservador SET DEFAULT 0.9000,
          ALTER COLUMN decay_rate_moderado    SET DEFAULT 0.5500,
          ALTER COLUMN decay_rate_agressivo   SET DEFAULT 0.3800;
    """)
