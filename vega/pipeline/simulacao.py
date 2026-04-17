"""Etapa 4 — Simulação de cenários de recuperação.

Referência: SAD_KatalyzerVega_v1.docx seção 5.4 (cenários conservador/
moderado/agressivo) e Pipeline_KatalyzerVega_v1.docx seção 1 (visão geral).

Escopo deste módulo:
  - decay_curve: curva mensal de recuperação sobre o valor-alvo.
  - calcular_payback: mês em que a recuperação acumulada cobre o custo.
  - calcular_elasticidade: adesão percentual esperada em função do desconto.
  - encontrar_desconto_otimo: melhor ponto de equilíbrio adesão × valor.

Toda a simulação trabalha em CENTAVOS e em PERCENTUAIS — nunca em float
de moeda. Valores monetários só viram float na camada de formatação.

RN-06: enquanto sessoes_analise.decay_calibrado = false, a UI deve
exibir o card de aviso âmbar no gráfico de recuperação da Aba 7.
Este módulo NÃO controla a flag — ele apenas gera as curvas.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence


# Descontos percentuais avaliados para a elasticidade
DESCONTOS_AVALIADOS_PCT: tuple[int, ...] = (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50)


@dataclass(frozen=True)
class PontoElasticidade:
    """Um ponto da curva de elasticidade (desconto × adesão × valor recuperado)."""
    desconto_pct: int
    adesao_pct: float
    valor_recuperado_cents: int


def decay_curve(
    valor_alvo_cents: int,
    rate: float,
    ceiling: float,
    meses: int = 12,
) -> list[float]:
    """Gera curva de recuperação cumulativa mensal com teto (ceiling) realista.

    Modelo exponencial: converge assintoticamente para ceiling * valor_alvo.
    Benchmarks de DA municipal com plataforma de protesto ativa: 15-40% do
    valor-alvo em 12 meses (C1.1 — rates realistas).

    Args:
        valor_alvo_cents: valor total do escopo do cenário em centavos.
        rate: velocidade de convergência para o ceiling (típico: 0.04–0.08).
        ceiling: fração máxima do valor_alvo efetivamente recuperável (0.0–1.0).
        meses: horizonte de projeção (default 12).

    Retorna lista de valores em R$ (float) acumulados mês a mês.
    """
    if meses <= 0:
        return []
    if valor_alvo_cents <= 0:
        return [0.0] * meses
    return [
        round(valor_alvo_cents * ceiling * (1 - math.exp(-rate * m)) / 100, 2)
        for m in range(1, meses + 1)
    ]


def calcular_payback(curva: Sequence[float], custo_reais: float) -> Optional[int]:
    """Retorna o mês (1-based) em que a recuperação acumulada cobre o custo.

    Custo em reais. Curva em R$ cumulativos (output de decay_curve).
    Retorna None se a curva não cobre o custo no horizonte fornecido.
    """
    for i, val in enumerate(curva, start=1):
        if val >= custo_reais:
            return i
    return None


def _adesao_para_desconto(desconto_pct: int, adesao_base: float) -> float:
    """Curva de adesão assumida em função do desconto.

    Elasticidade fraca em descontos pequenos (0–10%) e saturação após 40%.
    Baseline (desconto 0) = adesao_base. Ganho máximo: ~4× em 40%+.

    Modelo heurístico — deve ser recalibrado com dados de campanhas
    reais assim que a carteira de cohortes_campanha tiver volume.
    """
    desconto = max(0, min(desconto_pct, 50))
    # Logística simples: partida em base, assíntota em ~base * 4.5
    fator = 1 + 3.5 * (desconto / 50) ** 1.4
    return round(adesao_base * fator, 2)


def calcular_elasticidade(
    valor_alvo_cents: int,
    adesao_base: float = 12.0,
    descontos_pct: Sequence[int] = DESCONTOS_AVALIADOS_PCT,
) -> list[PontoElasticidade]:
    """Gera a curva de elasticidade desconto × adesão × valor recuperado.

    Para cada desconto avaliado:
      - adesão é calculada via _adesao_para_desconto
      - valor_recuperado = valor_alvo * adesão% * (1 - desconto%)

    ``adesao_base`` é a adesão esperada SEM desconto (em %).
    ``valor_alvo_cents`` é o valor total da carteira-alvo em centavos.
    """
    pontos: list[PontoElasticidade] = []
    for d in descontos_pct:
        adesao_pct = _adesao_para_desconto(d, adesao_base)
        fracao_paga = (adesao_pct / 100) * (1 - d / 100)
        valor_recuperado = round(valor_alvo_cents * fracao_paga)
        pontos.append(PontoElasticidade(
            desconto_pct=int(d),
            adesao_pct=adesao_pct,
            valor_recuperado_cents=valor_recuperado,
        ))
    return pontos


def encontrar_desconto_otimo(
    elasticidade: Sequence[PontoElasticidade],
) -> Optional[PontoElasticidade]:
    """Retorna o ponto que maximiza valor_recuperado_cents.

    Em caso de empate (idêntico valor), retorna o de MENOR desconto — o
    cliente prefere ceder o mínimo possível. Retorna None se a lista
    estiver vazia.
    """
    if not elasticidade:
        return None
    melhor = elasticidade[0]
    for p in elasticidade[1:]:
        if p.valor_recuperado_cents > melhor.valor_recuperado_cents:
            melhor = p
        elif (
            p.valor_recuperado_cents == melhor.valor_recuperado_cents
            and p.desconto_pct < melhor.desconto_pct
        ):
            melhor = p
    return melhor
