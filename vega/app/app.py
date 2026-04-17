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
    tab_cenarios,
)
from vega.app.components.tooltip import vega_tooltip_css


TABS = [
    ("diagnostico",     "1. Diagnóstico"),
    ("segmentacao",     "2. Segmentação"),
    ("scoring",         "3. Scoring"),
    ("safra_aging",     "4. Safra & Aging"),
    ("contactabilidade","5. Contactabilidade"),
    ("historico",       "6. Histórico"),
    ("cenarios",        "7. Cenários"),
]

_DELFT  = "#0A2A5F"
_VIOLET = "#7B2CBF"
_GREEN  = "#059669"
_GRAY   = "#9CA3AF"
_AMBER  = "#D97706"


def _is_demo() -> bool:
    return os.environ.get("DEMO_MODE", "true").lower() in ("1", "true", "yes")


def _initial_store_data() -> tuple[int | None, int | None]:
    """Carrega a carteira e sessão mais recentes do banco no startup.

    Usado apenas quando DEMO_MODE=false — permite que as abas recebam
    carteira_id/sessao_id válidos no primeiro render sem interação do usuário.
    """
    if _is_demo():
        return None, None
    try:
        from vega.db.connection import get_conn  # import local para não quebrar DEMO_MODE
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT c.id, s.id
                    FROM vega.carteiras c
                    JOIN vega.sessoes_analise s ON s.carteira_id = c.id
                    ORDER BY c.created_at DESC, s.created_at DESC
                    LIMIT 1
                """)
                row = cur.fetchone()
        if row:
            return int(row[0]), int(row[1])
    except Exception:
        pass
    return None, None

_SECTION_LABEL = {
    "fontSize": 9, "fontWeight": 700, "color": _GRAY,
    "letterSpacing": "0.8px", "textTransform": "uppercase",
    "marginTop": 16, "marginBottom": 4,
}
_PARAM_LABEL = {"fontSize": 10, "color": "#374151", "marginBottom": 2, "marginTop": 6}


def _sidebar() -> html.Div:
    return html.Div(
        [
            html.Div("Katalyzer", style={"fontWeight": 700, "fontSize": 18, "color": _DELFT, "letterSpacing": -0.5}),
            html.Div("Vega", style={"fontSize": 11, "color": _VIOLET, "fontWeight": 600, "marginBottom": 2}),
            html.Div("Dívida ativa municipal", style={"fontSize": 10, "color": _GRAY, "marginBottom": 14}),
            html.Hr(style={"border": "none", "borderTop": "1px solid #E5E7EB", "margin": "0 0 4px"}),

            # ── Higienização ──────────────────────────────────
            html.Div("Higienização", style=_SECTION_LABEL),
            html.Div("Valor mínimo da CDA", style=_PARAM_LABEL),
            dcc.Slider(
                id="sl-valor-minimo", min=10, max=500, step=10, value=50,
                marks=None,
                tooltip={"always_visible": False, "template": "R$ {value}"},
                updatemode="mouseup",
            ),
            html.Div("Prazo de prescrição", style=_PARAM_LABEL),
            dcc.Slider(
                id="sl-prazo-prescricao", min=1, max=10, step=1, value=5,
                marks={1: "1a", 5: "5a", 10: "10a"},
                tooltip={"always_visible": False, "template": "{value} anos"},
                updatemode="mouseup",
            ),
            dcc.Loading(
                type="circle", color=_VIOLET,
                children=html.Div(id="reprocess-output", style={"height": 6}),
            ),

            # ── Tributos ──────────────────────────────────────
            html.Div("Tributos", style=_SECTION_LABEL),
            dcc.Checklist(
                id="chips-tributos",
                options=[{"label": f" {t}", "value": t} for t in ["IPTU", "ISS", "ITBI", "TAXAS", "OUTROS"]],
                value=["IPTU", "ISS", "ITBI", "TAXAS", "OUTROS"],
                inline=True,
                inputStyle={"marginRight": 3},
                labelStyle={"fontSize": 10, "marginRight": 8, "cursor": "pointer"},
            ),

            # ── Pesos do Score ────────────────────────────────
            html.Div("Pesos do Score", style=_SECTION_LABEL),
            html.Div("Dimensão Valor (0–30)", style=_PARAM_LABEL),
            dcc.Slider(
                id="sl-peso-valor", min=0, max=30, step=1, value=30,
                marks={0: "0", 15: "15", 30: "30"},
                tooltip={"always_visible": False},
                updatemode="mouseup",
            ),
            html.Div("Dimensão Urgência (0–30)", style=_PARAM_LABEL),
            dcc.Slider(
                id="sl-peso-urgencia", min=0, max=30, step=1, value=30,
                marks={0: "0", 15: "15", 30: "30"},
                tooltip={"always_visible": False},
                updatemode="mouseup",
            ),

            # ── Thresholds Q1 ─────────────────────────────────
            html.Div("Thresholds Q1", style=_SECTION_LABEL),
            html.Div("Prioridade mínima", style=_PARAM_LABEL),
            dcc.Slider(
                id="sl-thr-prioridade", min=0, max=100, step=5, value=40,
                marks={0: "0", 50: "50", 100: "100"},
                tooltip={"always_visible": False},
                updatemode="mouseup",
            ),
            html.Div("Recuperabilidade mínima", style=_PARAM_LABEL),
            dcc.Slider(
                id="sl-thr-recuperab", min=0, max=100, step=5, value=30,
                marks={0: "0", 50: "50", 100: "100"},
                tooltip={"always_visible": False},
                updatemode="mouseup",
            ),

            # ── Benchmark ─────────────────────────────────────
            html.Div("Benchmark", style=_SECTION_LABEL),
            dcc.Dropdown(
                id="dd-benchmark",
                options=[
                    {"label": "Médio nacional", "value": "nacional"},
                    {"label": "Melhor município", "value": "top"},
                    {"label": "Sem benchmark",   "value": "nenhum"},
                ],
                value="nacional",
                clearable=False,
                style={"fontSize": 11},
            ),

            html.Hr(style={"border": "none", "borderTop": "1px solid #E5E7EB", "margin": "16px 0 10px"}),

            html.Button(
                "Salvar parâmetros",
                id="btn-salvar-params",
                n_clicks=0,
                style={
                    "width": "100%", "padding": "8px 12px",
                    "background": _DELFT, "color": "#fff",
                    "border": "none", "borderRadius": 6,
                    "fontSize": 11, "fontWeight": 500, "cursor": "pointer",
                },
            ),
            html.Div(id="save-status", style={
                "fontSize": 10, "color": _GREEN, "marginTop": 6, "textAlign": "center",
            }),
            *(
                [html.Div("DEMO MODE ATIVO", style={
                    "fontSize": 9, "color": _AMBER, "fontWeight": 700,
                    "letterSpacing": "0.5px", "textAlign": "center", "marginTop": 14,
                })]
                if _is_demo() else []
            ),
        ],
        style={
            "width": 280,
            "minWidth": 280,
            "padding": "20px 14px",
            "borderRight": "1px solid #e5e7eb",
            "background": "#fafafa",
            "minHeight": "100vh",
            "boxSizing": "border-box",
            "overflowY": "auto",
        },
    )


def _tabs() -> dcc.Tabs:
    return dcc.Tabs(
        id="tabs-principal",
        value="diagnostico",
        children=[dcc.Tab(label=label, value=value) for value, label in TABS],
    )


def _layout() -> html.Div:
    carteira_id_init, sessao_id_init = _initial_store_data()
    return html.Div(
        [
            dcc.Store(id="store-carteira-id", data=carteira_id_init),
            dcc.Store(id="store-sessao-id",   data=sessao_id_init),
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


def _registrar_sidebar_callbacks(app: Dash) -> None:

    @app.callback(
        Output("store-parametros", "data"),
        Input("sl-valor-minimo",     "value"),
        Input("sl-prazo-prescricao", "value"),
        Input("chips-tributos",      "value"),
        Input("sl-peso-valor",       "value"),
        Input("sl-peso-urgencia",    "value"),
        Input("sl-thr-prioridade",   "value"),
        Input("sl-thr-recuperab",    "value"),
        Input("dd-benchmark",        "value"),
    )
    def atualizar_parametros(vm, pp, tributos, pv, pu, tp, tr, bm):
        return {
            "valor_minimo_cents":       (vm or 50) * 100,
            "prazo_prescricao_anos":    pp or 5,
            "tributos":                 tributos or ["IPTU", "ISS", "ITBI", "TAXAS", "OUTROS"],
            "peso_valor":               pv if pv is not None else 30,
            "peso_urgencia":            pu if pu is not None else 30,
            "threshold_q1_prioridade":  tp if tp is not None else 40,
            "threshold_q1_recuperab":   tr if tr is not None else 30,
            "benchmark":                bm or "nacional",
        }

    @app.callback(
        Output("reprocess-output", "children"),
        Input("sl-valor-minimo",     "value"),
        Input("sl-prazo-prescricao", "value"),
        State("store-carteira-id",   "data"),
        State("store-sessao-id",     "data"),
        prevent_initial_call=True,
    )
    def reprocessar_higienizacao(valor_minimo, prazo, carteira_id, sessao_id):
        if os.environ.get("DEMO_MODE", "true").lower() in ("1", "true", "yes"):
            return None
        if not carteira_id or not sessao_id:
            raise PreventUpdate
        try:
            from vega.db.connection import get_conn
            from vega.pipeline.higienizacao import Higienizador

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE vega.sessoes_analise
                              SET valor_minimo_cents = %(vm)s,
                                  prazo_prescricao_anos = %(pp)s
                            WHERE id = %(sid)s""",
                        {"vm": (valor_minimo or 50) * 100, "pp": prazo or 5, "sid": sessao_id},
                    )
                conn.commit()
            Higienizador().processar(carteira_id, sessao_id)
        except Exception:
            pass
        return None

    @app.callback(
        Output("save-status", "children"),
        Input("btn-salvar-params", "n_clicks"),
        State("store-sessao-id",   "data"),
        State("store-parametros",  "data"),
        prevent_initial_call=True,
    )
    def salvar_parametros(n_clicks, sessao_id, parametros):
        if not n_clicks:
            raise PreventUpdate
        if os.environ.get("DEMO_MODE", "true").lower() in ("1", "true", "yes"):
            return "✓ Parâmetros aplicados (demo)."
        if not sessao_id or not parametros:
            return "⚠ Selecione uma carteira primeiro."
        try:
            from vega.db.connection import get_conn

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE vega.sessoes_analise
                              SET valor_minimo_cents = %(vm)s,
                                  prazo_prescricao_anos = %(pp)s
                            WHERE id = %(sid)s""",
                        {
                            "vm":  parametros.get("valor_minimo_cents", 5000),
                            "pp":  parametros.get("prazo_prescricao_anos", 5),
                            "sid": sessao_id,
                        },
                    )
                conn.commit()
        except Exception as exc:
            return f"Erro: {exc}"
        return "✓ Parâmetros salvos."


def create_app() -> Dash:
    app = Dash(__name__, title="Katalyzer Vega", suppress_callback_exceptions=True)

    _tooltip_css = vega_tooltip_css()
    app.index_string = f"""<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        {{%favicon%}}
        {{%css%}}
        <style>{_tooltip_css}</style>
    </head>
    <body>
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>"""

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
        if tab == "cenarios":
            return tab_cenarios.get_layout(carteira_id, sessao_id)
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
    tab_cenarios.registrar_callbacks(app)

    # Callbacks da sidebar interativa
    _registrar_sidebar_callbacks(app)

    return app


app = create_app()
server = app.server


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("LOG_LEVEL", "INFO").upper() == "DEBUG"
    app.run(host="0.0.0.0", port=port, debug=debug)
