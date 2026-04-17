"""Geração de insights via OpenAI por aba."""
from __future__ import annotations

import os

_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
_SYSTEM = (
    "Você é um analista sênior de carteiras de dívida ativa municipal. "
    "Responda sempre em português. Seja direto e use os números fornecidos."
)


def _completar(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
        max_tokens=800,
    )
    return resp.choices[0].message.content


def gerar_insights_diagnostico(metricas: dict) -> str:
    """Insights cruzados da Aba 1 — Diagnóstico."""
    prompt = f"""
Analise os dados abaixo e gere 4 insights acionáveis.
Cada insight: título curto + descrição com números reais + ação recomendada.

Dados:
{metricas}
"""
    return _completar(prompt)


def gerar_insights_segmentacao(metricas: dict) -> str:
    """Insights cruzados da Aba 2 — Segmentação."""
    prompt = f"""
Analise a segmentação da carteira abaixo e gere 4 insights acionáveis.
Foque em: concentração de valor por faixa, proporção PF vs PJ, e oportunidades de campanha segmentada.
Cada insight: título curto + descrição com números reais + ação recomendada.

Dados:
{metricas}
"""
    return _completar(prompt)


def gerar_insights_scoring(metricas: dict) -> str:
    """Insights cruzados da Aba 3 — Scoring."""
    prompt = f"""
Analise a distribuição de scores e quadrantes abaixo e gere 4 insights acionáveis.
Foque em: dimensão do Q1 vs esforço operacional, CDAs em Q3 para execução fiscal, e oportunidades de recuperação rápida.
Cada insight: título curto + descrição com números reais + ação recomendada.

Dados:
{metricas}
"""
    return _completar(prompt)


def gerar_insights_safra_aging(metricas: dict) -> str:
    """Insights cruzados da Aba 4 — Safra & Aging."""
    prompt = f"""
Analise os dados de safra e aging da carteira abaixo e gere 4 insights acionáveis.
Foque em: safra com melhor desempenho, risco de prescrição iminente (bruta vs líquida),
concentração de valor por faixa etária e padrão sazonal de inscrições vs recuperações.
Cada insight: título curto + descrição com números reais + ação recomendada.

Dados:
{metricas}
"""
    return _completar(prompt)


def gerar_insights_contactabilidade(metricas: dict) -> str:
    """Insights cruzados da Aba 5 — Contactabilidade."""
    prompt = f"""
Analise os dados de contactabilidade da carteira abaixo e gere 4 insights acionáveis.
Foque em: percentual de incontactáveis e seu valor em risco, lacunas de cobertura por canal,
oportunidades de enriquecimento de dados e segmentos prioritários para campanha digital.
Cada insight: título curto + descrição com números reais + ação recomendada.

Dados:
{metricas}
"""
    return _completar(prompt)


def gerar_insights_historico(metricas: dict) -> str:
    """Insights cruzados da Aba 6 — Histórico de Parcelamento."""
    prompt = f"""
Analise os dados históricos de parcelamento da carteira abaixo e gere 4 insights acionáveis.
Foque em: taxa de reincidência e seu impacto no valor da carteira, padrão de quebra de parcelamento,
programas com melhor e pior desempenho e oportunidades de reabordagem de devedores que quebraram.
Cada insight: título curto + descrição com números reais + ação recomendada.

Dados:
{metricas}
"""
    return _completar(prompt)


def gerar_insights_cenarios(metricas: dict) -> str:
    """Insights cruzados da Aba 7 — Cenários de Recuperação."""
    prompt = f"""
Analise os cenários de recuperação abaixo e gere 4 insights acionáveis.
Foque em: diferença de ROI entre cenários, payback do moderado vs agressivo,
ponto ótimo de desconto pela curva de elasticidade e recomendação de abordagem
considerando o perfil de risco da carteira.
Cada insight: título curto + descrição com números reais + ação recomendada.

Dados:
{metricas}
"""
    return _completar(prompt)


class InsightGenerator:
    """Ponto único para gerar insights de qualquer aba via índice."""

    _FUNCS = {
        0: gerar_insights_diagnostico,
        1: gerar_insights_segmentacao,
        2: gerar_insights_scoring,
        3: gerar_insights_safra_aging,
        4: gerar_insights_contactabilidade,
        5: gerar_insights_historico,
        6: gerar_insights_cenarios,
    }

    def gerar(self, aba: int, metricas: dict) -> str:
        if not os.environ.get("OPENAI_API_KEY"):
            return "Configure OPENAI_API_KEY para gerar insights com IA."
        fn = self._FUNCS.get(aba)
        if fn is None:
            return f"Aba {aba} não suportada."
        return fn(metricas)
