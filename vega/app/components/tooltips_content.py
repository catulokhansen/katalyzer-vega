"""Conteudo dos tooltips contextuais do Katalyzer Vega.

49 entradas indexadas por ID (T-AB-NN).
"""
from __future__ import annotations

TOOLTIPS: dict[str, dict] = {

    # ── Aba 1 - Diagnostico ──────────────────────────────────────────────────

    "T-01-01": {
        "titulo": "Carteira bruta",
        "componente": "KPI",
        "aba": "Aba 1 - Diagnostico",
        "o_que_mostra": (
            "Valor total da carteira recebida do cliente antes de qualquer higienizacao"
            " - soma de todas as CDAs, incluindo prescritas, irrisorias e devedores inexistentes."
        ),
        "o_que_procurar": (
            "Compare com o total de CDAs (contagem). Um ticket medio baixo (<R$ 1.500)"
            " sinaliza carteira pulverizada; ticket alto (>R$ 10.000) sinaliza carteira"
            " concentrada em PJ ou grandes devedores."
        ),
        "como_interpretar": [
            "Ate R$ 20M: carteira de municipio pequeno (ate 50k habitantes).",
            "R$ 20M-100M: municipio medio.",
            "> R$ 100M: municipio grande - exige capacidade operacional maior.",
        ],
        "acao_sugerida": (
            "Use esse valor como referencia macro, mas nunca como valor-alvo de recuperacao."
            " O valor real disponivel para cobranca e a carteira ATIVA (apos higienizacao)."
        ),
    },

    "T-01-02": {
        "titulo": "Estoque morto",
        "componente": "KPI",
        "aba": "Aba 1 - Diagnostico",
        "o_que_mostra": (
            "Percentual da carteira bruta eliminado pela higienizacao - CDAs que nao devem"
            " ser trabalhadas por prescricao, valor irrisorio ou devedor inexistente."
        ),
        "o_que_procurar": (
            "Qual e o percentual total e qual causa domina o funil abaixo. Prescricao"
            " dominante = problema historico de gestao. Irrisorio dominante = problema de"
            " politica de inscricao."
        ),
        "como_interpretar": [
            "< 20%: carteira com higienizacao previa consistente - raro.",
            "20-35%: padrao de mercado para carteiras bem geridas.",
            "35-50%: problema historico de gestao - argumento de urgencia.",
            "> 50%: inacao estrutural - receita publica sendo perdida sistematicamente.",
        ],
        "acao_sugerida": (
            "Se > 40%, abrir o funil decomposto e identificar a causa dominante. Use o"
            " percentual como argumento comercial: 'nos ultimos 4 anos o municipio perdeu"
            " R$ X por inacao'. O gestor entende melhor essa narrativa que numeros absolutos."
        ),
    },

    "T-01-03": {
        "titulo": "Carteira ativa",
        "componente": "KPI",
        "aba": "Aba 1 - Diagnostico",
        "o_que_mostra": (
            "Valor real disponivel para cobranca apos higienizacao. Universo sobre o qual"
            " scoring e cenarios sao calculados."
        ),
        "o_que_procurar": (
            "Relacao entre bruta e ativa. Se ativa < 50% da bruta, carteira com serios"
            " problemas estruturais."
        ),
        "como_interpretar": [
            "> 75% da bruta: boa base para operacao imediata.",
            "50-75%: padrao.",
            "< 50%: muito deteriorada - priorize protesto em massa antes de qualquer campanha.",
        ],
        "acao_sugerida": (
            "Todos os cenarios da Aba 7 devem ter essa base como denominador. Projecao de"
            " recuperacao e sempre percentual da ativa, nunca da bruta."
        ),
    },

    "T-01-04": {
        "titulo": "Recuperavel estimado",
        "componente": "KPI",
        "aba": "Aba 1 - Diagnostico",
        "o_que_mostra": (
            "Valor estimado para recuperacao em 12 meses no cenario moderado (soma Q1 + Q2"
            " x rate moderado x ceiling). Projecao inicial, nao compromisso."
        ),
        "o_que_procurar": (
            "Compare com a carteira ativa. Geralmente fica entre 15% e 30% da ativa."
            " Acima de 35% = rates de decay provavelmente descalibrados."
        ),
        "como_interpretar": [
            "15-25% da carteira ativa: projecao realista.",
            "> 30%: valor otimista - verificar calibracao na Aba 4.",
            "< 10%: carteira muito deteriorada ou contactabilidade muito baixa.",
        ],
        "acao_sugerida": (
            "Nunca use em proposta comercial sem passar pelos cenarios detalhados da Aba 7."
            " Esse KPI e orientacao inicial."
        ),
    },

    "T-01-05": {
        "titulo": "Composicao por tributo",
        "componente": "Grafico doughnut",
        "aba": "Aba 1 - Diagnostico",
        "o_que_mostra": (
            "Distribuicao do valor ativo entre tributos (IPTU, ISS, ITBI, taxas, multas,"
            " COSIP). Cada fatia = um tributo."
        ),
        "o_que_procurar": (
            "Qual tributo domina em valor. IPTU em PF = problema residencial/habitual."
            " ISS dominante = carteira empresarial. Taxas dominantes = problema de recadastramento."
        ),
        "como_interpretar": [
            "IPTU > 60%: carteira predominantemente residencial - campanha digital em massa.",
            "ISS > 50%: carteira empresarial - abordagem diferenciada, alta concentracao em PJ.",
            "Taxas > 40%: possivel problema cadastral - muitos contribuintes podem estar isentos.",
        ],
        "acao_sugerida": (
            "A distribuicao define o canal preferencial. IPTU -> WhatsApp/SMS."
            " ISS -> ligacao comercial + negociacao individual. ITBI -> protesto imediato."
        ),
    },

    "T-01-06": {
        "titulo": "Funil de higienizacao",
        "componente": "Grafico funil decomposto",
        "aba": "Aba 1 - Diagnostico",
        "o_que_mostra": (
            "Decomposicao do estoque morto em 3 segmentos: prescricao (vermelho escuro),"
            " valor irrisorio (vermelho), devedor inexistente (laranja). Mostra visualmente"
            " qual causa mais elimina CDAs."
        ),
        "o_que_procurar": (
            "Qual cor domina. Proporcao entre as causas e tao importante quanto o total."
            " Uma carteira com 30% de estoque morto dominado por prescricao e radicalmente"
            " diferente de uma com 30% dominada por irrisorio."
        ),
        "como_interpretar": [
            "Prescricao dominante: municipio nao tem operacao de cobranca estruturada ha"
            " anos. Argumento de urgencia.",
            "Irrisorio dominante: politica de inscricao problematica - muitas CDAs de"
            " R$ 30 a R$ 200. Custo de cobranca nao compensa.",
            "Devedor inexistente dominante: problema cadastral grave - CPFs/CNPJs invalidos,"
            " enderecos vazios, contribuintes nunca cadastrados corretamente.",
        ],
        "acao_sugerida": (
            "Se prescricao > 60% do estoque morto: leve esse dado para a abertura da"
            " reuniao com o gestor. Se irrisorio > 40%: sugerir ao cliente elevar o valor"
            " minimo de inscricao na proxima politica de DA. Se inexistente > 30%: priorizar"
            " enriquecimento cadastral externo antes da proxima safra."
        ),
    },

    "T-01-07": {
        "titulo": "Concentracao Pareto",
        "componente": "Grafico linha curva",
        "aba": "Aba 1 - Diagnostico",
        "o_que_mostra": (
            "Curva de Pareto - eixo X: % acumulado de contribuintes (maior -> menor devedor)."
            " Eixo Y: % acumulado do valor."
        ),
        "o_que_procurar": (
            "Ponto de inflexao. Mais concava = mais concentrada. Curva linear = carteira pulverizada."
        ),
        "como_interpretar": [
            "Top 10% = 70%+ do valor: MUITO concentrada - foco em B2B individualizado.",
            "Top 10% = 40-60%: concentrada, padrao.",
            "Top 10% < 40%: pulverizada - jogo de volume digital.",
        ],
        "acao_sugerida": (
            "Em carteiras muito concentradas, negociacao individual com top 20-30 contribuintes"
            " vale mais que qualquer campanha de massa. Em pulverizadas, invista em automacao digital."
        ),
    },

    "T-01-08": {
        "titulo": "Valor x idade por tributo",
        "componente": "Grafico barras empilhadas",
        "aba": "Aba 1 - Diagnostico",
        "o_que_mostra": (
            "Cruzamento entre faixa etaria da CDA (< 1 ano, 1-2, 2-3, 3-4, 4-5 anos) e tributo."
            " Cada barra = faixa etaria; segmentos = tributos."
        ),
        "o_que_procurar": (
            "Tributos que concentram valor em faixas proximas da prescricao (3-5 anos)."
            " Identifique tambem tributos crescendo desproporcionalmente em safras recentes."
        ),
        "como_interpretar": [
            "IPTU concentrado em 4-5 anos: prescricao iminente - urgente.",
            "ISS concentrado em 1-2 anos: safras recentes tem janela de ouro para recuperacao.",
            "ITBI em qualquer faixa: divida de transacao, geralmente recuperavel por protesto rapido.",
        ],
        "acao_sugerida": (
            "Priorize barras proximas da prescricao, especialmente tributos com alta"
            " recuperabilidade historica. Faixas 4-5 anos: protesto em massa imediato."
        ),
    },

    "T-01-09": {
        "titulo": "Top contribuintes",
        "componente": "Tabela",
        "aba": "Aba 1 - Diagnostico",
        "o_que_mostra": (
            "Lista dos contribuintes com maior valor devido. Para cada um: numero de CDAs,"
            " valor total, densidade (valor por CDA), padrao de densidade, quadrante e acao sugerida."
        ),
        "o_que_procurar": (
            "Contribuintes com valor > 5% da carteira total. Tambem olhe o padrao de"
            " densidade: 1 CDA de R$ 500k e muito diferente de 200 CDAs de R$ 2.500."
        ),
        "como_interpretar": [
            "Concentrado (1-3 CDAs): divida pontual, negociacao direta - protesto resolve rapido.",
            "Medio (4-9 CDAs): inadimplencia relativa - propor acordo global com desconto.",
            "Pulverizado (10+ CDAs): devedor contumaz - acordo global obrigatorio.",
        ],
        "acao_sugerida": (
            "Para os 20 primeiros, NUNCA siga a acao sugerida automatica sem revisao."
            " Sao casos individuais. Marcar reuniao com o procurador do municipio."
        ),
    },

    "T-01-10": {
        "titulo": "Alerta de concentracao de risco",
        "componente": "Card de alerta",
        "aba": "Aba 1 - Diagnostico",
        "o_que_mostra": (
            "Card automatico quando algum contribuinte representa > 10% da carteira ativa."
            " Mostra nome do contribuinte e percentual."
        ),
        "o_que_procurar": (
            "Se o alerta apareceu, voce tem um caso especial. Os cenarios da Aba 7 devem"
            " ser calculados com e sem esse contribuinte."
        ),
        "como_interpretar": [
            "10-15%: concentracao significativa - trate separado.",
            "15-25%: concentracao alta - cenario sem o contribuinte e essencial.",
            "> 25%: concentracao extrema - praticamente uma negociacao individual disfarçada de carteira.",
        ],
        "acao_sugerida": (
            "Nao apresente cenarios ao gestor sem rodar os dois lados: com o grande devedor"
            " recuperando e sem."
        ),
    },

    "T-01-11": {
        "titulo": "Fluxo entrada vs recuperacao",
        "componente": "Grafico combo (barras + linha)",
        "aba": "Aba 1 - Diagnostico",
        "o_que_mostra": (
            "Historico dos ultimos 12 meses - novas CDAs entradas na carteira por mes (barras)"
            " versus recuperado (linha)."
        ),
        "o_que_procurar": (
            "Se a carteira esta crescendo ou reduzindo."
            " Barras consistentemente maiores que a linha = carteira crescendo."
        ),
        "como_interpretar": [
            "Crescimento liquido > +20 CDAs/mes: municipio sem operacao ativa.",
            "Equilibrio (+-10 CDAs/mes): estavel, operacao razoavel.",
            "Reducao liquida: operacao ativa eficaz - raro sem Katalyzer ou equivalente.",
        ],
        "acao_sugerida": (
            "Se ha crescimento liquido, use o saldo mensal como metrica de sucesso na proposta:"
            " Katalyzer nao so recupera o passado como estabiliza o presente."
        ),
    },

    # ── Aba 2 - Segmentacao ──────────────────────────────────────────────────

    "T-02-01": {
        "titulo": "Distribuicao por faixa de valor",
        "componente": "Grafico barras verticais",
        "aba": "Aba 2 - Segmentacao",
        "o_que_mostra": (
            "Carteira ativa em 5 faixas: ate R$500, R$500-2k, R$2k-10k, R$10k-50k, acima"
            " de R$50k. Cada barra = valor total acumulado na faixa."
        ),
        "o_que_procurar": (
            "Onde esta concentrado o VALOR (nao a quantidade). Estrategia deve priorizar"
            " onde esta o dinheiro, nao o volume."
        ),
        "como_interpretar": [
            "Concentracao em R$10k-50k: sweet spot operacional - WhatsApp + parcelamento 6x.",
            "Concentracao em ate R$500: custo de cobranca unitaria e critico.",
            "Concentracao em >R$50k: carteira de grandes devedores - negociacao individual.",
        ],
        "acao_sugerida": (
            "Use o slider de valor minimo na sidebar para excluir a faixa ate R$500 se ela"
            " representa < 5% do valor total. Pode melhorar o ROI em 30-40%."
        ),
    },

    "T-02-02": {
        "titulo": "PF vs PJ",
        "componente": "Grafico barras",
        "aba": "Aba 2 - Segmentacao",
        "o_que_mostra": (
            "Distribuicao do valor ativo entre pessoa fisica e pessoa juridica. Mostra"
            " tambem o numero de contribuintes em cada categoria."
        ),
        "o_que_procurar": (
            "Proporcao de valor versus contagem. PJ = poucos contribuintes com muito valor."
            " PF = muitos contribuintes com valor pulverizado."
        ),
        "como_interpretar": [
            "PJ > 60% do valor: foco em ISS e grandes CDAs - abordagem corporativa, ligacao comercial.",
            "PF > 60% do valor: foco em IPTU e taxas - abordagem digital em massa, WhatsApp, parcelamento.",
            "Equilibrado (40-60%): requer duas estrategias paralelas.",
        ],
        "acao_sugerida": (
            "Separe mentalmente PJ e PF como duas carteiras diferentes."
            " Nunca trate como um universo unico."
        ),
    },

    "T-02-03": {
        "titulo": "Matriz de segmentos",
        "componente": "Tabela pivotada",
        "aba": "Aba 2 - Segmentacao",
        "o_que_mostra": (
            "Cruzamento tributo x faixa de valor. Cada celula = valor total daquela"
            " combinacao. Identifica o sweet spot operacional da carteira."
        ),
        "o_que_procurar": (
            "Celula com maior valor absoluto = combinacao mais relevante. Carteiras saudaveis"
            " tem varias celulas relevantes; frageis concentram tudo em uma celula."
        ),
        "como_interpretar": [
            "IPTU x R$2k-10k: tipicamente o sweet spot operacional.",
            "ISS x >R$50k: PJ com problema serio - prioridade maxima em negociacao individual.",
            "Taxas x ate R$500: pode nao valer o esforco de cobranca.",
        ],
        "acao_sugerida": (
            "Identifique as 3 celulas com maior valor - 70% do esforco operacional vai nelas."
        ),
    },

    # ── Aba 3 - Scoring ──────────────────────────────────────────────────────

    "T-03-01": {
        "titulo": "Matriz 2x2 (quadrantes)",
        "componente": "Matriz de priorizacao",
        "aba": "Aba 3 - Scoring",
        "o_que_mostra": (
            "Divisao da carteira em Q1 (Acao imediata), Q2 (Campanha massa), Q3"
            " (Protesto/Judicial), Q4 (Monitorar). Eixos: Prioridade do Titulo (0-60)"
            " x Recuperabilidade do Contribuinte (0-50)."
        ),
        "o_que_procurar": (
            "Distribuicao de valor entre quadrantes. Carteira saudavel tem 40-60% do valor"
            " em Q1+Q2."
        ),
        "como_interpretar": [
            "Q1 > 40% do valor: excelente - grande oportunidade de recuperacao imediata.",
            "Q1 entre 15-30%: padrao.",
            "Q3 > 40%: carteira deteriorada - operacao sera majoritariamente protesto.",
            "Q4 > 30%: divida morta - enriquecimento cadastral necessario.",
        ],
        "acao_sugerida": (
            "Semana 1-2 e Q1 (WhatsApp + ligacoes). Semana 3-4 e Q2 (campanhas automatizadas)."
            " Mes 2+ e Q3 (protesto em massa). Q4 fica fora da operacao."
        ),
    },

    "T-03-02": {
        "titulo": "Alerta de Q1 vazio",
        "componente": "Banner ambar",
        "aba": "Aba 3 - Scoring",
        "o_que_mostra": (
            "Aviso quando nenhum contribuinte atinge os criterios de Q1"
            " (Prioridade >= threshold_prio E Recuperabilidade >= threshold_rec)."
        ),
        "o_que_procurar": (
            "Se aparece, a carteira tem problema estrutural. Ou scores de contactabilidade"
            " muito baixos ou thresholds altos demais."
        ),
        "como_interpretar": [
            "Q1 vazio com threshold padrao (40/30): contactabilidade ruim - enriquecimento cadastral urgente.",
            "Q1 vazio com threshold alto (>50): ajustar sliders na sidebar.",
        ],
        "acao_sugerida": (
            "Primeiro: reduzir threshold_recuperabilidade para 20 e ver se Q1 aparece."
            " Se sim, problema e contactabilidade - orcar enriquecimento."
            " Se nao, acao majoritariamente via protesto (Q3)."
        ),
    },

    "T-03-03": {
        "titulo": "Alerta de Q1 excessivamente grande",
        "componente": "Banner ambar",
        "aba": "Aba 3 - Scoring",
        "o_que_mostra": (
            "Aviso quando Q1 contem > 18% dos contribuintes ativos. Capacidade operacional"
            " tipica de equipe de cobranca municipal e 8-15%."
        ),
        "o_que_procurar": (
            "Percentual exato e quantos contribuintes. Se e 20% -> ajuste thresholds."
            " Se e 35% -> calibracao totalmente inadequada."
        ),
        "como_interpretar": [
            "18-25%: ajustar thresholds para cima (ex: 45/35) e segmentar Q1 em ondas.",
            "25-35%: thresholds muito baixos - revisar pesos das dimensoes.",
            "> 35%: scores inflados - calibracao herdada de outra carteira nao se aplica.",
        ],
        "acao_sugerida": (
            "Segmentar Q1 em 2 ou 3 ondas por valor: onda 1 (top 100), onda 2 (proximos 200),"
            " onda 3 (restante)."
        ),
    },

    "T-03-04": {
        "titulo": "Histograma Score Prioridade",
        "componente": "Grafico histograma",
        "aba": "Aba 3 - Scoring",
        "o_que_mostra": (
            "Distribuicao das CDAs por faixa do eixo Prioridade do Titulo (0-60 pontos)."
        ),
        "o_que_procurar": (
            "Forma da distribuicao. Espalhada com cauda para pontuacoes altas = saudavel."
            " Concentrada no meio (25-35) = carteira homogenea."
        ),
        "como_interpretar": [
            "Distribuicao bimodal (picos nos extremos): carteira polarizada, segmentacao facil.",
            "Distribuicao normal centralizada: bom poder de discriminacao.",
            "Concentrada em scores baixos: carteira envelhecida com muitas CDAs proximas"
            " da prescricao mas baixo valor.",
        ],
        "acao_sugerida": (
            "Ajuste o threshold de Prioridade para Q1 na regiao onde a distribuicao mostra"
            " uma 'barriga' - geralmente o terco superior."
        ),
    },

    "T-03-05": {
        "titulo": "Histograma Score Recuperabilidade",
        "componente": "Grafico histograma",
        "aba": "Aba 3 - Scoring",
        "o_que_mostra": (
            "Distribuicao das CDAs por faixa do eixo Recuperabilidade do Contribuinte"
            " (0-50 pontos). Combina contactabilidade e comportamento historico."
        ),
        "o_que_procurar": (
            "Cauda esquerda (0-15) = contribuintes praticamente irrecuperaveis via campanha"
            " digital. Se grande, investir em enriquecimento cadastral antes da operacao."
        ),
        "como_interpretar": [
            "Cauda esquerda > 30%: muitos incontactaveis - enriquecimento obrigatorio.",
            "Massa em 20-35: carteira tipica, contactabilidade mista.",
            "Cauda direita dominante: excelentes dados - campanha digital tem grande potencial.",
        ],
        "acao_sugerida": (
            "Para contribuintes com score < 15 e valor > R$ 10k: priorizar enriquecimento"
            " externo (Serpro, Neoway). Custo ~R$ 1,50/consulta se paga rapidamente."
        ),
    },

    # ── Aba 4 - Safra & Aging ────────────────────────────────────────────────

    "T-04-01": {
        "titulo": "Safras analisadas",
        "componente": "KPI",
        "aba": "Aba 4 - Safra & Aging",
        "o_que_mostra": (
            "Numero de safras distintas (anos de inscricao) presentes na carteira ativa."
        ),
        "o_que_procurar": (
            "Proximo de 5 = carteira recente, saudavel."
            " Acima de 7 = CDAs muito antigas - sinal de inacao historica."
        ),
        "como_interpretar": [
            "3-5 safras: carteira recente, gestao consistente.",
            "5-7 safras: padrao.",
            "> 7 safras: carteira muito envelhecida - urgencia de protesto imediato.",
        ],
        "acao_sugerida": (
            "Se ha safras anteriores a 2019 ativas: verificar se tem protesto ou parcelamento."
            " Se nao tem, estao prescritas - revisar criterios de higienizacao."
        ),
    },

    "T-04-02": {
        "titulo": "Melhor safra",
        "componente": "KPI",
        "aba": "Aba 4 - Safra & Aging",
        "o_que_mostra": (
            "Ano da safra com maior taxa de recuperacao historica (tabela historico_safra)."
            " Se nao ha historico, mostra '--'."
        ),
        "o_que_procurar": (
            "Qual foi o ano e qual foi a taxa. Essa safra e o benchmark interno."
        ),
        "como_interpretar": [
            "Melhor safra e a mais recente: tendencia positiva, operacao melhorando.",
            "Melhor safra e antiga: a melhor performance foi com uma campanha especifica - identificar qual e por que funcionou.",
            "Taxa > 25%: excelente para DA municipal.",
            "Taxa 15-25%: dentro do padrao.",
            "Taxa < 15%: operacao de recuperacao sempre foi fraca.",
        ],
        "acao_sugerida": (
            "Use a melhor safra como baseline para projecao dos cenarios"
            " (regression to mean aplicada)."
        ),
    },

    "T-04-03": {
        "titulo": "Prescricao bruta x liquida",
        "componente": "KPI dual",
        "aba": "Aba 4 - Safra & Aging",
        "o_que_mostra": (
            "Dois valores lado a lado - prescricao bruta (todas CDAs prescrevendo em 12m)"
            " e prescricao liquida (descontadas as com prescricao ja interrompida por"
            " protesto ou parcelamento ativo)."
        ),
        "o_que_procurar": (
            "A diferenca entre bruta e liquida. Se bruta = liquida, nada esta protegido"
            " - urgencia maxima."
        ),
        "como_interpretar": [
            "Liquida > 70% da bruta: quase nada protegido - protesto em massa imediato.",
            "Liquida 30-70% da bruta: operacao parcial, completar a protecao.",
            "Liquida < 30% da bruta: maioria ja protegida - focar em recuperacao.",
        ],
        "acao_sugerida": (
            "O numero operacional e o LIQUIDO. Nunca use a bruta como argumento de urgencia"
            " sem explicar que parte ja esta protegida."
        ),
    },

    "T-04-04": {
        "titulo": "Idade media ponderada",
        "componente": "KPI",
        "aba": "Aba 4 - Safra & Aging",
        "o_que_mostra": (
            "Idade media da carteira ativa em anos, ponderada pelo valor das CDAs"
            " (CDAs de maior valor puxam o indicador)."
        ),
        "o_que_procurar": (
            "Quao envelhecida e a carteira em termos de valor."
            " > 3 anos = maior parte do dinheiro proxima da prescricao."
        ),
        "como_interpretar": [
            "< 2 anos: carteira jovem, tempo para campanha ampla.",
            "2-3 anos: padrao - planejar operacao em 12-18 meses.",
            "3-4 anos: envelhecida - protesto e prioridade.",
            "> 4 anos: critica - parte significativa prescreve em menos de 12 meses.",
        ],
        "acao_sugerida": (
            "Carteira jovem = campanha de 18 meses faz sentido."
            " Envelhecida = tudo em 6 meses ou perde muito valor."
        ),
    },

    "T-04-05": {
        "titulo": "Analise de safra (vintage)",
        "componente": "Grafico combo (barras + linha)",
        "aba": "Aba 4 - Safra & Aging",
        "o_que_mostra": (
            "Por safra: valor inscrito (barras) versus taxa de recuperacao historica"
            " em 12 meses (linha)."
        ),
        "o_que_procurar": (
            "Safras com alta taxa e baixo valor = oportunidades pequenas mas eficientes."
            " Baixa taxa e alto valor = problema estrutural."
        ),
        "como_interpretar": [
            "Taxa crescente ao longo das safras: operacao melhorando.",
            "Taxa decrescente: operacao piorando.",
            "Taxa estagnada em 15-20%: operacao tipica - ha margem para crescer.",
        ],
        "acao_sugerida": (
            "Identifique a safra com melhor performance e investigue qual campanha coincidiu"
            " com ela. Repetir a formula aumenta a probabilidade de desempenho similar."
        ),
    },

    "T-04-06": {
        "titulo": "Curva de aging",
        "componente": "Grafico barras empilhadas",
        "aba": "Aba 4 - Safra & Aging",
        "o_que_mostra": (
            "Valor da carteira por faixa de idade (<6m, 6m-1a, 1a-2a, 2a-3a, 3a-4a, 4a-5a)."
            " Duas series por barra: CDAs normais (cor solida) e CDAs com prescricao"
            " interrompida (hachuradas)."
        ),
        "o_que_procurar": (
            "Distribuicao do valor ao longo do tempo. Barras a direita = urgencia."
            " Barras hachuradas = protecao ja feita."
        ),
        "como_interpretar": [
            "Concentracao a esquerda (<1a): carteira jovem.",
            "Concentracao central (1a-3a): sweet spot para operacao.",
            "Concentracao a direita (3a-5a): envelhecida - protesto urgente nas CDAs solidas.",
            "Barras 4a-5a quase todas hachuradas: operacao anterior protegeu bem.",
        ],
        "acao_sugerida": (
            "(1) Proteja CDAs de 4a-5a solidas com protesto em massa;"
            " (2) trabalhe 2a-3a com campanha digital;"
            " (3) deixe <1a para segunda onda."
        ),
    },

    "T-04-07": {
        "titulo": "Decay de recuperacao por safra",
        "componente": "Grafico multiplas linhas",
        "aba": "Aba 4 - Safra & Aging",
        "o_que_mostra": (
            "Curvas de recuperacao real de cada safra ao longo dos meses apos inscricao."
            " Uma linha por safra, mostrando como a taxa decai com o tempo."
        ),
        "o_que_procurar": (
            "Ponto de inflexao de cada safra - onde a curva começa a estagnar"
            " (normalmente M9-M15). Depois disso, acoes convencionais tem baixo retorno."
        ),
        "como_interpretar": [
            "Curva sobe rapido nos primeiros 6m e estabiliza: operacao eficaz.",
            "Curva cresce lentamente e nunca estabiliza: poderia recuperar mais com pressao.",
            "Curva estagna cedo (< 6m): pouca variedade de canais - operacao monofocal.",
        ],
        "acao_sugerida": (
            "Use esses dados para CALIBRAR os rates de decay dos cenarios da Aba 7."
            " Se a safra 2024 recuperou 70% do seu total em 6 meses, o rate real e ~0.06"
            " para ceiling ~0.25."
        ),
    },

    "T-04-08": {
        "titulo": "Sazonalidade mensal",
        "componente": "Grafico barras agrupadas",
        "aba": "Aba 4 - Safra & Aging",
        "o_que_mostra": (
            "Media historica de inscricoes e recuperacoes por mes do ano (Jan-Dez)."
            " Identifica meses de alta e baixa receptividade."
        ),
        "o_que_procurar": (
            "Meses com pico de recuperacao e meses de vale. Tambem meses com muita"
            " inscricao mas pouca recuperacao - problema sazonal de politica tributaria."
        ),
        "como_interpretar": [
            "Pico jan-mar: efeito IPVA e ferias - contribuintes tem receita excedente.",
            "Pico em jul: 13o salario antecipado em alguns setores.",
            "Pico nov-dez: decimo terceiro, comercio aquecido.",
            "Vales tipicos: abr-jun e ago-out.",
        ],
        "acao_sugerida": (
            "Programe a campanha principal para iniciar 15 dias antes do pico historico."
            " Evite lancamentos em meses de vale."
        ),
    },

    # ── Aba 5 - Contactabilidade ─────────────────────────────────────────────

    "T-05-01": {
        "titulo": "Contactaveis digital",
        "componente": "KPI",
        "aba": "Aba 5 - Contactabilidade",
        "o_que_mostra": (
            "Percentual de contribuintes ativos com pelo menos um canal digital disponivel"
            " (celular, WhatsApp ou email)."
        ),
        "o_que_procurar": (
            "Quao dependente a operacao sera de canais caros"
            " (ligacao, presencial, correspondencia)."
        ),
        "como_interpretar": [
            "> 70%: excelente - operacao digital primeiro, outros canais residuais.",
            "50-70%: padrao - plano hibrido.",
            "< 50%: problemas cadastrais - enriquecimento urgente.",
        ],
        "acao_sugerida": (
            "Se < 50%, calcule o custo de enriquecimento externo e compare com o valor"
            " incontactavel. Regra: se o enriquecimento custa menos de 1% do valor a"
            " recuperar, faca antes de comecar."
        ),
    },

    "T-05-02": {
        "titulo": "So endereco",
        "componente": "KPI",
        "aba": "Aba 5 - Contactabilidade",
        "o_que_mostra": (
            "Percentual de contribuintes que tem apenas endereco fisico cadastrado"
            " - sem celular, email ou WhatsApp."
        ),
        "o_que_procurar": (
            "Esses contribuintes so podem ser alcancados por canais caros"
            " (correspondencia, presencial, protesto)."
        ),
        "como_interpretar": [
            "< 15%: tranquilo - canais caros sao residuais.",
            "15-30%: relevante - precisa de estrategia especifica.",
            "> 30%: problematico - operar via Regulariza como canal passivo.",
        ],
        "acao_sugerida": (
            "Para esse grupo, o melhor canal e passivo: Regulariza + divulgacao local"
            " + protesto. Nao gaste orcamento em canais ativos."
        ),
    },

    "T-05-03": {
        "titulo": "Incontactaveis",
        "componente": "KPI",
        "aba": "Aba 5 - Contactabilidade",
        "o_que_mostra": (
            "Percentual de contribuintes sem NENHUM dado de contato valido"
            " - nem endereco, nem celular, nem email."
        ),
        "o_que_procurar": (
            "Percentual e valor absoluto. Se percentual alto mas valor baixo, ignore."
            " Se valor incontactavel > R$ 100k, e oportunidade perdida."
        ),
        "como_interpretar": [
            "< 5%: excelente.",
            "5-15%: padrao - tratar como Q4 (monitorar).",
            "> 15%: problema cadastral grave - revisao do processo de inscricao do municipio.",
        ],
        "acao_sugerida": (
            "Para incontactaveis de alto valor (> R$ 10k por CDA): unico caminho e"
            " protesto em massa + enriquecimento cadastral externo."
        ),
    },

    "T-05-04": {
        "titulo": "Valor incontactavel",
        "componente": "KPI",
        "aba": "Aba 5 - Contactabilidade",
        "o_que_mostra": (
            "Valor absoluto (R$) da carteira com contribuintes incontactaveis - dinheiro que"
            " so pode ser recuperado com acoes alternativas (protesto, Regulariza passivo, judicial)."
        ),
        "o_que_procurar": (
            "Compare com carteira ativa total. Se > 15% = problema que merece investimento"
            " em enriquecimento. Se < 5%, deixe para depois."
        ),
        "como_interpretar": [
            "Valor proporcional ao % de incontactaveis: contribuintes incontactaveis tem valor medio similar aos outros.",
            "Valor desproporcionalmente alto: alguns grandes devedores estao entre os incontactaveis - enriquecimento obrigatorio.",
        ],
        "acao_sugerida": (
            "Calcule o break-even: com mais de R$ 75k incontactavel, o enriquecimento ja se"
            " paga (~R$ 1.500 para 1.000 registros se pode recuperar 20% do valor)."
        ),
    },

    "T-05-05": {
        "titulo": "Cobertura por canal",
        "componente": "Grafico barras horizontais",
        "aba": "Aba 5 - Contactabilidade",
        "o_que_mostra": (
            "Percentual de cobertura para cada canal (celular, WhatsApp, email, telefone"
            " fixo, endereco). Um contribuinte pode ter multiplos canais."
        ),
        "o_que_procurar": (
            "Qual canal tem maior cobertura e quais tem gap grande."
            " WhatsApp e celular geralmente caminham juntos."
        ),
        "como_interpretar": [
            "WhatsApp > 60%: canal primario da operacao.",
            "Celular > 70% mas WhatsApp < 40%: validacao de WhatsApp nao executada - rodar discovery.",
            "Email > 50%: raro, indica carteira PJ predominante.",
            "Endereco proximo de 100% mas outros canais baixos: dados de contato nunca atualizados.",
        ],
        "acao_sugerida": (
            "Priorize o canal com maior cobertura para a campanha principal. Sempre tenha"
            " um canal fallback. Nunca confie em um canal so."
        ),
    },

    "T-05-06": {
        "titulo": "Contactabilidade x faixa de valor",
        "componente": "Grafico barras empilhadas",
        "aba": "Aba 5 - Contactabilidade",
        "o_que_mostra": (
            "Por faixa de valor, mostra a divisao entre contactaveis digitais, so-endereco"
            " e incontactaveis."
        ),
        "o_que_procurar": (
            "Se a contactabilidade e uniforme nas faixas ou desequilibrada. Em muitas carteiras,"
            " faixas altas tem pior contactabilidade (PJs com CNPJs desatualizados)."
        ),
        "como_interpretar": [
            "Contactabilidade uniforme: operacao direta, estrategia unica.",
            "Incontactaveis concentrados em faixas altas: enriquecimento obrigatorio.",
            "Incontactaveis em faixas baixas: irrelevante operacionalmente.",
        ],
        "acao_sugerida": (
            "O pior cenario e alto valor incontactavel em faixas altas - parece que voce tem"
            " pouco dinheiro mas na verdade tem muito, so nao consegue alcancar."
        ),
    },

    "T-05-07": {
        "titulo": "Heatmap qualidade por canal",
        "componente": "Tabela colorida",
        "aba": "Aba 5 - Contactabilidade",
        "o_que_mostra": (
            "Matriz tributo x canal com percentual de cobertura."
            " Cores: verde (>50%), ambar (30-49%), vermelho (<30%)."
        ),
        "o_que_procurar": (
            "Celulas vermelhas em canais principais (WhatsApp, celular)"
            " - onde a operacao vai ter problemas de alcance."
        ),
        "como_interpretar": [
            "ISS com WhatsApp baixo: PJs com contatos desatualizados - comum.",
            "IPTU com endereco 100% mas celular 30%: carteira de imoveis cadastrados ha muito tempo.",
            "Taxas com todos os canais baixos: problema cadastral estrutural no processo de inscricao.",
        ],
        "acao_sugerida": (
            "Ajuste a estrategia por tributo. Se IPTU tem celular baixo mas endereco alto,"
            " considere correspondencia para IPTU e digital para ISS."
        ),
    },

    # ── Aba 6 - Historico ────────────────────────────────────────────────────

    "T-06-01": {
        "titulo": "Reincidentes %",
        "componente": "KPI",
        "aba": "Aba 6 - Historico",
        "o_que_mostra": (
            "Percentual de contribuintes na carteira atual que ja tinham debitos em anos"
            " anteriores (cross-safra)."
        ),
        "o_que_procurar": (
            "Alto = muitos contribuintes com historico (bom: voce sabe o padrao; ruim: sao"
            " devedores cronicos). Baixo = carteira predominantemente nova."
        ),
        "como_interpretar": [
            "< 20%: carteira nova, prior weight fraco.",
            "20-40%: padrao - mistura saudavel.",
            "> 40%: muitos devedores cronicos - estrategia diferenciada.",
        ],
        "acao_sugerida": (
            "Se alto: segmente reincidentes em tres grupos - reincidente-pagador (prioridade"
            " maxima), so-parcelou-e-quebrou (oferta diferente, prazo menor),"
            " devedor-contumaz (negociacao individual)."
        ),
    },

    "T-06-02": {
        "titulo": "Valor reincidentes",
        "componente": "KPI",
        "aba": "Aba 6 - Historico",
        "o_que_mostra": (
            "Valor total da carteira atual que pertence a contribuintes reincidentes."
        ),
        "o_que_procurar": (
            "Comparar com o percentual de reincidentes. Se reincidencia e 30% dos"
            " contribuintes mas 60% do valor, os reincidentes tem ticket medio mais alto."
        ),
        "como_interpretar": [
            "Valor proporcional: reincidencia homogenea.",
            "Valor alto, % contribuintes baixo: reincidentes sao grandes devedores - priorizar.",
            "Valor baixo, % contribuintes alto: reincidentes sao pulverizados - campanha em massa serve.",
        ],
        "acao_sugerida": (
            "O valor reincidente e o melhor preditor operacional - esses contribuintes ja"
            " conhecem o processo, respondem a campanhas. Priorize-os."
        ),
    },

    "T-06-03": {
        "titulo": "Taxa de quebra media",
        "componente": "KPI",
        "aba": "Aba 6 - Historico",
        "o_que_mostra": (
            "Percentual medio de parcelamentos interrompidos no historico da carteira."
        ),
        "o_que_procurar": (
            "Se alto, politica de parcelamento atual e problematica - prazos longos demais,"
            " parcelas altas demais, ou selecao inadequada."
        ),
        "como_interpretar": [
            "< 30%: operacao bem calibrada - maioria conclui.",
            "30-50%: padrao.",
            "> 50%: politica de parcelamento ruim - revisar prazos e valores minimos.",
        ],
        "acao_sugerida": (
            "Se > 50%: teste prazo menor (6x em vez de 12x), parcela minima maior"
            " (R$ 200 em vez de R$ 50), e entrada maior (30% em vez de 10%)."
            " Reduz quebras em 15-25 pontos."
        ),
    },

    "T-06-04": {
        "titulo": "Parcela media de quebra",
        "componente": "KPI",
        "aba": "Aba 6 - Historico",
        "o_que_mostra": (
            "Em qual numero de parcela, em media, os parcelamentos sao quebrados."
            " A 'esperanca de vida' do parcelamento."
        ),
        "o_que_procurar": (
            "Parcela media baixa (< 4) = problema operacional, desistem cedo."
            " Alta (> 8) = bom comprometimento mas muitos parcelamentos longos nao terminam."
        ),
        "como_interpretar": [
            "Parcela = 4: apos a primeira dificuldade (60 dias), desistem.",
            "Parcela = 6: desistem apos relaxar, achar que ja conseguiram.",
            "Parcela = 10+: bom comprometimento mas politica de prazo longo demais.",
        ],
        "acao_sugerida": (
            "Ofereça parcelamentos com prazo ate a parcela media de quebra + 1."
            " Se quebra em media na 6a, ofereça 6x ou 7x."
            " Isso força o compromisso realista."
        ),
    },

    "T-06-05": {
        "titulo": "Reincidencia vs primeiro debito",
        "componente": "Grafico barras horizontais",
        "aba": "Aba 6 - Historico",
        "o_que_mostra": (
            "Divisao da carteira em tres categorias: reincidente-pagador (ja pagou antes),"
            " so-parcelou (aderiu mas quebrou), primeiro-debito (sem historico)."
        ),
        "o_que_procurar": (
            "Proporcao entre as tres categorias. Reincidente-pagador e o perfil mais valioso"
            " operacionalmente."
        ),
        "como_interpretar": [
            "Reincidente-pagador > 30%: excelente - contribuintes ja testaram o sistema.",
            "So-parcelou dominante: desafio - quebraram antes, podem quebrar de novo.",
            "Primeiro-debito dominante: carteira verde - boa taxa de adesao esperada.",
        ],
        "acao_sugerida": (
            "Reincidente-pagador: oferta padrao, campanha digital. "
            "So-parcelou-e-quebrou: prazo menor, entrada maior, parcelas menores. "
            "Primeiro-debito: oferta inicial atrativa (20-25% de desconto)."
        ),
    },

    "T-06-06": {
        "titulo": "Sobrevivencia do parcelamento",
        "componente": "Grafico linha",
        "aba": "Aba 6 - Historico",
        "o_que_mostra": (
            "Curva de sobrevivencia - % de parcelamentos ativos por numero de parcelas"
            " cumpridas. Comeca em 100% e decai conforme quebras."
        ),
        "o_que_procurar": (
            "Pontos de inflexao da curva. Queda abrupta em parcela especifica = problema sistemico."
        ),
        "como_interpretar": [
            "Queda acentuada na 4a parcela: fadiga tipica, o 'alivio inicial' passou.",
            "Queda na 12a parcela: chegada do final do ano - orcamento apertado.",
            "Curva suave: bom design de parcelamento.",
            "Queda proxima de 0 antes da 6a: politica mal calibrada.",
        ],
        "acao_sugerida": (
            "Estruture parcelamentos para vencerem antes do ponto de queda critica."
            " Se a maioria quebra na 7a, ofereça 6x como teto."
        ),
    },

    "T-06-07": {
        "titulo": "Historico por programa",
        "componente": "Tabela",
        "aba": "Aba 6 - Historico",
        "o_que_mostra": (
            "Para cada programa historico (ex: REFIS 2022): quantos aderiram, concluiram,"
            " quebraram, taxa de conclusao."
        ),
        "o_que_procurar": (
            "Qual programa teve a melhor taxa de conclusao e o que fez de diferente."
        ),
        "como_interpretar": [
            "Taxa de conclusao > 60%: otimo programa - replique as condicoes.",
            "Taxa 46-59%: padrao - ha espaco para melhorar.",
            "Taxa < 45%: programa problematico - nao repita as mesmas condicoes.",
        ],
        "acao_sugerida": (
            "Use o melhor programa historico como template para o proximo."
            " Nao reinvente quando ha dados."
        ),
    },

    "T-06-08": {
        "titulo": "Concentracao geografica",
        "componente": "Tabela",
        "aba": "Aba 6 - Historico",
        "o_que_mostra": (
            "Top 10 bairros por valor da carteira. Para cada bairro: numero de contribuintes,"
            " valor total, percentual do valor total."
        ),
        "o_que_procurar": (
            "Concentracao geografica. Um bairro pode representar 20% da carteira"
            " - permite estrategia geolocalizada."
        ),
        "como_interpretar": [
            "Top 3 bairros > 50% do valor: forte concentracao - pode fazer feirao local.",
            "Distribuicao uniforme: operacao 100% digital faz sentido.",
            "Concentracao em bairros especificos: pode ter problema estrutural (zona inundavel, bairro em crise).",
        ],
        "acao_sugerida": (
            "Se top 3 bairros > 40%: organize feirao de negociacao presencial nesses bairros."
            " Custo baixo, conversao alta."
        ),
    },

    "T-06-09": {
        "titulo": "Cohort pos-campanha",
        "componente": "Tabela",
        "aba": "Aba 6 - Historico",
        "o_que_mostra": (
            "Por cohort (grupo de uma campanha especifica): quantos aderiram, concluiram,"
            " quebraram, voltaram a carteira e foram reabordados com sucesso."
            " Perfil dominante (pagador/quebrado/pulverizado)."
        ),
        "o_que_procurar": (
            "Qual perfil dominante cada campanha atraiu."
            " Revela o tipo de contribuinte que responde a cada tipo de oferta."
        ),
        "como_interpretar": [
            "Perfil 'pagador' dominante: campanha atraiu bons contribuintes - replique condicoes.",
            "Perfil 'quebrado' dominante: oferta atraiu perfil problematico - revise condicoes de entrada.",
            "Perfil 'pulverizado' dominante: grande alcance mas dispersao - pode ter gasto muito orcamento.",
        ],
        "acao_sugerida": (
            "Alinhe a proxima campanha com a cohort que deu melhor resultado historico."
        ),
    },

    # ── Aba 7 - Cenarios ─────────────────────────────────────────────────────

    "T-07-01": {
        "titulo": "Tabela de cenarios",
        "componente": "Grid 4 colunas",
        "aba": "Aba 7 - Cenarios",
        "o_que_mostra": (
            "Tres cenarios (Conservador, Moderado, Agressivo) com linhas: quadrantes"
            " incluidos, contribuintes-alvo, valor-alvo, adesao projetada, recuperacao,"
            " custo operacional, ROI, payback e plateau."
        ),
        "o_que_procurar": (
            "A diferenca entre cenarios. Conservador = so Q1. Moderado = Q1+Q2."
            " Agressivo = Q1+Q2+Q3."
        ),
        "como_interpretar": [
            "Diferenca moderado->agressivo pequena: protesto tera pouco retorno - Q3 e irrecuperavel.",
            "Diferenca grande: protesto vale muito - Q3 tem massa recuperavel.",
            "ROI conservador < 3:1: operacao inviavel mesmo no cenario seguro.",
        ],
        "acao_sugerida": (
            "Apresente SEMPRE os tres cenarios ao cliente. O gestor escolhe o nivel de risco,"
            " nao voce. Recomende o Moderado na maioria dos casos."
        ),
    },

    "T-07-02": {
        "titulo": "Card de aviso - decay nao calibrado",
        "componente": "Banner ambar",
        "aba": "Aba 7 - Cenarios",
        "o_que_mostra": (
            "Aviso sempre que sessoes_analise.decay_calibrado = false. Indica que os rates"
            " usados sao referencias de mercado, nao calibracoes com dados reais."
        ),
        "o_que_procurar": (
            "Se este card esta visivel - se estiver, NUNCA use as projecoes em apresentacao"
            " comercial final."
        ),
        "como_interpretar": [
            "Card visivel: cenario e APROXIMACAO - pode estar errado em +-30-40%.",
            "Card nao visivel: rates foram calibrados com dados da Aba 4 - projecao tem fundamento real.",
        ],
        "acao_sugerida": (
            "Antes de apresentar: va ate a Aba 4, extraia os rates reais das safras historicas,"
            " ajuste os rates dos cenarios na sidebar, e marque decay_calibrado = true."
        ),
    },

    "T-07-03": {
        "titulo": "Trava de sanidade - cenario anomalo",
        "componente": "Banner vermelho",
        "aba": "Aba 7 - Cenarios",
        "o_que_mostra": (
            "Trava automatica que bloqueia o grafico de recuperacao quando algum cenario"
            " projeta > 50% do valor ativo recuperado em 12 meses."
            " Exige override com justificativa textual."
        ),
        "o_que_procurar": (
            "Se a trava disparou, os parametros estao errados."
            " Benchmark: 15-40% em 12 meses."
        ),
        "como_interpretar": [
            "Trava disparou com rates default: erro no dado da carteira - valor ativo subestimado.",
            "Trava disparou com rates modificados: rates calibrados estao errados - revisar Aba 4.",
            "Trava disparou em carteira pequena: pode ser efeito de amostra (< R$ 1M tem numeros volateis).",
        ],
        "acao_sugerida": (
            "NUNCA clique em 'Confirmar override' so para liberar o grafico."
            " Investigue o motivo antes."
        ),
    },

    "T-07-04": {
        "titulo": "Recuperacao cumulativa mes a mes",
        "componente": "Grafico linha (3 series)",
        "aba": "Aba 7 - Cenarios",
        "o_que_mostra": (
            "3 curvas mostrando recuperacao acumulada ao longo de 12 meses para cada cenario."
            " Estrela (*) marca o mes de payback em cada linha."
        ),
        "o_que_procurar": (
            "Formato das curvas. Decay exponencial correto = subida rapida nos primeiros"
            " 3 meses e desaceleracao."
        ),
        "como_interpretar": [
            "Payback M1-M2: operacao altamente lucrativa - pouco comum, desconfiar.",
            "Payback M3-M4: padrao excelente.",
            "Payback M5-M7: operacao viavel.",
            "Payback > M8: operacao arriscada.",
            "Sem payback: operacao inviavel - reformule estrategia.",
        ],
        "acao_sugerida": (
            "O payback e o argumento mais importante para o gestor."
            " 'No cenario moderado o retorno aparece no 3o mes.'"
            " Destaque a estrela na apresentacao."
        ),
    },

    "T-07-05": {
        "titulo": "ROI por cenario",
        "componente": "Grafico barras",
        "aba": "Aba 7 - Cenarios",
        "o_que_mostra": (
            "3 barras (uma por cenario) com ROI no formato X:1"
            " - reais recuperados para cada real investido em custo operacional."
        ),
        "o_que_procurar": (
            "Qual cenario tem melhor ROI. Geralmente nao e o agressivo"
            " - maior escopo exige mais operacao."
        ),
        "como_interpretar": [
            "ROI < 2:1: operacao custa quase tanto quanto recupera - inviavel.",
            "ROI 2-3:1: operacao justa - margem apertada.",
            "ROI 4-6:1: operacao saudavel.",
            "ROI > 6:1: excelente - ou algo esta subestimado (provavelmente custos).",
        ],
        "acao_sugerida": (
            "ROI nao e o unico criterio. Destaque ambos - ROI e valor absoluto - ao cliente."
            " Conservador com ROI 8:1 e recuperacao de R$ 500k pode ser pior que agressivo"
            " com ROI 4:1 e recuperacao de R$ 2M."
        ),
    },

    "T-07-06": {
        "titulo": "Elasticidade de desconto",
        "componente": "Grafico 2 eixos",
        "aba": "Aba 7 - Cenarios",
        "o_que_mostra": (
            "Curva que mostra como a adesao (eixo esquerdo) e o valor liquido recuperado"
            " (eixo direito) variam conforme o desconto oferecido (eixo X, de 0% a 50%)."
            " Linha vertical marca o desconto otimo."
        ),
        "o_que_procurar": (
            "O ponto otimo da curva de valor liquido - o desconto que maximiza a recuperacao"
            " (geralmente 20-30%)."
        ),
        "como_interpretar": [
            "Otimo em 15-20%: carteira pouco sensivel a desconto - contribuintes aderem com pouco estimulo.",
            "Otimo em 25-30%: padrao.",
            "Otimo em >35%: carteira muito resistente - contribuintes so aderem com desconto agressivo.",
            "Curva muito flat: elasticidade baixa - desconto tem pouco efeito na adesao.",
        ],
        "acao_sugerida": (
            "O desconto otimo e o numero que vai na proposta comercial. Nao arredonde para"
            " cima nem para baixo - o otimo matematico maximiza o retorno real do municipio."
        ),
    },
}


def get_tooltip(tip_id: str) -> dict:
    """Retorna o tooltip pelo ID ou levanta KeyError com mensagem clara."""
    if tip_id not in TOOLTIPS:
        raise KeyError(
            f"Tooltip '{tip_id}' nao encontrado. IDs disponiveis: {sorted(TOOLTIPS)}"
        )
    return TOOLTIPS[tip_id]
