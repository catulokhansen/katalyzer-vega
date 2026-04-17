"""Casos de teste obrigatórios — Higienização.

Referência: Pipeline_KatalyzerVega_v1.docx, seção 6.1.

Todos os testes usam uma data de referência fixa (HOJE) para garantir
determinismo — a função interna `_processar_cda` aceita o parâmetro
`hoje` justamente para isso.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from dateutil.relativedelta import relativedelta

from vega.pipeline.higienizacao import (
    CDABruta,
    ParametrosSessao,
    _processar_cda,
)


# Data de referência fixa para os testes.
HOJE = date(2026, 4, 16)

# Parâmetros default (iguais à migração 002).
PARAMS = ParametrosSessao(valor_minimo_cents=5_000, prazo_prescricao_anos=5)


def _cda(
    *,
    valor_total_cents: int = 1_000_000,
    data_inscricao: date = date(2024, 1, 1),
    status_da: str | None = "ativo",
    id: int = 1,
    contribuinte_id: str = "12345678901",
) -> CDABruta:
    """Helper para criar CDABruta com defaults razoáveis."""
    return CDABruta(
        id=id,
        contribuinte_id=contribuinte_id,
        valor_total_cents=valor_total_cents,
        data_inscricao=data_inscricao,
        status_da=status_da,
    )


# --- H-01 ----------------------------------------------------------------
def test_H01_cda_abaixo_do_valor_minimo_eh_irrisoria():
    """valor_total = R$ 49,99 com valor_minimo = R$ 50,00 → irrisorio."""
    cda = _cda(valor_total_cents=4_999, data_inscricao=date(2024, 1, 1))
    resultado = _processar_cda(cda, PARAMS, hoje=HOJE)

    assert resultado.ativa is False
    assert resultado.causa_eliminacao == "irrisorio"


# --- H-02 ----------------------------------------------------------------
def test_H02_cda_exatamente_no_valor_minimo_eh_ativa():
    """valor_total = R$ 50,00 e valor_minimo = R$ 50,00 → ativa."""
    cda = _cda(valor_total_cents=5_000, data_inscricao=date(2024, 1, 1))
    resultado = _processar_cda(cda, PARAMS, hoje=HOJE)

    assert resultado.ativa is True
    assert resultado.causa_eliminacao is None


# --- H-03 ----------------------------------------------------------------
def test_H03_cda_prescrita_sem_interrupcao_eh_eliminada_por_prescricao():
    """data_inscricao = 5 anos e 1 dia atrás, status ativo → prescricao."""
    data_inscricao = HOJE - relativedelta(years=5) - timedelta(days=1)
    cda = _cda(data_inscricao=data_inscricao, status_da="ativo")
    resultado = _processar_cda(cda, PARAMS, hoje=HOJE)

    assert resultado.ativa is False
    assert resultado.causa_eliminacao == "prescricao"
    assert resultado.prescricao_interrompida is False


# --- H-04 ----------------------------------------------------------------
def test_H04_cda_prescrita_com_protesto_ativo_permanece_ativa():
    """5 anos e 1 dia + status=protestado → ativa, prescricao_interrompida=True."""
    data_inscricao = HOJE - relativedelta(years=5) - timedelta(days=1)
    cda = _cda(data_inscricao=data_inscricao, status_da="protestado")
    resultado = _processar_cda(cda, PARAMS, hoje=HOJE)

    assert resultado.ativa is True
    assert resultado.prescricao_interrompida is True
    assert resultado.causa_eliminacao is None


# --- H-05 ----------------------------------------------------------------
def test_H05_cda_com_parcelamento_ativo_tem_flag_de_prescricao_interrompida():
    """3 anos atrás + parcelado → ativa, prescricao_interrompida=True."""
    data_inscricao = HOJE - relativedelta(years=3)
    cda = _cda(data_inscricao=data_inscricao, status_da="parcelado")
    resultado = _processar_cda(cda, PARAMS, hoje=HOJE)

    assert resultado.ativa is True
    assert resultado.prescricao_interrompida is True


# --- H-06 ----------------------------------------------------------------
def test_H06_devedor_com_status_baixado_eh_eliminado_como_inexistente():
    """status=baixado → causa=devedor_inexistente."""
    cda = _cda(status_da="baixado")
    resultado = _processar_cda(cda, PARAMS, hoje=HOJE)

    assert resultado.ativa is False
    assert resultado.causa_eliminacao == "devedor_inexistente"


# --- H-07 ----------------------------------------------------------------
def test_H07_cda_ativa_valida_sem_interrupcoes_nem_eliminacoes():
    """valor acima do mínimo, data dentro do prazo, status ativo → ativa limpa."""
    cda = _cda(
        valor_total_cents=200_000,
        data_inscricao=HOJE - relativedelta(years=2),
        status_da="ativo",
    )
    resultado = _processar_cda(cda, PARAMS, hoje=HOJE)

    assert resultado.ativa is True
    assert resultado.prescricao_interrompida is False
    assert resultado.causa_eliminacao is None


# --- H-08 ----------------------------------------------------------------
def test_H08_ordem_dos_criterios_irrisorio_vence_prescricao():
    """Mesmo com data prescrita, valor < mínimo → causa='irrisorio' (não 'prescricao')."""
    data_prescrita = HOJE - relativedelta(years=5) - timedelta(days=1)
    cda = _cda(valor_total_cents=4_999, data_inscricao=data_prescrita, status_da="ativo")
    resultado = _processar_cda(cda, PARAMS, hoje=HOJE)

    assert resultado.ativa is False
    assert resultado.causa_eliminacao == "irrisorio"


# --- Extras --------------------------------------------------------------

def test_idempotencia_processar_cda_mesma_entrada_mesma_saida():
    """Reprocessar a mesma CDA com os mesmos parâmetros → resultado idêntico."""
    cda = _cda()
    r1 = _processar_cda(cda, PARAMS, hoje=HOJE)
    r2 = _processar_cda(cda, PARAMS, hoje=HOJE)
    assert r1 == r2


def test_ajuizado_interrompe_prescricao():
    """status=ajuizado deve marcar prescricao_interrompida=True."""
    cda = _cda(
        data_inscricao=HOJE - relativedelta(years=5) - timedelta(days=1),
        status_da="ajuizado",
    )
    r = _processar_cda(cda, PARAMS, hoje=HOJE)
    assert r.ativa is True
    assert r.prescricao_interrompida is True
