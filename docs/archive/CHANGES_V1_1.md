# CHANGES_V1_1.md — Katalyzer Vega

**Versão alvo:** v1.1
**Status:** A implementar
**Origem:** análise crítica pelo cientista de dados sênior (abril 2026) + correção do custo do Q3 em operação municipal

Este documento detalha as mudanças da Categoria 1 (pré-primeiro cliente) que devem ser implementadas antes do Vega operar com dados reais. Após implementação, atualizar SAD, Pipeline, PRD, ModeloDados e CLAUDE.md para v1.1 e arquivar este documento.

---

## C1.1 — Rates de decay realistas com ceiling

### Problema

A função atual `valor_alvo * (1 - exp(-rate * n))` assume que a recuperação acumulada tende a 100% do valor-alvo em 12 meses. Na prática, benchmarks de DA municipal ficam entre 15-40% do valor-alvo em 12 meses. Os rates defaults (0.9, 0.55, 0.38) produzem cenários irreais (99%+ de recuperação) que podem ser apresentados sem crítica a gestores municipais.

### Mudança

**Onde:** `vega/pipeline/simulacao.py`

Refatorar `decay_curve` para aceitar parâmetro `ceiling` que representa a assíntota realista:

```python
def decay_curve(valor_alvo_cents: int, rate: float, ceiling: float, meses: int = 12) -> list[float]:
    """
    Gera curva de recuperação cumulativa mensal com teto (ceiling) realista.

    Args:
        valor_alvo_cents: valor total do escopo do cenário em centavos
        rate: velocidade de convergência para o ceiling
        ceiling: fração máxima do valor_alvo efetivamente recuperável (0.0 a 1.0)
        meses: horizonte de projeção (default 12)

    Retorna lista de valores em R$ (float) acumulados mês a mês.
    """
    return [
        round(valor_alvo_cents * ceiling * (1 - math.exp(-rate * m)) / 100, 2)
        for m in range(1, meses + 1)
    ]
```

**Onde:** `vega/db/migrations/versions/010_add_decay_ceiling.py`

Criar nova migration Alembic adicionando colunas `ceiling_conservador`, `ceiling_moderado`, `ceiling_agressivo` em `vega.sessoes_analise` com defaults:

```sql
ALTER TABLE vega.sessoes_analise
  ADD COLUMN ceiling_conservador NUMERIC(4,3) NOT NULL DEFAULT 0.22,
  ADD COLUMN ceiling_moderado NUMERIC(4,3) NOT NULL DEFAULT 0.32,
  ADD COLUMN ceiling_agressivo NUMERIC(4,3) NOT NULL DEFAULT 0.42;
```

Atualizar defaults de rate na mesma migration:
- `decay_rate_conservador`: de 0.9 para 0.04
- `decay_rate_moderado`: de 0.55 para 0.06
- `decay_rate_agressivo`: de 0.38 para 0.08

**Justificativa dos valores:**

| Cenário | Rate | Ceiling | Recuperação em 12m |
|---------|------|---------|---------------------|
| Conservador | 0.04 | 22% | ~8% do valor-alvo |
| Moderado | 0.06 | 32% | ~16% do valor-alvo |
| Agressivo | 0.08 | 42% | ~26% do valor-alvo |

Esses valores são compatíveis com benchmarks de operações de DA municipal em carteiras bem geridas, com plataforma de protesto ativa. Analista calibra manualmente quando tiver dados de `historico_safra` suficientes.

### Testes obrigatórios

Adicionar em `tests/pipeline/test_simulacao.py`:

- `test_decay_curve_respeita_ceiling` — para rate alto e ceiling baixo, recuperação em 12m deve estar próxima do ceiling * valor_alvo, não do valor_alvo integral
- `test_decay_curve_valores_monotonicos` — cada mês n+1 deve ter recuperação >= mês n
- `test_decay_curve_defaults_realistas` — com rates/ceilings default, cenário moderado deve projetar entre 10-20% de recuperação do valor-alvo em 12m

---

## C1.2 — Trava de sanidade nos cenários

### Problema

Mesmo após C1.1, o analista pode modificar manualmente os parâmetros na sidebar e gerar cenário com recuperação projetada acima de benchmarks realistas. Não há limite técnico que impeça isso. Em produção, cenário irreal pode ser apresentado a gestor municipal e gerar crise de expectativa.

### Mudança

**Onde:** `vega/app/tabs/tab_cenarios.py`

Antes de renderizar o gráfico de recuperação cumulativa, verificar:

```python
def _validar_sanidade_cenarios(valor_ativo_cents: int, cenarios: dict) -> dict | None:
    """
    Retorna dict com warning se algum cenário projeta recuperação > 50%
    do valor ativo em 12 meses. Retorna None se todos ok.
    """
    LIMITE_SANIDADE = 0.50  # 50% do valor ativo em 12m
    anomalias = []
    for nome_cenario, dados in cenarios.items():
        recup_12m = dados['curva'][-1] * 100  # em centavos
        pct_valor_ativo = recup_12m / valor_ativo_cents if valor_ativo_cents else 0
        if pct_valor_ativo > LIMITE_SANIDADE:
            anomalias.append({
                'cenario': nome_cenario,
                'pct_valor_ativo': round(pct_valor_ativo * 100, 1),
                'valor_projetado_cents': int(recup_12m),
            })
    return {'anomalias': anomalias} if anomalias else None
```

**Onde:** `vega/app/components/alerts.py`

Adicionar componente `alerta_cenario_anomalo(anomalias)`:

```python
def alerta_cenario_anomalo(anomalias: list[dict]) -> html.Div:
    """
    Banner vermelho bloqueando visualização do gráfico de cenários.
    Exige override explícito com justificativa.
    """
    return html.Div([
        html.Div([
            html.Span('🚫', style={'fontSize':'24px','flexShrink':'0'}),
            html.Div([
                html.Div('Projeção anômala detectada', style={
                    'fontSize':'14px','fontWeight':'600','color':'#991B1B','marginBottom':'4px'
                }),
                html.Div([
                    f"O cenário {a['cenario']} projeta {a['pct_valor_ativo']}% de recuperação do valor ativo em 12 meses, "
                    f"excedendo benchmarks de mercado (tipicamente 15-35%). "
                    "Verifique se as curvas de decay foram calibradas ou se os parâmetros foram alterados manualmente."
                    for a in anomalias
                ], style={'fontSize':'12px','color':'#991B1B','lineHeight':'1.6'}),
                dcc.Textarea(
                    id='textarea-justificativa-override',
                    placeholder='Justifique o override (obrigatório para visualizar)',
                    style={'width':'100%','marginTop':'12px','minHeight':'60px',
                           'padding':'8px','fontSize':'12px','border':'1px solid #FCA5A5',
                           'borderRadius':'6px'}
                ),
                html.Button('Confirmar override e visualizar', id='btn-override-cenario',
                           disabled=True, style={...})
            ])
        ], style={
            'background':'#FEE2E2','border':'2px solid #FCA5A5','borderRadius':'8px',
            'padding':'16px 20px','display':'flex','gap':'12px','alignItems':'flex-start',
        })
    ])
```

Callback habilita o botão apenas quando `len(justificativa) >= 20`.

### Testes obrigatórios

- `test_sanidade_cenario_normal` — cenário com 20% em 12m não ativa alerta
- `test_sanidade_cenario_anomalo` — cenário com 60% em 12m ativa alerta para aquele cenário específico
- `test_sanidade_multiplos_cenarios_anomalos` — se conservador e moderado ambos >50%, ambos listados

---

## C1.3 — NBA do Q3 alinhada ao modelo de convênio municipal

### Problema

A heurística atual de `_derivar_acao_sugerida` para Q3:

```python
if quadrante == "Q3":
    if valor_alto:
        return "Protesto em cartório"
    return "Execução fiscal em lote"
```

Considera implicitamente que protesto tem custo significativo para o ente. Isso é **incorreto no contexto municipal**: o protesto extrajudicial no Brasil é gratuito para o ente que opera via convênio com cartórios (modelo IEPTB). O custo é embutido nos emolumentos pagos pelo devedor na regularização. Municípios clientes da Katalyzer operam via Órion e têm essa integração pronta.

A heurística também ignora que Q3 é heterogêneo — contém contribuintes com perfis operacionais muito diferentes.

### Mudança

**Onde:** `vega/pipeline/scoring.py`

Nova lógica de `_derivar_acao_sugerida` para Q3:

```python
def _derivar_acao_sugerida(self, quadrante, contact, cda_hig) -> str:
    """
    NBA (Next-Best-Action): sugestão determinística.
    NÃO é prescrição — é ponto de partida para o analista.

    Para municípios operando via Órion, protesto é gratuito (convênio
    com cartórios, modelo IEPTB) — recomendação padrão para Q3.
    """
    # ... Q1, Q2 permanecem inalterados ...

    if quadrante == "Q3":
        status = (cda_hig.cda_bruta.status_da or "ativo").lower()

        # Q3a: baixa técnica — irrecuperável
        if status in ("baixado", "falecido", "cancelado"):
            return "Baixa técnica — irrecuperável"

        # Q3c: prescrição já interrompida por protesto/parcelamento
        if cda_hig.prescricao_interrompida:
            return "Monitorar — prescrição já interrompida"

        # Q3d: prescrição iminente — protesto urgente
        if cda_hig.dias_para_prescricao < 365:
            return "Protesto urgente — prescrição em 12 meses"

        # Q3b: protesto padrão (recomendação default para Q3 viável)
        return "Protesto em cartório"

    return "Monitorar — sem ação ativa"  # Q4
```

**Nota importante:** o NBA agora distingue quatro sub-categorias internas do Q3 (Q3a baixa técnica, Q3b protesto padrão, Q3c monitorar, Q3d protesto urgente). A UI da matriz 2×2 pode permanecer visual 2×2 para comunicação simples, mas a exportação CSV e a tabela de top contribuintes devem mostrar a sub-categoria na coluna "Ação Sugerida".

### Onde mais atualizar

1. **`Pipeline_KatalyzerVega_v1.docx` seção 5.3** — atualizar referência rápida do NBA com a nova lógica de Q3
2. **`vega-onboarding.html`** — remover o item "Q3 baixo valor = protesto destrói valor" da seção erros comuns (estava incorreto para ente municipal). Substituir por item novo que explica o modelo de convênio:

> **Protesto é gratuito para o município**
> Via convênio com cartórios (modelo IEPTB), o custo do protesto extrajudicial é pago pelo devedor na regularização. Para o ente que opera via Órion, protestar 10 ou 10.000 CDAs tem custo marginal zero. A análise de viabilidade do protesto não é financeira — é jurídica (contribuinte vivo, CDA válida) e estratégica (prescrição iminente, valor operacional).

3. **Atualizar card da Aba 7** mencionando que o custo operacional dos cenários é predominantemente SaaS fixo + humano, não variável por CDA. Isso muda o ROI de escala a favor do cenário agressivo.

### Testes obrigatórios

Adicionar em `tests/pipeline/test_scoring.py` (4 novos casos):

- `test_nba_q3_baixa_tecnica` — contribuinte com `status_da='baixado'` em Q3 → "Baixa técnica — irrecuperável"
- `test_nba_q3_prescricao_interrompida` — Q3 com `prescricao_interrompida=True` → "Monitorar — prescrição já interrompida"
- `test_nba_q3_prescricao_iminente` — Q3 com 180 dias para prescrição → "Protesto urgente — prescrição em 12 meses"
- `test_nba_q3_padrao` — Q3 viável sem flags especiais → "Protesto em cartório" (não depende mais de valor_alto)

---

## C1.4 — Alerta "Q1 excessivamente grande"

### Problema

O PRD seção 3.1 define o alerta "Q1 vazio" quando nenhuma CDA atende aos thresholds. Falta o alerta gêmeo: **Q1 grande demais para ser operacionalmente executável**. Na prática, equipes de cobrança municipais conseguem trabalhar efetivamente 8-15% da carteira por ciclo de campanha. Q1 acima de 18% é sinal de que os thresholds estão mal calibrados ou que a equipe vai colapsar no primeiro mês.

### Mudança

**Onde:** `vega/app/tabs/tab_scoring.py`

Adicionar verificação análoga ao "Q1 vazio":

```python
def verificar_q1_dimensao(scores_df, total_contribuintes) -> str | None:
    """
    Retorna string do tipo de alerta ('vazio' | 'excessivo' | None)
    """
    q1 = scores_df[scores_df['quadrante'] == 'Q1']
    contrib_q1 = q1['contribuinte_id'].nunique()

    if contrib_q1 == 0:
        return 'vazio'

    pct_carteira = contrib_q1 / total_contribuintes
    if pct_carteira > 0.18:
        return 'excessivo'

    return None
```

**Onde:** `vega/app/components/alerts.py`

Adicionar componente `alerta_q1_excessivo(contrib_q1, pct_carteira)`:

```python
def alerta_q1_excessivo(contrib_q1: int, pct_carteira: float) -> html.Div:
    return html.Div([
        html.Div([
            html.Span('⚠', style={'fontSize':'20px'}),
            html.Div([
                html.Div('Q1 excessivamente grande', style={
                    'fontSize':'13px','fontWeight':'600','color':'#92400E'
                }),
                html.Div(
                    f"Q1 contém {round(pct_carteira*100,1)}% dos contribuintes ativos ({contrib_q1} contribuintes). "
                    "Capacidade operacional típica de equipe de cobrança é de 8-15% da carteira. "
                    "Considere elevar os thresholds na sidebar ou segmentar Q1 em ondas de priorização.",
                    style={'fontSize':'12px','color':'#92400E','lineHeight':'1.6','marginTop':'4px'}
                ),
            ])
        ], style={
            'background':'#FEF3C7','border':'1px solid #FCD34D','borderRadius':'8px',
            'padding':'12px 16px','display':'flex','gap':'10px','alignItems':'flex-start',
        })
    ])
```

Exibir no topo da Aba 3, abaixo do alerta de Q1 vazio (mutuamente exclusivos).

### Onde mais atualizar

- `PRD_KatalyzerVega_v1.docx` seção 3.1 — adicionar documentação do alerta gêmeo
- `vega-onboarding.html` seção "As 7 abas" → Aba 3 → aba-alerta — mencionar ambos os alertas
- `CLAUDE.md` — adicionar em "Regras de negócio críticas" como RN-09:

> **RN-09 — Alerta de Q1 excessivamente grande**
> Se Q1 contém >18% dos contribuintes ativos, exibir alerta âmbar na Aba 3 com recomendação de elevar thresholds ou segmentar Q1 em ondas. Capacidade operacional típica de equipe de cobrança municipal é 8-15% da carteira.

### Testes obrigatórios

- `test_alerta_q1_vazio` — Q1 com 0 contribuintes → retorna 'vazio'
- `test_alerta_q1_normal` — Q1 com 10% dos contribuintes → retorna None
- `test_alerta_q1_excessivo` — Q1 com 25% dos contribuintes → retorna 'excessivo'
- `test_alerta_q1_borderline` — Q1 com 17.9% não alerta, com 18.1% alerta (testa o threshold)

---

## C1.5 — Clarificação do termo "Score" como Priority Index

### Problema

O termo "Score" em contexto de crédito tem significado estatístico específico (probabilidade relacionada a default, calibrada em range interpretável). O Vega usa "Score" para um índice ordinal de priorização. Essa divergência de terminologia vai causar confusão em reuniões com stakeholders de background bancário/crédito.

### Mudança

Mudança **leve** — manter "Score" na UI do produto (familiaridade de mercado), mas reforçar nos materiais técnicos que se trata de **Priority Index**.

**Onde:** `vega/app/tabs/tab_scoring.py` — card de rodapé da Aba 3

Texto atual:

> Score v1 · Modelo Determinístico: 4 dimensões...
> AVISO: O score é um instrumento de priorização e segmentação — não representa probabilidade de pagamento...

Texto novo:

> **Priority Index v1 · Modelo Determinístico** (display name: Score)
>
> Instrumento ordinal de priorização baseado em 4 dimensões: dim_valor, dim_urgencia, dim_contato, dim_comportamento. Eixo Prioridade (0-60) + Recuperabilidade (0-50).
>
> **Este índice NÃO é um score estatístico de probabilidade de default.** É um ranqueamento heurístico usado para segmentar a carteira em quadrantes de ação. As dimensões dim_contato e dim_comportamento são correlacionadas e somadas linearmente por design do modelo v1. Use para ordenar e segmentar — nunca para projetar taxas de conversão individuais.
>
> Uma versão supervisionada com probabilidade calibrada (Score v2) está no roadmap para após 6-12 meses de dados operacionais acumulados.

**Onde mais atualizar:**

- `SAD_KatalyzerVega_v1.docx` seção 5.3 — renomear "Score v1" para "Priority Index v1 (Score v1 display name)" e adicionar nota explicativa
- `Pipeline_KatalyzerVega_v1.docx` seção 5 — mesma mudança
- `CLAUDE.md` — adicionar nota no "Score v1 referência rápida":

> **Nota terminológica:** Score v1 é um Priority Index (índice ordinal de priorização), não um score estatístico de probabilidade. Mantido o nome "Score" por familiaridade de mercado, mas tecnicamente é um ranqueamento heurístico. Evoluir para score probabilístico é o objetivo do Score v2 (LightGBM supervisionado).

---

## Resumo — arquivos a modificar

### Código (sessão 1 do Claude Code)

| Arquivo | Tipo de mudança |
|---------|-----------------|
| `vega/pipeline/simulacao.py` | Refatorar `decay_curve` com ceiling |
| `vega/db/migrations/versions/010_add_decay_ceiling.py` | Nova migration — colunas ceiling em sessoes_analise + novos defaults de rate |
| `vega/app/tabs/tab_cenarios.py` | Adicionar trava de sanidade + UI de override |
| `vega/app/components/alerts.py` | Novos componentes: `alerta_cenario_anomalo`, `alerta_q1_excessivo` |
| `vega/pipeline/scoring.py` | Nova lógica Q3 com sub-categorias |
| `vega/app/tabs/tab_scoring.py` | Alerta Q1 excessivo + texto Priority Index no rodapé |
| `tests/pipeline/test_simulacao.py` | 3 testes novos |
| `tests/pipeline/test_scoring.py` | 4 testes novos |
| `tests/app/test_alerts.py` | 4 testes novos |

### Documentação (sessão 2, dedicada a docs)

| Documento | Seção | Mudança |
|-----------|-------|---------|
| SAD v1.1 | 5.3 | Priority Index terminology |
| SAD v1.1 | 5.4 | Rates + ceiling realistas |
| SAD v1.1 | 9 | Novo ADR-W-004: rates calibrados |
| Pipeline v1.1 | 5.3 | NBA Q3 com sub-categorias |
| Pipeline v1.1 | 5.4 | Função decay_curve com ceiling |
| PRD v1.1 | 3.1 | Alerta Q1 excessivo |
| PRD v1.1 | 7.2 | Trava de sanidade nos cenários |
| ModeloDados v1.1 | 3.2 | Colunas ceiling em sessoes_analise |
| CLAUDE.md | Regras de negócio | RN-09 nova (Q1 excessivo) |
| CLAUDE.md | Score v1 referência | Nota Priority Index |
| CLAUDE.md | O que nunca fazer | Item sobre trava de sanidade |
| vega-onboarding.html | Erros comuns | Remover erro "protesto destrói valor", adicionar "protesto é gratuito" |
| vega-onboarding.html | Perguntas do gestor | Mencionar modelo de convênio na resposta sobre custo |

---

## Após implementação

1. Executar `pytest tests/ -v` — todos devem passar
2. Atualizar versão dos documentos para **v1.1** no rodapé de cada um
3. Commit com mensagem: `feat(v1.1): rates realistas, trava de sanidade, NBA Q3 ajustada, alerta Q1 excessivo`
4. Tag: `v1.1.0`
5. Arquivar este `CHANGES_V1_1.md` em `docs/archive/` — ele não deve ser fonte de verdade após as mudanças serem absorvidas
