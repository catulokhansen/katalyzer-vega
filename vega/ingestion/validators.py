"""Validação de schema por linha do CSV bruto.

Referência: Pipeline_KatalyzerVega_v1.docx, seção 2.4.

Linhas inválidas são rejeitadas com causa registrada — não interrompem
o carregamento das demais. O loader agrega os erros por tipo.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional


# Erros que impedem a persistência da linha.
ERROS_CRITICOS: tuple[str, ...] = (
    "numero_cda_ausente",
    "cpf_cnpj_ausente",
    "valor_principal_ausente",
    "data_inscricao_ausente",
    "data_inscricao_invalida",
)

# Todos os códigos de erro possíveis retornados por CDAValidator.validar.
CODIGOS_ERRO: tuple[str, ...] = (
    "numero_cda_ausente",
    "cpf_cnpj_ausente",
    "valor_principal_ausente",
    "data_inscricao_ausente",
    "data_inscricao_invalida",
    "data_inscricao_futura",
    "valor_principal_negativo",
    "valor_principal_nao_numerico",
    "cpf_cnpj_formato_invalido",
)


def parse_date(valor) -> Optional[date]:
    """Tenta converter um valor para date. Aceita: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY.

    Retorna None se a conversão falhar.
    """
    if valor is None:
        return None
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    if isinstance(valor, datetime):
        return valor.date()
    texto = str(valor).strip()
    if not texto:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def _vazio(valor) -> bool:
    """True se o valor for None, NaN ou string vazia."""
    if valor is None:
        return True
    # pandas NaN tem o comportamento de valor != valor
    try:
        if valor != valor:  # noqa: PLR0124
            return True
    except Exception:
        pass
    if isinstance(valor, str) and not valor.strip():
        return True
    return False


class CDAValidator:
    """Valida cada linha do CSV bruto.

    Linhas inválidas: rejeitadas com causa registrada.
    Linhas válidas: passam para a normalização no loader.
    """

    ERROS_CRITICOS = ERROS_CRITICOS

    def validar(self, row: dict) -> tuple[bool, Optional[str]]:
        """Retorna (True, None) se válido, (False, "codigo_erro") se inválido.

        A ordem de verificação segue a Tabela 7 do Pipeline doc — qualquer
        alteração quebra a compatibilidade com os testes de H-01..H-08.
        """
        if _vazio(row.get("numero_cda")):
            return False, "numero_cda_ausente"

        if _vazio(row.get("contribuinte_cpf_cnpj")):
            return False, "cpf_cnpj_ausente"

        cpf_cnpj = re.sub(r"\D", "", str(row["contribuinte_cpf_cnpj"]))
        if len(cpf_cnpj) not in (11, 14):
            return False, "cpf_cnpj_formato_invalido"

        if _vazio(row.get("valor_principal")):
            return False, "valor_principal_ausente"

        try:
            valor = float(str(row["valor_principal"]).replace(",", "."))
        except (ValueError, TypeError):
            return False, "valor_principal_nao_numerico"
        if valor < 0:
            return False, "valor_principal_negativo"

        if _vazio(row.get("data_inscricao")):
            return False, "data_inscricao_ausente"

        data = parse_date(row["data_inscricao"])
        if data is None:
            return False, "data_inscricao_invalida"

        if data > date.today():
            return False, "data_inscricao_futura"

        return True, None
