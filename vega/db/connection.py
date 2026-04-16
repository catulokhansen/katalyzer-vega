"""Conexão PostgreSQL via psycopg2 — sem ORM."""
from __future__ import annotations

import os

import psycopg2
from psycopg2.extensions import connection as PGConnection


def get_conn() -> PGConnection:
    """Abre uma conexão psycopg2 usando DATABASE_URL do ambiente.

    O caller é responsável por fechar — uso recomendado:

        with get_conn() as conn:
            df = pd.read_sql(sql, conn, params={...})
    """
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL não definida no ambiente.")
    return psycopg2.connect(dsn)
