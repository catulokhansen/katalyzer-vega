"""Conteudo dos tooltips contextuais do Katalyzer Vega.

Fase 1: apenas T-01-01, T-01-02 e T-01-06 populados.
Os demais estao marcados como TODO Fase 2.
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

    # TODO Fase 2 — T-01-03
    # TODO Fase 2 — T-01-04
    # TODO Fase 2 — T-01-05

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

    # TODO Fase 2 — T-01-07
    # TODO Fase 2 — T-01-08
    # TODO Fase 2 — T-01-09
    # TODO Fase 2 — T-01-10
    # TODO Fase 2 — T-01-11

    # ── Aba 2 — Segmentacao ──────────────────────────────────────────────────

    # TODO Fase 2 — T-02-01
    # TODO Fase 2 — T-02-02
    # TODO Fase 2 — T-02-03

    # ── Aba 3 — Scoring ──────────────────────────────────────────────────────

    # TODO Fase 2 — T-03-01
    # TODO Fase 2 — T-03-02
    # TODO Fase 2 — T-03-03
    # TODO Fase 2 — T-03-04
    # TODO Fase 2 — T-03-05

    # ── Aba 4 — Safra & Aging ────────────────────────────────────────────────

    # TODO Fase 2 — T-04-01
    # TODO Fase 2 — T-04-02
    # TODO Fase 2 — T-04-03
    # TODO Fase 2 — T-04-04
    # TODO Fase 2 — T-04-05
    # TODO Fase 2 — T-04-06
    # TODO Fase 2 — T-04-07
    # TODO Fase 2 — T-04-08

    # ── Aba 5 — Contactabilidade ─────────────────────────────────────────────

    # TODO Fase 2 — T-05-01
    # TODO Fase 2 — T-05-02
    # TODO Fase 2 — T-05-03
    # TODO Fase 2 — T-05-04
    # TODO Fase 2 — T-05-05
    # TODO Fase 2 — T-05-06
    # TODO Fase 2 — T-05-07

    # ── Aba 6 — Historico ────────────────────────────────────────────────────

    # TODO Fase 2 — T-06-01
    # TODO Fase 2 — T-06-02
    # TODO Fase 2 — T-06-03
    # TODO Fase 2 — T-06-04
    # TODO Fase 2 — T-06-05
    # TODO Fase 2 — T-06-06
    # TODO Fase 2 — T-06-07
    # TODO Fase 2 — T-06-08
    # TODO Fase 2 — T-06-09

    # ── Aba 7 — Cenarios ─────────────────────────────────────────────────────

    # TODO Fase 2 — T-07-01
    # TODO Fase 2 — T-07-02
    # TODO Fase 2 — T-07-03
    # TODO Fase 2 — T-07-04
    # TODO Fase 2 — T-07-05
    # TODO Fase 2 — T-07-06
}


def get_tooltip(tip_id: str) -> dict:
    """Retorna o tooltip pelo ID ou levanta KeyError com mensagem clara."""
    if tip_id not in TOOLTIPS:
        raise KeyError(
            f"Tooltip '{tip_id}' nao encontrado. IDs disponiveis: {sorted(TOOLTIPS)}"
        )
    return TOOLTIPS[tip_id]
