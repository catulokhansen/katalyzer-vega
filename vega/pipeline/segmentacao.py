"""Etapa 2b — Segmentação.

Referência: Pipeline_KatalyzerVega_v1.docx, seção 4.

Calcula os campos derivados classificatórios que alimentam as visões das
Abas 1, 2, 4 e 5. Funções puras — sem acesso ao banco.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional, Sequence

import pandas as pd


# Faixas de valor — limites em centavos. Doc: seção 4.1.1.
FAIXAS_VALOR: Sequence[tuple[int, Optional[int], str]] = (
    (0,       50_000,   "ate_500"),    # R$ 0       — R$ 500
    (50_001,  200_000,  "500_2k"),     # R$ 500,01  — R$ 2.000
    (200_001, 1_000_000, "2k_10k"),    # R$ 2.000,01 — R$ 10.000
    (1_000_001, 5_000_000, "10k_50k"), # R$ 10.000,01 — R$ 50.000
    (5_000_001, None,    "acima_50k"), # acima de R$ 50.000
)


def classificar_faixa_valor(
    valor_cents: int,
    faixas: Sequence[tuple[int, Optional[int], str]] = FAIXAS_VALOR,
) -> str:
    """Classifica o valor (em centavos) em uma das 5 faixas de valor."""
    for min_cents, max_cents, label in faixas:
        if valor_cents < min_cents:
            continue
        if max_cents is None or valor_cents <= max_cents:
            return label
    return "acima_50k"


def classificar_faixa_idade(dias_para_prescricao: int) -> str:
    """Classifica CDAs pelo tempo RESTANTE até prescrever.

    ATENÇÃO: os labels referem-se ao tempo RESTANTE, não decorrido.
    Uma CDA com < 6 meses restantes tem label "4a_5a" (urgência máxima).
    Convenção alinhada com o gráfico de aging da Aba 4 — ver seção 4.1.2.
    """
    dias = dias_para_prescricao
    if dias > 365 * 4:
        return "lt_6m"
    if dias > 365 * 3:
        return "6m_1a"
    if dias > 365 * 2:
        return "1a_2a"
    if dias > 365:
        return "2a_3a"
    if dias > 365 // 2:
        return "3a_4a"
    return "4a_5a"


def classificar_safra(data_inscricao: date) -> int:
    """Safra = ano de inscrição da CDA (análise vintage e calibração de decay)."""
    return data_inscricao.year


def calcular_padrao_densidade(df_ativas: pd.DataFrame) -> pd.Series:
    """Calcula padrão de densidade por contribuinte.

    Padrão:
      concentrado:  1-3 CDAs por contribuinte
      medio:        4-9 CDAs por contribuinte
      pulverizado: 10+ CDAs por contribuinte

    Recebe DataFrame com coluna ``contribuinte_id``. Retorna Series com
    o mesmo index, contendo o rótulo do padrão para cada CDA.

    Um contribuinte Pulverizado com 47 CDAs deve ser abordado via acordo
    global — negociação CDA a CDA é operacionalmente inviável.
    """
    if "contribuinte_id" not in df_ativas.columns:
        raise KeyError("df_ativas deve ter coluna 'contribuinte_id'")

    if df_ativas.empty:
        return pd.Series([], dtype=object, index=df_ativas.index)

    contagem = df_ativas.groupby("contribuinte_id")["contribuinte_id"].transform("count")

    return contagem.map(
        lambda n: "concentrado" if n <= 3 else ("medio" if n <= 9 else "pulverizado")
    )


# Pontuação base por nível — usada por dim_contato no scoring.
PONTOS_CONTATO: dict[str, int] = {
    "digital_completo": 25,
    "digital_parcial":  20,
    "email_apenas":     14,
    "telefone_apenas":  14,
    "so_endereco":       8,
    "incontactavel":     0,
}


def _truthy(valor: Any) -> bool:
    """True se o valor representa um dado preenchido (não None/NaN/vazio)."""
    if valor is None:
        return False
    try:
        if valor != valor:  # NaN check
            return False
    except Exception:
        pass
    if isinstance(valor, str):
        return bool(valor.strip())
    return bool(valor)


def classificar_contactabilidade(row: Any) -> dict[str, Any]:
    """Calcula flags e nível de contactabilidade para uma CDA.

    Aceita dict, pandas Series ou objeto com atributos nomeados.
    Retorna dict com flags por canal + ``nivel_contato`` (usado em dim_contato).
    """
    def _get(chave: str) -> Any:
        if isinstance(row, dict):
            return row.get(chave)
        if hasattr(row, "get"):
            return row.get(chave)
        return getattr(row, chave, None)

    tem_whatsapp = _truthy(_get("whatsapp"))
    tem_celular  = _truthy(_get("celular"))
    tem_email    = _truthy(_get("email"))
    tem_telefone = _truthy(_get("telefone"))
    tem_endereco = _truthy(_get("logradouro")) and _truthy(_get("bairro"))

    if tem_whatsapp and tem_celular and tem_email:
        nivel = "digital_completo"
    elif tem_whatsapp or tem_celular:
        nivel = "digital_parcial"
    elif tem_email:
        nivel = "email_apenas"
    elif tem_telefone:
        nivel = "telefone_apenas"
    elif tem_endereco:
        nivel = "so_endereco"
    else:
        nivel = "incontactavel"

    return {
        "tem_whatsapp": tem_whatsapp,
        "tem_celular":  tem_celular,
        "tem_email":    tem_email,
        "tem_telefone": tem_telefone,
        "tem_endereco": tem_endereco,
        "nivel_contato": nivel,
    }
