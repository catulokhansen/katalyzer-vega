"""Testes obrigatórios — decay_curve com ceiling realista (C1.1).

Referência: CHANGES_V1_1.md seção C1.1.
"""
from __future__ import annotations

import pytest

from vega.pipeline.simulacao import decay_curve


def test_decay_curve_respeita_ceiling():
    """Para rate alto e ceiling baixo, recuperação em 12m deve estar próxima do
    ceiling * valor_alvo — não do valor_alvo integral."""
    valor_alvo = 10_000_000  # R$ 100.000 em centavos
    rate    = 0.80
    ceiling = 0.25
    curva   = decay_curve(valor_alvo, rate, ceiling, meses=12)

    recup_12m_cents = round(curva[-1] * 100)
    teto_cents      = round(ceiling * valor_alvo)

    # Nunca ultrapassa o teto (1% de tolerância de arredondamento)
    assert recup_12m_cents <= round(teto_cents * 1.01), (
        f"Recuperação {recup_12m_cents} excede ceiling {teto_cents}"
    )
    # Muito abaixo do valor integral
    assert recup_12m_cents < valor_alvo, (
        "Recuperação não deve exceder o valor-alvo integral"
    )


def test_decay_curve_valores_monotonicos():
    """Cada mês n+1 deve ter recuperação acumulada >= mês n (curva nunca decresce)."""
    curva = decay_curve(5_000_000, rate=0.06, ceiling=0.32, meses=12)
    for i in range(len(curva) - 1):
        assert curva[i + 1] >= curva[i], (
            f"Curva não é monotônica: mês {i + 1} ({curva[i]}) > mês {i + 2} ({curva[i + 1]})"
        )


def test_decay_curve_defaults_realistas():
    """Com rate/ceiling do cenário moderado, recuperação em 12m deve estar entre 10-20%."""
    valor_alvo = 100_000_000  # R$ 1.000.000 em centavos
    curva      = decay_curve(valor_alvo, rate=0.06, ceiling=0.32, meses=12)

    recup_12m_cents = round(curva[-1] * 100)
    pct             = recup_12m_cents / valor_alvo

    assert 0.10 <= pct <= 0.20, (
        f"Recuperação moderada fora do benchmark 10-20%: {pct:.1%}"
    )
