"""Katalyzer Vega — entrypoint Dash.

Sobe na porta 8050 com sidebar e 7 tabs. Conteúdo carregado via lazy
callback único que roteia para o módulo da aba ativa.
"""
from __future__ import annotations

import os

from dash import Dash, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from vega.app.tabs import (
    tab_diagnostico,
    tab_segmentacao,
    tab_scoring,
    tab_safra_aging,
    tab_contactabilidade,
    tab_historico,
)


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

    # Roteamento lazy: carrega conteúdo da aba quando ela é ativada
    @app.callback(
        Output("conteudo-aba", "children"),
        Input("tabs-principal", "value"),
        State("store-carteira-id", "data"),
        State("store-sessao-id", "data"),
    )
    def render_conteudo_aba(
        tab: str,
        carteira_id: int | None,
        sessao_id: int | None,
    ) -> html.Div:
        if tab == "diagnostico":
            return tab_diagnostico.get_layout(carteira_id, sessao_id)
        if tab == "segmentacao":
            return tab_segmentacao.get_layout(carteira_id, sessao_id)
        if tab == "scoring":
            return tab_scoring.get_layout(carteira_id, sessao_id)
        if tab == "safra_aging":
            return tab_safra_aging.get_layout(carteira_id, sessao_id)
        if tab == "contactabilidade":
            return tab_contactabilidade.get_layout(carteira_id, sessao_id)
        if tab == "historico":
            return tab_historico.get_layout(carteira_id, sessao_id)
        return html.Div(
            "Aba em construção.",
            style={"color": "#9ca3af", "padding": 24, "fontSize": 13},
        )

    # Callbacks internos por aba
    tab_diagnostico.registrar_callbacks(app)
    tab_segmentacao.registrar_callbacks(app)
    tab_scoring.registrar_callbacks(app)
    tab_safra_aging.registrar_callbacks(app)
    tab_contactabilidade.registrar_callbacks(app)
    tab_historico.registrar_callbacks(app)

    return app


app = create_app()
server = app.server


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("LOG_LEVEL", "INFO").upper() == "DEBUG"
    app.run(host="0.0.0.0", port=port, debug=debug)
