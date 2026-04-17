"""Aba 7 — Cenários de Recuperação.

DEMO_MODE=true  → fixtures estáticos do município de Beberibe (carteira 2026).
DEMO_MODE=false → queries reais via vega.db.queries + simulacao.py.

RN-06: card âmbar de aviso sobre decay não calibrado — obrigatório quando
sessoes_analise.decay_calibrado = false. Visibilidade controlada em get_layout
(estado inicial) e atualizada pelo callback toggle_aviso_decay.
"""
from __future__ import annotations

import os
from typing import Any

import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from vega.pipeline.simulacao import (
    calcular_elasticidade,
    calcular_payback,
    decay_curve,
    encontrar_desconto_otimo,
)

# ── Paleta ────────────────────────────────────────────────────────────────────
DELFT  = "#0A2A5F"
VIOLET = "#7B2CBF"
AMBER  = "#D97706"
GREEN  = "#059669"
GRAY   = "#9CA3AF"

_CARD = {
    "background": "#fff",
    "borderRadius": 10,
    "border": "1px solid #E5E7EB",
    "padding": "16px 18px",
    "marginBottom": 12,
}
_PLOT_FONT   = {"family": "system-ui, -apple-system, sans-serif", "size": 11, "color": "#6B7280"}
_GRID_COLOR  = "rgba(0,0,0,.05)"

# Taxas de decay por cenário (vide simulacao.py — rate = fração que PERMANECE)
_RATE_CONS = 0.90  # conservador: recuperação lenta e persistente
_RATE_MOD  = 0.55  # moderado
_RATE_AGR  = 0.38  # agressivo: recuperação rápida nos primeiros meses

_DEFAULT_ADESAO: dict[str, float] = {"cons": 12.0, "mod": 10.0, "agr": 8.0}
_DEFAULT_CUSTO:  dict[str, float] = {"cons": 85_000.0, "mod": 137_000.0, "agr": 205_000.0}


# ── Mock data — Beberibe 2026 ─────────────────────────────────────────────────
_MOCK_BASE: dict[str, dict] = {
    "Q1": {"count_contrib": 450, "valor_cents": 850_000_000},   # R$ 8,5M
    "Q2": {"count_contrib": 320, "valor_cents": 520_000_000},   # R$ 5,2M
    "Q3": {"count_contrib": 280, "valor_cents": 680_000_000},   # R$ 6,8M
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_demo() -> bool:
    return os.environ.get("DEMO_MODE", "true").lower() in ("1", "true", "yes")


def _fmt_reais(cents: int) -> str:
    val = cents / 100
    if val >= 1_000_000:
        return f"R$ {val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"R$ {val / 1_000:.1f}k"
    return f"R$ {val:,.0f}"


def _payback_str(pb: int | None) -> str:
    return f"Mês {pb}" if pb is not None else ">12m"


def _plateau_str(pl: int | None) -> str:
    return f"Mês {pl}" if pl is not None else "12m+"


# ── Simulação ─────────────────────────────────────────────────────────────────

def _calcular_plateau(curva: list[int]) -> int | None:
    """Primeiro mês em que a recuperação mensal cai abaixo de 5% do Mês 1."""
    if not curva or curva[0] == 0:
        return None
    threshold = curva[0] * 0.05
    for i, v in enumerate(curva, 1):
        if v < threshold:
            return i
    return None


def _calcular_um(valor_cents: int, adesao_pct: float, custo_reais: float, rate: float) -> dict:
    valor_efetivo = round(valor_cents * adesao_pct / 100)
    curva = decay_curve(valor_efetivo, rate, 12)
    rec_cents = sum(curva)
    roi = round(
        (rec_cents / 100 - custo_reais) / custo_reais * 100, 1
    ) if custo_reais > 0 else 0.0
    return {
        "curva":           curva,
        "recuperacao_cents": rec_cents,
        "roi":             roi,
        "payback":         calcular_payback(curva, custo_reais),
        "plateau":         _calcular_plateau(curva),
    }


def _calcular_cenarios(base: dict, adesoes: dict, custos: dict) -> dict:
    val_cons = base["Q1"]["valor_cents"]
    val_mod  = base["Q1"]["valor_cents"] + base["Q2"]["valor_cents"]
    val_agr  = val_mod + base["Q3"]["valor_cents"]
    return {
        "cons":     _calcular_um(val_cons, adesoes["cons"], custos["cons"], _RATE_CONS),
        "mod":      _calcular_um(val_mod,  adesoes["mod"],  custos["mod"],  _RATE_MOD),
        "agr":      _calcular_um(val_agr,  adesoes["agr"],  custos["agr"],  _RATE_AGR),
        "val_cons": val_cons,
        "val_mod":  val_mod,
        "val_agr":  val_agr,
    }


def _decay_calibrado(sessao_id: int | None) -> bool:
    if sessao_id is None or _is_demo():
        return False
    try:
        from vega.db.connection import get_conn
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT decay_calibrado FROM vega.sessoes_analise WHERE id = %s",
                    (sessao_id,),
                )
                row = cur.fetchone()
                return bool(row and row[0])
    except Exception:
        return False


# ── Figuras ───────────────────────────────────────────────────────────────────

def _fig_recuperacao_cumulativa(res: dict) -> go.Figure:
    """3 linhas cumulativas + estrela (★) no mês de payback."""
    meses = list(range(1, 13))
    fig = go.Figure()

    cenarios = [
        ("cons", "Conservador", GRAY,   "dot"),
        ("mod",  "Moderado",    VIOLET, None),
        ("agr",  "Agressivo",   DELFT,  "dash"),
    ]
    for key, label, color, dash in cenarios:
        acum, total = [], 0
        for v in res[key]["curva"]:
            total += v
            acum.append(total / 100)

        line = {"color": color, "width": 2}
        if dash:
            line["dash"] = dash

        fig.add_trace(go.Scatter(
            x=meses, y=acum, name=label,
            mode="lines+markers",
            line=line, marker={"size": 4},
        ))

        pb = res[key]["payback"]
        if pb is not None and 1 <= pb <= 12:
            fig.add_trace(go.Scatter(
                x=[pb], y=[acum[pb - 1]],
                mode="markers",
                marker={"symbol": "star", "size": 14, "color": color},
                name=f"Payback {label}", showlegend=False,
            ))

    fig.update_layout(
        height=280,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        font=_PLOT_FONT,
        plot_bgcolor="white", paper_bgcolor="white",
        legend={"orientation": "h", "y": -0.22, "font": {"size": 10}},
        xaxis={"title": "Mês", "showgrid": False, "dtick": 1},
        yaxis={"title": "Recuperação acumulada (R$)", "showgrid": True, "gridcolor": _GRID_COLOR},
    )
    return fig


def _fig_roi(res: dict) -> go.Figure:
    rois   = [res["cons"]["roi"], res["mod"]["roi"], res["agr"]["roi"]]
    colors = [GRAY, VIOLET, DELFT]
    fig = go.Figure(go.Bar(
        x=["Conservador", "Moderado", "Agressivo"],
        y=rois,
        marker_color=colors,
        text=[f"{r:.1f}%" for r in rois],
        textposition="outside",
    ))
    fig.update_layout(
        height=240,
        margin={"l": 0, "r": 0, "t": 20, "b": 0},
        font=_PLOT_FONT,
        plot_bgcolor="white", paper_bgcolor="white",
        yaxis={"title": "ROI (%)", "showgrid": True, "gridcolor": _GRID_COLOR},
        xaxis={"showgrid": False},
    )
    return fig


def _fig_elasticidade(val_mod_cents: int, adesao_base: float) -> go.Figure:
    """Adesão % (eixo Y esq.) × valor líquido R$M (eixo Y dir.) — desconto ótimo destacado."""
    pontos = calcular_elasticidade(val_mod_cents, adesao_base)
    otimo  = encontrar_desconto_otimo(pontos)

    descontos = [p.desconto_pct for p in pontos]
    adesoes   = [p.adesao_pct   for p in pontos]
    valores   = [p.valor_recuperado_cents / 100 / 1_000_000 for p in pontos]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=descontos, y=adesoes, name="Adesão (%)",
        mode="lines+markers",
        line={"color": GREEN, "width": 2}, marker={"size": 5},
        yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=descontos, y=valores, name="Valor líquido (R$M)",
        mode="lines+markers",
        line={"color": VIOLET, "width": 2}, marker={"size": 5},
        yaxis="y2",
    ))

    if otimo:
        otimo_val_m = otimo.valor_recuperado_cents / 100 / 1_000_000
        fig.add_vline(
            x=otimo.desconto_pct,
            line_dash="dot", line_color=AMBER, line_width=1.5,
            annotation_text=(
                f"Ótimo: {otimo.desconto_pct}% desc.\n"
                f"R$ {otimo_val_m:.2f}M"
            ),
            annotation_position="top right",
            annotation_font_size=10,
            annotation_font_color=AMBER,
        )

    fig.update_layout(
        height=260,
        margin={"l": 0, "r": 50, "t": 0, "b": 0},
        font=_PLOT_FONT,
        plot_bgcolor="white", paper_bgcolor="white",
        legend={"orientation": "h", "y": -0.22, "font": {"size": 10}},
        xaxis={"title": "Desconto (%)", "showgrid": False, "dtick": 5},
        yaxis={
            "title": "Adesão (%)",
            "showgrid": True, "gridcolor": _GRID_COLOR,
        },
        yaxis2={
            "title": "Valor líquido (R$M)",
            "overlaying": "y", "side": "right", "showgrid": False,
        },
    )
    return fig


# ── Componentes ───────────────────────────────────────────────────────────────

def _aviso_decay_style(visible: bool) -> dict:
    base: dict = {
        "display":        "flex",
        "alignItems":     "flex-start",
        "background":     "#FFFBEB",
        "border":         "1px solid #FCD34D",
        "borderRadius":   8,
        "padding":        "12px 16px",
        "marginBottom":   12,
    }
    if not visible:
        base["display"] = "none"
    return base


def _aviso_decay(visible: bool) -> html.Div:
    return html.Div([
        html.Div("⚠", style={"fontSize": 20, "marginRight": 12, "alignSelf": "center"}),
        html.Div([
            html.Div(
                "Curvas de decay usam parâmetros de referência de mercado.",
                style={"fontWeight": 600, "fontSize": 13},
            ),
            html.Div(
                "Para calibração use o Decay de recuperação por safra (Aba 4).",
                style={"fontSize": 11, "color": GRAY},
            ),
        ]),
    ], id="aviso-decay-7", style=_aviso_decay_style(visible))


def _input_cell(value: float, input_id: str, suffix: str) -> html.Td:
    return html.Td([
        dcc.Input(
            id=input_id,
            type="number",
            value=value,
            step=0.5 if "adesao" in input_id else 1000,
            min=0.1 if "adesao" in input_id else 0,
            max=100 if "adesao" in input_id else None,
            style={
                "width": 80,
                "padding": "4px 6px",
                "border": "1px solid #D1D5DB",
                "borderRadius": 4,
                "fontSize": 13,
                "textAlign": "right",
            },
        ),
        html.Span(suffix, style={"fontSize": 11, "color": GRAY, "marginLeft": 4}),
    ], style={"padding": "8px 12px", "textAlign": "center"})


def _tabela_cenarios(base: dict, res: dict) -> html.Div:
    _th = {
        "padding": "8px 12px", "fontSize": 12,
        "fontWeight": 700, "textAlign": "center",
        "borderBottom": "2px solid #E5E7EB",
    }
    _td = {
        "padding": "8px 12px", "fontSize": 13,
        "textAlign": "center", "borderBottom": "1px solid #F3F4F6",
    }
    _td_lbl = {
        "padding": "8px 12px", "fontSize": 12,
        "color": GRAY, "fontWeight": 500,
        "textAlign": "left", "borderBottom": "1px solid #F3F4F6",
    }

    val_cons = base["Q1"]["valor_cents"]
    val_mod  = base["Q1"]["valor_cents"] + base["Q2"]["valor_cents"]
    val_agr  = val_mod + base["Q3"]["valor_cents"]
    n_cons   = base["Q1"]["count_contrib"]
    n_mod    = base["Q1"]["count_contrib"] + base["Q2"]["count_contrib"]
    n_agr    = n_mod + base["Q3"]["count_contrib"]

    return html.Div([
        html.Table([
            html.Thead(html.Tr([
                html.Th("Métrica",      style={**_th, "textAlign": "left"}),
                html.Th("Conservador",  style={**_th, "color": GRAY}),
                html.Th("Moderado",     style={**_th, "color": VIOLET}),
                html.Th("Agressivo",    style={**_th, "color": DELFT}),
            ])),
            html.Tbody([
                html.Tr([
                    html.Td("Quadrantes", style=_td_lbl),
                    html.Td("Q1",             style=_td),
                    html.Td("Q1 + Q2",        style=_td),
                    html.Td("Q1 + Q2 + Q3",   style=_td),
                ]),
                html.Tr([
                    html.Td("Contribuintes-alvo", style=_td_lbl),
                    html.Td(f"{n_cons:,}", style=_td),
                    html.Td(f"{n_mod:,}",  style=_td),
                    html.Td(f"{n_agr:,}",  style=_td),
                ]),
                html.Tr([
                    html.Td("Valor-alvo", style=_td_lbl),
                    html.Td(_fmt_reais(val_cons), style=_td),
                    html.Td(_fmt_reais(val_mod),  style=_td),
                    html.Td(_fmt_reais(val_agr),  style=_td),
                ]),
                # Adesão M1 — editável
                html.Tr([
                    html.Td("Adesão M1 (%)", style=_td_lbl),
                    _input_cell(_DEFAULT_ADESAO["cons"], "input-adesao-cons", "%"),
                    _input_cell(_DEFAULT_ADESAO["mod"],  "input-adesao-mod",  "%"),
                    _input_cell(_DEFAULT_ADESAO["agr"],  "input-adesao-agr",  "%"),
                ]),
                # Recuperação projetada — highlight
                html.Tr([
                    html.Td("Recuperação projetada",
                            style={**_td_lbl, "fontWeight": 700, "color": "#111"}),
                    html.Td(html.Span(
                                id="span-rec-cons",
                                children=_fmt_reais(res["cons"]["recuperacao_cents"]),
                            ),
                            style={**_td, "fontWeight": 700, "color": GREEN,  "background": "#F0FDF4"}),
                    html.Td(html.Span(
                                id="span-rec-mod",
                                children=_fmt_reais(res["mod"]["recuperacao_cents"]),
                            ),
                            style={**_td, "fontWeight": 700, "color": VIOLET, "background": "#F5F3FF"}),
                    html.Td(html.Span(
                                id="span-rec-agr",
                                children=_fmt_reais(res["agr"]["recuperacao_cents"]),
                            ),
                            style={**_td, "fontWeight": 700, "color": DELFT,  "background": "#EFF6FF"}),
                ]),
                # Custo operacional — editável
                html.Tr([
                    html.Td("Custo operacional", style=_td_lbl),
                    _input_cell(_DEFAULT_CUSTO["cons"], "input-custo-cons", "R$"),
                    _input_cell(_DEFAULT_CUSTO["mod"],  "input-custo-mod",  "R$"),
                    _input_cell(_DEFAULT_CUSTO["agr"],  "input-custo-agr",  "R$"),
                ]),
                html.Tr([
                    html.Td("ROI", style=_td_lbl),
                    html.Td(html.Span(id="span-roi-cons",
                                      children=f"{res['cons']['roi']:.1f}%"), style=_td),
                    html.Td(html.Span(id="span-roi-mod",
                                      children=f"{res['mod']['roi']:.1f}%"),  style=_td),
                    html.Td(html.Span(id="span-roi-agr",
                                      children=f"{res['agr']['roi']:.1f}%"),  style=_td),
                ]),
                html.Tr([
                    html.Td("Payback", style=_td_lbl),
                    html.Td(html.Span(id="span-payback-cons",
                                      children=_payback_str(res["cons"]["payback"])), style=_td),
                    html.Td(html.Span(id="span-payback-mod",
                                      children=_payback_str(res["mod"]["payback"])),  style=_td),
                    html.Td(html.Span(id="span-payback-agr",
                                      children=_payback_str(res["agr"]["payback"])),  style=_td),
                ]),
                html.Tr([
                    html.Td("Plateau", style=_td_lbl),
                    html.Td(html.Span(id="span-plateau-cons",
                                      children=_plateau_str(res["cons"]["plateau"])), style=_td),
                    html.Td(html.Span(id="span-plateau-mod",
                                      children=_plateau_str(res["mod"]["plateau"])),  style=_td),
                    html.Td(html.Span(id="span-plateau-agr",
                                      children=_plateau_str(res["agr"]["plateau"])),  style=_td),
                ]),
            ]),
        ], style={"width": "100%", "borderCollapse": "collapse"}),
    ], style=_CARD)


def _chart_card(title: str, subtitle: str, figure_or_graph: Any) -> html.Div:
    return html.Div([
        html.Div([
            html.Div(title, style={"fontSize": 13, "fontWeight": 600}),
            html.Div(subtitle, style={"fontSize": 10, "color": GRAY}),
        ], style={"marginBottom": 12}),
        figure_or_graph,
    ], style=_CARD)


def _btn_insights() -> html.Div:
    return html.Div([
        html.Button(
            "Gerar insights cruzados",
            id="btn-insights-6",
            n_clicks=0,
            style={
                "background": VIOLET,
                "color": "#fff",
                "border": "none",
                "borderRadius": 6,
                "padding": "10px 20px",
                "fontSize": 13,
                "fontWeight": 600,
                "cursor": "pointer",
            },
        ),
        dcc.Loading(type="dot", color="#7B2CBF", style={"marginTop": 12}, children=html.Div(id="insights-result-6")),
    ], style=_CARD)


# ── Layout ────────────────────────────────────────────────────────────────────

def get_layout(carteira_id: int | None = None, sessao_id: int | None = None) -> html.Div:
    """Renderiza o conteúdo completo da Aba 7 — Cenários de Recuperação."""
    if _is_demo():
        base = _MOCK_BASE
    else:
        if carteira_id is None or sessao_id is None:
            return html.Div(
                "Selecione uma carteira e sessão para ver os Cenários.",
                style={"color": "#9ca3af", "padding": 24},
            )
        from vega.db import queries
        df = queries.base_cenarios(carteira_id, sessao_id)
        base = {
            row["quadrante"]: {
                "count_contrib": int(row["count_contrib"]),
                "valor_cents":   int(row["valor_cents"]),
            }
            for _, row in df.iterrows()
        }
        for q in ("Q1", "Q2", "Q3"):
            if q not in base:
                base[q] = {"count_contrib": 0, "valor_cents": 0}

    res = _calcular_cenarios(base, _DEFAULT_ADESAO, _DEFAULT_CUSTO)

    return html.Div([
        # 1. Tabela de projeção de cenários
        _tabela_cenarios(base, res),

        # 2. Aviso âmbar RN-06 — obrigatório (oculta só quando decay_calibrado=true)
        _aviso_decay(visible=not _decay_calibrado(sessao_id)),

        # 3. Chart: Recuperação cumulativa (3 linhas + estrela de payback)
        _chart_card(
            "Recuperação Cumulativa — 12 meses",
            "★ indica o mês de payback em cada cenário",
            dcc.Graph(
                id="graph-rec-cumulativa-7",
                figure=_fig_recuperacao_cumulativa(res),
                config={"displayModeBar": False},
            ),
        ),

        # 4. Chart: ROI por cenário
        _chart_card(
            "ROI por Cenário",
            "(Recuperação projetada − Custo operacional) / Custo × 100",
            dcc.Graph(
                id="graph-roi-cenarios-7",
                figure=_fig_roi(res),
                config={"displayModeBar": False},
            ),
        ),

        # 5. Chart: Elasticidade de desconto (duplo eixo Y)
        _chart_card(
            "Elasticidade de Desconto",
            "Base: cenário moderado · adesão esperada (%) × valor líquido projetado (R$M)",
            dcc.Graph(
                id="graph-elasticidade-7",
                figure=_fig_elasticidade(res["val_mod"], _DEFAULT_ADESAO["mod"]),
                config={"displayModeBar": False},
            ),
        ),

        # 6. Botão de insights cruzados
        _btn_insights(),

        # Store local com a base dos cenários (passado aos callbacks via State)
        dcc.Store(id="store-base-cenarios-7", data={
            "Q1": dict(base["Q1"]),
            "Q2": dict(base["Q2"]),
            "Q3": dict(base["Q3"]),
        }),
    ])


# ── Callbacks ─────────────────────────────────────────────────────────────────

def registrar_callbacks(app: Any) -> None:

    @app.callback(
        Output("span-rec-cons",         "children"),
        Output("span-rec-mod",          "children"),
        Output("span-rec-agr",          "children"),
        Output("span-roi-cons",         "children"),
        Output("span-roi-mod",          "children"),
        Output("span-roi-agr",          "children"),
        Output("span-payback-cons",     "children"),
        Output("span-payback-mod",      "children"),
        Output("span-payback-agr",      "children"),
        Output("span-plateau-cons",     "children"),
        Output("span-plateau-mod",      "children"),
        Output("span-plateau-agr",      "children"),
        Output("graph-rec-cumulativa-7","figure"),
        Output("graph-roi-cenarios-7",  "figure"),
        Output("graph-elasticidade-7",  "figure"),
        Input("input-adesao-cons",      "value"),
        Input("input-adesao-mod",       "value"),
        Input("input-adesao-agr",       "value"),
        Input("input-custo-cons",       "value"),
        Input("input-custo-mod",        "value"),
        Input("input-custo-agr",        "value"),
        Input("store-parametros",       "data"),
        State("store-base-cenarios-7",  "data"),
        prevent_initial_call=True,
    )
    def atualizar_cenarios(
        adesao_cons, adesao_mod, adesao_agr,
        custo_cons,  custo_mod,  custo_agr,
        _parametros,
        base_data,
    ):
        if base_data is None:
            raise PreventUpdate

        adesoes = {
            "cons": float(adesao_cons if adesao_cons is not None else _DEFAULT_ADESAO["cons"]),
            "mod":  float(adesao_mod  if adesao_mod  is not None else _DEFAULT_ADESAO["mod"]),
            "agr":  float(adesao_agr  if adesao_agr  is not None else _DEFAULT_ADESAO["agr"]),
        }
        custos = {
            "cons": float(custo_cons if custo_cons is not None else _DEFAULT_CUSTO["cons"]),
            "mod":  float(custo_mod  if custo_mod  is not None else _DEFAULT_CUSTO["mod"]),
            "agr":  float(custo_agr  if custo_agr  is not None else _DEFAULT_CUSTO["agr"]),
        }
        res = _calcular_cenarios(base_data, adesoes, custos)

        return (
            _fmt_reais(res["cons"]["recuperacao_cents"]),
            _fmt_reais(res["mod"]["recuperacao_cents"]),
            _fmt_reais(res["agr"]["recuperacao_cents"]),
            f"{res['cons']['roi']:.1f}%",
            f"{res['mod']['roi']:.1f}%",
            f"{res['agr']['roi']:.1f}%",
            _payback_str(res["cons"]["payback"]),
            _payback_str(res["mod"]["payback"]),
            _payback_str(res["agr"]["payback"]),
            _plateau_str(res["cons"]["plateau"]),
            _plateau_str(res["mod"]["plateau"]),
            _plateau_str(res["agr"]["plateau"]),
            _fig_recuperacao_cumulativa(res),
            _fig_roi(res),
            _fig_elasticidade(res["val_mod"], adesoes["mod"]),
        )

    @app.callback(
        Output("aviso-decay-7", "style"),
        Input("store-sessao-id", "data"),
        prevent_initial_call=True,
    )
    def toggle_aviso_decay(sessao_id):
        return _aviso_decay_style(visible=not _decay_calibrado(sessao_id))

    @app.callback(
        Output("insights-result-6",    "children"),
        Input("btn-insights-6",        "n_clicks"),
        State("store-carteira-id",     "data"),
        State("store-sessao-id",       "data"),
        State("input-adesao-cons",     "value"),
        State("input-adesao-mod",      "value"),
        State("input-adesao-agr",      "value"),
        State("input-custo-cons",      "value"),
        State("input-custo-mod",       "value"),
        State("input-custo-agr",       "value"),
        State("store-base-cenarios-7", "data"),
        prevent_initial_call=True,
    )
    def gerar_insights(
        n_clicks,
        carteira_id, sessao_id,
        adesao_cons, adesao_mod, adesao_agr,
        custo_cons,  custo_mod,  custo_agr,
        base_data,
    ):
        if not n_clicks:
            raise PreventUpdate

        base = base_data or {
            "Q1": dict(_MOCK_BASE["Q1"]),
            "Q2": dict(_MOCK_BASE["Q2"]),
            "Q3": dict(_MOCK_BASE["Q3"]),
        }
        adesoes = {
            "cons": float(adesao_cons if adesao_cons is not None else _DEFAULT_ADESAO["cons"]),
            "mod":  float(adesao_mod  if adesao_mod  is not None else _DEFAULT_ADESAO["mod"]),
            "agr":  float(adesao_agr  if adesao_agr  is not None else _DEFAULT_ADESAO["agr"]),
        }
        custos = {
            "cons": float(custo_cons if custo_cons is not None else _DEFAULT_CUSTO["cons"]),
            "mod":  float(custo_mod  if custo_mod  is not None else _DEFAULT_CUSTO["mod"]),
            "agr":  float(custo_agr  if custo_agr  is not None else _DEFAULT_CUSTO["agr"]),
        }
        res = _calcular_cenarios(base, adesoes, custos)

        metricas = {
            "conservador": {
                "quadrantes":             "Q1",
                "valor_alvo":             _fmt_reais(res["val_cons"]),
                "adesao_pct":             adesoes["cons"],
                "recuperacao_projetada":  _fmt_reais(res["cons"]["recuperacao_cents"]),
                "roi_pct":                res["cons"]["roi"],
                "payback_mes":            res["cons"]["payback"],
            },
            "moderado": {
                "quadrantes":             "Q1 + Q2",
                "valor_alvo":             _fmt_reais(res["val_mod"]),
                "adesao_pct":             adesoes["mod"],
                "recuperacao_projetada":  _fmt_reais(res["mod"]["recuperacao_cents"]),
                "roi_pct":                res["mod"]["roi"],
                "payback_mes":            res["mod"]["payback"],
            },
            "agressivo": {
                "quadrantes":             "Q1 + Q2 + Q3",
                "valor_alvo":             _fmt_reais(res["val_agr"]),
                "adesao_pct":             adesoes["agr"],
                "recuperacao_projetada":  _fmt_reais(res["agr"]["recuperacao_cents"]),
                "roi_pct":                res["agr"]["roi"],
                "payback_mes":            res["agr"]["payback"],
            },
        }

        try:
            from vega.insights.generator import gerar_insights_cenarios
            texto = gerar_insights_cenarios(metricas)
        except Exception as exc:
            texto = f"Erro ao gerar insights: {exc}"

        return html.Div([
            html.Div([
                html.Span("IA", style={
                    "background": VIOLET, "color": "#fff",
                    "fontSize": 10, "fontWeight": 700,
                    "padding": "2px 6px", "borderRadius": 4, "marginRight": 8,
                }),
                html.Span(
                    "Insights cruzados gerados por IA",
                    style={"fontSize": 12, "color": GRAY},
                ),
            ], style={"marginBottom": 8}),
            html.Pre(texto, style={
                "whiteSpace": "pre-wrap", "fontSize": 12,
                "lineHeight": 1.6, "margin": 0,
            }),
        ])
