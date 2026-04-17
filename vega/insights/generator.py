"""Geração de insights via ChatGPT (session token) ou OpenAI API (fallback)."""
from __future__ import annotations

import json
import os
import uuid

_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
_SYSTEM = (
    "Você é um analista sênior de carteiras de dívida ativa municipal. "
    "Responda sempre em português. Seja direto e use os números fornecidos."
)

_CONVERSATION_URL = "https://chat.openai.com/backend-api/conversation"
_HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Origin": "https://chat.openai.com",
    "Referer": "https://chat.openai.com/",
}


def _completar_via_access_token(prompt: str, access_token: str) -> str:
    import httpx

    payload = {
        "action": "next",
        "messages": [{
            "id": str(uuid.uuid4()),
            "author": {"role": "user"},
            "content": {
                "content_type": "text",
                "parts": [f"{_SYSTEM}\n\n{prompt}"],
            },
        }],
        "model": _MODEL,
        "timezone_offset_min": -180,
        "history_and_training_disabled": True,
        "conversation_mode": {"kind": "primary_assistant"},
    }
    headers = {
        **_HEADERS_BASE,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    resultado = ""
    with httpx.Client(timeout=90) as client:
        with client.stream("POST", _CONVERSATION_URL, json=payload, headers=headers) as resp:
            if resp.status_code == 401:
                raise RuntimeError(
                    "Token expirado. Execute novamente: python scripts/auth_chatgpt.py"
                )
            resp.raise_for_status()
            for linha in resp.iter_lines():
                if not linha.startswith("data: "):
                    continue
                dados = linha[6:]
                if dados == "[DONE]":
                    break
                try:
                    partes = (
                        json.loads(dados)
                        .get("message", {})
                        .get("content", {})
                        .get("parts", [])
                    )
                    if partes and isinstance(partes[0], str):
                        resultado = partes[0]
                except (json.JSONDecodeError, KeyError):
                    continue

    return resultado or "Resposta vazia recebida do ChatGPT."


def _completar_via_api(prompt: str, api_key: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
        max_tokens=800,
    )
    return resp.choices[0].message.content


def _completar(prompt: str) -> str:
    access_token = os.environ.get("CHATGPT_ACCESS_TOKEN")
    if access_token:
        return _completar_via_access_token(prompt, access_token)
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        return _completar_via_api(prompt, api_key)
    raise RuntimeError(
        "Configure CHATGPT_ACCESS_TOKEN (recomendado) "
        "ou OPENAI_API_KEY no .env para gerar insights."
    )


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
        tem_access_token = bool(os.environ.get("CHATGPT_ACCESS_TOKEN"))
        tem_api_key = bool(os.environ.get("OPENAI_API_KEY"))
        if not tem_access_token and not tem_api_key:
            return (
                "Configure CHATGPT_ACCESS_TOKEN (recomendado) "
                "ou OPENAI_API_KEY no .env para gerar insights."
            )
        fn = self._FUNCS.get(aba)
        if fn is None:
            return f"Aba {aba} não suportada."
        return fn(metricas)
