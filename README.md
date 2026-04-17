# Katalyzer Vega

Ferramenta interna de análise de carteira de dívida ativa municipal.
Backoffice — não é acessada pelo cliente municipal.

> Para o que é, stack, regras de negócio, padrões de código e o que **não** fazer:
> ler `CLAUDE_Vega.md` antes de qualquer alteração.

---

## Stack

Python 3.11+ · Dash (Plotly) · PostgreSQL 15+ (schema `vega`) ·
psycopg2 + pandas · Alembic · Docker Compose · OpenAI (gpt-4o)

**Sem SQLAlchemy.** SQL puro em `vega/db/queries.py` via `pd.read_sql()`.

---

## Como rodar — desenvolvimento local

```bash
# 1. Virtualenv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Variáveis de ambiente
cp .env.example .env
# Preencher DATABASE_URL, SECRET_KEY e OPENAI_API_KEY

# 3. PostgreSQL via Docker
docker compose up -d postgres

# 4. Migrations
alembic upgrade head

# 5. App
python -m vega.app.app
# → http://localhost:8050
```

## Como rodar — Docker completo

```bash
cp .env.example .env
docker compose up
# Postgres em :5432, Vega em :8050
```

Rodar as migrations dentro do container do app:

```bash
docker compose exec app alembic upgrade head
```

---

## Migrations

```bash
alembic revision -m "descricao"   # nova migration
alembic upgrade head              # aplicar
alembic downgrade -1              # rollback
```

As migrations vivem em `vega/db/migrations/versions/`, numeradas `001` a `009`,
encadeadas via `down_revision`.
O schema `vega` é criado automaticamente pelo `env.py` (ou via
`scripts/init_schema.sql` quando o Postgres sobe pela primeira vez no Docker).

---

## Rodando com dados reais

Por padrão o app sobe em `DEMO_MODE=true` com fixtures estáticos.
Para usar o banco PostgreSQL real:

**1. Garanta que o banco está rodando e as migrations aplicadas:**

```bash
# PostgreSQL via Docker
docker compose up -d postgres
alembic upgrade head

# Ou PostgreSQL local (snap/pacote) — confirme que está rodando:
pg_isready -h localhost -p 5432
alembic upgrade head
```

**2. Crie os dados de demonstração (Beberibe CE):**

```bash
source venv/bin/activate
python scripts/seed_demo.py
# Imprime: carteira_id=X  sessao_id=Y
```

O seed:
- Cria uma carteira (Beberibe/CE) + sessão com parâmetros default
- Carrega `tests/fixtures/carteira_teste.csv` (25 CDAs)
- Roda higienização, segmentação e scoring completos
- Popula `fluxo_mensal` (12 meses) e `cohorts_campanha` (4 programas)

**3. Troque para DEMO_MODE=false no `.env`:**

```bash
# .env
DEMO_MODE=false
DATABASE_URL=postgresql://vega:vega@localhost:5432/katalyzer_vega
OPENAI_API_KEY=sk-...   # opcional — apenas para geração de insights
```

**4. Suba o app:**

```bash
python -m vega.app.app
# → http://localhost:8050
```

O app carrega automaticamente a carteira mais recente do banco.
O badge "DEMO MODE ATIVO" some quando `DEMO_MODE=false`.

---

## Testes

```bash
pytest tests/ -v
```

---

## Estrutura

```
vega/
├── app/          # Dash — entrypoint, layout, tabs, components
├── pipeline/     # higienização, segmentação, scoring, simulação
├── ingestion/    # loader CSV/API, validators, mapping
├── db/           # connection.py, queries.py, migrations/
├── insights/     # geração via OpenAI por aba
└── utils/        # formatters, export
```

Detalhes completos em `CLAUDE_Vega.md`.
