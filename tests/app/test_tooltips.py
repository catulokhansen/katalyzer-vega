"""Testes da infraestrutura de tooltips — Fase 2 (49 tooltips completos)."""
from __future__ import annotations

import re

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


# ── 8. Cobertura total — 49 IDs esperados ────────────────────────────────────

EXPECTED_IDS = [
    "T-01-01", "T-01-02", "T-01-03", "T-01-04", "T-01-05",
    "T-01-06", "T-01-07", "T-01-08", "T-01-09", "T-01-10", "T-01-11",
    "T-02-01", "T-02-02", "T-02-03",
    "T-03-01", "T-03-02", "T-03-03", "T-03-04", "T-03-05",
    "T-04-01", "T-04-02", "T-04-03", "T-04-04", "T-04-05",
    "T-04-06", "T-04-07", "T-04-08",
    "T-05-01", "T-05-02", "T-05-03", "T-05-04", "T-05-05",
    "T-05-06", "T-05-07",
    "T-06-01", "T-06-02", "T-06-03", "T-06-04", "T-06-05",
    "T-06-06", "T-06-07", "T-06-08", "T-06-09",
    "T-07-01", "T-07-02", "T-07-03", "T-07-04", "T-07-05", "T-07-06",
]


def test_todos_os_49_ids_existem():
    from vega.app.components.tooltips_content import TOOLTIPS

    faltando = [tid for tid in EXPECTED_IDS if tid not in TOOLTIPS]
    assert not faltando, f"IDs faltando no TOOLTIPS: {faltando}"
    assert len(TOOLTIPS) == 49, f"Esperados 49 tooltips, encontrados {len(TOOLTIPS)}"


# ── 9. Sem marcadores TODO Fase 2 ────────────────────────────────────────────

def test_nenhum_todo_fase2_restante():
    import pathlib
    arquivo = pathlib.Path(__file__).parent.parent.parent / "vega" / "app" / "components" / "tooltips_content.py"
    conteudo = arquivo.read_text(encoding="utf-8")
    assert "TODO Fase 2" not in conteudo, "Ainda ha marcadores 'TODO Fase 2' em tooltips_content.py"


# ── 10. Formato dos IDs padronizado ──────────────────────────────────────────

def test_formato_ids_padronizado():
    from vega.app.components.tooltips_content import TOOLTIPS

    padrao = re.compile(r"^T-\d{2}-\d{2}$")
    for tip_id in TOOLTIPS:
        assert padrao.match(tip_id), f"ID fora do padrao T-NN-NN: {tip_id!r}"


# ── 11. Cada tooltip aplicado em alguma aba ───────────────────────────────────

def test_cada_tooltip_aplicado_em_alguma_aba():
    import pathlib

    tabs_dir = pathlib.Path(__file__).parent.parent.parent / "vega" / "app" / "tabs"
    alerts_file = pathlib.Path(__file__).parent.parent.parent / "vega" / "app" / "components" / "alerts.py"

    todos_arquivos = list(tabs_dir.glob("*.py")) + [alerts_file]
    conteudo_total = "\n".join(f.read_text(encoding="utf-8") for f in todos_arquivos)

    nao_aplicados = [tid for tid in EXPECTED_IDS if f'"{tid}"' not in conteudo_total]
    assert not nao_aplicados, (
        f"Tooltips nao aplicados em nenhuma aba: {nao_aplicados}"
    )
