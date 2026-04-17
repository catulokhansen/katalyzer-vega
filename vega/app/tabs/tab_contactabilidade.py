"""Aba 5 — Contactabilidade.

DEMO_MODE=true  → fixtures estáticos do município de Beberibe (carteira 2026).
DEMO_MODE=false → queries reais via vega.db.queries.
"""
from __future__ import annotations

import os
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

# ── Paleta ────────────────────────────────────────────────────────────────────
DELFT  = "#0A2A5F"
VIOLET = "#7B2CBF"
AMBER  = "#D97706"
GREEN  = "#059669"
RED    = "#DC2626"
GRAY   = "#9CA3AF"

_CARD = {
    "background": "#fff",
    "borderRadius": 10,
    "border": "1px solid #E5E7EB",
    "padding": "16px 18px",
    "marginBottom": 12,
}
_LABEL_STYLE = {"fontSize": 11, "color": GRAY, "fontWeight": 500, "marginBottom": 6}
_PLOT_FONT   = {"family": "system-ui, -apple-system, sans-serif", "size": 11, "color": "#6B7280"}
_GRID_COLOR  = "rgba(0,0,0,.05)"

_FAIXAS_ORDEM  = ["ate_500", "500_2k", "2k_10k", "10k_50k", "acima_50k"]
_FAIXAS_LABELS = {"ate_500": "≤ R$500", "500_2k": "R$500–2k",
                  "2k_10k": "R$2k–10k", "10k_50k": "R$10k–50k", "acima_50k": "> R$50k"}
_CANAIS_LABELS = {"celular": "Celular", "whatsapp": "WhatsApp",
                  "email": "E-mail", "telefone": "Telefone", "endereco": "Endereço"}
_CANAIS_ORDEM  = ["celular", "whatsapp", "email", "telefone", "endereco"]


def _is_demo() -> bool:
    return os.environ.get("DEMO_MODE", "true").lower() in ("1", "true", "yes")


def _fmt_reais(cents: int) -> str:
    val = cents / 100
    if val >= 1_000_000:
        return f"R$ {val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"R$ {val / 1_000:.1f}k"
    return f"R$ {val:,.0f}"


# ── Mock data — Beberibe 2026 ─────────────────────────────────────────────────
_MOCK_METRICAS: dict = {
    "pct_contactaveis": 62.3,
    "pct_so_endereco": 28.1,
    "pct_incontactaveis": 9.6,
    "valor_incontactavel_cents": 87_500_000,
}

_MOCK_COBERTURA = pd.DataFrame({
    "canal":         ["celular", "whatsapp", "email", "telefone", "endereco"],
    "pct_cobertura": [58.4,      41.2,       34.7,    22.8,       90.5],
})

_MOCK_CONTATO_FAIXA = pd.DataFrame([
    {"faixa_valor": "ate_500",   "nivel_contato_agrupado": "digital",       "valor_cents": 180_000_000},
    {"faixa_valor": "ate_500",   "nivel_contato_agrupado": "so_endereco",   "valor_cents":  62_000_000},
    {"faixa_valor": "ate_500",   "nivel_contato_agrupado": "incontactavel", "valor_cents":  18_000_000},
    {"faixa_valor": "500_2k",    "nivel_contato_agrupado": "digital",       "valor_cents": 390_000_000},
    {"faixa_valor": "500_2k",    "nivel_contato_agrupado": "so_endereco",   "valor_cents": 145_000_000},
    {"faixa_valor": "500_2k",    "nivel_contato_agrupado": "incontactavel", "valor_cents":  42_000_000},
    {"faixa_valor": "2k_10k",    "nivel_contato_agrupado": "digital",       "valor_cents": 620_000_000},
    {"faixa_valor": "2k_10k",    "nivel_contato_agrupado": "so_endereco",   "valor_cents": 210_000_000},
    {"faixa_valor": "2k_10k",    "nivel_contato_agrupado": "incontactavel", "valor_cents":  55_000_000},
    {"faixa_valor": "10k_50k",   "nivel_contato_agrupado": "digital",       "valor_cents": 480_000_000},
    {"faixa_valor": "10k_50k",   "nivel_contato_agrupado": "so_endereco",   "valor_cents": 180_000_000},
    {"faixa_valor": "10k_50k",   "nivel_contato_agrupado": "incontactavel", "valor_cents":  38_000_000},
    {"faixa_valor": "acima_50k", "nivel_contato_agrupado": "digital",       "valor_cents": 310_000_000},
    {"faixa_valor": "acima_50k", "nivel_contato_agrupado": "so_endereco",   "valor_cents":  95_000_000},
    {"faixa_valor": "acima_50k", "nivel_contato_agrupado": "incontactavel", "valor_cents":  20_000_000},
])

_MOCK_HEATMAP = pd.DataFrame([
    {"tributo": "IPTU",         "canal": "celular",  "pct_cobertura": 61.2},
    {"tributo": "IPTU",         "canal": "whatsapp", "pct_cobertura": 44.8},
    {"tributo": "IPTU",         "canal": "email",    "pct_cobertura": 37.5},
    {"tributo": "IPTU",         "canal": "telefone", "pct_cobertura": 25.1},
    {"tributo": "IPTU",         "canal": "endereco", "pct_cobertura": 92.3},
    {"tributo": "ISS",          "canal": "celular",  "pct_cobertura": 52.8},
    {"tributo": "ISS",          "canal": "whatsapp", "pct_cobertura": 38.4},
    {"tributo": "ISS",          "canal": "email",    "pct_cobertura": 41.2},
    {"tributo": "ISS",          "canal": "telefone", "pct_cobertura": 19.7},
    {"tributo": "ISS",          "canal": "endereco", "pct_cobertura": 88.6},
    {"tributo": "TAXA_LIMPEZA", "canal": "celular",  "pct_cobertura": 48.3},
    {"tributo": "TAXA_LIMPEZA", "canal": "whatsapp", "pct_cobertura": 32.1},
    {"tributo": "TAXA_LIMPEZA", "canal": "email",    "pct_cobertura": 22.8},
    {"tributo": "TAXA_LIMPEZA", "canal": "telefone", "pct_cobertura": 18.4},
    {"tributo": "TAXA_LIMPEZA", "canal": "endereco", "pct_cobertura": 91.7},
])


# ── Acesso real ao banco ──────────────────────────────────────────────────────

def _real_metricas(carteira_id: int) -> dict:
    from vega.db import queries
    df = queries.metricas_contactabilidade(carteira_id)
    if df.empty:
        return _MOCK_METRICAS
    row = df.iloc[0]
    return {
        "pct_contactaveis":        float(row["pct_contactaveis"] or 0),
        "pct_so_endereco":         float(row["pct_so_endereco"] or 0),
        "pct_incontactaveis":      float(row["pct_incontactaveis"] or 0),
        "valor_incontactavel_cents": int(row["valor_incontactavel_cents"] or 0),
    }


# ── KPIs ─────────────────────────────────────────────────────────────────────

def _kpi_card(label: str, value: str, sub: str = "", color: str = DELFT) -> html.Div:
    children = [
        html.Div(label, style=_LABEL_STYLE),
        html.Div(value, style={"fontSize": 22, "fontWeight": 700, "color": color}),
    ]
    if sub:
        children.append(html.Div(sub, style={"fontSize": 11, "color": GRAY, "marginTop": 2}))
    return html.Div(children, style={**_CARD, "marginBottom": 0})


def _row_kpis(m: dict) -> html.Div:
    return html.Div([
        _kpi_card(
            "Contactáveis digital",
            f"{m['pct_contactaveis']:.1f}%",
            "celular, WhatsApp, e-mail ou telefone",
            GREEN,
        ),
        _kpi_card(
            "Só endereço",
            f"{m['pct_so_endereco']:.1f}%",
            "sem contato digital",
            AMBER,
        ),
        _kpi_card(
            "Incontactáveis",
            f"{m['pct_incontactaveis']:.1f}%",
            "sem qualquer dado de contato",
            RED,
        ),
        _kpi_card(
            "Valor incontactável",
            _fmt_reais(m["valor_incontactavel_cents"]),
            "em risco de não recuperação",
            RED,
        ),
    ], style={
        "display": "grid",
        "gridTemplateColumns": "1fr 1fr 1fr 1fr",
        "gap": 12,
        "marginBottom": 16,
    })


# ── Figuras Plotly ────────────────────────────────────────────────────────────

def _fig_cobertura_canal(df: pd.DataFrame) -> go.Figure:
    """Barras horizontais — cobertura por canal."""
    canal_colors = {
        "celular":  "#3B82F6",
        "whatsapp": "#22C55E",
        "email":    "#8B5CF6",
        "telefone": "#F59E0B",
        "endereco": "#6B7280",
    }
    order = list(reversed(_CANAIS_ORDEM))
    df = df.set_index("canal").reindex(order).reset_index()
    labels = [_CANAIS_LABELS.get(c, c) for c in df["canal"]]
    colors = [canal_colors.get(c, GRAY) for c in df["canal"]]

    fig = go.Figure(go.Bar(
        x=df["pct_cobertura"],
        y=labels,
        orientation="h",
        marker_color=colors,
        text=[f"{v:.1f}%" for v in df["pct_cobertura"]],
        textposition="outside",
    ))
    fig.update_layout(
        height=220,
        margin={"l": 0, "r": 60, "t": 0, "b": 0},
        font=_PLOT_FONT,
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis={
            "range": [0, 110],
            "showgrid": True,
            "gridcolor": _GRID_COLOR,
            "title": "Cobertura (%)",
        },
        yaxis={"showgrid": False},
    )
    return fig


def _fig_contato_faixa(df: pd.DataFrame) -> go.Figure:
    """Barras empilhadas: valor por faixa × nível de contacto."""
    nivel_config = {
        "digital":       {"color": GREEN,  "label": "Digital"},
        "so_endereco":   {"color": AMBER,  "label": "Só endereço"},
        "incontactavel": {"color": RED,    "label": "Incontactável"},
    }
    ordem_faixas = [f for f in _FAIXAS_ORDEM if f in df["faixa_valor"].values]
    x_labels = [_FAIXAS_LABELS.get(f, f) for f in ordem_faixas]

    fig = go.Figure()
    for nivel, cfg in nivel_config.items():
        sub = df[df["nivel_contato_agrupado"] == nivel].set_index("faixa_valor")
        y = [sub.loc[f, "valor_cents"] / 100 if f in sub.index else 0 for f in ordem_faixas]
        fig.add_trace(go.Bar(
            name=cfg["label"],
            x=x_labels,
            y=y,
            marker_color=cfg["color"],
            opacity=0.88,
        ))
    fig.update_layout(
        height=260,
        barmode="stack",
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        font=_PLOT_FONT,
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend={"orientation": "h", "y": -0.22, "font": {"size": 10}},
        xaxis={"showgrid": False},
        yaxis={"showgrid": True, "gridcolor": _GRID_COLOR, "title": "Valor (R$)"},
    )
    return fig


# ── Heatmap HTML ──────────────────────────────────────────────────────────────

def _cell_style(pct: float) -> dict:
    if pct >= 50:
        return {"background": "#D1FAE5", "color": "#065F46"}
    if pct >= 30:
        return {"background": "#FEF3C7", "color": "#92400E"}
    return {"background": "#FEE2E2", "color": "#991B1B"}


def _heatmap_tabela(df: pd.DataFrame) -> html.Div:
    """Tabela pivot tributo × canal com células coloridas."""
    if df.empty:
        return html.Div("Sem dados de qualidade", style={"color": GRAY, "fontSize": 12})

    canais_presentes = [c for c in _CANAIS_ORDEM if c in df["canal"].values]
    pivot = df.pivot_table(
        index="tributo", columns="canal", values="pct_cobertura", fill_value=0.0
    )
    tributos = pivot.index.tolist()

    _th = {"padding": "8px 12px", "fontSize": 11, "fontWeight": 600,
           "borderBottom": "2px solid #E5E7EB", "background": "#F9FAFB"}
    header = html.Tr([
        html.Th("Tributo", style={**_th, "textAlign": "left"}),
        *[html.Th(_CANAIS_LABELS.get(c, c), style={**_th, "textAlign": "center"})
          for c in canais_presentes],
    ])

    rows = []
    for tributo in tributos:
        cells = [html.Td(
            tributo,
            style={"padding": "7px 12px", "fontSize": 12, "fontWeight": 500,
                   "borderBottom": "1px solid #F3F4F6"},
        )]
        for canal in canais_presentes:
            pct = float(pivot.loc[tributo, canal]) if canal in pivot.columns else 0.0
            cs = _cell_style(pct)
            cells.append(html.Td(
                f"{pct:.0f}%",
                style={
                    "padding": "6px 10px", "fontSize": 12, "textAlign": "center",
                    "fontWeight": 700, "borderRadius": 4,
                    "borderBottom": "1px solid #F3F4F6",
                    **cs,
                },
            ))
        rows.append(html.Tr(cells))

    legend = html.Div([
        html.Span("", style={
            "display": "inline-block", "width": 10, "height": 10,
            "background": "#D1FAE5", "borderRadius": 2, "marginRight": 4,
        }),
        html.Span("≥ 50%", style={"fontSize": 10, "color": "#065F46", "marginRight": 12}),
        html.Span("", style={
            "display": "inline-block", "width": 10, "height": 10,
            "background": "#FEF3C7", "borderRadius": 2, "marginRight": 4,
        }),
        html.Span("30–49%", style={"fontSize": 10, "color": "#92400E", "marginRight": 12}),
        html.Span("", style={
            "display": "inline-block", "width": 10, "height": 10,
            "background": "#FEE2E2", "borderRadius": 2, "marginRight": 4,
        }),
        html.Span("< 30%", style={"fontSize": 10, "color": "#991B1B"}),
    ], style={"marginTop": 10})

    return html.Div([
        html.Div(
            html.Table(
                [html.Thead(header), html.Tbody(rows)],
                style={"width": "100%", "borderCollapse": "separate",
                       "borderSpacing": "0 2px"},
            ),
            style={"overflowX": "auto"},
        ),
        legend,
    ])


# ── Componentes auxiliares ────────────────────────────────────────────────────

def _chart_card(title: str, subtitle: str, figure: go.Figure) -> html.Div:
    return html.Div([
        html.Div([
            html.Div(title, style={"fontSize": 13, "fontWeight": 600}),
            html.Div(subtitle, style={"fontSize": 10, "color": GRAY}),
        ], style={"marginBottom": 12}),
        dcc.Graph(figure=figure, config={"displayModeBar": False}),
    ], style=_CARD)


def _btn_insights() -> html.Div:
    return html.Div([
        html.Button(
            "Gerar insights cruzados",
            id="btn-insights-4",
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
        dcc.Loading(type="dot", color="#7B2CBF", style={"marginTop": 12}, children=html.Div(id="insights-result-4")),
    ], style=_CARD)


# ── Layout ────────────────────────────────────────────────────────────────────

def get_layout(carteira_id: int | None = None, sessao_id: int | None = None) -> html.Div:
    """Renderiza o conteúdo completo da Aba 5 — Contactabilidade."""
    if _is_demo():
        m              = _MOCK_METRICAS
        df_cobertura   = _MOCK_COBERTURA
        df_faixa       = _MOCK_CONTATO_FAIXA
        df_heatmap     = _MOCK_HEATMAP
    else:
        if carteira_id is None:
            return html.Div(
                "Selecione uma carteira para ver Contactabilidade.",
                style={"color": "#9ca3af", "padding": 24},
            )
        from vega.db import queries
        m              = _real_metricas(carteira_id)
        df_cobertura   = queries.cobertura_por_canal(carteira_id)
        df_faixa       = queries.contactabilidade_por_faixa(carteira_id)
        df_heatmap     = queries.heatmap_qualidade(carteira_id)

    return html.Div([
        # 1. Linha de 4 KPIs
        _row_kpis(m),

        # 2. Cobertura por canal
        _chart_card(
            "Cobertura por Canal",
            "% de CDAs ativas com cada canal de contacto preenchido",
            _fig_cobertura_canal(df_cobertura),
        ),

        # 3. Contactabilidade × faixa de valor
        _chart_card(
            "Contactabilidade por Faixa de Valor",
            "Valor ativo (R$) por faixa × nível de contacto",
            _fig_contato_faixa(df_faixa),
        ),

        # 4. Heatmap qualidade de dados
        html.Div([
            html.Div([
                html.Div("Qualidade de Dados por Canal e Tributo",
                         style={"fontSize": 13, "fontWeight": 600}),
                html.Div("% de CDAs com canal preenchido · verde ≥50% · âmbar 30–49% · vermelho <30%",
                         style={"fontSize": 10, "color": GRAY}),
            ], style={"marginBottom": 12}),
            _heatmap_tabela(df_heatmap),
        ], style=_CARD),

        # 5. Botão de insights
        _btn_insights(),
    ])


# ── Callbacks ─────────────────────────────────────────────────────────────────

def registrar_callbacks(app: Any) -> None:
    """Registra callbacks da Aba 5: geração de insights cruzados."""

    @app.callback(
        Output("insights-result-4", "children"),
        Input("btn-insights-4",     "n_clicks"),
        State("store-carteira-id",  "data"),
        State("store-sessao-id",    "data"),
        prevent_initial_call=True,
    )
    def gerar_insights(
        n_clicks: int,
        carteira_id: int | None,
        sessao_id: int | None,
    ) -> html.Div:
        if not n_clicks:
            raise PreventUpdate

        if _is_demo():
            m = _MOCK_METRICAS
        else:
            if not carteira_id:
                raise PreventUpdate
            m = _real_metricas(carteira_id)

        from vega.insights.generator import gerar_insights_contactabilidade
        texto = gerar_insights_contactabilidade(m)

        return html.Div([
            html.Div([
                html.Span("IA", style={
                    "background": VIOLET, "color": "#fff",
                    "fontSize": 9, "fontWeight": 700,
                    "padding": "1px 5px", "borderRadius": 3,
                    "marginRight": 8,
                }),
                html.Span(
                    "Insights gerados por IA — revisar antes de usar",
                    style={"fontSize": 10, "color": GRAY},
                ),
            ], style={"marginBottom": 8}),
            html.Div(
                texto,
                style={"fontSize": 12, "lineHeight": "1.7", "whiteSpace": "pre-wrap"},
            ),
        ], style={
            "background": "#F5F3FF",
            "border": "1px solid #DDD6FE",
            "borderRadius": 8,
            "padding": "12px 16px",
            "marginTop": 8,
        })
