"""Componentes de alerta reutilizáveis do Katalyzer Vega."""
from __future__ import annotations

from dash import dcc, html

from vega.app.components.tooltip import tooltip


def alerta_cenario_anomalo(anomalias: list[dict]) -> html.Div:
    """Banner vermelho de projeção anômala com textarea de override obrigatório."""
    linhas = [
        html.Li(
            f"Cenário {a['cenario']}: projeta {a['pct_valor_ativo']}% de recuperação "
            "do valor ativo em 12 meses (benchmark típico: 15–35%).",
            style={"fontSize": 12, "color": "#991B1B", "marginBottom": 4},
        )
        for a in anomalias
    ]
    return html.Div([
        html.Div([
            html.Span("🚫", style={"fontSize": "24px", "flexShrink": "0"}),
            html.Div([
                html.Div([
                    html.Div("Projeção anômala detectada", style={
                        "fontSize": "14px", "fontWeight": "600",
                        "color": "#991B1B", "marginBottom": "4px",
                    }),
                    tooltip("T-07-03"),
                ], style={"display": "flex", "alignItems": "center", "gap": "6px"}),
                html.Ul(linhas, style={"margin": "0 0 8px 16px", "padding": 0}),
                html.Div(
                    "Parâmetros editados manualmente superam benchmarks de DA municipal "
                    "(15–35% de recuperação em 12m com plataforma ativa). "
                    "Verifique se as curvas de decay foram calibradas com dados reais.",
                    style={"fontSize": 12, "color": "#991B1B", "marginBottom": 10},
                ),
                dcc.Textarea(
                    id="textarea-justificativa-override",
                    placeholder="Justifique o override (mínimo 20 caracteres para confirmar)",
                    style={
                        "width": "100%", "minHeight": "60px", "marginTop": "8px",
                        "padding": "8px", "fontSize": "12px",
                        "border": "1px solid #FCA5A5", "borderRadius": "6px",
                        "boxSizing": "border-box",
                    },
                ),
                html.Button(
                    "Confirmar override e visualizar",
                    id="btn-override-cenario",
                    n_clicks=0,
                    disabled=True,
                    style={
                        "marginTop": "8px", "padding": "8px 16px",
                        "background": "#991B1B", "color": "#fff",
                        "border": "none", "borderRadius": "6px",
                        "fontSize": "12px", "cursor": "pointer",
                    },
                ),
            ]),
        ], style={
            "background": "#FEE2E2", "border": "2px solid #FCA5A5",
            "borderRadius": "8px", "padding": "16px 20px",
            "display": "flex", "gap": "12px", "alignItems": "flex-start",
        }),
    ])


def alerta_q1_excessivo(contrib_q1: int, pct_carteira: float) -> html.Div:
    """Banner âmbar — Q1 excede capacidade operacional típica (>18% dos contribuintes)."""
    return html.Div([
        html.Div([
            html.Span("⚠", style={"fontSize": "20px"}),
            html.Div([
                html.Div([
                    html.Div("Q1 excessivamente grande", style={
                        "fontSize": "13px", "fontWeight": "600", "color": "#92400E",
                    }),
                    tooltip("T-03-03"),
                ], style={"display": "flex", "alignItems": "center", "gap": "6px"}),
                html.Div(
                    f"Q1 contém {round(pct_carteira * 100, 1)}% dos contribuintes ativos "
                    f"({contrib_q1} contribuintes). Capacidade operacional típica de equipe "
                    "de cobrança é de 8–15% da carteira. Considere elevar os thresholds na "
                    "sidebar ou segmentar Q1 em ondas de priorização.",
                    style={
                        "fontSize": "12px", "color": "#92400E",
                        "lineHeight": "1.6", "marginTop": "4px",
                    },
                ),
            ]),
        ], style={
            "background": "#FEF3C7", "border": "1px solid #FCD34D",
            "borderRadius": "8px", "padding": "12px 16px",
            "display": "flex", "gap": "10px", "alignItems": "flex-start",
        }),
    ])
