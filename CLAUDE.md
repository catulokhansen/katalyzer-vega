# CLAUDE.md — Katalyzer Vega

**Leia este arquivo no início de cada sessão antes de qualquer código.**

---

## O que é este projeto

O Katalyzer Vega é uma ferramenta interna de análise de carteira de dívida ativa municipal. Opera no backoffice da Katalyzer Tecnologia. O cliente municipal nunca acessa esta ferramenta — ela é usada pelo time de dados para diagnosticar carteiras antes de estruturar operações de recuperação.

**Não confundir com o Katalyzer Órion** (sistema de cobrança em produção, Rails 8 + React 19). O Vega é um sistema completamente separado: banco de dados próprio, deploy independente, sem compartilhamento de schemas ou FKs com o Órion.

---

## Stack

```
Python 3.11+
Dash (Plotly) 2.x         — dashboard e UI
PostgreSQL 15+             — banco de dados próprio (schema: vega)
psycopg2 + pandas          — acesso ao banco via SQL puro + read_sql()
Alembic                    — migrations de schema (sem ORM)
Docker + Docker Compose    — containerização
Railway ou Render          — deploy cloud
OpenAI (gpt-4o)            — geração de insights cruzados via botão por aba
```

**Não usar SQLAlchemy.** O time escreve SQL diretamente. Toda query fica em `db/queries.py` usando `pd.read_sql(sql, conn, params={...})`. Alembic é usado apenas para gerenciar migrations — não como ORM.

---

## Estrutura de pastas

```
katalyzer-vega/
├── vega/
│   ├── app/
│   │   ├── app.py                # Entry point Dash — server = app.server
│   │   ├── layout.py             # Layout global: sidebar + tabs
│   │   ├── tabs/
│   │   │   ├── tab_diagnostico.py
│   │   │   ├── tab_segmentacao.py
│   │   │   ├── tab_scoring.py
│   │   │   ├── tab_safra_aging.py
│   │   │   ├── tab_contactabilidade.py
│   │   │   ├── tab_historico.py
│   │   │   └── tab_cenarios.py
│   │   └── components/
│   │       ├── charts.py         # Funções de geração de figuras Plotly
│   │       ├── tables.py         # Tabelas Dash DataTable
│   │       ├── metrics.py        # Cards de KPI
│   │       └── alerts.py         # Alertas e banners (concentração, Q1 vazio, decay)
│   ├── pipeline/
│   │   ├── higienizacao.py       # Etapa 2a — critérios de eliminação
│   │   ├── segmentacao.py        # Etapa 2b — campos derivados
│   │   ├── scoring.py            # Etapa 3 — Score v1 determinístico
│   │   └── simulacao.py          # Etapa 4 — curvas de decay e elasticidade
│   ├── ingestion/
│   │   ├── loader.py             # Carregamento CSV e API
│   │   ├── validators.py         # Validação de schema do CSV
│   │   └── column_mapping.py     # Mapeamento de nomes de coluna
│   ├── db/
│   │   ├── connection.py         # get_conn() — psycopg2 connection pool
│   │   ├── migrations/           # Alembic — numeradas 001_ a 009_
│   │   └── queries.py            # Queries analíticas por aba — SQL puro + pd.read_sql
│   ├── insights/
│   │   └── generator.py          # Chamada OpenAI para geração de insights por aba
│   └── utils/
│       ├── formatters.py         # Formatar R$, %, datas
│       └── export.py             # CSV, Parquet, DOCX
├── tests/
│   ├── pipeline/
│   │   ├── test_higienizacao.py  # 8 casos obrigatórios (Pipeline doc seção 6.1)
│   │   └── test_scoring.py       # 8 casos obrigatórios (Pipeline doc seção 6.2)
│   └── fixtures/
│       └── carteira_teste.csv    # 20+ linhas cobrindo todos os critérios
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── CLAUDE.md                     # este arquivo
```

---

## Como rodar

```bash
# Desenvolvimento local
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Preencher DATABASE_URL, SECRET_KEY e OPENAI_API_KEY no .env

docker compose up -d postgres
alembic upgrade head
python -m vega.app.app

# Com Docker completo
docker compose up

# Testes
pytest tests/ -v

# Migrations
alembic revision -m "descricao"
alembic upgrade head
alembic downgrade -1
```

---

## Variáveis de ambiente obrigatórias

```
DATABASE_URL=postgresql://vega:senha@localhost:5432/katalyzer_vega
SECRET_KEY=chave-de-sessao-longa-e-aleatoria
DEMO_MODE=true          # true = fixtures estáticos | false = PostgreSQL real
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...   # geração de insights cruzados por aba
OPENAI_MODEL=gpt-4o     # modelo padrão — trocar aqui se mudar
```

---

## Banco de dados — schema vega

9 tabelas. Documentação completa: `ModeloDados_KatalyzerVega_v1.docx`.

```
vega.carteiras           — registro de cada carteira carregada
vega.sessoes_analise     — parâmetros ativos por analista × carteira
vega.cdas_brutas         — CDAs originais — IMUTÁVEL após carga
vega.cdas_higienizadas   — resultado da higienização + campos derivados
vega.scores              — Score v1: 4 dim + 2 eixos + quadrante + NBA
vega.cohorts_campanha    — histórico de programas de parcelamento
vega.historico_safra     — taxas de recuperação por safra × meses
vega.fluxo_mensal        — entradas e recuperações mensais
vega.snapshots_analise   — snapshots de análises finalizadas (append-only)
```

**Convenções obrigatórias:**
- Toda query filtra por `carteira_id` — sem exceção
- Queries de scoring também filtram por `sessao_id`
- Valores monetários em centavos (bigint) — dividir por 100 para exibição
- `cdas_brutas` é imutável — reprocessamento cria novos registros em `cdas_higienizadas`

---

## Padrão de acesso ao banco

```python
# db/connection.py
import psycopg2
import os

def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])

# db/queries.py
import pandas as pd
from vega.db.connection import get_conn

def metricas_diagnostico(carteira_id: int) -> pd.DataFrame:
    sql = """
        SELECT ativa, causa_eliminacao,
               SUM(valor_corrigido_cents) AS valor_cents,
               COUNT(*) AS total_cdas
        FROM vega.cdas_higienizadas
        WHERE carteira_id = %(carteira_id)s
        GROUP BY ativa, causa_eliminacao
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params={"carteira_id": carteira_id})
```

Toda query analítica segue esse padrão: SQL explícito em `queries.py`, resultado como DataFrame pandas, sem ORM no meio.

---

## Padrão de geração de insights (OpenAI)

```python
# insights/generator.py
from openai import OpenAI
import os

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

def gerar_insights_diagnostico(metricas: dict) -> str:
    """
    Recebe métricas reais da carteira como dict,
    retorna texto de insights em linguagem natural.
    """
    prompt = f"""
    Você é um analista sênior de carteiras de dívida ativa municipal.
    Analise os dados abaixo e gere 4 insights acionáveis e diretos.
    Cada insight deve ter: título curto + descrição com os números reais + ação recomendada.

    Dados da carteira:
    {metricas}
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
    )
    return response.choices[0].message.content
```

**Regras para os prompts de insights:**
- Sempre passar os números reais da carteira — nunca textos genéricos
- Cada aba tem seu próprio prompt focado nas métricas daquela aba
- O texto retornado é renderizado em cards com badge "IA" (violet) para distinguir dos alertas determinísticos
- Nunca usar a LLM para calcular valores financeiros — só para interpretar métricas já calculadas

---

## Regras de negócio críticas — NÃO ALTERAR sem alinhamento

**RN-01 — Urgência monotônica crescente**
`dim_urgencia = round((dias_decorridos / dias_totais_prescricao) * peso)`. Nunca usar função triangular com pico intermediário. CDAs próximas da prescrição têm score máximo — isso é intencional.

**RN-02 — Thresholds de Q1 são absolutos**
Q1 = prioridade >= `threshold_q1_prioridade` AND recuperabilidade >= `threshold_q1_recuperab`. Nunca usar mediana como threshold. Os valores são configuráveis por sessão (defaults: 40 e 30).

**RN-03 — Prescrição bruta × líquida**
CDAs com `prescricao_interrompida=True` (status `parcelado` ou `protestado`) NÃO são eliminadas. Continuam ativas. O KPI de prescrição tem duas versões: bruto (todas que vencem em 12m) e líquido (descontadas as interrompidas).

**RN-04 — Funil decomposto por causa**
O funil de higienização exibe o estoque morto com 3 segmentos: prescrição, valor irrisório, devedor inexistente. Nunca agregar em "estoque morto" genérico.

**RN-05 — Score é índice ordinal**
Nunca exibir o score como probabilidade de pagamento. O card de rodapé da Aba 3 deve sempre exibir o aviso de índice ordinal.

**RN-06 — Decay é referência até calibração**
O card de aviso âmbar no gráfico de recuperação da Aba 7 deve ser exibido sempre que `sessoes_analise.decay_calibrado = false`. Só some quando o analista confirmar calibração com dados reais.

**RN-07 — Alerta de concentração de risco**
Se algum contribuinte representa > 10% da carteira ativa, exibir card de alerta na Aba 1 com nome do contribuinte, percentual e botão "Ver impacto nos cenários →". Esta verificação é automática — não é opcional.

**RN-08 — NBA é sugestão, não prescrição**
A coluna "Ação Sugerida" sempre com ícone `!` prefixado e badge âmbar. Sempre com nota abaixo da tabela explicando que são sugestões determinísticas. Nunca usar linguagem de obrigação.

---

## Pipeline — sequência obrigatória

```
CSV/API → Ingestão → Higienização → Segmentação → Scoring → Simulação
```

O pipeline é **idempotente**: reprocessar com os mesmos parâmetros produz o mesmo resultado.

Quando os parâmetros de higienização mudam (valor mínimo ou prazo de prescrição), o pipeline reprocessa a higienização e segmentação completas para a sessão. Exibir spinner na UI durante o reprocessamento.

---

## Score v1 — deve ser idêntico ao Órion Rails

O `ScorerV1` em `pipeline/scoring.py` deve produzir exatamente os mesmos resultados que a engine Score do Katalyzer Órion (Ruby). Se encontrar divergência: **pare e reporte ao tech lead antes de corrigir.**

```python
# Referência rápida das faixas de dim_valor (peso default 30):
# até R$500  → 5 pts  | R$500–2k  → 12 pts | R$2k–10k  → 20 pts
# R$10k–50k  → 26 pts | >R$50k    → 30 pts

# dim_urgencia = monotônica:
# ratio = min(dias_decorridos / dias_totais, 1.0)
# score = round(ratio * peso)

# dim_contato (peso default 25):
# digital_completo=25 | digital_parcial=20 | email_apenas=14
# telefone_apenas=14  | so_endereco=8      | incontactavel=0

# dim_comportamento (proxy por status_da, peso default 25):
# reincidente_pagador=18 | so_parcelou=14 | primeiro_debito=10
```

---

## Padrões de código Python

```python
# Sempre usar type hints
def calcular_dim_valor(valor_cents: int, peso: int = 30) -> int: ...

# Docstrings em funções públicas
def higienizar(carteira_id: int, sessao_id: int) -> HigienizacaoResult:
    """
    Processa todas as CDAs brutas de uma carteira.
    Retorna métricas de resultado (ativas, eliminadas por causa).
    """

# Constantes em UPPER_SNAKE_CASE no topo do módulo
VALOR_MINIMO_DEFAULT_CENTS = 5_000
PRAZO_PRESCRICAO_DEFAULT_ANOS = 5
THRESHOLD_CONCENTRACAO_RISCO_PCT = 10.0

# Valores monetários: sempre em centavos internamente
# Converter SOMENTE na camada de formatação (utils/formatters.py)
def formatar_reais(cents: int) -> str:
    return f"R$ {cents / 100:_.2f}".replace(".", ",").replace("_", ".")
```

---

## Padrões Dash

```python
# Cada aba é um módulo em app/tabs/
# Exporta: layout (dcc.Tab content) + registrar_callbacks(app)

# Lazy loading — dados só carregados quando a aba é ativada
@app.callback(
    Output('conteudo-aba-1', 'children'),
    Input('tabs-principal', 'value'),
    State('store-carteira-id', 'data'),
    prevent_initial_call=True
)
def carregar_aba_diagnostico(tab_ativa, carteira_id):
    if tab_ativa != 'diagnostico':
        raise PreventUpdate
    # carregar dados aqui via queries.py

# Stores para estado compartilhado entre abas
# dcc.Store(id='store-carteira-id') — carteira ativa
# dcc.Store(id='store-sessao-id')   — sessão ativa
# dcc.Store(id='store-parametros')  — parâmetros da sidebar
```

---

## O que nunca fazer

- Não usar SQLAlchemy — psycopg2 + pandas direto
- Não criar FKs para schemas externos (Órion, etc.)
- Não armazenar valores monetários como float — sempre centavos (int)
- Não exibir CPF/CNPJ completo na UI — sempre mascarar: `***.000.000-**`
- Não usar score como probabilidade de pagamento em nenhuma interface
- Não remover o card de aviso de decay enquanto `decay_calibrado = false`
- Não remover o disclaimer de NBA (sugestão determinística)
- Não alterar a lógica de `dim_urgencia` para ter pico intermediário
- Não usar mediana como threshold de Q1
- Não carregar todas as abas simultaneamente no mount — lazy loading obrigatório
- Não acessar o banco PostgreSQL do Órion — o Vega tem banco próprio
- Não usar a LLM para calcular valores financeiros — só para interpretar métricas já calculadas

---

## Documentos de referência

Todos em Project Knowledge do Claude:

| Documento | Cobre |
|-----------|-------|
| `SAD_KatalyzerVega_v1.docx` | Arquitetura, stack, deploy, ADRs, 8 regras de negócio |
| `ModeloDados_KatalyzerVega_v1.docx` | 9 tabelas com DDL completo, queries por aba, LGPD |
| `Pipeline_KatalyzerVega_v1.docx` | Ingestão CSV, higienização, segmentação, scoring v1, testes |
| `PRD_KatalyzerVega_v1.docx` | Especificação funcional das 7 abas — KPIs, charts, queries |
| `katalyzer-diagnostico-workbench-v4.html` | Fonte de verdade visual — referência de layout e UX |
