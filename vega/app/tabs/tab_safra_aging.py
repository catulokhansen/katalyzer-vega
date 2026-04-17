"""Aba 4 — Safra & Aging.

DEMO_MODE=true  → fixtures estáticos do município de Beberibe (carteira 2026).
DEMO_MODE=false → queries reais via vega.db.queries.

Curva de aging: barras empilhadas com 2 séries por faixa etária.
  - Valor normal: gradiente verde→vermelho monotônico por urgência (RN-01).
  - Prescrição interrompida: mesmo gradiente com padrão hachurado (Plotly marker.pattern).
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

# Gradiente monotônico de aging — lt_6m=verde → 4a_5a=vermelho escuro (RN-01)
_AGING_FAIXAS  = ["lt_6m", "6m_1a", "1a_2a", "2a_3a", "3a_4a", "4a_5a"]
_AGING_LABELS  = ["< 6m", "6m–1a", "1a–2a", "2a–3a", "3a–4a", "4a–5a"]
_AGING_COLORS  = ["#22C55E", "#84CC16", "#EAB308", "#F97316", "#EF4444", "#991B1B"]

_MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
             "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


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
    "safras_analisadas": 6,
    "melhor_safra": 2021,
    "prescricao_bruta_cents": 320_000_000,
    "prescricao_liquida_cents": 198_000_000,
    "idade_media_ponderada": 3.2,
    "mediana_idade": 2.8,
}

_MOCK_VINTAGE = pd.DataFrame({
    "safra": [2018, 2019, 2020, 2021, 2022, 2023],
    "valor_inscrito_cents": [
        480_000_000, 520_000_000, 390_000_000,
        610_000_000, 550_000_000, 400_000_000,
    ],
    "taxa_recuperacao_pct": [8.2, 11.5, 6.8, 14.3, 9.7, 4.1],
})

_MOCK_AGING = pd.DataFrame({
    "faixa_idade": _AGING_FAIXAS,
    "valor_normal_cents": [
        95_000_000, 380_000_000, 620_000_000,
        750_000_000, 580_000_000, 290_000_000,
    ],
    "valor_interrompido_cents": [
        8_000_000, 45_000_000, 87_000_000,
        120_000_000, 95_000_000, 48_000_000,
    ],
})

_MOCK_DECAY_MESES = list(range(0, 61, 6))  # 0, 6, 12, …, 60
_MOCK_DECAY_RATES: dict[int, list] = {
    2019: [0.0, 2.1, 4.8, 6.9, 8.3, 9.4, 10.2, 10.8, 11.2, 11.4, 11.5],
    2020: [0.0, 1.4, 3.2, 5.1, 6.3, 7.2, 7.9,  8.3,  8.5,  8.6,  6.8],
    2021: [0.0, 3.5, 7.1, 10.2, 12.5, 13.8, 14.3, None, None, None, None],
    2022: [0.0, 2.8, 5.3, 7.8,  9.7,  None, None, None, None, None, None],
}

_MOCK_SAZONALIDADE = pd.DataFrame({
    "mes": list(range(1, 13)),
    "media_inscritas": [
        142, 98, 187, 223, 310, 285,
        178, 195, 267, 312, 289, 341,
    ],
    "media_recuperadas": [
        31, 22, 45, 67, 88, 71,
        52, 61, 78, 94, 82, 102,
    ],
})


def _mock_decay_df() -> pd.DataFrame:
    rows = []
    for safra, rates in _MOCK_DECAY_RATES.items():
        for meses, taxa in zip(_MOCK_DECAY_MESES, rates):
            if taxa is not None:
                rows.append({
                    "safra": safra,
                    "meses_desde_inscricao": meses,
                    "taxa_recuperacao_pct": taxa,
                })
    return pd.DataFrame(rows)


# ── Acesso real ao banco ──────────────────────────────────────────────────────

def _real_metricas(carteira_id: int) -> dict:
    from vega.db import queries
    df = queries.metricas_safra(carteira_id)
    if df.empty:
        return _MOCK_METRICAS
    row = df.iloc[0]
    return {
        "safras_analisadas": int(row["safras_analisadas"] or 0),
        "melhor_safra": int(row["melhor_safra"]) if row["melhor_safra"] else "—",
        "prescricao_bruta_cents": int(row["prescricao_bruta_cents"] or 0),
        "prescricao_liquida_cents": int(row["prescricao_liquida_cents"] or 0),
        "idade_media_ponderada": float(row["idade_media_ponderada"] or 0),
        "mediana_idade": float(row["mediana_idade"] or 0),
    }


# ── KPIs ─────────────────────────────────────────────────────────────────────

def _kpi_card(label: str, value: str, sub: str = "") -> html.Div:
    children = [
        html.Div(label, style=_LABEL_STYLE),
        html.Div(value, style={"fontSize": 22, "fontWeight": 700, "color": DELFT}),
    ]
    if sub:
        children.append(
            html.Div(sub, style={"fontSize": 11, "color": GRAY, "marginTop": 2})
        )
    return html.Div(children, style={**_CARD, "marginBottom": 0})


def _kpi_prescricao(bruta_cents: int, liquida_cents: int) -> html.Div:
    return html.Div([
        html.Div("Prescrição (12m)", style=_LABEL_STYLE),
        html.Div([
            html.Div([
                html.Div("Bruta", style={"fontSize": 10, "color": GRAY}),
                html.Div(
                    _fmt_reais(bruta_cents),
                    style={"fontSize": 18, "fontWeight": 700, "color": RED},
                ),
            ], style={"textAlign": "center"}),
            html.Div(
                "×",
                style={"fontSize": 14, "color": GRAY, "alignSelf": "center", "padding": "0 8px"},
            ),
            html.Div([
                html.Div("Líquida", style={"fontSize": 10, "color": GRAY}),
                html.Div(
                    _fmt_reais(liquida_cents),
                    style={"fontSize": 18, "fontWeight": 700, "color": AMBER},
                ),
            ], style={"textAlign": "center"}),
        ], style={"display": "flex", "alignItems": "center"}),
        html.Div(
            "interrompidas descontadas",
            style={"fontSize": 10, "color": GRAY, "marginTop": 4},
        ),
    ], style={**_CARD, "marginBottom": 0})


def _row_kpis(m: dict) -> html.Div:
    return html.Div([
        _kpi_card("Safras analisadas", str(m["safras_analisadas"]), "anos distintos"),
        _kpi_card("Melhor safra", str(m["melhor_safra"]), "maior taxa de recuperação"),
        _kpi_prescricao(m["prescricao_bruta_cents"], m["prescricao_liquida_cents"]),
        _kpi_card(
            "Idade média ponderada",
            f"{m['idade_media_ponderada']:.1f} anos",
            f"mediana: {m['mediana_idade']:.1f} anos",
        ),
    ], style={
        "display": "grid",
        "gridTemplateColumns": "1fr 1fr 1fr 1fr",
        "gap": 12,
        "marginBottom": 16,
    })


# ── Figuras Plotly ────────────────────────────────────────────────────────────

def _fig_vintage(df: pd.DataFrame) -> go.Figure:
    """Barras (valor inscrito) + linha (taxa de recuperação) — duplo eixo Y."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["safra"].astype(str),
        y=df["valor_inscrito_cents"] / 100,
        name="Valor inscrito",
        marker_color=DELFT,
        opacity=0.82,
        yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=df["safra"].astype(str),
        y=df["taxa_recuperacao_pct"],
        name="Taxa recuperação %",
        mode="lines+markers",
        line={"color": GREEN, "width": 2},
        marker={"size": 6},
        yaxis="y2",
    ))
    max_taxa = df["taxa_recuperacao_pct"].max() if not df.empty else 20
    fig.update_layout(
        height=260,
        margin={"l": 0, "r": 40, "t": 0, "b": 0},
        font=_PLOT_FONT,
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend={"orientation": "h", "y": -0.18, "font": {"size": 10}},
        xaxis={"showgrid": False},
        yaxis={"title": "Valor (R$)", "showgrid": True, "gridcolor": _GRID_COLOR},
        yaxis2={
            "title": "Taxa recuperação (%)",
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
            "range": [0, max(float(max_taxa) * 1.4, 20)],
        },
    )
    return fig


def _fig_aging(df: pd.DataFrame) -> go.Figure:
    """Barras empilhadas: valor normal (sólido) + interrompido (hachurado).

    Cores monotônicas da esquerda para a direita (RN-01):
    verde (#22C55E) → vermelho escuro (#991B1B).
    """
    labels_map = dict(zip(_AGING_FAIXAS, _AGING_LABELS))
    colors_map = dict(zip(_AGING_FAIXAS, _AGING_COLORS))
    order_map  = {f: i for i, f in enumerate(_AGING_FAIXAS)}

    df = df.copy()
    df["label"] = df["faixa_idade"].map(labels_map).fillna(df["faixa_idade"])
    df["_ord"]  = df["faixa_idade"].map(order_map).fillna(99)
    df = df.sort_values("_ord")

    bar_colors = [colors_map.get(f, GRAY) for f in df["faixa_idade"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["label"],
        y=df["valor_normal_cents"] / 100,
        name="Valor ativo",
        marker_color=bar_colors,
        legendgroup="normal",
    ))
    fig.add_trace(go.Bar(
        x=df["label"],
        y=df["valor_interrompido_cents"] / 100,
        name="Prescrição interrompida",
        marker={
            "color": bar_colors,
            "pattern": {"shape": "/", "solidity": 0.55},
        },
        legendgroup="interrompido",
    ))
    fig.update_layout(
        height=260,
        barmode="stack",
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        font=_PLOT_FONT,
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend={"orientation": "h", "y": -0.2, "font": {"size": 10}},
        xaxis={"showgrid": False},
        yaxis={"showgrid": True, "gridcolor": _GRID_COLOR, "title": "Valor (R$)"},
    )
    return fig


def _fig_decay(df: pd.DataFrame) -> go.Figure:
    """Múltiplas linhas de decay — uma por safra."""
    palette = [DELFT, GREEN, AMBER, VIOLET, RED, GRAY, "#06B6D4", "#F43F5E"]
    fig = go.Figure()
    for i, safra in enumerate(sorted(df["safra"].unique())):
        dfs = df[df["safra"] == safra].sort_values("meses_desde_inscricao")
        fig.add_trace(go.Scatter(
            x=dfs["meses_desde_inscricao"],
            y=dfs["taxa_recuperacao_pct"],
            name=str(safra),
            mode="lines+markers",
            line={"color": palette[i % len(palette)], "width": 2},
            marker={"size": 5},
            connectgaps=False,
        ))
    fig.update_layout(
        height=260,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        font=_PLOT_FONT,
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend={
            "orientation": "h", "y": -0.22,
            "font": {"size": 10}, "title_text": "Safra",
        },
        xaxis={"title": "Meses desde inscrição", "showgrid": False, "dtick": 6},
        yaxis={"title": "Taxa recuperação (%)", "showgrid": True, "gridcolor": _GRID_COLOR},
    )
    return fig


def _fig_sazonalidade(df: pd.DataFrame) -> go.Figure:
    """Barras agrupadas Jan–Dez: CDAs inscritas vs recuperadas."""
    mes_labels = [_MESES_PT[int(m) - 1] for m in df["mes"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=mes_labels,
        y=df["media_inscritas"],
        name="Inscritas (média)",
        marker_color=DELFT,
        opacity=0.85,
    ))
    fig.add_trace(go.Bar(
        x=mes_labels,
        y=df["media_recuperadas"],
        name="Recuperadas (média)",
        marker_color=GREEN,
        opacity=0.85,
    ))
    fig.update_layout(
        height=240,
        barmode="group",
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        font=_PLOT_FONT,
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend={"orientation": "h", "y": -0.22, "font": {"size": 10}},
        xaxis={"showgrid": False},
        yaxis={"showgrid": True, "gridcolor": _GRID_COLOR, "title": "CDAs (média mensal)"},
    )
    return fig


# ── Componentes auxiliares ────────────────────────────────────────────────────

def _chart_card(title: str, subtitle: str, figure: go.Figure) -> html.Div:
    return html.Div([
        html.Div([
            html.Div(title, style={"fontSize": 13, "fontWeight": 600}),
            html.Div(subtitle, style={"fontSize": 10, "color": GRAY}),
        ], style={"marginBottom": 12}),
        dcc.Graph(figure=figure, config={"displayModeBar": False}),
    ], style=_CARD)


def _aviso_historico_vazio() -> html.Div:
    return html.Div([
        html.Div("⚠", style={"fontSize": 20, "marginRight": 12, "alignSelf": "center"}),
        html.Div([
            html.Div(
                "Histórico de safras não disponível",
                style={"fontWeight": 600, "fontSize": 13},
            ),
            html.Div(
                "Popule vega.historico_safra para ativar a curva de decay.",
                style={"fontSize": 11, "color": GRAY},
            ),
        ]),
    ], style={
        "display": "flex",
        "alignItems": "flex-start",
        "background": "#FFFBEB",
        "border": "1px solid #FCD34D",
        "borderRadius": 8,
        "padding": "12px 16px",
    })


def _btn_insights() -> html.Div:
    return html.Div([
        html.Button(
            "Gerar insights cruzados",
            id="btn-insights-3",
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
        html.Div(id="insights-result-3", style={"marginTop": 12}),
    ], style=_CARD)


# ── Layout ────────────────────────────────────────────────────────────────────

def get_layout(carteira_id: int | None = None, sessao_id: int | None = None) -> html.Div:
    """Renderiza o conteúdo completo da Aba 4 — Safra & Aging."""
    if _is_demo():
        m               = _MOCK_METRICAS
        df_vintage      = _MOCK_VINTAGE
        df_aging        = _MOCK_AGING
        df_decay        = _mock_decay_df()
        df_sazon        = _MOCK_SAZONALIDADE
        historico_vazio = False
    else:
        if carteira_id is None:
            return html.Div(
                "Selecione uma carteira para ver Safra & Aging.",
                style={"color": "#9ca3af", "padding": 24},
            )
        from vega.db import queries
        m               = _real_metricas(carteira_id)
        df_vintage      = queries.vintage_por_safra(carteira_id)
        df_aging        = queries.aging_por_faixa(carteira_id)
        df_decay        = queries.decay_por_safra(carteira_id)
        df_sazon        = queries.sazonalidade(carteira_id)
        historico_vazio = df_decay.empty

    return html.Div([
        # 1. Linha de 4 KPIs
        _row_kpis(m),

        # 2. Análise de safra/vintage
        _chart_card(
            "Análise de Safra / Vintage",
            "Valor inscrito por safra (barras) × taxa de recuperação histórica (linha)",
            _fig_vintage(df_vintage),
        ),

        # 3. Curva de aging
        _chart_card(
            "Curva de Aging",
            "Valor ativo por faixa etária · normal (sólido) × prescrição interrompida (hachurado)",
            _fig_aging(df_aging),
        ),

        # 4. Decay de recuperação
        html.Div([
            html.Div([
                html.Div("Decay de Recuperação por Safra", style={"fontSize": 13, "fontWeight": 600}),
                html.Div(
                    "Taxa acumulada de recuperação (%) × meses desde inscrição",
                    style={"fontSize": 10, "color": GRAY},
                ),
            ], style={"marginBottom": 12}),
            _aviso_historico_vazio() if historico_vazio else dcc.Graph(
                figure=_fig_decay(df_decay),
                config={"displayModeBar": False},
            ),
        ], style=_CARD),

        # 5. Sazonalidade
        _chart_card(
            "Sazonalidade",
            "Média de CDAs inscritas e recuperadas por mês do ano",
            _fig_sazonalidade(df_sazon),
        ),

        # 6. Botão de insights
        _btn_insights(),
    ])


# ── Callbacks ─────────────────────────────────────────────────────────────────

def registrar_callbacks(app: Any) -> None:
    """Registra callbacks da Aba 4: geração de insights cruzados."""

    @app.callback(
        Output("insights-result-3", "children"),
        Input("btn-insights-3",     "n_clicks"),
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

        from vega.insights.generator import gerar_insights_safra_aging
        texto = gerar_insights_safra_aging(m)

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
