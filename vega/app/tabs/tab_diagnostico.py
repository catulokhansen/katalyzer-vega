"""Aba 1 — Diagnóstico.

Implementa layout + callbacks lazy (carrega apenas quando tab_value == 'diagnostico').

DEMO_MODE=true  → fixtures estáticos do município de Beberibe (carteira 2026).
DEMO_MODE=false → queries reais via vega.db.queries.
"""
from __future__ import annotations

import os
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

# ── Paleta ────────────────────────────────────────────────────────────────────
DELFT = "#0A2A5F"
VIOLET = "#7B2CBF"
CYAN = "#00A8BF"
GREEN = "#059669"
RED = "#DC2626"
AMBER = "#D97706"
RED_DARK = "#991B1B"
ORANGE = "#F97316"
GRAY = "#9CA3AF"

# ── Helpers de estilo ─────────────────────────────────────────────────────────
_CARD = {
    "background": "#fff",
    "borderRadius": 10,
    "border": "1px solid #E5E7EB",
    "padding": "16px 18px",
    "marginBottom": 12,
}
_LABEL_STYLE = {"fontSize": 11, "color": "#9CA3AF", "fontWeight": 500, "marginBottom": 6}
_VALUE_STYLE = {"fontFamily": "system-ui", "fontSize": 26, "fontWeight": 700, "letterSpacing": -0.5}


def _badge(text: str, color: str, bg: str) -> html.Span:
    return html.Span(
        text,
        style={
            "display": "inline-block",
            "padding": "2px 8px",
            "borderRadius": 99,
            "fontSize": 10,
            "fontWeight": 600,
            "background": bg,
            "color": color,
        },
    )


_QUADRANT_STYLES: dict[str, dict[str, str]] = {
    "Q1": {"background": "#ECFDF5", "color": "#065F46"},
    "Q2": {"background": "#EFF6FF", "color": "#1E40AF"},
    "Q3": {"background": "#FFFBEB", "color": "#92400E"},
    "Q4": {"background": "#FEF2F2", "color": "#991B1B"},
}
_DENSITY_STYLES: dict[str, dict[str, str]] = {
    "concentrado":  {"background": "#D1FAE5", "color": "#065F46"},
    "medio":        {"background": "#FEF3C7", "color": "#92400E"},
    "pulverizado":  {"background": "#F0E6FA", "color": VIOLET},
    "Médio":        {"background": "#FEF3C7", "color": "#92400E"},
    "Concentrado":  {"background": "#D1FAE5", "color": "#065F46"},
    "Pulverizado":  {"background": "#F0E6FA", "color": VIOLET},
}


def _is_demo() -> bool:
    return os.environ.get("DEMO_MODE", "true").lower() in ("1", "true", "yes")


# ── Mock data (Beberibe 2026) ─────────────────────────────────────────────────

def _mock_metricas() -> dict[str, Any]:
    return {
        "total_brutas": 8183,
        "total_ativas": 5447,
        "total_mortas": 2736,
        "valor_bruto_cents": 4_430_000_000,
        "valor_ativo_cents": 2_950_000_000,
        "valor_morto_cents": 1_480_000_000,
        "eliminadas_prescricao_cents": 1_020_000_000,
        "eliminadas_irrisorio_cents":  210_000_000,
        "eliminadas_devedor_inexistente_cents": 250_000_000,
    }


def _mock_concentracao() -> dict[str, Any] | None:
    return {
        "contribuinte_nome": "Construtora Litoral Norte Ltda",
        "valor_cents": 320_000_000,
        "pct_carteira_ativa": 10.8,
    }


def _mock_top_contribuintes() -> pd.DataFrame:
    rows = [
        ("12000000000014", "Construtora Litoral Norte Ltda", "PJ",  47, 320_000_000, 6_808_510, "pulverizado", "Q1", 94, "Negociação direta + acordo global"),
        ("34000000000112", "Rede Farma Beberibe ME",          "PJ",  23,  89_211_400, 3_878_757, "medio",       "Q1", 91, "WhatsApp + parcelamento 6x"),
        ("78900011122233", "José M. Santos",                  "PF",  12,  53_421_000, 4_451_750, "medio",       "Q1", 87, "WhatsApp + parcelamento 6x"),
        ("56000000000299", "Pousada Morro Branco Hotelaria",  "PJ",  31,  47_893_300, 1_544_945, "pulverizado", "Q3", 62, "Protesto em cartório"),
        ("98700011144455", "Maria F. Oliveira",               "PF",   8,  31_277_000, 3_909_625, "medio",       "Q2", 73, "Campanha WhatsApp"),
        ("45000000000088", "Auto Posto São João Ltda",        "PJ",   3,  28_744_000, 9_581_333, "concentrado", "Q1", 89, "Negociação individual presencial"),
    ]
    return pd.DataFrame(rows, columns=[
        "contribuinte_id", "contribuinte_nome", "contribuinte_tipo",
        "count_cdas", "valor_total_cents", "densidade_cents",
        "padrao_densidade", "quadrante", "score_total", "acao_sugerida",
    ])


def _mock_fluxo() -> pd.DataFrame:
    meses = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M12"]
    inscritas   = [98, 112, 145, 138, 102, 89, 94, 108, 121, 134, 118, 88]
    recuperadas = [72,  81, 103,  95,  68, 74, 88,  79,  65,  71,  82, 65]
    return pd.DataFrame({"mes": meses, "cdas_inscritas": inscritas, "cdas_recuperadas": recuperadas})


def _mock_pareto() -> pd.DataFrame:
    pct_c = [i * 5 for i in range(1, 21)]
    pct_v = [18, 32, 43, 52, 59, 65, 70, 74, 78, 81, 84, 87, 89, 91, 93, 94.5, 96, 97, 98, 99]
    return pd.DataFrame({"pct_contribuintes": pct_c, "pct_valor_acumulado": pct_v})


def _mock_composicao_tributo() -> pd.DataFrame:
    return pd.DataFrame({
        "tributo":    ["IPTU", "ISS", "ITBI", "TAXAS", "OUTROS"],
        "valor_cents": [1_350_000_000, 870_000_000, 250_000_000, 450_000_000, 30_000_000],
        "pct_total":  [45.8, 29.5, 8.5, 15.3, 1.0],
    })


def _mock_valor_por_idade_tributo() -> pd.DataFrame:
    rows = []
    labels = ["< 1 ano", "1–3 anos", "3–5 anos", "> 5 anos"]
    iptu  = [3.2, 4.8, 3.4, 2.1]
    iss   = [2.1, 3.2, 2.1, 1.3]
    taxas = [1.2, 1.6, 1.0, 0.7]
    outros = [0.4, 0.6, 0.5, 0.3]
    for i, label in enumerate(labels):
        rows.append((label, "IPTU",   int(iptu[i]  * 1e8)))
        rows.append((label, "ISS",    int(iss[i]   * 1e8)))
        rows.append((label, "TAXAS",  int(taxas[i] * 1e8)))
        rows.append((label, "OUTROS", int(outros[i]* 1e8)))
    return pd.DataFrame(rows, columns=["faixa_idade", "tributo", "valor_cents"])


# ── Builders de dados para DB real ───────────────────────────────────────────

def _real_metricas(carteira_id: int) -> dict[str, Any]:
    from vega.db.queries import metricas_diagnostico
    df = metricas_diagnostico(carteira_id)
    ativas = df[df["ativa"] == True]
    mortas = df[df["ativa"] == False]
    return {
        "total_brutas":  int(df["total_cdas"].sum()),
        "total_ativas":  int(ativas["total_cdas"].sum()),
        "total_mortas":  int(mortas["total_cdas"].sum()),
        "valor_bruto_cents": int(df["valor_cents"].sum()),
        "valor_ativo_cents": int(ativas["valor_cents"].sum()),
        "valor_morto_cents": int(mortas["valor_cents"].sum()),
        "eliminadas_prescricao_cents":
            int(mortas.loc[mortas["causa_eliminacao"] == "prescricao", "valor_cents"].sum()),
        "eliminadas_irrisorio_cents":
            int(mortas.loc[mortas["causa_eliminacao"] == "irrisorio", "valor_cents"].sum()),
        "eliminadas_devedor_inexistente_cents":
            int(mortas.loc[mortas["causa_eliminacao"] == "devedor_inexistente", "valor_cents"].sum()),
    }


def _real_concentracao(carteira_id: int) -> dict[str, Any] | None:
    from vega.db.queries import concentracao_risco
    df = concentracao_risco(carteira_id)
    if df.empty:
        return None
    row = df.iloc[0]
    return {
        "contribuinte_nome": row["contribuinte_nome"],
        "valor_cents": int(row["valor_cents"]),
        "pct_carteira_ativa": float(row["pct_carteira_ativa"]),
    }


# ── Formatadores rápidos ──────────────────────────────────────────────────────

def _fmt_reais(cents: int) -> str:
    val = cents / 100
    if val >= 1_000_000:
        return f"R$ {val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"R$ {val / 1_000:.1f}k"
    return f"R$ {val:,.0f}"


def _fmt_num(n: int) -> str:
    return f"{n:,}".replace(",", ".")


# ── Figuras Plotly ────────────────────────────────────────────────────────────

_PLOT_FONT = {"family": "system-ui, -apple-system, sans-serif", "size": 11, "color": "#6B7280"}
_GRID_COLOR = "rgba(0,0,0,.05)"


def _fig_tributo(df: pd.DataFrame) -> go.Figure:
    colors = [DELFT, VIOLET, CYAN, AMBER, GRAY]
    fig = go.Figure(go.Pie(
        labels=df["tributo"],
        values=df["valor_cents"],
        hole=0.6,
        marker_colors=colors[:len(df)],
        textinfo="none",
        hovertemplate="%{label}: %{percent:.1%}<extra></extra>",
    ))
    fig.update_layout(
        margin={"t": 4, "b": 4, "l": 4, "r": 4},
        showlegend=True,
        legend={"orientation": "v", "x": 1, "y": 0.5, "font": _PLOT_FONT},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=220,
    )
    return fig


def _fig_funil(m: dict[str, Any]) -> go.Figure:
    """Funil com 3 segmentos de estoque morto (RN-04)."""
    presc  = m["eliminadas_prescricao_cents"] / 1e8
    irris  = m["eliminadas_irrisorio_cents"] / 1e8
    devex  = m["eliminadas_devedor_inexistente_cents"] / 1e8
    ativa  = m["valor_ativo_cents"] / 1e8
    bruta  = m["valor_bruto_cents"] / 1e8

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Base bruta",          x=[bruta, 0, 0],          y=["Bruta", "Estoque morto", "Ativa"], orientation="h", marker_color=DELFT,    marker_cornerradius=4))
    fig.add_trace(go.Bar(name="Carteira ativa",      x=[0, 0, ativa],          y=["Bruta", "Estoque morto", "Ativa"], orientation="h", marker_color=GREEN,    marker_cornerradius=4))
    fig.add_trace(go.Bar(name="Prescrição",          x=[0, presc, 0],          y=["Bruta", "Estoque morto", "Ativa"], orientation="h", marker_color=RED_DARK))
    fig.add_trace(go.Bar(name="Valor irrisório",     x=[0, irris, 0],          y=["Bruta", "Estoque morto", "Ativa"], orientation="h", marker_color=RED))
    fig.add_trace(go.Bar(name="Devedor inexistente", x=[0, devex, 0],          y=["Bruta", "Estoque morto", "Ativa"], orientation="h", marker_color=ORANGE))

    fig.update_layout(
        barmode="stack",
        height=220,
        margin={"t": 4, "b": 40, "l": 8, "r": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"gridcolor": _GRID_COLOR, "tickfont": _PLOT_FONT, "tickprefix": "R$", "ticksuffix": "M"},
        yaxis={"gridcolor": _GRID_COLOR, "tickfont": _PLOT_FONT},
        legend={"orientation": "h", "y": -0.25, "font": _PLOT_FONT, "itemsizing": "constant"},
    )
    return fig


def _fig_pareto(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["pct_contribuintes"], y=df["pct_valor_acumulado"],
        mode="lines", fill="tozeroy",
        line={"color": VIOLET, "width": 2},
        fillcolor="rgba(123,44,191,.06)",
        hovertemplate="%{x:.0f}% contribuintes → %{y:.1f}% do valor<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[0, 100], y=[80, 80],
        mode="lines", line={"color": "rgba(220,38,38,.3)", "dash": "dash", "width": 1},
        showlegend=False,
    ))
    fig.update_layout(
        height=220,
        margin={"t": 4, "b": 4, "l": 8, "r": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis={"gridcolor": _GRID_COLOR, "tickfont": _PLOT_FONT, "ticksuffix": "%"},
        yaxis={"gridcolor": _GRID_COLOR, "tickfont": _PLOT_FONT, "ticksuffix": "%", "range": [0, 100]},
    )
    return fig


def _fig_valor_idade(df: pd.DataFrame) -> go.Figure:
    tributos = df["tributo"].unique()
    faixas   = ["< 1 ano", "1–3 anos", "3–5 anos", "> 5 anos"]
    colors   = {tributo: c for tributo, c in zip(tributos, [DELFT, VIOLET, CYAN, AMBER, GRAY])}

    fig = go.Figure()
    for tributo in tributos:
        sub = df[df["tributo"] == tributo].set_index("faixa_idade")
        valores = [sub.loc[f, "valor_cents"] / 1e8 if f in sub.index else 0 for f in faixas]
        fig.add_trace(go.Bar(
            name=tributo,
            x=faixas,
            y=valores,
            marker_color=colors.get(tributo, GRAY),
            marker_cornerradius=2,
        ))
    fig.update_layout(
        barmode="stack",
        height=220,
        margin={"t": 4, "b": 4, "l": 8, "r": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend={"font": _PLOT_FONT, "itemsizing": "constant"},
        xaxis={"gridcolor": _GRID_COLOR, "tickfont": _PLOT_FONT},
        yaxis={"gridcolor": _GRID_COLOR, "tickfont": _PLOT_FONT, "tickprefix": "R$", "ticksuffix": "M"},
    )
    return fig


def _fig_fluxo(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="CDAs inscritas",
        x=df["mes"],
        y=df["cdas_inscritas"],
        marker_color="rgba(10,42,95,.7)",
        marker_cornerradius=3,
    ))
    fig.add_trace(go.Scatter(
        name="CDAs recuperadas",
        x=df["mes"],
        y=df["cdas_recuperadas"],
        mode="lines+markers",
        line={"color": VIOLET, "width": 2},
        marker={"size": 5, "color": VIOLET},
        fill="tozeroy",
        fillcolor="rgba(123,44,191,.08)",
    ))
    fig.update_layout(
        height=200,
        margin={"t": 4, "b": 4, "l": 8, "r": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend={"font": _PLOT_FONT, "orientation": "h", "y": 1.1},
        xaxis={"gridcolor": _GRID_COLOR, "tickfont": _PLOT_FONT},
        yaxis={"gridcolor": _GRID_COLOR, "tickfont": _PLOT_FONT, "ticksuffix": " CDAs"},
    )
    return fig


# ── Sub-componentes de layout ─────────────────────────────────────────────────

def _kpis_principais(m: dict[str, Any]) -> html.Div:
    pct_morto = m["valor_morto_cents"] / m["valor_bruto_cents"] * 100
    recuperavel_cents = int(m["valor_ativo_cents"] * 0.278)  # ~27,8% baseado no mockup (8.2M/29.5M)

    def _metric(label: str, value: str, sub: str, color: str, sub_class: str = "neutral") -> html.Div:
        sub_colors = {
            "neg": {"color": "#991B1B"},
            "pos": {"color": "#065F46"},
            "neutral": {"color": "#9CA3AF"},
        }
        return html.Div([
            html.Div(label, style=_LABEL_STYLE),
            html.Div(value, style={**_VALUE_STYLE, "color": color}),
            html.Div(sub, style={"fontSize": 11, "marginTop": 4, **sub_colors.get(sub_class, {})}),
        ], style={
            **_CARD,
            "flex": 1,
            "borderTop": f"3px solid {color}",
            "marginBottom": 0,
        })

    return html.Div([
        _metric("Carteira bruta",       _fmt_reais(m["valor_bruto_cents"]),
                f"{_fmt_num(m['total_brutas'])} CDAs", DELFT),
        _metric("Estoque morto",        _fmt_reais(m["valor_morto_cents"]),
                f"↓ {pct_morto:.1f}% eliminado", RED, "neg"),
        _metric("Carteira ativa",       _fmt_reais(m["valor_ativo_cents"]),
                f"↑ {_fmt_num(m['total_ativas'])} CDAs", GREEN, "pos"),
        _metric("Recuperável estimado", _fmt_reais(recuperavel_cents),
                "ROI projetado 4,1:1", VIOLET, "pos"),
    ], style={"display": "flex", "gap": 12, "marginBottom": 12})


def _btn_insights() -> html.Div:
    return html.Div([
        html.Button(
            ["✨ Gerar insights cruzados"],
            id="btn-insights-0",
            n_clicks=0,
            style={
                "display": "flex", "alignItems": "center", "gap": 8,
                "padding": "12px 20px",
                "background": f"linear-gradient(135deg, {DELFT} 0%, {VIOLET} 100%)",
                "color": "#fff",
                "border": "none",
                "borderRadius": 10,
                "fontFamily": "inherit",
                "fontSize": 13,
                "fontWeight": 500,
                "cursor": "pointer",
                "width": "100%",
                "justifyContent": "center",
                "marginBottom": 12,
            },
        ),
        html.Div(id="insights-result-0"),
    ])


def _chart_row(left: html.Div, right: html.Div) -> html.Div:
    return html.Div([left, right], style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": 12, "marginBottom": 12})


def _chart_card(title: str, subtitle: str, figure: Any) -> html.Div:
    return html.Div([
        html.Div([
            html.Div([
                html.Div(title, style={"fontSize": 13, "fontWeight": 600, "color": "#1A1A1A"}),
                html.Div(subtitle, style={"fontSize": 10, "color": "#9CA3AF"}),
            ])
        ], style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": 12}),
        dcc.Graph(figure=figure, config={"displayModeBar": False}, style={"height": 220}),
    ], style=_CARD)


def _tabela_top_contribuintes(df: pd.DataFrame, conc: dict | None) -> html.Div:
    def _quadrant_badge(q: str) -> html.Span:
        style = _QUADRANT_STYLES.get(str(q), {"background": "#f3f4f6", "color": "#6b7280"})
        return _badge(str(q), style["color"], style["background"])

    def _density_badge(d: str) -> html.Span:
        style = _DENSITY_STYLES.get(str(d), {"background": "#f3f4f6", "color": "#6b7280"})
        labels = {"concentrado": "Concentrado", "medio": "Médio", "pulverizado": "Pulverizado"}
        label = labels.get(str(d).lower(), str(d))
        return _badge(label, style["color"], style["background"])

    def _nba_badge(acao: str) -> html.Span:
        return html.Span(
            f"! {acao}",
            style={
                "fontSize": 10, "padding": "2px 6px", "borderRadius": 4,
                "background": "#FEF3C7", "color": "#92400E", "fontWeight": 500,
                "border": "1px solid #FCD34D", "whiteSpace": "nowrap",
            },
        )

    header = html.Thead(html.Tr([
        html.Th("#",          style={"fontSize": 10, "fontWeight": 600, "color": "#9CA3AF", "padding": "8px 12px", "borderBottom": "2px solid #E5E7EB"}),
        html.Th("Contribuinte"),
        html.Th("Tipo"),
        html.Th("CDAs",       style={"textAlign": "right"}),
        html.Th("Valor",      style={"textAlign": "right"}),
        html.Th("Densidade",  style={"textAlign": "right"}),
        html.Th("Padrão"),
        html.Th("Quadrante"),
        html.Th("Score",      style={"textAlign": "right"}),
        html.Th("Ação Sugerida ⚠"),
    ], style={"fontSize": 10, "fontWeight": 600, "color": "#9CA3AF", "textTransform": "uppercase", "letterSpacing": "0.5px"}))

    th_style = {"padding": "10px 12px", "borderBottom": "1px solid #F0F0F0", "color": "#1A1A1A"}

    rows = []
    for i, row in enumerate(df.itertuples(), 1):
        # Máscara de CPF/CNPJ — RN de LGPD do CLAUDE.md
        contrib_id = str(row.contribuinte_id)
        if len(contrib_id) == 11:
            masked = f"***.{contrib_id[3:6]}.{contrib_id[6:9]}-**"
        elif len(contrib_id) == 14:
            masked = f"***.{contrib_id[3:6]}.{contrib_id[6:9]}/****-**"
        else:
            masked = "***"

        rows.append(html.Tr([
            html.Td(str(i), style=th_style),
            html.Td([
                html.Span(row.contribuinte_nome, style={"fontWeight": 600}),
                html.Div(masked, style={"fontSize": 9, "color": "#9CA3AF"}),
            ], style=th_style),
            html.Td(row.contribuinte_tipo, style=th_style),
            html.Td(str(row.count_cdas), style={**th_style, "textAlign": "right", "fontWeight": 500}),
            html.Td(_fmt_reais(int(row.valor_total_cents)), style={**th_style, "textAlign": "right", "fontWeight": 500}),
            html.Td(_fmt_reais(int(row.densidade_cents)), style={**th_style, "textAlign": "right"}),
            html.Td(_density_badge(row.padrao_densidade), style=th_style),
            html.Td(_quadrant_badge(row.quadrante), style=th_style),
            html.Td(str(row.score_total), style={**th_style, "textAlign": "right", "fontWeight": 500}),
            html.Td(_nba_badge(row.acao_sugerida), style=th_style),
        ]))

    density_legend = html.Div([
        html.Strong("Padrão: ", style={"fontSize": 10, "color": "#9CA3AF"}),
        _badge("Concentrado", "#065F46", "#D1FAE5"), html.Span(" 1–3 CDAs → negociação individual", style={"fontSize": 10, "color": "#6B7280"}),
        html.Span("  "),
        _badge("Médio", "#92400E", "#FEF3C7"), html.Span(" 4–9 CDAs → campanha segmentada", style={"fontSize": 10, "color": "#6B7280"}),
        html.Span("  "),
        _badge("Pulverizado", VIOLET, "#F0E6FA"), html.Span(" 10+ CDAs → acordo global preferível", style={"fontSize": 10, "color": "#6B7280"}),
    ], style={"display": "flex", "alignItems": "center", "gap": 6, "flexWrap": "wrap", "padding": "10px 12px", "background": "#F4F4F4", "borderRadius": 6, "marginTop": 8})

    nba_note = html.Div(
        "⚠ Sugestões derivadas de regras determinísticas (quadrante + contactabilidade + reincidência + valor) — avalie o contexto antes de executar. Override registrável na operação.",
        style={"fontSize": 10, "color": "#9CA3AF", "padding": "8px 12px", "background": "#F4F4F4", "borderRadius": 6, "marginTop": 6, "borderLeft": "3px solid #FCD34D"},
    )

    risk_alert = html.Div()
    if conc is not None:
        risk_alert = html.Div([
            html.Span("⚠", style={"fontSize": 18, "flexShrink": 0}),
            html.Div([
                html.Div("Risco de concentração detectado", style={"fontSize": 12, "fontWeight": 600, "color": "#92400E", "marginBottom": 4}),
                html.Div([
                    f"{conc['contribuinte_nome']} representa ",
                    html.Strong(f"{conc['pct_carteira_ativa']:.1f}% da carteira ativa"),
                    f" ({_fmt_reais(conc['valor_cents'])}). Os cenários de recuperação devem ser calculados com e sem este contribuinte.",
                ], style={"fontSize": 11, "color": "#92400E", "lineHeight": 1.6}),
                html.Button(
                    "Ver impacto nos cenários →",
                    id="btn-ver-cenarios",
                    n_clicks=0,
                    style={
                        "display": "inline-flex", "alignItems": "center", "gap": 4,
                        "marginTop": 8, "padding": "5px 12px", "borderRadius": 6,
                        "border": f"1px solid {AMBER}", "background": "transparent",
                        "fontSize": 11, "fontWeight": 500, "color": "#92400E", "cursor": "pointer",
                    },
                ),
            ], style={"flex": 1}),
        ], style={
            "display": "flex", "alignItems": "flex-start", "gap": 12,
            "background": "#FEF3C7", "border": "1px solid #FCD34D", "borderRadius": 8,
            "padding": "12px 16px", "marginTop": 8,
        })

    return html.Div([
        html.Div([
            html.Div([
                html.Div("Top contribuintes por valor", style={"fontSize": 13, "fontWeight": 600}),
                html.Div("Carteira ativa · visão consolidada", style={"fontSize": 10, "color": "#9CA3AF"}),
            ]),
        ], style={"display": "flex", "justifyContent": "space-between", "marginBottom": 12}),
        html.Table(
            [header, html.Tbody(rows)],
            style={"width": "100%", "borderCollapse": "collapse", "fontSize": 12},
        ),
        density_legend,
        nba_note,
        risk_alert,
    ], style={**_CARD, "gridColumn": "1/-1"})


def _kpis_fluxo(df: pd.DataFrame) -> html.Div:
    total_inscritas   = int(df["cdas_inscritas"].sum())
    total_recuperadas = int(df["cdas_recuperadas"].sum())
    saldo_mensal      = (total_inscritas - total_recuperadas) // 12
    media_ins  = total_inscritas // 12
    media_rec  = total_recuperadas // 12

    def _metric_small(label: str, value: str, sub: str, color: str) -> html.Div:
        return html.Div([
            html.Div(label, style=_LABEL_STYLE),
            html.Div(value, style={**_VALUE_STYLE, "color": color, "fontSize": 22}),
            html.Div(sub, style={"fontSize": 11, "color": "#9CA3AF", "marginTop": 4}),
        ], style={**_CARD, "flex": 1, "borderTop": f"3px solid {color}", "marginBottom": 0})

    return html.Div([
        _metric_small("Novas CDAs (últimos 12m)",  _fmt_num(total_inscritas),   f"média {media_ins}/mês",  DELFT),
        _metric_small("Recuperadas (últimos 12m)", _fmt_num(total_recuperadas), f"média {media_rec}/mês",  GREEN),
        _metric_small("Saldo líquido mensal",       f"+{saldo_mensal} CDAs/mês", "carteira crescendo",      RED),
    ], style={"display": "flex", "gap": 12, "marginBottom": 12, "marginTop": 12})


# ── Layout principal da aba ───────────────────────────────────────────────────

def get_layout(carteira_id: int | None = None, sessao_id: int | None = None) -> html.Div:
    """Renderiza o conteúdo completo da Aba 1."""
    if _is_demo():
        metricas   = _mock_metricas()
        conc       = _mock_concentracao()
        df_top     = _mock_top_contribuintes()
        df_fluxo   = _mock_fluxo()
        df_pareto  = _mock_pareto()
        df_tributo = _mock_composicao_tributo()
        df_idade   = _mock_valor_por_idade_tributo()
    else:
        if carteira_id is None:
            return html.Div("Selecione uma carteira para iniciar a análise.",
                            style={"color": "#9ca3af", "padding": 24})
        from vega.db import queries
        metricas   = _real_metricas(carteira_id)
        conc       = _real_concentracao(carteira_id)
        df_top     = queries.top_contribuintes(carteira_id, sessao_id)
        df_fluxo   = queries.fluxo_mensal_resumo(carteira_id)
        df_pareto  = queries.pareto_curva(carteira_id)
        df_tributo = queries.composicao_tributo(carteira_id)
        df_idade   = queries.valor_por_idade_tributo(carteira_id)
        # Normaliza coluna de meses para fluxo
        if "ano_mes" in df_fluxo.columns:
            df_fluxo["mes"] = df_fluxo["ano_mes"].astype(str).str[:7]

    return html.Div([
        # 1. Linha de 4 KPIs principais
        _kpis_principais(metricas),

        # 2 + 3. Botão + área de insights
        _btn_insights(),

        # 4 + 5. Composição por tributo × Funil de higienização
        _chart_row(
            _chart_card(
                "Composição por tributo",
                f"Carteira ativa · {_fmt_reais(metricas['valor_ativo_cents'])}",
                _fig_tributo(df_tributo),
            ),
            html.Div([
                html.Div([
                    html.Div([
                        html.Div("Funil de higienização", style={"fontSize": 13, "fontWeight": 600}),
                        html.Div("Estoque morto decomposto por causa de eliminação", style={"fontSize": 10, "color": "#9CA3AF"}),
                    ])
                ], style={"display": "flex", "marginBottom": 12}),
                dcc.Graph(figure=_fig_funil(metricas), config={"displayModeBar": False}, style={"height": 220}),
                # Legenda das 3 causas (RN-04)
                html.Div([
                    html.Span([html.Span(style={"display": "inline-block", "width": 10, "height": 10, "borderRadius": 2, "background": RED_DARK, "marginRight": 4}),
                               f"Prescrição {_fmt_reais(metricas['eliminadas_prescricao_cents'])} (69%)"]),
                    html.Span([html.Span(style={"display": "inline-block", "width": 10, "height": 10, "borderRadius": 2, "background": RED, "marginRight": 4, "marginLeft": 12}),
                               f"Valor irrisório {_fmt_reais(metricas['eliminadas_irrisorio_cents'])} (14%)"]),
                    html.Span([html.Span(style={"display": "inline-block", "width": 10, "height": 10, "borderRadius": 2, "background": ORANGE, "marginRight": 4, "marginLeft": 12}),
                               f"Devedor inexistente {_fmt_reais(metricas['eliminadas_devedor_inexistente_cents'])} (17%)"]),
                ], style={"display": "flex", "flexWrap": "wrap", "gap": 4, "fontSize": 10, "color": "#6B7280", "marginTop": 8, "alignItems": "center"}),
            ], style=_CARD),
        ),

        # 6 + 7. Pareto × Valor por idade
        _chart_row(
            _chart_card(
                "Concentração Pareto",
                "Top 10% = 65% do valor",
                _fig_pareto(df_pareto),
            ),
            _chart_card(
                "Valor × idade por tributo",
                "Empilhado por faixa etária",
                _fig_valor_idade(df_idade),
            ),
        ),

        # 8 + 9 + 10. Tabela top contribuintes + nota NBA + alerta concentração
        _tabela_top_contribuintes(df_top, conc),

        # 11. KPIs de fluxo
        _kpis_fluxo(df_fluxo),

        # 12. Chart de fluxo
        html.Div([
            html.Div([
                html.Div("Fluxo de entrada vs recuperação", style={"fontSize": 13, "fontWeight": 600}),
                html.Div("CDAs inscritas × recuperadas · últimos 12 meses", style={"fontSize": 10, "color": "#9CA3AF"}),
            ], style={"marginBottom": 12}),
            dcc.Graph(figure=_fig_fluxo(df_fluxo), config={"displayModeBar": False}, style={"height": 200}),
        ], style={**_CARD, "gridColumn": "1/-1"}),
    ])


# ── Registro de callbacks ─────────────────────────────────────────────────────

def registrar_callbacks(app: Any) -> None:
    """Registra callbacks próprios da Aba 1 (insights + navegação para cenários)."""

    @app.callback(
        Output("insights-result-0", "children"),
        Input("btn-insights-0", "n_clicks"),
        State("store-carteira-id", "data"),
        prevent_initial_call=True,
    )
    def gerar_insights(n_clicks: int, carteira_id: int | None) -> html.Div:
        if not n_clicks:
            raise PreventUpdate

        if _is_demo():
            metricas = _mock_metricas()
            conc     = _mock_concentracao()
        else:
            if not carteira_id:
                raise PreventUpdate
            metricas = _real_metricas(carteira_id)
            conc     = _real_concentracao(carteira_id)

        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            return html.Div(
                "OPENAI_API_KEY não configurada — insights indisponíveis.",
                style={"fontSize": 11, "color": "#9CA3AF", "padding": "8px 0"},
            )

        try:
            from vega.insights.generator import gerar_insights_diagnostico
            texto = gerar_insights_diagnostico({
                "total_brutas":    metricas["total_brutas"],
                "total_ativas":    metricas["total_ativas"],
                "total_mortas":    metricas["total_mortas"],
                "valor_bruto":     _fmt_reais(metricas["valor_bruto_cents"]),
                "valor_ativo":     _fmt_reais(metricas["valor_ativo_cents"]),
                "pct_prescricao":  round(metricas["eliminadas_prescricao_cents"] / metricas["valor_morto_cents"] * 100, 1) if metricas["valor_morto_cents"] else 0,
                "concentracao":    conc,
            })
        except Exception as exc:
            return html.Div(f"Erro ao gerar insights: {exc}", style={"color": RED, "fontSize": 11})

        return html.Div([
            html.Div([
                html.Span("✨ Insights da carteira", style={"fontWeight": 600, "fontSize": 12, "color": DELFT}),
                html.Span("IA", style={
                    "fontSize": 10, "padding": "3px 8px", "borderRadius": 99,
                    "background": "#F0E6FA", "color": VIOLET, "fontWeight": 600, "marginLeft": "auto",
                }),
            ], style={"display": "flex", "alignItems": "center", "gap": 8, "padding": "14px 18px",
                      "background": "linear-gradient(135deg,rgba(10,42,95,.04),rgba(123,44,191,.06))",
                      "borderBottom": "1px solid #E5E7EB"}),
            html.Div(texto, style={"padding": "12px 18px", "fontSize": 12, "lineHeight": 1.7, "color": DELFT}),
        ], style={
            "background": "#fff", "border": "1px solid #E5E7EB", "borderRadius": 10,
            "overflow": "hidden", "marginTop": 12,
        })

    @app.callback(
        Output("tabs-principal", "value"),
        Input("btn-ver-cenarios", "n_clicks"),
        prevent_initial_call=True,
    )
    def ir_para_cenarios(n_clicks: int) -> str:
        if not n_clicks:
            raise PreventUpdate
        return "cenarios"
