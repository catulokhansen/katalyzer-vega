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
