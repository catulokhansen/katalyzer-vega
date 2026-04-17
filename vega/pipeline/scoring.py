"""Etapa 3 — Scoring v1 (determinístico, 4 dimensões).

Referência: Pipeline_KatalyzerVega_v1.docx, seção 5.

ATENÇÃO — regras de negócio obrigatórias:
  RN-01  dim_urgencia é MONOTÔNICA CRESCENTE.
         Fórmula: min(dias_decorridos / dias_totais, 1.0) * peso.
         NUNCA função triangular com pico intermediário.
  RN-02  Thresholds de Q1 são ABSOLUTOS (configuráveis por sessão).
         Nunca usar mediana.
  RN-05  Score é índice ORDINAL — não é probabilidade de pagamento.

O ScorerV1 deve reproduzir exatamente a engine Score do Katalyzer Órion.
Qualquer divergência: parar e reportar ao tech lead.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from vega.pipeline.segmentacao import classificar_contactabilidade


# --- Parâmetros da sessão ------------------------------------------------


@dataclass(frozen=True)
class ParametrosScoring:
    """Parâmetros do scoring carregados de vega.sessoes_analise.

    Defaults iguais aos da migração 002_create_sessoes_analise.
    """
    peso_dim_valor: int = 30
    peso_dim_urgencia: int = 30
    peso_dim_contato: int = 25
    peso_dim_comportamento: int = 25
    threshold_q1_prioridade: int = 40
    threshold_q1_recuperab: int = 30


# --- Resultado -----------------------------------------------------------


@dataclass
class ScoreResult:
    """Resultado do cálculo de score para uma CDA."""
    dim_valor: int
    dim_urgencia: int
    dim_contato: int
    dim_comportamento: int
    eixo_prioridade: int
    eixo_recuperabilidade: int
    quadrante: str
    acao_sugerida: str
    versao_score: str = "v1"
    pesos_usados: dict[str, int] = field(default_factory=dict)


# --- Scorer --------------------------------------------------------------


def _as_dict(row: Any) -> dict[str, Any]:
    """Normaliza row (dict, Series ou objeto) para dict[str, Any]."""
    if isinstance(row, dict):
        return row
    if hasattr(row, "to_dict"):
        return row.to_dict()
    return {k: getattr(row, k) for k in dir(row) if not k.startswith("_")}


def _get(row: Any, chave: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(chave, default)
    if hasattr(row, "get"):
        return row.get(chave, default)
    return getattr(row, chave, default)


class ScorerV1:
    """Score v1 — 4 dimensões, 2 eixos, 4 quadrantes, 1 NBA por CDA."""

    # ---- Dimensões ----

    def calcular_dim_valor(self, valor_cents: int, peso: int = 30) -> int:
        """dim_valor: 0 a peso. Escala progressiva por faixa de valor.

        Referência interna (para peso=30):
          ≤ R$ 500        → 5   pts
          ≤ R$ 2.000      → 12  pts
          ≤ R$ 10.000     → 20  pts
          ≤ R$ 50.000     → 26  pts
          > R$ 50.000     → 30  pts
        """
        if valor_cents <= 50_000:
            return round(peso * 5 / 30)
        if valor_cents <= 200_000:
            return round(peso * 12 / 30)
        if valor_cents <= 1_000_000:
            return round(peso * 20 / 30)
        if valor_cents <= 5_000_000:
            return round(peso * 26 / 30)
        return peso

    def calcular_dim_urgencia(
        self, dias_decorridos: int, dias_totais: int, peso: int = 30
    ) -> int:
        """dim_urgencia: MONOTÔNICA CRESCENTE. RN-01.

        Fórmula: min(dias_decorridos / dias_totais, 1.0) * peso.
        Qualquer alteração para função com pico intermediário é BUG.
        """
        if dias_totais <= 0:
            # CDA já prescreveu antes do cálculo — urgência máxima.
            return peso
        ratio = min(dias_decorridos / dias_totais, 1.0)
        if ratio < 0:
            ratio = 0
        return round(ratio * peso)

    def calcular_dim_contato(self, nivel_contato: str, peso: int = 25) -> int:
        """dim_contato: baseado no nível de contactabilidade.

        Escala base (peso=25):
          incontactavel=0 | so_endereco=8 | telefone_apenas=14
          email_apenas=14 | digital_parcial=20 | digital_completo=25
        """
        PONTOS = {
            "digital_completo": 25,
            "digital_parcial":  20,
            "email_apenas":     14,
            "telefone_apenas":  14,
            "so_endereco":       8,
            "incontactavel":     0,
        }
        base = PONTOS.get(nivel_contato, 0)
        return round(base * peso / 25)

    def calcular_dim_comportamento(
        self,
        status_da: Optional[str],
        data_parcelamento: Optional[date],
        peso: int = 25,
    ) -> int:
        """dim_comportamento: histórico de relacionamento.

        Heurística (peso=25):
          tem data_parcelamento e não está parcelado/protestado
             → 18  (reincidente que quitou parcialmente)
          status parcelado → 14 (só parcelou)
          status protestado → 10 (protestado / primeiro débito)
          caso geral → 10 (sem histórico / primeiro débito)
        """
        status = (status_da or "ativo").lower()
        if data_parcelamento and status not in ("parcelado", "protestado"):
            return round(18 * peso / 25)
        if status == "parcelado":
            return round(14 * peso / 25)
        if status == "protestado":
            return round(10 * peso / 25)
        return round(10 * peso / 25)

    # ---- Score completo ----

    def calcular_score(self, row: Any, params: ParametrosScoring) -> ScoreResult:
        """Calcula score completo: 4 dim → 2 eixos → quadrante → NBA.

        ``row`` deve expor (dict/Series/objeto):
          - valor_corrigido_cents: int
          - dias_decorridos: int
          - dias_totais: int
          - status_da: str | None
          - data_parcelamento: date | None
          - whatsapp, celular, email, telefone, logradouro, bairro
          - padrao_densidade: str | None  (p/ NBA Q1 pulverizado)
        """
        contact = classificar_contactabilidade(row)

        valor_cents = int(_get(row, "valor_corrigido_cents", 0) or 0)
        dias_decorridos = int(_get(row, "dias_decorridos", 0) or 0)
        dias_totais = int(_get(row, "dias_totais", 0) or 0)

        dim_valor = self.calcular_dim_valor(valor_cents, params.peso_dim_valor)
        dim_urg = self.calcular_dim_urgencia(
            dias_decorridos, dias_totais, params.peso_dim_urgencia
        )
        dim_con = self.calcular_dim_contato(
            contact["nivel_contato"], params.peso_dim_contato
        )
        dim_comp = self.calcular_dim_comportamento(
            _get(row, "status_da"),
            _get(row, "data_parcelamento"),
            params.peso_dim_comportamento,
        )

        prioridade = dim_valor + dim_urg               # 0..(peso_valor + peso_urgencia)
        recuperab  = dim_con + dim_comp                # 0..(peso_contato + peso_comportamento)

        quadrante = self._classificar_quadrante(prioridade, recuperab, params)
        acao = self._derivar_acao_sugerida(quadrante, contact, row)

        return ScoreResult(
            dim_valor=dim_valor,
            dim_urgencia=dim_urg,
            dim_contato=dim_con,
            dim_comportamento=dim_comp,
            eixo_prioridade=prioridade,
            eixo_recuperabilidade=recuperab,
            quadrante=quadrante,
            acao_sugerida=acao,
            versao_score="v1",
            pesos_usados={
                "peso_dim_valor": params.peso_dim_valor,
                "peso_dim_urgencia": params.peso_dim_urgencia,
                "peso_dim_contato": params.peso_dim_contato,
                "peso_dim_comportamento": params.peso_dim_comportamento,
                "thr_pri": params.threshold_q1_prioridade,
                "thr_rec": params.threshold_q1_recuperab,
            },
        )

    # ---- Quadrante ----

    def _classificar_quadrante(
        self, pri: int, rec: int, params: ParametrosScoring
    ) -> str:
        """Classifica em Q1..Q4 usando thresholds absolutos (RN-02)."""
        thr_pri = params.threshold_q1_prioridade
        thr_rec = params.threshold_q1_recuperab
        if pri >= thr_pri and rec >= thr_rec:
            return "Q1"
        if pri < thr_pri and rec >= thr_rec:
            return "Q2"
        if pri >= thr_pri and rec < thr_rec:
            return "Q3"
        return "Q4"

    # ---- NBA (Next-Best-Action) ----

    def _derivar_acao_sugerida(
        self, quadrante: str, contact: dict[str, Any], row: Any
    ) -> str:
        """NBA — sugestão determinística, NÃO prescrição (RN-08)."""
        tem_wpp = contact["tem_whatsapp"]
        tem_cel = contact["tem_celular"]
        valor_cents = int(_get(row, "valor_corrigido_cents", 0) or 0)
        valor_alto = valor_cents > 1_000_000
        pulverizado = _get(row, "padrao_densidade") == "pulverizado"

        if quadrante == "Q1":
            if pulverizado:
                return "Negociação direta + acordo global"
            if valor_alto and not tem_wpp:
                return "Ligação comercial + parcelamento 6x"
            if tem_wpp:
                return "WhatsApp + parcelamento 6x"
            return "Campanha de massa + parcelamento 6x"

        if quadrante == "Q2":
            if tem_wpp:
                return "Campanha WhatsApp"
            if tem_cel:
                return "Campanha SMS"
            return "Correspondência + Regulariza"

        if quadrante == "Q3":
            if valor_alto:
                return "Protesto em cartório"
            return "Execução fiscal em lote"

        # Q4
        return "Monitorar — sem ação ativa"
