"""Aba 3 — Scoring.

DEMO_MODE=true  → fixtures estáticos do município de Beberibe (carteira 2026).
DEMO_MODE=false → queries reais via vega.db.queries.

A matriz de quadrantes e o alerta Q1 vazio são recalculados via callback
quando os thresholds da sidebar (store-parametros) mudam.
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

# Estilos de quadrante — cores e bordas
_Q_STYLE: dict[str, dict[str, str]] = {
    "Q1": {"bg": "#ECFDF5", "text": "#065F46", "border": "#6EE7B7", "label": "Q1 — Alvo principal"},
    "Q2": {"bg": "#EFF6FF", "text": "#1E40AF", "border": "#93C5FD", "label": "Q2 — Alta recuperab."},
    "Q3": {"bg": "#FFFBEB", "text": "#92400E", "border": "#FCD34D", "label": "Q3 — Alta prioridade"},
    "Q4": {"bg": "#FEF2F2", "text": "#991B1B", "border": "#FCA5A5", "label": "Q4 — Monitorar"},
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
# Distribuições de score — 5 447 CDAs totais
# Prioridade (0–60): bins de 5 pts — pico em 30–40, caudas curtas
_MOCK_PRI_BIN_LOWER = list(range(0, 60, 5))   # [0,5,10,...,55]
_MOCK_PRI_COUNTS    = [45, 89, 234, 389, 623, 799, 812, 934, 721, 501, 189, 111]
# Sum = 5447 ✓ — CDAs com pri>=40: 721+501+189+111 = 1522

# Recuperabilidade (0–50): bins de 5 pts — leve skew para baixo
_MOCK_REC_BIN_LOWER = list(range(0, 50, 5))   # [0,5,10,...,45]
_MOCK_REC_COUNTS    = [412, 587, 798, 645, 467, 712, 689, 534, 378, 225]
# Sum = 5447 ✓ — CDAs com rec>=30: 712+689+534+378+225 = 2538

_MOCK_TOTAL_VALOR_CENTS = 2_950_000_000


def _mock_distribuicao_quadrantes(thr_pri: int = 40, thr_rec: int = 30) -> pd.DataFrame:
    """Calcula quadrantes dinamicamente pela hipótese de independência."""
    total = 5447

    n_hi_pri = sum(c for b, c in zip(_MOCK_PRI_BIN_LOWER, _MOCK_PRI_COUNTS) if b >= thr_pri)
    n_lo_pri = total - n_hi_pri
    n_hi_rec = sum(c for b, c in zip(_MOCK_REC_BIN_LOWER, _MOCK_REC_COUNTS) if b >= thr_rec)
    n_lo_rec = total - n_hi_rec

    q1 = max(0, round(n_hi_pri * n_hi_rec / total))
    q2 = max(0, round(n_lo_pri * n_hi_rec / total))
    q3 = max(0, round(n_hi_pri * n_lo_rec / total))
    q4 = max(0, total - q1 - q2 - q3)

    # Pesos de valor por quadrante (Q1 concentra mais valor que CDAs)
    w1, w2, w3, w4 = 2.5, 1.35, 1.5, 0.25
    denom = q1 * w1 + q2 * w2 + q3 * w3 + q4 * w4 or 1
    scale = _MOCK_TOTAL_VALOR_CENTS / denom

    v1 = round(q1 * w1 * scale)
    v2 = round(q2 * w2 * scale)
    v3 = round(q3 * w3 * scale)
    v4 = max(0, _MOCK_TOTAL_VALOR_CENTS - v1 - v2 - v3)
    total_v = v1 + v2 + v3 + v4 or 1

    return pd.DataFrame({
        "quadrante":     ["Q1", "Q2", "Q3", "Q4"],
        "count_cdas":    [q1, q2, q3, q4],
        "count_contrib": [max(1, round(q1 * 0.41)), max(1, round(q2 * 0.38)),
                          max(1, round(q3 * 0.40)), max(1, round(q4 * 0.55))],
        "valor_cents":   [v1, v2, v3, v4],
        "pct_valor":     [round(v / total_v * 100, 1) for v in [v1, v2, v3, v4]],
    })


def _mock_distribuicao_prioridade() -> pd.DataFrame:
    df = pd.DataFrame({
        "bin_min":   _MOCK_PRI_BIN_LOWER,
        "count_cdas": _MOCK_PRI_COUNTS,
    })
    df["bin_label"] = df["bin_min"].apply(lambda x: f"{x}–{x + 5}")
    return df


def _mock_distribuicao_recuperabilidade() -> pd.DataFrame:
    df = pd.DataFrame({
        "bin_min":    _MOCK_REC_BIN_LOWER,
        "count_cdas": _MOCK_REC_COUNTS,
    })
    df["bin_label"] = df["bin_min"].apply(lambda x: f"{x}–{x + 5}")
    return df


# ── Carregadores para banco real ──────────────────────────────────────────────

def _real_quadrantes(carteira_id: int, sessao_id: int, thr_pri: int, thr_rec: int) -> pd.DataFrame:
    from vega.db.queries import distribuicao_quadrantes
    return distribuicao_quadrantes(carteira_id, sessao_id, thr_pri, thr_rec)


def _real_prioridade(carteira_id: int, sessao_id: int) -> pd.DataFrame:
    from vega.db.queries import distribuicao_prioridade
    return distribuicao_prioridade(carteira_id, sessao_id)


def _real_recuperabilidade(carteira_id: int, sessao_id: int) -> pd.DataFrame:
    from vega.db.queries import distribuicao_recuperabilidade
    return distribuicao_recuperabilidade(carteira_id, sessao_id)


# ── Figuras Plotly ────────────────────────────────────────────────────────────

def _fig_histograma_prioridade(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=df["bin_label"],
        y=df["count_cdas"],
        marker_color=DELFT,
        marker_cornerradius=3,
        hovertemplate="%{x}: %{y:,} CDAs<extra></extra>",
    ))
    fig.update_layout(
        height=220,
        margin={"t": 4, "b": 4, "l": 8, "r": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis={"gridcolor": _GRID_COLOR, "tickfont": _PLOT_FONT, "tickangle": -30},
        yaxis={"gridcolor": _GRID_COLOR, "tickfont": _PLOT_FONT, "ticksuffix": " CDAs"},
    )
    return fig


def _fig_histograma_recuperabilidade(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=df["bin_label"],
        y=df["count_cdas"],
        marker_color=VIOLET,
        marker_cornerradius=3,
        hovertemplate="%{x}: %{y:,} CDAs<extra></extra>",
    ))
    fig.update_layout(
        height=220,
        margin={"t": 4, "b": 4, "l": 8, "r": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis={"gridcolor": _GRID_COLOR, "tickfont": _PLOT_FONT, "tickangle": -30},
        yaxis={"gridcolor": _GRID_COLOR, "tickfont": _PLOT_FONT, "ticksuffix": " CDAs"},
    )
    return fig


# ── Componentes reativos (alimentados por callback) ───────────────────────────

def _render_q1_alert(df_q: pd.DataFrame) -> html.Div:
    """Retorna banner âmbar se Q1 estiver vazio, ou Div vazio caso contrário."""
    q1_row = df_q[df_q["quadrante"] == "Q1"]
    q1_count = int(q1_row["count_cdas"].sum()) if not q1_row.empty else 0
    if q1_count > 0:
        return html.Div()
    return html.Div([
        html.Span("⚠", style={"fontSize": 18, "flexShrink": 0}),
        html.Div([
            html.Div("Nenhuma CDA atinge os thresholds de Q1",
                     style={"fontSize": 12, "fontWeight": 600, "color": "#92400E", "marginBottom": 4}),
            html.Div(
                "Os thresholds configurados são exigentes demais para esta carteira. "
                "Considere reduzir os valores de prioridade e/ou recuperabilidade na sidebar.",
                style={"fontSize": 11, "color": "#92400E", "lineHeight": 1.6},
            ),
        ], style={"flex": 1}),
    ], style={
        "display": "flex", "alignItems": "flex-start", "gap": 12,
        "background": "#FEF3C7", "border": "1px solid #FCD34D", "borderRadius": 8,
        "padding": "12px 16px", "marginBottom": 12,
    })


def _render_matriz(df_q: pd.DataFrame, thr_pri: int, thr_rec: int) -> html.Div:
    """Renderiza matriz 2×2 com células coloridas por quadrante."""

    def _row(df_q: pd.DataFrame, q: str) -> dict[str, Any]:
        row = df_q[df_q["quadrante"] == q]
        if row.empty:
            return {"count_cdas": 0, "count_contrib": 0, "valor_cents": 0, "pct_valor": 0.0}
        r = row.iloc[0]
        return {
            "count_cdas":    int(r.get("count_cdas",    0)),
            "count_contrib": int(r.get("count_contrib", 0)),
            "valor_cents":   int(r.get("valor_cents",   0)),
            "pct_valor":     float(r.get("pct_valor",   0.0)),
        }

    def _cell(q: str) -> html.Div:
        d = _row(df_q, q)
        s = _Q_STYLE[q]
        return html.Div([
            html.Div([
                html.Span(q, style={
                    "fontSize": 10, "fontWeight": 700, "padding": "2px 8px",
                    "borderRadius": 99, "background": s["bg"], "color": s["text"],
                    "border": f"1px solid {s['border']}",
                }),
                html.Div(s["label"], style={"fontSize": 10, "color": s["text"], "marginTop": 4}),
            ], style={"marginBottom": 10}),
            html.Div(_fmt_reais(d["valor_cents"]), style={
                "fontSize": 22, "fontWeight": 700, "color": s["text"], "letterSpacing": -0.5,
            }),
            html.Div([
                html.Span(f"{d['pct_valor']:.1f}% do valor",
                          style={"fontSize": 11, "fontWeight": 500}),
            ], style={"color": s["text"], "marginTop": 4, "marginBottom": 8}),
            html.Div([
                html.Span(f"{_fmt_num(d['count_cdas'])} CDAs",
                          style={"fontSize": 11, "color": "#6B7280"}),
                html.Span(" · ", style={"color": "#D1D5DB"}),
                html.Span(f"{_fmt_num(d['count_contrib'])} contrib.",
                          style={"fontSize": 11, "color": "#6B7280"}),
            ]),
        ], style={
            "background": s["bg"],
            "border": f"1px solid {s['border']}",
            "borderRadius": 10,
            "padding": "14px 16px",
        })

    subtitle = (
        f"Prioridade ≥ {thr_pri} | Recuperabilidade ≥ {thr_rec} "
        f"— thresholds ativos da sessão"
    )

    # Legenda dos eixos
    axis_label_style = {
        "fontSize": 10, "fontWeight": 600, "color": GRAY,
        "textTransform": "uppercase", "letterSpacing": "0.5px",
    }

    return html.Div([
        html.Div([
            html.Div("Matriz de quadrantes", style={"fontSize": 13, "fontWeight": 600}),
            html.Div(subtitle, style={"fontSize": 10, "color": GRAY}),
        ], style={"marginBottom": 12}),

        # Container principal: rótulo Y + grade
        html.Div([
            # Rótulo eixo Y (recuperabilidade)
            html.Div("↑ Recuperabilidade", style={
                **axis_label_style,
                "writingMode": "vertical-rl",
                "transform": "rotate(180deg)",
                "padding": "8px 0",
                "alignSelf": "center",
            }),
            # Grade 2×2: [Q2, Q1] / [Q4, Q3]
            html.Div([
                _cell("Q2"),
                _cell("Q1"),
                _cell("Q4"),
                _cell("Q3"),
            ], style={
                "display": "grid",
                "gridTemplateColumns": "1fr 1fr",
                "gap": 10,
                "flex": 1,
            }),
        ], style={"display": "flex", "gap": 12, "alignItems": "stretch"}),

        # Rótulo eixo X (prioridade)
        html.Div("Prioridade →", style={
            **axis_label_style,
            "textAlign": "right",
            "marginTop": 6,
            "paddingRight": 4,
        }),
    ], style={**_CARD, "marginBottom": 12})


def _btn_insights_2() -> html.Div:
    return html.Div([
        html.Button(
            "✨ Gerar insights cruzados",
            id="btn-insights-2",
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
        dcc.Loading(type="dot", color="#7B2CBF", children=html.Div(id="insights-result-2")),
    ])


def _card_aviso_ordinal() -> html.Div:
    """Card fixo de rodapé — RN-05: score é índice ordinal, não probabilidade."""
    return html.Div([
        html.Span("ℹ", style={"fontSize": 16, "flexShrink": 0, "color": DELFT}),
        html.Div([
            html.Strong("Score é um índice ordinal, não uma probabilidade de pagamento. ",
                        style={"color": DELFT, "fontSize": 11}),
            html.Span(
                "O Score v1 classifica CDAs por prioridade relativa de abordagem. "
                "Scores mais altos indicam maior urgência + recuperabilidade combinadas, "
                "mas não representam chance percentual de recebimento.",
                style={"fontSize": 11, "color": "#6B7280"},
            ),
        ]),
    ], style={
        "display": "flex", "alignItems": "flex-start", "gap": 12,
        "background": "#EFF6FF", "border": "1px solid #BFDBFE", "borderRadius": 8,
        "padding": "12px 16px", "marginTop": 4,
    })


# ── Layout principal ──────────────────────────────────────────────────────────

def get_layout(carteira_id: int | None = None, sessao_id: int | None = None) -> html.Div:
    """Renderiza o conteúdo completo da Aba 3 — Scoring."""
    thr_pri, thr_rec = 40, 30  # defaults — callback sobrescreve quando store-parametros muda

    if _is_demo():
        df_q   = _mock_distribuicao_quadrantes(thr_pri, thr_rec)
        df_pri = _mock_distribuicao_prioridade()
        df_rec = _mock_distribuicao_recuperabilidade()
    else:
        if carteira_id is None or sessao_id is None:
            return html.Div(
                "Selecione uma carteira e inicie uma sessão para ver o scoring.",
                style={"color": "#9ca3af", "padding": 24},
            )
        df_q   = _real_quadrantes(carteira_id, sessao_id, thr_pri, thr_rec)
        df_pri = _real_prioridade(carteira_id, sessao_id)
        df_rec = _real_recuperabilidade(carteira_id, sessao_id)

    return html.Div([
        # 1. Alerta Q1 vazio (reativo)
        html.Div(_render_q1_alert(df_q), id="scoring-q1-alert"),

        # 2. Matriz 2×2 (reativa)
        html.Div(_render_matriz(df_q, thr_pri, thr_rec), id="scoring-matrix"),

        # 3 + 4. Histogramas estáticos
        html.Div([
            html.Div([
                html.Div([
                    html.Div("Score Prioridade", style={"fontSize": 13, "fontWeight": 600}),
                    html.Div("Distribuição 0–60 · 12 bins de 5 pts", style={"fontSize": 10, "color": GRAY}),
                ], style={"marginBottom": 12}),
                dcc.Graph(
                    figure=_fig_histograma_prioridade(df_pri),
                    config={"displayModeBar": False},
                ),
            ], style=_CARD),
            html.Div([
                html.Div([
                    html.Div("Score Recuperabilidade", style={"fontSize": 13, "fontWeight": 600}),
                    html.Div("Distribuição 0–50 · 10 bins de 5 pts", style={"fontSize": 10, "color": GRAY}),
                ], style={"marginBottom": 12}),
                dcc.Graph(
                    figure=_fig_histograma_recuperabilidade(df_rec),
                    config={"displayModeBar": False},
                ),
            ], style=_CARD),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": 12, "marginBottom": 12}),

        # 5. Botão de insights
        _btn_insights_2(),

        # 6. Card rodapé — RN-05 (sempre visível)
        _card_aviso_ordinal(),
    ])


# ── Registro de callbacks ─────────────────────────────────────────────────────

def registrar_callbacks(app: Any) -> None:
    """Registra callbacks da Aba 3: atualização de matriz por threshold + insights."""

    @app.callback(
        Output("scoring-q1-alert", "children"),
        Output("scoring-matrix",   "children"),
        Input("store-parametros",  "data"),
        State("store-carteira-id", "data"),
        State("store-sessao-id",   "data"),
    )
    def atualizar_matriz(
        parametros: dict | None,
        carteira_id: int | None,
        sessao_id:   int | None,
    ) -> tuple[html.Div, html.Div]:
        thr_pri = (parametros or {}).get("threshold_q1_prioridade", 40)
        thr_rec = (parametros or {}).get("threshold_q1_recuperab",  30)

        if _is_demo():
            df_q = _mock_distribuicao_quadrantes(thr_pri, thr_rec)
        else:
            if not carteira_id or not sessao_id:
                raise PreventUpdate
            df_q = _real_quadrantes(carteira_id, sessao_id, thr_pri, thr_rec)

        return _render_q1_alert(df_q), _render_matriz(df_q, thr_pri, thr_rec)

    @app.callback(
        Output("insights-result-2", "children"),
        Input("btn-insights-2",     "n_clicks"),
        State("store-carteira-id",  "data"),
        State("store-sessao-id",    "data"),
        State("store-parametros",   "data"),
        prevent_initial_call=True,
    )
    def gerar_insights(
        n_clicks:   int,
        carteira_id: int | None,
        sessao_id:   int | None,
        parametros:  dict | None,
    ) -> html.Div:
        if not n_clicks:
            raise PreventUpdate

        thr_pri = (parametros or {}).get("threshold_q1_prioridade", 40)
        thr_rec = (parametros or {}).get("threshold_q1_recuperab",  30)

        if _is_demo():
            df_q   = _mock_distribuicao_quadrantes(thr_pri, thr_rec)
            df_pri = _mock_distribuicao_prioridade()
            df_rec = _mock_distribuicao_recuperabilidade()
        else:
            if not carteira_id or not sessao_id:
                raise PreventUpdate
            df_q   = _real_quadrantes(carteira_id, sessao_id, thr_pri, thr_rec)
            df_pri = _real_prioridade(carteira_id, sessao_id)
            df_rec = _real_recuperabilidade(carteira_id, sessao_id)

        if not os.environ.get("OPENAI_API_KEY"):
            return html.Div(
                "OPENAI_API_KEY não configurada — insights indisponíveis.",
                style={"fontSize": 11, "color": GRAY, "padding": "8px 0"},
            )

        try:
            from vega.insights.generator import gerar_insights_scoring
            texto = gerar_insights_scoring({
                "quadrantes": df_q.to_dict("records"),
                "thr_prioridade": thr_pri,
                "thr_recuperab":  thr_rec,
                "media_prioridade": round(
                    sum(b * c for b, c in zip(_MOCK_PRI_BIN_LOWER, _MOCK_PRI_COUNTS))
                    / sum(_MOCK_PRI_COUNTS), 1
                ) if _is_demo() else round(float((df_pri["bin_min"] * df_pri["count_cdas"]).sum()
                                                 / df_pri["count_cdas"].sum()), 1),
                "media_recuperabilidade": round(
                    sum(b * c for b, c in zip(_MOCK_REC_BIN_LOWER, _MOCK_REC_COUNTS))
                    / sum(_MOCK_REC_COUNTS), 1
                ) if _is_demo() else round(float((df_rec["bin_min"] * df_rec["count_cdas"]).sum()
                                                 / df_rec["count_cdas"].sum()), 1),
            })
        except Exception as exc:
            return html.Div(f"Erro ao gerar insights: {exc}", style={"color": RED, "fontSize": 11})

        return html.Div([
            html.Div([
                html.Span("✨ Insights de scoring", style={"fontWeight": 600, "fontSize": 12, "color": DELFT}),
                html.Span("IA", style={
                    "fontSize": 10, "padding": "3px 8px", "borderRadius": 99,
                    "background": "#F0E6FA", "color": VIOLET, "fontWeight": 600, "marginLeft": "auto",
                }),
            ], style={
                "display": "flex", "alignItems": "center", "gap": 8, "padding": "14px 18px",
                "background": "linear-gradient(135deg,rgba(10,42,95,.04),rgba(123,44,191,.06))",
                "borderBottom": "1px solid #E5E7EB",
            }),
            html.Div(texto, style={"padding": "12px 18px", "fontSize": 12, "lineHeight": 1.7, "color": DELFT}),
        ], style={
            "background": "#fff", "border": "1px solid #E5E7EB", "borderRadius": 10,
            "overflow": "hidden", "marginTop": 12,
        })
