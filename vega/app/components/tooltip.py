"""Componente de tooltip contextual estatico para o Katalyzer Vega."""
from __future__ import annotations

from dash import html

from vega.app.components.tooltips_content import get_tooltip
from vega.app.constants import (
    AMBER_BG,
    CYAN_BG,
    GREEN_BG,
    VIOLET,
    VIOLET_BG,
)

_CARD_STYLE: dict = {
    "position": "absolute",
    "zIndex": 9999,
    "top": "calc(100% + 6px)",
    "left": 0,
    "maxWidth": "360px",
    "width": "360px",
    "background": "#fff",
    "border": "1px solid #E5E7EB",
    "borderRadius": "8px",
    "boxShadow": "0 8px 24px rgba(0,0,0,.12)",
    "display": "none",
    "animation": "vega-tooltip-fadein 150ms ease",
    "fontFamily": "'Poppins', system-ui, sans-serif",
}

_BLOCK_BASE: dict = {
    "padding": "8px 12px",
    "fontSize": "12px",
    "lineHeight": "1.6",
    "color": "#374151",
}

_BLOCK_LABEL: dict = {
    "fontSize": "10px",
    "fontWeight": "600",
    "textTransform": "uppercase",
    "letterSpacing": "0.6px",
    "marginBottom": "4px",
    "color": "#6B7280",
}

# CSS de animacao injetado uma vez via um componente no layout raiz.
# Como nao podemos usar arquivos .css externos, incluimos aqui como referencia.
# O app.py deve incluir vega_tooltip_css() no layout antes das tabs.
_TOOLTIP_CSS = """
@keyframes vega-tooltip-fadein {
    from { opacity: 0; transform: translateY(-4px); }
    to   { opacity: 1; transform: translateY(0); }
}
.vega-tooltip-wrapper {
    position: relative;
    display: inline-flex;
    align-items: center;
}
.vega-tooltip-wrapper:hover .vega-tooltip-card,
.vega-tooltip-card:hover {
    display: block !important;
}
.vega-tooltip-icon:focus-visible {
    outline: 2px solid #7B2CBF;
    outline-offset: 2px;
    border-radius: 50%;
}
"""


def vega_tooltip_css() -> str:
    """Retorna as regras CSS dos tooltips para injetar via app.index_string."""
    return _TOOLTIP_CSS


def tooltip(tip_id: str) -> html.Span:
    """Renderiza icone (i) com card de tooltip ao passar o cursor.

    Args:
        tip_id: ID do tooltip conforme TOOLTIPS em tooltips_content.py (ex: 'T-01-01').

    Returns:
        html.Span com o icone e o card de conteudo.
    """
    data = get_tooltip(tip_id)

    # Bloco "Como interpretar" — lista de bullets
    interpretar_items = [
        html.Li(item, style={"marginBottom": "2px"})
        for item in data["como_interpretar"]
    ]

    card = html.Div(
        [
            # Header
            html.Div(
                [
                    html.Span(
                        data["titulo"],
                        style={
                            "fontFamily": "'Sora', system-ui, sans-serif",
                            "fontSize": "14px",
                            "fontWeight": "700",
                            "color": "#111827",
                        },
                    ),
                    html.Span(
                        data["componente"],
                        style={
                            "fontSize": "10px",
                            "fontWeight": "500",
                            "color": "#6B7280",
                            "marginLeft": "8px",
                            "padding": "1px 6px",
                            "background": "#F3F4F6",
                            "borderRadius": "4px",
                        },
                    ),
                ],
                style={
                    "padding": "10px 12px 8px",
                    "borderBottom": "1px solid #F3F4F6",
                    "display": "flex",
                    "alignItems": "center",
                    "flexWrap": "wrap",
                    "gap": "6px",
                },
            ),
            # Bloco O que mostra (cyan)
            html.Div(
                [
                    html.Div("O que mostra", style=_BLOCK_LABEL),
                    html.Div(data["o_que_mostra"], style={"fontSize": "12px", "lineHeight": "1.6"}),
                ],
                style={**_BLOCK_BASE, "background": CYAN_BG},
            ),
            # Bloco O que procurar (violet)
            html.Div(
                [
                    html.Div("O que procurar", style=_BLOCK_LABEL),
                    html.Div(data["o_que_procurar"], style={"fontSize": "12px", "lineHeight": "1.6"}),
                ],
                style={**_BLOCK_BASE, "background": VIOLET_BG},
            ),
            # Bloco Como interpretar (amber)
            html.Div(
                [
                    html.Div("Como interpretar", style=_BLOCK_LABEL),
                    html.Ul(
                        interpretar_items,
                        style={
                            "margin": "0",
                            "paddingLeft": "16px",
                            "fontSize": "12px",
                            "lineHeight": "1.6",
                        },
                    ),
                ],
                style={**_BLOCK_BASE, "background": AMBER_BG},
            ),
            # Bloco Acao sugerida (green)
            html.Div(
                [
                    html.Div("Acao sugerida", style=_BLOCK_LABEL),
                    html.Div(data["acao_sugerida"], style={"fontSize": "12px", "lineHeight": "1.6"}),
                ],
                style={**_BLOCK_BASE, "background": GREEN_BG},
            ),
            # Footer com ID
            html.Div(
                tip_id,
                style={
                    "padding": "6px 12px",
                    "fontSize": "10px",
                    "color": "#9CA3AF",
                    "fontFamily": "'JetBrains Mono', monospace",
                    "borderTop": "1px solid #F3F4F6",
                    "background": "#FAFAFA",
                    "borderRadius": "0 0 8px 8px",
                },
            ),
        ],
        className="vega-tooltip-card",
        role="tooltip",
        id=f"tooltip-card-{tip_id}",
        style=_CARD_STYLE,
    )

    return html.Span(
        [
            html.Span(
                "\u24d8",  # ⓘ
                className="vega-tooltip-icon",
                tabIndex=0,
                **{"aria-label": f"Ajuda: {data['titulo']}"},
                style={
                    "display": "inline-flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "width": "14px",
                    "height": "14px",
                    "fontSize": "12px",
                    "color": VIOLET,
                    "cursor": "help",
                    "borderRadius": "50%",
                    "flexShrink": 0,
                },
            ),
            card,
        ],
        className="vega-tooltip-wrapper",
        id=f"tooltip-wrapper-{tip_id}",
    )
