"""Mapeamento de nomes de coluna do CSV bruto para o schema canônico.

Referência: Pipeline_KatalyzerVega_v1.docx, seção 2.3.

O mapeamento é aplicado ANTES da validação. A chave é o nome da coluna como
aparece no CSV (normalizado para lowercase + strip) e o valor é o nome
canônico esperado pelo resto do pipeline.
"""
from __future__ import annotations


COLUMN_MAP: dict[str, str] = {
    # numero_cda
    "num_cda": "numero_cda",
    "cda": "numero_cda",
    "inscricao": "numero_cda",
    "numero_inscricao": "numero_cda",
    # contribuinte_cpf_cnpj
    "cpf": "contribuinte_cpf_cnpj",
    "cnpj": "contribuinte_cpf_cnpj",
    "cpf_cnpj": "contribuinte_cpf_cnpj",
    "documento": "contribuinte_cpf_cnpj",
    # tributo
    "tipo_tributo": "tributo",
    "tipo": "tributo",
    "natureza": "tributo",
    # valor_principal
    "valor": "valor_principal",
    "vl_principal": "valor_principal",
    "principal": "valor_principal",
    # data_inscricao
    "dt_inscricao": "data_inscricao",
    "data_inscricao_da": "data_inscricao",
    "inscrito_em": "data_inscricao",
    # status_da
    "situacao": "status_da",
    "status": "status_da",
    "situacao_cda": "status_da",
}


def normalizar_nome_coluna(nome: str) -> str:
    """Normaliza o nome da coluna do CSV: lower + strip."""
    return str(nome).strip().lower()


def aplicar_column_map(colunas: list[str]) -> dict[str, str]:
    """Retorna dicionário {coluna_original: coluna_canonica}.

    Se a coluna já tem nome canônico, é mantida. Caso contrário,
    é traduzida via COLUMN_MAP. Colunas desconhecidas são preservadas
    com o nome normalizado (lowercase) — o validador decide se elas
    são obrigatórias ou não.
    """
    resultado: dict[str, str] = {}
    for col in colunas:
        chave = normalizar_nome_coluna(col)
        resultado[col] = COLUMN_MAP.get(chave, chave)
    return resultado
