"""Testes obrigatórios — alertas de Q1 e sanidade de cenários.

C1.4: verificar_q1_dimensao — Referência: CHANGES_V1_1.md seção C1.4.
C1.2: _validar_sanidade_cenarios — Referência: CHANGES_V1_1.md seção C1.2.
"""
from __future__ import annotations

import pandas as pd
import pytest

from vega.app.tabs.tab_scoring import verificar_q1_dimensao
from vega.app.tabs.tab_cenarios import _validar_sanidade_cenarios


# ── C1.4 — verificar_q1_dimensao ─────────────────────────────────────────────

def _df_q(q1: int, outros: int = 400) -> pd.DataFrame:
    """Helper: DataFrame com count_contrib para Q1 e demais quadrantes."""
    return pd.DataFrame({
        "quadrante":    ["Q1", "Q2", "Q3", "Q4"],
        "count_contrib": [q1, round(outros * 0.4), round(outros * 0.35), round(outros * 0.25)],
    })


def test_alerta_q1_vazio():
    """Q1 com 0 contribuintes → retorna 'vazio'."""
    df    = _df_q(q1=0, outros=500)
    total = int(df["count_contrib"].sum())
    assert verificar_q1_dimensao(df, total) == "vazio"


def test_alerta_q1_normal():
    """Q1 com ~10% dos contribuintes → retorna None (dentro da faixa operacional)."""
    df    = _df_q(q1=50, outros=450)   # 50/500 = 10%
    total = int(df["count_contrib"].sum())
    assert verificar_q1_dimensao(df, total) is None


def test_alerta_q1_excessivo():
    """Q1 com 25% dos contribuintes → retorna 'excessivo'."""
    df    = _df_q(q1=125, outros=375)  # 125/500 = 25%
    total = int(df["count_contrib"].sum())
    assert verificar_q1_dimensao(df, total) == "excessivo"


def test_alerta_q1_borderline():
    """17.9% não alerta; 18.1% alerta (testa o threshold de 18%)."""
    # 179/1000 = 17.9% → abaixo do limite
    df_below = pd.DataFrame({
        "quadrante":     ["Q1", "Q2"],
        "count_contrib": [179, 821],
    })
    # 181/1000 = 18.1% → acima do limite
    df_above = pd.DataFrame({
        "quadrante":     ["Q1", "Q2"],
        "count_contrib": [181, 819],
    })
    assert verificar_q1_dimensao(df_below, 1000) is None
    assert verificar_q1_dimensao(df_above, 1000) == "excessivo"


# ── C1.2 — _validar_sanidade_cenarios ────────────────────────────────────────

def _res(cons_pct: float, mod_pct: float, agr_pct: float, valor_ativo: int = 10_000_000) -> dict:
    """Helper: cria res dict com curvas de 1 ponto representando recuperação percentual.

    curva[-1] deve estar em R$ (float). _validar_sanidade_cenarios faz:
        recup_12m_cents = round(curva[-1] * 100)
        pct = recup_12m_cents / valor_ativo_cents
    Logo: curva[-1] = pct/100 * valor_ativo_cents / 100
    """
    def _curva(pct: float) -> list[float]:
        return [round(valor_ativo * (pct / 100) / 100, 2)]

    return {
        "cons": {"curva": _curva(cons_pct)},
        "mod":  {"curva": _curva(mod_pct)},
        "agr":  {"curva": _curva(agr_pct)},
    }


def test_sanidade_cenario_normal():
    """Cenário com 20% em 12m não ativa alerta (abaixo do limite de 50%)."""
    res = _res(cons_pct=10.0, mod_pct=15.0, agr_pct=20.0)
    assert _validar_sanidade_cenarios(10_000_000, res) is None


def test_sanidade_cenario_anomalo():
    """Cenário agressivo com 60% em 12m ativa alerta apenas para ele."""
    res     = _res(cons_pct=10.0, mod_pct=20.0, agr_pct=60.0)
    result  = _validar_sanidade_cenarios(10_000_000, res)
    assert result is not None
    nomes   = [a["cenario"] for a in result["anomalias"]]
    assert "Agressivo" in nomes
    assert "Conservador" not in nomes
    assert "Moderado" not in nomes


def test_sanidade_multiplos_cenarios_anomalos():
    """Conservador e moderado ambos >50% — ambos listados nas anomalias."""
    res    = _res(cons_pct=55.0, mod_pct=65.0, agr_pct=20.0)
    result = _validar_sanidade_cenarios(10_000_000, res)
    assert result is not None
    nomes  = [a["cenario"] for a in result["anomalias"]]
    assert "Conservador" in nomes
    assert "Moderado" in nomes
    assert "Agressivo" not in nomes
