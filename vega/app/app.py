"""Katalyzer Vega — entrypoint Dash.

Sobe na porta 8050 com sidebar vazia e 7 tabs sem conteúdo.
Conteúdo de cada aba será carregado via lazy callbacks (vega/app/tabs/).
"""
from __future__ import annotations

import os

from dash import Dash, dcc, html

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


TABS = [
    ("diagnostico", "1. Diagnóstico"),
    ("segmentacao", "2. Segmentação"),
    ("scoring", "3. Scoring"),
    ("safra_aging", "4. Safra & Aging"),
    ("contactabilidade", "5. Contactabilidade"),
    ("historico", "6. Histórico"),
    ("cenarios", "7. Cenários"),
]


def _sidebar() -> html.Div:
    return html.Div(
        [
            html.H2("Katalyzer Vega", style={"margin": "0 0 4px 0"}),
            html.Div(
                "Análise de carteira de dívida ativa",
                style={"fontSize": 12, "color": "#6b7280", "marginBottom": 24},
            ),
            html.Div(
                "Sidebar — parâmetros (TBD)",
                style={"fontSize": 12, "color": "#9ca3af"},
            ),
        ],
        style={
            "width": 280,
            "padding": "24px 20px",
            "borderRight": "1px solid #e5e7eb",
            "background": "#fafafa",
            "minHeight": "100vh",
            "boxSizing": "border-box",
        },
    )


def _tabs() -> dcc.Tabs:
    return dcc.Tabs(
        id="tabs-principal",
        value="diagnostico",
        children=[dcc.Tab(label=label, value=value) for value, label in TABS],
    )


def _layout() -> html.Div:
    return html.Div(
        [
            dcc.Store(id="store-carteira-id"),
            dcc.Store(id="store-sessao-id"),
            dcc.Store(id="store-parametros"),
            html.Div(
                [
                    _sidebar(),
                    html.Div(
                        [
                            _tabs(),
                            html.Div(id="conteudo-aba", style={"padding": 24}),
                        ],
                        style={"flex": 1, "minWidth": 0},
                    ),
                ],
                style={"display": "flex", "minHeight": "100vh"},
            ),
        ],
        style={"fontFamily": "system-ui, -apple-system, sans-serif"},
    )


def create_app() -> Dash:
    app = Dash(__name__, title="Katalyzer Vega", suppress_callback_exceptions=True)
    app.layout = _layout()
    return app


app = create_app()
server = app.server


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("LOG_LEVEL", "INFO").upper() == "DEBUG"
    app.run(host="0.0.0.0", port=port, debug=debug)
