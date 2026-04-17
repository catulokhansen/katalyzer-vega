"""Aba 2 — Segmentação.

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

# ── Paleta (idêntica à Aba 1) ─────────────────────────────────────────────────
DELFT  = "#0A2A5F"
VIOLET = "#7B2CBF"
CYAN   = "#00A8BF"
AMBER  = "#D97706"
GRAY   = "#9CA3AF"
GREEN  = "#059669"

_CARD = {
    "background": "#fff",
    "borderRadius": 10,
    "border": "1px solid #E5E7EB",
    "padding": "16px 18px",
    "marginBottom": 12,
}
_LABEL_STYLE = {"fontSize": 11, "color": "#9CA3AF", "fontWeight": 500, "marginBottom": 6}
_PLOT_FONT   = {"family": "system-ui, -apple-system, sans-serif", "size": 11, "color": "#6B7280"}
_GRID_COLOR  = "rgba(0,0,0,.05)"

_FAIXA_LABELS: dict[str, str] = {
    "ate_500":   "Até R$500",
    "500_2k":    "R$500–2k",
    "2k_10k":    "R$2k–10k",
    "10k_50k":   "R$10k–50k",
    "acima_50k": ">R$50k",
}


def _is_demo() -> bool:
    return os.environ.get("DEMO_MODE", "true").lower() in ("1", "true", "yes")


def _fmt_reais(cents: int) -> str:
    val = cents / 100
    if val >= 1_000_000:
        return f"R$ {val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"R$ {val / 1_000:.1f}k"
    return f"R$ {val:,.0f}"


def _fmt_num(n: int) -> str:
    return f"{n:,}".replace(",", ".")


# ── Mock data (Beberibe 2026) ─────────────────────────────────────────────────

def _mock_distribuicao_faixa_valor() -> pd.DataFrame:
    return pd.DataFrame({
        "faixa_valor": ["ate_500", "500_2k", "2k_10k", "10k_50k", "acima_50k"],
        "count_cdas":  [812,       1543,     1891,     987,       214],
        "valor_cents": [24_800_000, 185_000_000, 510_000_000, 1_130_000_000, 1_100_200_000],
        "pct_count":   [14.9,  28.3,  34.7,  18.1,   3.9],
        "pct_valor":   [ 0.8,   6.3,  17.3,  38.3,  37.3],
    })


def _mock_pf_vs_pj() -> pd.DataFrame:
    return pd.DataFrame({
        "contribuinte_tipo": ["PF",            "PJ"],
        "count_cdas":        [3821,            1626],
        "valor_cents":       [1_180_000_000, 1_770_000_000],
        "count_contrib":     [2340,             487],
    })


def _mock_matriz_segmentos() -> pd.DataFrame:
    return pd.DataFrame({
        "tributo":     ["IPTU", "ISS",  "ITBI", "TAXAS", "OUTROS"],
        "ate_500":     [ 312,    211,     48,     198,      43],
        "500_2k":      [ 541,    387,    112,     421,      82],
        "2k_10k":      [ 721,    482,    198,     389,     101],
        "10k_50k":     [ 411,    287,    167,      89,      33],
        "acima_50k":   [  87,     63,     48,      12,       4],
    })


# ── Carregadores para banco real ──────────────────────────────────────────────

def _real_distribuicao_faixa_valor(carteira_id: int) -> pd.DataFrame:
    from vega.db.queries import distribuicao_faixa_valor
    return distribuicao_faixa_valor(carteira_id)


def _real_pf_vs_pj(carteira_id: int) -> pd.DataFrame:
    from vega.db.queries import pf_vs_pj
    return pf_vs_pj(carteira_id)


def _real_matriz_segmentos(carteira_id: int) -> pd.DataFrame:
    from vega.db.queries import matriz_segmentos
    return matriz_segmentos(carteira_id)


# ── Figuras Plotly ────────────────────────────────────────────────────────────

def _fig_faixa_valor(df: pd.DataFrame) -> go.Figure:
    labels = [_FAIXA_LABELS.get(f, f) for f in df["faixa_valor"]]
    fig = go.Figure(go.Bar(
        x=labels,
        y=df["count_cdas"],
        marker_color=VIOLET,
        marker_cornerradius=4,
        hovertemplate="%{x}<br>%{y:,} CDAs<extra></extra>",
    ))
    fig.update_layout(
        height=240,
        margin={"t": 4, "b": 4, "l": 8, "r": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis={"gridcolor": _GRID_COLOR, "tickfont": _PLOT_FONT},
        yaxis={"gridcolor": _GRID_COLOR, "tickfont": _PLOT_FONT, "ticksuffix": " CDAs"},
    )
    return fig


def _fig_pf_vs_pj(df: pd.DataFrame) -> go.Figure:
    cores = {"PF": DELFT, "PJ": VIOLET}
    fig = go.Figure()
    for _, row in df.iterrows():
        tipo = row["contribuinte_tipo"]
        fig.add_trace(go.Bar(
            name=tipo,
            x=[tipo],
            y=[row["count_cdas"]],
            marker_color=cores.get(tipo, GRAY),
            marker_cornerradius=4,
            hovertemplate=f"{tipo}: %{{y:,}} CDAs<br>{_fmt_reais(int(row['valor_cents']))}<extra></extra>",
        ))
    fig.update_layout(
        height=240,
        margin={"t": 4, "b": 4, "l": 8, "r": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis={"gridcolor": _GRID_COLOR, "tickfont": _PLOT_FONT},
        yaxis={"gridcolor": _GRID_COLOR, "tickfont": _PLOT_FONT, "ticksuffix": " CDAs"},
        barmode="group",
    )
    return fig


# ── Componentes de layout ─────────────────────────────────────────────────────

def _chart_card(title: str, subtitle: str, figure: Any) -> html.Div:
    return html.Div([
        html.Div([
            html.Div(title,    style={"fontSize": 13, "fontWeight": 600, "color": "#1A1A1A"}),
            html.Div(subtitle, style={"fontSize": 10, "color": "#9CA3AF"}),
        ], style={"marginBottom": 12}),
        dcc.Graph(figure=figure, config={"displayModeBar": False}),
    ], style=_CARD)


def _kpis_segmentacao(df_faixa: pd.DataFrame, df_pfpj: pd.DataFrame) -> html.Div:
    total_cdas  = int(df_faixa["count_cdas"].sum())
    total_valor = int(df_faixa["valor_cents"].sum())

    pf_row  = df_pfpj[df_pfpj["contribuinte_tipo"] == "PF"]
    pj_row  = df_pfpj[df_pfpj["contribuinte_tipo"] == "PJ"]
    pf_pct  = round(int(pf_row["count_cdas"].sum()) / total_cdas * 100, 1) if total_cdas else 0
    pj_pct  = round(100 - pf_pct, 1)

    def _kpi(label: str, value: str, sub: str, color: str) -> html.Div:
        return html.Div([
            html.Div(label, style=_LABEL_STYLE),
            html.Div(value, style={
                "fontFamily": "system-ui", "fontSize": 26, "fontWeight": 700,
                "letterSpacing": -0.5, "color": color,
            }),
            html.Div(sub, style={"fontSize": 11, "color": "#9CA3AF", "marginTop": 4}),
        ], style={
            **_CARD,
            "flex": 1,
            "borderTop": f"3px solid {color}",
            "marginBottom": 0,
        })

    total_contrib = int(df_pfpj["count_contrib"].sum())

    return html.Div([
        _kpi("CDAs ativas segmentadas", _fmt_num(total_cdas),
             f"{_fmt_num(total_contrib)} contribuintes", DELFT),
        _kpi("Valor ativo total", _fmt_reais(total_valor),
             "carteira higienizada", VIOLET),
        _kpi("Pessoa Física", f"{pf_pct}%",
             f"{_fmt_num(int(pf_row['count_cdas'].sum()))} CDAs", CYAN),
        _kpi("Pessoa Jurídica", f"{pj_pct}%",
             f"{_fmt_num(int(pj_row['count_cdas'].sum()))} CDAs", AMBER),
    ], style={"display": "flex", "gap": 12, "marginBottom": 12})


def _tabela_matriz(df: pd.DataFrame) -> html.Div:
    faixas = ["ate_500", "500_2k", "2k_10k", "10k_50k", "acima_50k"]
    faixas_presentes = [f for f in faixas if f in df.columns]
    labels = [_FAIXA_LABELS[f] for f in faixas_presentes]

    th_style = {
        "padding": "8px 12px", "fontSize": 10, "fontWeight": 600,
        "color": "#9CA3AF", "textTransform": "uppercase", "letterSpacing": "0.5px",
        "borderBottom": "2px solid #E5E7EB",
    }
    td_style = {
        "padding": "9px 12px", "fontSize": 12, "borderBottom": "1px solid #F0F0F0",
        "textAlign": "right",
    }

    header = html.Thead(html.Tr(
        [html.Th("Tributo", style={**th_style, "textAlign": "left"})]
        + [html.Th(l, style=th_style) for l in labels]
        + [html.Th("Total", style={**th_style, "color": DELFT})]
    ))

    rows = []
    totais = {f: 0 for f in faixas_presentes}
    for _, row in df.iterrows():
        cells = [html.Td(row["tributo"], style={**td_style, "textAlign": "left", "fontWeight": 600})]
        row_total = 0
        for f in faixas_presentes:
            v = int(row.get(f, 0))
            totais[f] += v
            row_total += v
            cells.append(html.Td(_fmt_num(v) if v else "—", style=td_style))
        cells.append(html.Td(_fmt_num(row_total), style={**td_style, "fontWeight": 700, "color": DELFT}))
        rows.append(html.Tr(cells))

    # Linha de totais
    grand_total = sum(totais.values())
    total_cells = [html.Td("Total", style={**td_style, "textAlign": "left", "fontWeight": 700, "color": DELFT})]
    for f in faixas_presentes:
        total_cells.append(html.Td(_fmt_num(totais[f]), style={**td_style, "fontWeight": 700}))
    total_cells.append(html.Td(_fmt_num(grand_total), style={**td_style, "fontWeight": 700, "color": DELFT}))
    rows.append(html.Tr(total_cells, style={"background": "#F9FAFB"}))

    return html.Div([
        html.Div([
            html.Div("Matriz de segmentos", style={"fontSize": 13, "fontWeight": 600}),
            html.Div("Tributo × faixa de valor — CDAs ativas", style={"fontSize": 10, "color": "#9CA3AF"}),
        ], style={"marginBottom": 12}),
        html.Div(
            html.Table(
                [header, html.Tbody(rows)],
                style={"width": "100%", "borderCollapse": "collapse", "fontSize": 12},
            ),
            style={"overflowX": "auto"},
        ),
    ], style=_CARD)


def _btn_insights_1() -> html.Div:
    return html.Div([
        html.Button(
            "✨ Gerar insights cruzados",
            id="btn-insights-1",
            n_clicks=0,
            style={
                "display": "flex", "alignItems": "center", "justifyContent": "center",
                "gap": 8, "padding": "12px 20px", "width": "100%",
                "background": f"linear-gradient(135deg, {DELFT} 0%, {VIOLET} 100%)",
                "color": "#fff", "border": "none", "borderRadius": 10,
                "fontFamily": "inherit", "fontSize": 13, "fontWeight": 500,
                "cursor": "pointer", "marginBottom": 12,
            },
        ),
        html.Div(id="insights-result-1"),
    ])


# ── Layout principal ──────────────────────────────────────────────────────────

def get_layout(carteira_id: int | None = None, sessao_id: int | None = None) -> html.Div:
    """Renderiza o conteúdo completo da Aba 2 — Segmentação."""
    if _is_demo():
        df_faixa = _mock_distribuicao_faixa_valor()
        df_pfpj  = _mock_pf_vs_pj()
        df_matriz = _mock_matriz_segmentos()
    else:
        if carteira_id is None:
            return html.Div(
                "Selecione uma carteira para iniciar a análise.",
                style={"color": "#9ca3af", "padding": 24},
            )
        df_faixa  = _real_distribuicao_faixa_valor(carteira_id)
        df_pfpj   = _real_pf_vs_pj(carteira_id)
        df_matriz = _real_matriz_segmentos(carteira_id)

    return html.Div([
        # 1. KPIs de segmentação
        _kpis_segmentacao(df_faixa, df_pfpj),

        # 2 + 3. Charts: distribuição faixa valor × PF vs PJ
        html.Div([
            _chart_card(
                "Distribuição por faixa de valor",
                f"CDAs ativas · {_fmt_num(int(df_faixa['count_cdas'].sum()))} total",
                _fig_faixa_valor(df_faixa),
            ),
            _chart_card(
                "Pessoa Física vs Pessoa Jurídica",
                "CDAs ativas por tipo de contribuinte",
                _fig_pf_vs_pj(df_pfpj),
            ),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": 12, "marginBottom": 12}),

        # 4. Tabela matriz de segmentos
        _tabela_matriz(df_matriz),

        # 5. Botão de insights
        _btn_insights_1(),
    ])


# ── Registro de callbacks ─────────────────────────────────────────────────────

def registrar_callbacks(app: Any) -> None:
    """Registra callbacks próprios da Aba 2 — insights de segmentação."""

    @app.callback(
        Output("insights-result-1", "children"),
        Input("btn-insights-1", "n_clicks"),
        State("store-carteira-id", "data"),
        prevent_initial_call=True,
    )
    def gerar_insights(n_clicks: int, carteira_id: int | None) -> html.Div:
        if not n_clicks:
            raise PreventUpdate

        if _is_demo():
            df_faixa = _mock_distribuicao_faixa_valor()
            df_pfpj  = _mock_pf_vs_pj()
            df_matriz = _mock_matriz_segmentos()
        else:
            if not carteira_id:
                raise PreventUpdate
            df_faixa  = _real_distribuicao_faixa_valor(carteira_id)
            df_pfpj   = _real_pf_vs_pj(carteira_id)
            df_matriz = _real_matriz_segmentos(carteira_id)

        if not os.environ.get("OPENAI_API_KEY"):
            return html.Div(
                "OPENAI_API_KEY não configurada — insights indisponíveis.",
                style={"fontSize": 11, "color": "#9CA3AF", "padding": "8px 0"},
            )

        try:
            from vega.insights.generator import gerar_insights_segmentacao
            texto = gerar_insights_segmentacao({
                "faixas": df_faixa[["faixa_valor", "count_cdas", "pct_valor"]].to_dict("records"),
                "pf_vs_pj": df_pfpj[["contribuinte_tipo", "count_cdas", "count_contrib"]].to_dict("records"),
                "total_ativas": int(df_faixa["count_cdas"].sum()),
                "valor_total":  _fmt_reais(int(df_faixa["valor_cents"].sum())),
            })
        except Exception as exc:
            return html.Div(f"Erro ao gerar insights: {exc}", style={"color": "#DC2626", "fontSize": 11})

        return html.Div([
            html.Div([
                html.Span("✨ Insights de segmentação", style={"fontWeight": 600, "fontSize": 12, "color": DELFT}),
                html.Span("IA", style={
                    "fontSize": 10, "padding": "3px 8px", "borderRadius": 99,
                    "background": "#F0E6FA", "color": VIOLET, "fontWeight": 600, "marginLeft": "auto",
                }),
            ], style={
                "display": "flex", "alignItems": "center", "gap": 8,
                "padding": "14px 18px",
                "background": "linear-gradient(135deg,rgba(10,42,95,.04),rgba(123,44,191,.06))",
                "borderBottom": "1px solid #E5E7EB",
            }),
            html.Div(texto, style={"padding": "12px 18px", "fontSize": 12, "lineHeight": 1.7, "color": DELFT}),
        ], style={
            "background": "#fff", "border": "1px solid #E5E7EB", "borderRadius": 10,
            "overflow": "hidden", "marginTop": 12,
        })
