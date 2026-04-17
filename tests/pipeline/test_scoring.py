"""Casos de teste obrigatórios — Scoring v1.

Referência: Pipeline_KatalyzerVega_v1.docx, seção 6.2.
"""
from __future__ import annotations

from datetime import date

import pytest

from vega.pipeline.scoring import ParametrosScoring, ScorerV1


PARAMS_DEFAULT = ParametrosScoring()  # thresholds 40/30, pesos 30/30/25/25


def _base_row(**overrides) -> dict:
    """Row com campos default plausíveis para uma CDA de teste."""
    base = {
        "valor_corrigido_cents": 500_000,     # R$ 5.000
        "dias_decorridos": 365,
        "dias_totais": 365 * 5,
        "status_da": "ativo",
        "data_parcelamento": None,
        "whatsapp": "11999990000",
        "celular": "11999990000",
        "email": "teste@example.com",
        "telefone": "1122220000",
        "logradouro": "Rua X",
        "bairro": "Centro",
        "padrao_densidade": "concentrado",
    }
    base.update(overrides)
    return base


# --- S-01 ----------------------------------------------------------------
def test_S01_urgencia_monotonica_proxima_da_prescricao_eh_maxima():
    """CDA com 1 dia para prescrever → dim_urgencia ≈ peso (30)."""
    scorer = ScorerV1()
    dias_totais = 365 * 5
    dim = scorer.calcular_dim_urgencia(
        dias_decorridos=dias_totais - 1,
        dias_totais=dias_totais,
        peso=30,
    )
    assert dim == 30, f"esperado ~30, obtido {dim}"


# --- S-02 ----------------------------------------------------------------
def test_S02_urgencia_monotonica_recente_eh_minima():
    """CDA com 1 dia desde a inscrição → dim_urgencia ≈ 0."""
    scorer = ScorerV1()
    dim = scorer.calcular_dim_urgencia(
        dias_decorridos=1,
        dias_totais=365 * 5,
        peso=30,
    )
    assert dim == 0


# --- S-03 ----------------------------------------------------------------
def test_S03_Q1_com_thresholds_default():
    """prioridade=42, recuperabilidade=32 → quadrante Q1."""
    scorer = ScorerV1()
    q = scorer._classificar_quadrante(pri=42, rec=32, params=PARAMS_DEFAULT)
    assert q == "Q1"


# --- S-04 ----------------------------------------------------------------
def test_S04_Q3_com_threshold_default():
    """prioridade=45, recuperabilidade=28 → quadrante Q3."""
    scorer = ScorerV1()
    q = scorer._classificar_quadrante(pri=45, rec=28, params=PARAMS_DEFAULT)
    assert q == "Q3"


# --- S-05 ----------------------------------------------------------------
def test_S05_threshold_customizado_pode_resultar_em_Q1_vazio():
    """Com thr_pri=55, thr_rec=45, e uma carteira modesta, nenhuma CDA atinge Q1."""
    scorer = ScorerV1()
    params = ParametrosScoring(
        threshold_q1_prioridade=55,
        threshold_q1_recuperab=45,
    )
    # Carteira sintética — valores baixos a médios, contactabilidade variada.
    rows = [
        _base_row(valor_corrigido_cents=50_000, dias_decorridos=100, dias_totais=365 * 5),
        _base_row(valor_corrigido_cents=300_000, dias_decorridos=500, dias_totais=365 * 5,
                  email=None, telefone=None, whatsapp=None, celular=None),
        _base_row(valor_corrigido_cents=700_000, dias_decorridos=700, dias_totais=365 * 5,
                  email=None, whatsapp=None, celular=None, telefone="1122223333"),
    ]
    quadrantes = [scorer.calcular_score(r, params).quadrante for r in rows]
    assert "Q1" not in quadrantes


# --- S-06 ----------------------------------------------------------------
def test_S06_idempotencia_duas_execucoes_com_mesma_entrada():
    """Mesmos parâmetros, duas execuções → scores idênticos."""
    scorer = ScorerV1()
    row = _base_row(
        valor_corrigido_cents=2_500_000,
        dias_decorridos=1200,
        dias_totais=365 * 5,
        status_da="ativo",
        padrao_densidade="medio",
    )
    s1 = scorer.calcular_score(row, PARAMS_DEFAULT)
    s2 = scorer.calcular_score(row, PARAMS_DEFAULT)
    assert s1 == s2


# --- S-07 ----------------------------------------------------------------
def test_S07_NBA_Q1_pulverizado_sugere_acordo_global():
    """Contribuinte pulverizado no Q1 → sugestão contém 'acordo global'."""
    scorer = ScorerV1()
    # Configuração forte de Q1: valor alto + urgência alta + contato digital completo.
    row = _base_row(
        valor_corrigido_cents=2_500_000,   # dim_valor = 26
        dias_decorridos=int(365 * 5 * 0.9),  # dim_urgencia ≈ 27
        dias_totais=365 * 5,
        padrao_densidade="pulverizado",
    )
    score = scorer.calcular_score(row, PARAMS_DEFAULT)
    assert score.quadrante == "Q1"
    assert "acordo global" in score.acao_sugerida.lower()


# --- S-08 ----------------------------------------------------------------
def test_S08_NBA_Q3_padrao_eh_protesto_em_cartorio():
    """Q3 viável (status ativo, prescrição não iminente) → NBA = 'Protesto em cartório'.

    Novo comportamento (C1.3): protesto é o default para Q3 viável —
    não depende mais de valor_alto. Município opera via convênio IEPTB,
    custo marginal zero para o ente.
    dias_decorridos=1000 → dias_para_prescricao=825 >= 365 (não iminente).
    """
    scorer = ScorerV1()
    row = _base_row(
        valor_corrigido_cents=3_000_000,
        dias_decorridos=1000,              # dias_para_prescricao=825 >= 365
        dias_totais=365 * 5,
        status_da="ativo",
        data_parcelamento=None,
        whatsapp=None,
        celular=None,
        email=None,
        telefone=None,
        logradouro=None,
        bairro=None,
    )
    score = scorer.calcular_score(row, PARAMS_DEFAULT)
    assert score.quadrante == "Q3"
    assert score.acao_sugerida == "Protesto em cartório"


# --- Extras de sanidade --------------------------------------------------

def test_dim_valor_faixas():
    """Confere as 5 faixas de dim_valor com peso default 30."""
    scorer = ScorerV1()
    assert scorer.calcular_dim_valor(50_000) == 5       # até R$ 500
    assert scorer.calcular_dim_valor(200_000) == 12     # até R$ 2k
    assert scorer.calcular_dim_valor(1_000_000) == 20   # até R$ 10k
    assert scorer.calcular_dim_valor(5_000_000) == 26   # até R$ 50k
    assert scorer.calcular_dim_valor(5_000_001) == 30   # acima de R$ 50k


def test_dim_urgencia_nunca_negativa():
    """Ratio negativo (inscrição futura) → clamp em 0, não negativo."""
    scorer = ScorerV1()
    assert scorer.calcular_dim_urgencia(-10, 365 * 5, peso=30) == 0


def test_dim_urgencia_fica_saturada_em_peso_quando_ratio_supera_1():
    """Ratio >1 → clamp em 1.0 → retorno = peso."""
    scorer = ScorerV1()
    # dias_decorridos > dias_totais não deveria ocorrer na prática,
    # mas o clamp precisa estar firme.
    assert scorer.calcular_dim_urgencia(365 * 10, 365 * 5, peso=30) == 30


def test_dim_contato_niveis():
    """Dim_contato respeita a escala base com peso 25."""
    scorer = ScorerV1()
    assert scorer.calcular_dim_contato("digital_completo") == 25
    assert scorer.calcular_dim_contato("digital_parcial") == 20
    assert scorer.calcular_dim_contato("email_apenas") == 14
    assert scorer.calcular_dim_contato("telefone_apenas") == 14
    assert scorer.calcular_dim_contato("so_endereco") == 8
    assert scorer.calcular_dim_contato("incontactavel") == 0


# --- C1.3 — NBA Q3 sub-categorias ----------------------------------------

def _q3_row(**overrides) -> dict:
    """Row forçado para Q3: prioridade alta (dim_valor+dim_urgencia≥40), rec baixa."""
    base = _base_row(
        valor_corrigido_cents=3_000_000,   # dim_valor=30
        dias_decorridos=1000,              # dim_urgencia=16 → prioridade=46>=40
        dias_totais=365 * 5,
        # sem contato → dim_contato=0, dim_comportamento=10 → rec=10<30 → Q3
        whatsapp=None, celular=None, email=None,
        telefone=None, logradouro=None, bairro=None,
        status_da="ativo",
        data_parcelamento=None,
        prescricao_interrompida=False,
    )
    base.update(overrides)
    return base


def test_nba_q3_baixa_tecnica():
    """status_da='baixado' em Q3 → 'Baixa técnica — irrecuperável'."""
    scorer = ScorerV1()
    row    = _q3_row(status_da="baixado")
    score  = scorer.calcular_score(row, PARAMS_DEFAULT)
    assert score.quadrante    == "Q3"
    assert score.acao_sugerida == "Baixa técnica — irrecuperável"


def test_nba_q3_prescricao_interrompida():
    """Q3 com prescricao_interrompida=True → 'Monitorar — prescrição já interrompida'."""
    scorer = ScorerV1()
    row    = _q3_row(prescricao_interrompida=True)
    score  = scorer.calcular_score(row, PARAMS_DEFAULT)
    assert score.quadrante    == "Q3"
    assert score.acao_sugerida == "Monitorar — prescrição já interrompida"


def test_nba_q3_prescricao_iminente():
    """Q3 com 180 dias para prescrição → 'Protesto urgente — prescrição em 12 meses'."""
    scorer = ScorerV1()
    # dias_totais=1825, dias_decorridos=1645 → dias_para_prescricao=180 < 365
    row = _q3_row(
        dias_decorridos=1645,
        dias_totais=365 * 5,
    )
    score = scorer.calcular_score(row, PARAMS_DEFAULT)
    assert score.quadrante    == "Q3"
    assert score.acao_sugerida == "Protesto urgente — prescrição em 12 meses"


def test_nba_q3_padrao_nao_depende_de_valor_alto():
    """Q3 com R$10k (não era 'valor_alto' na lógica antiga) → 'Protesto em cartório'.

    Antes da C1.3, valor_cents == 1_000_000 (== R$10k) resultava em
    'Execução fiscal em lote' (valor_alto = 1_000_000 > 1_000_000 = False).
    Novo comportamento: protesto é o default para Q3 viável, sem dependência de valor.

    dim_valor(1_000_000)=20, dim_urgencia(1460,1825,30)=24 → prioridade=44>=40.
    dias_para_prescricao=365 → não iminente (365 < 365 é False).
    """
    scorer = ScorerV1()
    row = _base_row(
        valor_corrigido_cents=1_000_000,   # R$ 10.000 — não era valor_alto na lógica antiga
        dias_decorridos=1460,              # dias_para_prescricao=365 (não < 365)
        dias_totais=365 * 5,
        whatsapp=None, celular=None, email=None,
        telefone=None, logradouro=None, bairro=None,
        status_da="ativo",
        prescricao_interrompida=False,
    )
    score = scorer.calcular_score(row, PARAMS_DEFAULT)
    assert score.quadrante    == "Q3"
    assert score.acao_sugerida == "Protesto em cartório"
