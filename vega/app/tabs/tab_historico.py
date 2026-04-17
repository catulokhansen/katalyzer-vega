"""Aba 6 — Histórico de Parcelamento.

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

_TIPO_LABELS = {
    "reincidente_pagador": "Reincidente pagador",
    "so_parcelou":         "Só parcelou",
    "primeiro_debito":     "Primeiro débito",
}
_TIPO_COLORS = {
    "reincidente_pagador": RED,
    "so_parcelou":         AMBER,
    "primeiro_debito":     DELFT,
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


# ── Mock data — Beberibe 2026 ─────────────────────────────────────────────────
_MOCK_METRICAS: dict = {
    "pct_reincidentes":         23.4,
    "valor_reincidentes_cents": 412_000_000,
    "taxa_quebra_media":        47.3,
    "parcela_media_quebra":     3.2,
}

_MOCK_REINCIDENCIA = pd.DataFrame({
    "tipo":       ["primeiro_debito", "reincidente_pagador", "so_parcelou"],
    "valor_cents": [1_245_000_000,    412_000_000,           285_000_000],
})

_MOCK_SOBREVIVENCIA: list[float] = [
    100.0, 88.3, 78.1, 69.4, 62.7, 57.3,
    53.8,  51.2, 49.6, 48.4, 47.6, 47.3,
]

_MOCK_PROGRAMAS = pd.DataFrame({
    "nome_programa":  [
        "REFIS Municipal 2023",
        "Regulariza Beberibe 2022",
        "Parcelamento COVID-19 2021",
        "REFIS 2019",
    ],
    "aderiram":       [342,  218, 501, 287],
    "concluiram":     [218,  145, 241, 198],
    "quebraram":      [124,   73, 260,  89],
    "taxa_conclusao": [63.7, 66.5, 48.1, 69.0],
})

_MOCK_CONCENTRACAO = pd.DataFrame({
    "bairro": [
        "Centro", "Beberibe Sede", "Parajuru", "Morro Branco",
        "Fontainha", "Sucatinga", "Barra Nova", "Uruaú",
        "Retiro Grande", "Lagoa do Mato",
    ],
    "contribuintes": [421, 287, 198, 176, 143, 138, 121, 98, 87, 74],
    "valor_cents": [
        380_000_000, 265_000_000, 198_000_000, 152_000_000,
        132_000_000, 118_000_000, 107_000_000,  89_000_000,
         76_000_000,  63_000_000,
    ],
    "pct_total": [19.8, 13.8, 10.3, 7.9, 6.9, 6.1, 5.6, 4.6, 4.0, 3.3],
})

_MOCK_COHORTS = pd.DataFrame({
    "nome_programa": [
        "REFIS Municipal 2023",
        "Regulariza Beberibe 2022",
        "Parcelamento COVID-19 2021",
        "REFIS 2019",
    ],
    "aderiram":            [342, 218, 501, 287],
    "concluiram":          [218, 145, 241, 198],
    "quebraram":           [124,  73, 260,  89],
    "voltaram_carteira":   [ 98,  58, 187,  67],
    "reabordados_sucesso": [ 41,  27,  63,  32],
    "perfil_dominante":    ["PF_IPTU", "PJ_ISS", "PF_IPTU", "PF_IPTU"],
})


# ── Acesso real ao banco ──────────────────────────────────────────────────────

def _real_metricas(carteira_id: int) -> dict:
    from vega.db import queries
    df = queries.metricas_historico(carteira_id)
    if df.empty:
        return _MOCK_METRICAS
    row = df.iloc[0]
    return {
        "pct_reincidentes":         float(row["pct_reincidentes"] or 0),
        "valor_reincidentes_cents": int(row["valor_reincidentes_cents"] or 0),
        "taxa_quebra_media":        float(row["taxa_quebra_media"] or 0),
        "parcela_media_quebra":     float(row["parcela_media_quebra"] or 0),
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
            "Reincidentes",
            f"{m['pct_reincidentes']:.1f}%",
            "CDAs com parcelamento anterior",
            RED,
        ),
        _kpi_card(
            "Valor reincidentes",
            _fmt_reais(m["valor_reincidentes_cents"]),
            "valor ativo em reincidentes",
        ),
        _kpi_card(
            "Taxa de quebra (média)",
            f"{m['taxa_quebra_media']:.1f}%",
            "parcelamentos encerrados por inadimplência",
            AMBER,
        ),
        _kpi_card(
            "Parcela média de quebra",
            f"{m['parcela_media_quebra']:.1f}ª",
            "parcela onde ocorre a quebra",
        ),
    ], style={
        "display": "grid",
        "gridTemplateColumns": "1fr 1fr 1fr 1fr",
        "gap": 12,
        "marginBottom": 16,
    })


# ── Figuras Plotly ────────────────────────────────────────────────────────────

def _fig_reincidencia(df: pd.DataFrame) -> go.Figure:
    """Barras horizontais: valor por tipo de comportamento do devedor."""
    ordem = ["reincidente_pagador", "so_parcelou", "primeiro_debito"]
    df = df.set_index("tipo").reindex(reversed(ordem)).reset_index().dropna(subset=["valor_cents"])
    labels = [_TIPO_LABELS.get(t, t) for t in df["tipo"]]
    colors = [_TIPO_COLORS.get(t, GRAY) for t in df["tipo"]]

    fig = go.Figure(go.Bar(
        x=df["valor_cents"] / 100,
        y=labels,
        orientation="h",
        marker_color=colors,
        opacity=0.88,
        text=[_fmt_reais(int(v)) for v in df["valor_cents"]],
        textposition="outside",
    ))
    fig.update_layout(
        height=200,
        margin={"l": 0, "r": 80, "t": 0, "b": 0},
        font=_PLOT_FONT,
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis={"showgrid": True, "gridcolor": _GRID_COLOR, "title": "Valor (R$)"},
        yaxis={"showgrid": False},
    )
    return fig


def _fig_sobrevivencia(sobrevivencia: list[float]) -> go.Figure:
    """Curva de sobrevivência de parcelamento (1ª a 12ª parcela)."""
    x = list(range(1, len(sobrevivencia) + 1))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x,
        y=sobrevivencia,
        mode="lines+markers",
        name="Ativos (%)",
        line={"color": DELFT, "width": 2.5},
        marker={"size": 6},
        fill="tozeroy",
        fillcolor="rgba(10,42,95,0.08)",
    ))
    # Linha de referência: taxa final
    if sobrevivencia:
        taxa_final = sobrevivencia[-1]
        fig.add_hline(
            y=taxa_final,
            line_dash="dot",
            line_color=AMBER,
            annotation_text=f"Conclusão: {taxa_final:.1f}%",
            annotation_position="top right",
            annotation_font_size=10,
        )
    fig.update_layout(
        height=250,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        font=_PLOT_FONT,
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis={
            "title": "Parcela",
            "showgrid": False,
            "dtick": 1,
            "tickmode": "linear",
        },
        yaxis={
            "title": "Ativos (%)",
            "range": [0, 110],
            "showgrid": True,
            "gridcolor": _GRID_COLOR,
        },
        showlegend=False,
    )
    return fig


# ── Tabelas HTML ──────────────────────────────────────────────────────────────

def _badge_taxa(taxa: float) -> html.Span:
    if taxa >= 60:
        bg, fg = "#D1FAE5", "#065F46"
    elif taxa >= 46:
        bg, fg = "#FEF3C7", "#92400E"
    else:
        bg, fg = "#FEE2E2", "#991B1B"
    return html.Span(
        f"{taxa:.1f}%",
        style={
            "background": bg, "color": fg, "fontWeight": 700,
            "fontSize": 11, "padding": "2px 8px", "borderRadius": 4,
        },
    )


def _badge_perfil(perfil: str) -> html.Span:
    return html.Span(
        perfil or "—",
        style={
            "background": "#EDE9FE", "color": VIOLET, "fontWeight": 600,
            "fontSize": 10, "padding": "2px 7px", "borderRadius": 4,
        },
    )


def _tabela_programas(df: pd.DataFrame) -> html.Div:
    """Tabela: histórico de parcelamento por programa."""
    _th = {"padding": "8px 12px", "fontSize": 11, "fontWeight": 600,
           "borderBottom": "2px solid #E5E7EB", "background": "#F9FAFB",
           "textAlign": "right"}
    header = html.Tr([
        html.Th("Programa", style={**_th, "textAlign": "left"}),
        html.Th("Aderiram",   style=_th),
        html.Th("Concluíram", style=_th),
        html.Th("Quebraram",  style=_th),
        html.Th("Conclusão",  style={**_th, "textAlign": "center"}),
    ])
    _td = {"padding": "7px 12px", "fontSize": 12, "textAlign": "right",
           "borderBottom": "1px solid #F3F4F6"}
    rows = [
        html.Tr([
            html.Td(row["nome_programa"],
                    style={**_td, "textAlign": "left", "fontWeight": 500}),
            html.Td(f"{row['aderiram']:,}",   style=_td),
            html.Td(f"{row['concluiram']:,}", style=_td),
            html.Td(f"{row['quebraram']:,}",  style=_td),
            html.Td(_badge_taxa(float(row["taxa_conclusao"])),
                    style={**_td, "textAlign": "center"}),
        ])
        for _, row in df.iterrows()
    ]
    return html.Div(
        html.Table(
            [html.Thead(header), html.Tbody(rows)],
            style={"width": "100%", "borderCollapse": "collapse"},
        ),
        style={"overflowX": "auto"},
    )


def _tabela_concentracao(df: pd.DataFrame) -> html.Div:
    """Tabela: concentração geográfica por bairro."""
    _th = {"padding": "8px 12px", "fontSize": 11, "fontWeight": 600,
           "borderBottom": "2px solid #E5E7EB", "background": "#F9FAFB",
           "textAlign": "right"}
    header = html.Tr([
        html.Th("Bairro",        style={**_th, "textAlign": "left"}),
        html.Th("Contribuintes", style=_th),
        html.Th("Valor",         style=_th),
        html.Th("% Total",       style=_th),
    ])
    _td = {"padding": "7px 12px", "fontSize": 12, "textAlign": "right",
           "borderBottom": "1px solid #F3F4F6"}
    rows = [
        html.Tr([
            html.Td(row["bairro"],
                    style={**_td, "textAlign": "left", "fontWeight": 500}),
            html.Td(f"{row['contribuintes']:,}", style=_td),
            html.Td(_fmt_reais(int(row["valor_cents"])),
                    style={**_td, "fontWeight": 600}),
            html.Td(f"{row['pct_total']:.1f}%",  style=_td),
        ])
        for _, row in df.iterrows()
    ]
    return html.Div(
        html.Table(
            [html.Thead(header), html.Tbody(rows)],
            style={"width": "100%", "borderCollapse": "collapse"},
        ),
        style={"overflowX": "auto"},
    )


def _tabela_cohorts(df: pd.DataFrame) -> html.Div:
    """Tabela: comportamento pós-campanha por cohort."""
    _th = {"padding": "8px 10px", "fontSize": 11, "fontWeight": 600,
           "borderBottom": "2px solid #E5E7EB", "background": "#F9FAFB",
           "textAlign": "right", "whiteSpace": "nowrap"}
    header = html.Tr([
        html.Th("Programa",            style={**_th, "textAlign": "left"}),
        html.Th("Aderiram",            style=_th),
        html.Th("Concluíram",          style=_th),
        html.Th("Quebraram",           style=_th),
        html.Th("Voltaram carteira",   style=_th),
        html.Th("Reabord. c/ sucesso", style=_th),
        html.Th("Perfil dominante",    style={**_th, "textAlign": "center"}),
    ])
    _td = {"padding": "7px 10px", "fontSize": 12, "textAlign": "right",
           "borderBottom": "1px solid #F3F4F6"}
    rows = [
        html.Tr([
            html.Td(row["nome_programa"],
                    style={**_td, "textAlign": "left", "fontWeight": 500}),
            html.Td(f"{row['aderiram']:,}",           style=_td),
            html.Td(f"{row['concluiram']:,}",          style=_td),
            html.Td(f"{row['quebraram']:,}",           style=_td),
            html.Td(f"{row['voltaram_carteira']:,}",   style=_td),
            html.Td(f"{row['reabordados_sucesso']:,}", style=_td),
            html.Td(_badge_perfil(row["perfil_dominante"]),
                    style={**_td, "textAlign": "center"}),
        ])
        for _, row in df.iterrows()
    ]
    return html.Div(
        html.Table(
            [html.Thead(header), html.Tbody(rows)],
            style={"width": "100%", "borderCollapse": "collapse"},
        ),
        style={"overflowX": "auto"},
    )


# ── Componentes auxiliares ────────────────────────────────────────────────────

def _chart_card(title: str, subtitle: str, figure: go.Figure) -> html.Div:
    return html.Div([
        html.Div([
            html.Div(title, style={"fontSize": 13, "fontWeight": 600}),
            html.Div(subtitle, style={"fontSize": 10, "color": GRAY}),
        ], style={"marginBottom": 12}),
        dcc.Graph(figure=figure, config={"displayModeBar": False}),
    ], style=_CARD)


def _table_card(title: str, subtitle: str, table: html.Div) -> html.Div:
    return html.Div([
        html.Div([
            html.Div(title, style={"fontSize": 13, "fontWeight": 600}),
            html.Div(subtitle, style={"fontSize": 10, "color": GRAY}),
        ], style={"marginBottom": 12}),
        table,
    ], style=_CARD)


def _btn_insights() -> html.Div:
    return html.Div([
        html.Button(
            "Gerar insights cruzados",
            id="btn-insights-5",
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
        html.Div(id="insights-result-5", style={"marginTop": 12}),
    ], style=_CARD)


# ── Layout ────────────────────────────────────────────────────────────────────

def get_layout(carteira_id: int | None = None, sessao_id: int | None = None) -> html.Div:
    """Renderiza o conteúdo completo da Aba 6 — Histórico."""
    if _is_demo():
        m               = _MOCK_METRICAS
        df_reincid      = _MOCK_REINCIDENCIA
        sobrevivencia   = _MOCK_SOBREVIVENCIA
        df_programas    = _MOCK_PROGRAMAS
        df_concentracao = _MOCK_CONCENTRACAO
        df_cohorts      = _MOCK_COHORTS
    else:
        if carteira_id is None:
            return html.Div(
                "Selecione uma carteira para ver Histórico.",
                style={"color": "#9ca3af", "padding": 24},
            )
        from vega.db import queries
        m               = _real_metricas(carteira_id)
        df_reincid      = queries.reincidencia_por_tipo(carteira_id)
        sobrevivencia   = queries.sobrevivencia_parcelamento(carteira_id)
        df_programas    = queries.programas_historico(carteira_id)
        df_concentracao = queries.concentracao_geografica(carteira_id)
        df_cohorts      = queries.cohort_campanha(carteira_id)

    return html.Div([
        # 1. Linha de 4 KPIs
        _row_kpis(m),

        # 2. Reincidência vs primeiro débito
        _chart_card(
            "Reincidência vs Primeiro Débito",
            "Valor ativo por tipo de comportamento histórico do devedor",
            _fig_reincidencia(df_reincid),
        ),

        # 3. Curva de sobrevivência
        html.Div([
            html.Div([
                html.Div("Curva de Sobrevivência do Parcelamento",
                         style={"fontSize": 13, "fontWeight": 600}),
                html.Div(
                    "% de parcelamentos ainda ativos por parcela · estimado de cohorts_campanha",
                    style={"fontSize": 10, "color": GRAY},
                ),
            ], style={"marginBottom": 12}),
            dcc.Graph(
                figure=_fig_sobrevivencia(sobrevivencia),
                config={"displayModeBar": False},
            ) if sobrevivencia else html.Div(
                "Sem histórico de parcelamento disponível.",
                style={"color": GRAY, "fontSize": 12, "padding": 8},
            ),
        ], style=_CARD),

        # 4. Tabela: histórico de programas
        _table_card(
            "Histórico de Parcelamento por Programa",
            "Taxa de conclusão: verde ≥60% · âmbar 46–59% · vermelho <45%",
            _tabela_programas(df_programas),
        ),

        # 5. Tabela: concentração geográfica
        _table_card(
            "Concentração Geográfica por Bairro",
            "Top 10 bairros por valor ativo",
            _tabela_concentracao(df_concentracao),
        ),

        # 6. Tabela: comportamento pós-campanha por cohort
        _table_card(
            "Comportamento Pós-Campanha por Cohort",
            "Histórico de adesão, conclusão, quebra e reabordagem por programa",
            _tabela_cohorts(df_cohorts),
        ),

        # 7. Botão de insights
        _btn_insights(),
    ])


# ── Callbacks ─────────────────────────────────────────────────────────────────

def registrar_callbacks(app: Any) -> None:
    """Registra callbacks da Aba 6: geração de insights cruzados."""

    @app.callback(
        Output("insights-result-5", "children"),
        Input("btn-insights-5",     "n_clicks"),
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

        from vega.insights.generator import gerar_insights_historico
        texto = gerar_insights_historico(m)

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
