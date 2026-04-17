"""Testes da infraestrutura de tooltips — Fase 1 (PoC com 3 tooltips)."""
from __future__ import annotations

import pytest
from dash import html


# ── 1. Carregamento do modulo ────────────────────────────────────────────────

def test_tooltip_content_carrega_sem_erro():
    from vega.app.components.tooltips_content import TOOLTIPS

    assert isinstance(TOOLTIPS, dict)
    assert len(TOOLTIPS) > 0


# ── 2. Estrutura correta ──────────────────────────────────────────────────────

_CHAVES_OBRIGATORIAS = {"titulo", "componente", "aba", "o_que_mostra", "o_que_procurar", "como_interpretar", "acao_sugerida"}


def test_get_tooltip_retorna_estrutura_correta():
    from vega.app.components.tooltips_content import get_tooltip

    data = get_tooltip("T-01-01")
    assert isinstance(data, dict)
    assert _CHAVES_OBRIGATORIAS == set(data.keys())


# ── 3. KeyError em ID inexistente ─────────────────────────────────────────────

def test_get_tooltip_id_inexistente_levanta_keyerror():
    from vega.app.components.tooltips_content import get_tooltip

    with pytest.raises(KeyError, match="T-99-99"):
        get_tooltip("T-99-99")


# ── 4. como_interpretar e lista ───────────────────────────────────────────────

def test_como_interpretar_e_lista():
    from vega.app.components.tooltips_content import TOOLTIPS

    for tip_id, data in TOOLTIPS.items():
        assert isinstance(data["como_interpretar"], list), (
            f"{tip_id}: 'como_interpretar' deve ser list[str], got {type(data['como_interpretar'])}"
        )
        for item in data["como_interpretar"]:
            assert isinstance(item, str), (
                f"{tip_id}: cada item de 'como_interpretar' deve ser str, got {type(item)}"
            )


# ── 5. Nenhum campo str vazio ─────────────────────────────────────────────────

_CAMPOS_STR = {"titulo", "componente", "aba", "o_que_mostra", "o_que_procurar", "acao_sugerida"}


def test_tooltip_campos_nao_vazios():
    from vega.app.components.tooltips_content import TOOLTIPS

    for tip_id, data in TOOLTIPS.items():
        for campo in _CAMPOS_STR:
            assert data[campo].strip(), (
                f"{tip_id}: campo '{campo}' esta vazio"
            )
        assert len(data["como_interpretar"]) > 0, (
            f"{tip_id}: 'como_interpretar' nao pode ser lista vazia"
        )
        for item in data["como_interpretar"]:
            assert item.strip(), f"{tip_id}: item vazio em 'como_interpretar'"


# ── 6. Componente renderiza html.Span ─────────────────────────────────────────

def test_component_tooltip_renderiza():
    from vega.app.components.tooltip import tooltip

    result = tooltip("T-01-01")
    assert isinstance(result, html.Span)


# ── 7. Nenhum caractere tipografico nos textos ────────────────────────────────

_TIPOGRAFICOS = [
    "\u2018",  # aspas simples esquerda
    "\u2019",  # aspas simples direita
    "\u201c",  # aspas duplas esquerda
    "\u201d",  # aspas duplas direita
    "\u2013",  # en dash
    "\u2014",  # em dash
]


def test_tooltip_sem_caracteres_tipograficos():
    from vega.app.components.tooltips_content import TOOLTIPS

    for tip_id, data in TOOLTIPS.items():
        for campo, valor in data.items():
            textos = valor if isinstance(valor, list) else [valor]
            for texto in textos:
                for char in _TIPOGRAFICOS:
                    assert char not in texto, (
                        f"{tip_id}.{campo}: caractere tipografico proibido {repr(char)} encontrado"
                    )
