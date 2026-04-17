"""Carregamento de CSV bruto para vega.cdas_brutas.

Referência: Pipeline_KatalyzerVega_v1.docx, seções 2.2, 2.3 e 2.5.

Fluxo:
  1. Lê CSV com pandas.
  2. Aplica COLUMN_MAP para renomear colunas conhecidas.
  3. Valida cada linha com CDAValidator.
  4. Normaliza (centavos, uppercase tributo, datas, contribuinte_tipo, whatsapp).
  5. Persiste linhas válidas em vega.cdas_brutas via INSERT psycopg2.
  6. Retorna dict com totais: total, validas, rejeitadas, erros por tipo.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import psycopg2.extras

from vega.db.connection import get_conn
from vega.ingestion.column_mapping import aplicar_column_map
from vega.ingestion.validators import CDAValidator, parse_date


# Tributos reconhecidos — qualquer valor fora desta lista é mapeado para OUTRO.
TRIBUTOS_VALIDOS: frozenset[str] = frozenset(
    {"IPTU", "ISS", "ITBI", "TAXAS", "MULTAS", "COSIP", "OUTRO"}
)

# Status reconhecidos pelo sistema de DA — qualquer outro vira "ativo".
STATUS_DA_VALIDOS: frozenset[str] = frozenset(
    {"ativo", "parcelado", "protestado", "ajuizado", "quitado",
     "baixado", "cancelado", "inexistente", "inativo"}
)

# Campos com datas que precisam passar por parse_date.
CAMPOS_DATA: tuple[str, ...] = (
    "data_inscricao",
    "data_vencimento",
    "data_parcelamento",
    "data_protesto",
)

INSERT_CDA_BRUTA_SQL = """
    INSERT INTO vega.cdas_brutas (
        carteira_id, tenant_id, numero_cda,
        contribuinte_id, contribuinte_nome, contribuinte_tipo,
        tributo,
        valor_principal_cents, valor_juros_cents, valor_multa_cents, valor_total_cents,
        data_inscricao, data_vencimento, exercicio,
        logradouro, bairro, municipio, uf, cep,
        telefone, celular, whatsapp, email,
        status_da, data_parcelamento, data_protesto,
        raw_jsonb
    ) VALUES (
        %(carteira_id)s, %(tenant_id)s, %(numero_cda)s,
        %(contribuinte_id)s, %(contribuinte_nome)s, %(contribuinte_tipo)s,
        %(tributo)s,
        %(valor_principal_cents)s, %(valor_juros_cents)s, %(valor_multa_cents)s, %(valor_total_cents)s,
        %(data_inscricao)s, %(data_vencimento)s, %(exercicio)s,
        %(logradouro)s, %(bairro)s, %(municipio)s, %(uf)s, %(cep)s,
        %(telefone)s, %(celular)s, %(whatsapp)s, %(email)s,
        %(status_da)s, %(data_parcelamento)s, %(data_protesto)s,
        %(raw_jsonb)s
    )
"""


def _valor_para_cents(valor: Any, default: int = 0) -> int:
    """Converte um valor monetário em reais (float ou string) para centavos.

    Aceita separador decimal vírgula ou ponto. Valores vazios retornam default.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return default
    texto = str(valor).strip()
    if not texto:
        return default
    # Se houver vírgula + ponto, assumir ponto como separador de milhar.
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", ".")
    try:
        return round(float(texto) * 100)
    except (ValueError, TypeError):
        return default


def _clean_str(valor: Any) -> Optional[str]:
    """Trata valores string: retorna None se vazio/NaN, senão strip."""
    if valor is None:
        return None
    if isinstance(valor, float) and pd.isna(valor):
        return None
    texto = str(valor).strip()
    return texto or None


def _digitos(valor: Any) -> Optional[str]:
    """Retorna somente os dígitos do valor, ou None se vazio."""
    texto = _clean_str(valor)
    if texto is None:
        return None
    digitos = re.sub(r"\D", "", texto)
    return digitos or None


def _normalizar_tributo(valor: Any) -> str:
    texto = _clean_str(valor)
    if texto is None:
        return "OUTRO"
    upper = texto.upper()
    return upper if upper in TRIBUTOS_VALIDOS else "OUTRO"


def _normalizar_status_da(valor: Any) -> str:
    texto = _clean_str(valor)
    if texto is None:
        return "ativo"
    lower = texto.lower()
    return lower if lower in STATUS_DA_VALIDOS else "ativo"


def _contribuinte_tipo(cpf_cnpj_digitos: str) -> Optional[str]:
    """11 dígitos = PF, 14 dígitos = PJ."""
    if len(cpf_cnpj_digitos) == 11:
        return "PF"
    if len(cpf_cnpj_digitos) == 14:
        return "PJ"
    return None


def _exercicio_de(exercicio_raw: Any, data_inscricao: date) -> Optional[int]:
    """Deriva exercício de data_inscricao se ausente."""
    texto = _clean_str(exercicio_raw)
    if texto:
        try:
            return int(float(texto))
        except (ValueError, TypeError):
            pass
    return data_inscricao.year


def _buscar_tenant_id(conn, carteira_id: int) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT tenant_id FROM vega.carteiras WHERE id = %s",
            (carteira_id,),
        )
        linha = cur.fetchone()
    if linha is None:
        raise ValueError(f"Carteira {carteira_id} não encontrada em vega.carteiras")
    return linha[0]


def _normalizar_linha(
    row: dict[str, Any],
    carteira_id: int,
    tenant_id: str,
) -> dict[str, Any]:
    """Aplica todas as transformações documentadas na seção 2.5 do Pipeline doc."""
    cpf_cnpj_digitos = re.sub(r"\D", "", str(row["contribuinte_cpf_cnpj"]))

    valor_principal_cents = _valor_para_cents(row.get("valor_principal"))
    valor_juros_cents = _valor_para_cents(row.get("valor_juros"))
    valor_multa_cents = _valor_para_cents(row.get("valor_multa"))
    valor_total_cents = valor_principal_cents + valor_juros_cents + valor_multa_cents

    data_inscricao = parse_date(row.get("data_inscricao"))
    # data_inscricao já foi validada como obrigatória e não-futura.
    assert data_inscricao is not None

    data_vencimento = parse_date(row.get("data_vencimento"))
    data_parcelamento = parse_date(row.get("data_parcelamento"))
    data_protesto = parse_date(row.get("data_protesto"))

    # Heurística de whatsapp: se ausente, copiar celular (se presente).
    whatsapp = _digitos(row.get("whatsapp"))
    celular = _digitos(row.get("celular"))
    if whatsapp is None and celular is not None:
        whatsapp = celular

    cep = _digitos(row.get("cep"))

    normalizada: dict[str, Any] = {
        "carteira_id": carteira_id,
        "tenant_id": tenant_id,
        "numero_cda": str(row["numero_cda"]).strip(),
        "contribuinte_id": cpf_cnpj_digitos,
        "contribuinte_nome": _clean_str(row.get("contribuinte_nome")),
        "contribuinte_tipo": _contribuinte_tipo(cpf_cnpj_digitos),
        "tributo": _normalizar_tributo(row.get("tributo")),
        "valor_principal_cents": valor_principal_cents,
        "valor_juros_cents": valor_juros_cents,
        "valor_multa_cents": valor_multa_cents,
        "valor_total_cents": valor_total_cents,
        "data_inscricao": data_inscricao,
        "data_vencimento": data_vencimento,
        "exercicio": _exercicio_de(row.get("exercicio"), data_inscricao),
        "logradouro": _clean_str(row.get("logradouro")),
        "bairro": _clean_str(row.get("bairro")),
        "municipio": _clean_str(row.get("municipio")),
        "uf": (_clean_str(row.get("uf")) or "").upper()[:2] or None,
        "cep": cep,
        "telefone": _digitos(row.get("telefone")),
        "celular": celular,
        "whatsapp": whatsapp,
        "email": _clean_str(row.get("email")),
        "status_da": _normalizar_status_da(row.get("status_da")),
        "data_parcelamento": data_parcelamento,
        "data_protesto": data_protesto,
        "raw_jsonb": psycopg2.extras.Json(_raw_payload(row)),
    }
    return normalizada


def _raw_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Payload serializável com a linha original — para auditoria."""
    payload: dict[str, Any] = {}
    for k, v in row.items():
        if v is None:
            payload[k] = None
        elif isinstance(v, float) and pd.isna(v):
            payload[k] = None
        elif isinstance(v, (str, int, float, bool)):
            payload[k] = v
        else:
            payload[k] = str(v)
    return payload


def _renomear_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica o COLUMN_MAP ao DataFrame, preservando colunas desconhecidas.

    Se o mapeamento produz colunas duplicadas (ex.: CSV tem "cpf" e também
    "contribuinte_cpf_cnpj"), a primeira ocorrência vence e as duplicatas
    são descartadas — o cliente deve manter apenas uma coluna-fonte por
    campo canônico.
    """
    mapping = aplicar_column_map(list(df.columns))
    renomeado = df.rename(columns=mapping)
    # Remove colunas duplicadas mantendo a primeira
    renomeado = renomeado.loc[:, ~renomeado.columns.duplicated()]
    return renomeado


def load_csv(
    filepath: str | Path,
    carteira_id: int,
    sessao_id: int,
) -> dict[str, Any]:
    """Carrega um CSV de CDAs brutas em vega.cdas_brutas.

    Parameters
    ----------
    filepath : caminho para o CSV.
    carteira_id : identificador da carteira em vega.carteiras.
    sessao_id : identificador da sessão de análise — registrado no resultado
        para rastreabilidade. A tabela vega.cdas_brutas é imutável e não
        guarda sessao_id; quem guarda é vega.cdas_higienizadas.

    Returns
    -------
    dict com as chaves:
      - total: total de linhas lidas do CSV
      - validas: linhas inseridas em vega.cdas_brutas
      - rejeitadas: linhas descartadas pela validação
      - erros: dict {codigo_erro: contagem}
      - carteira_id, sessao_id: ecoados para conveniência
    """
    caminho = Path(filepath)
    if not caminho.exists():
        raise FileNotFoundError(f"CSV não encontrado: {caminho}")

    # dtype=str preserva zeros à esquerda em CPF/CNPJ/CEP e evita
    # interpretação automática de datas. A normalização é feita depois.
    df = pd.read_csv(caminho, dtype=str, keep_default_na=False, na_values=[""])
    df = _renomear_colunas(df)

    validator = CDAValidator()
    erros: Counter[str] = Counter()
    linhas_validas: list[dict[str, Any]] = []

    with get_conn() as conn:
        tenant_id = _buscar_tenant_id(conn, carteira_id)

        for _, row_series in df.iterrows():
            row = {k: (None if (isinstance(v, float) and pd.isna(v)) else v)
                   for k, v in row_series.to_dict().items()}

            ok, erro = validator.validar(row)
            if not ok:
                erros[erro] += 1
                continue

            try:
                normalizada = _normalizar_linha(row, carteira_id, tenant_id)
            except Exception:
                # Falhas de normalização pós-validação são raras mas devem ser
                # contabilizadas — indicam inconsistência entre o validador
                # e as transformações. Registramos como "normalizacao_falhou".
                erros["normalizacao_falhou"] += 1
                continue

            linhas_validas.append(normalizada)

        if linhas_validas:
            with conn.cursor() as cur:
                psycopg2.extras.execute_batch(cur, INSERT_CDA_BRUTA_SQL, linhas_validas)
        conn.commit()

    total = int(len(df))
    validas = len(linhas_validas)
    rejeitadas = total - validas

    return {
        "total": total,
        "validas": validas,
        "rejeitadas": rejeitadas,
        "erros": dict(erros),
        "carteira_id": carteira_id,
        "sessao_id": sessao_id,
    }
