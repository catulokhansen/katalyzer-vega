#!/usr/bin/env python3
"""Autentica com ChatGPT e salva o access token no .env."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ENV_PATH = Path(__file__).parent.parent / ".env"


def _atualizar_env(token: str) -> None:
    lines = ENV_PATH.read_text().splitlines() if ENV_PATH.exists() else []
    chave = "CHATGPT_ACCESS_TOKEN"
    nova_linha = f"{chave}={token}"
    encontrou = False
    novas_linhas = []
    for linha in lines:
        if re.match(rf"^{chave}=", linha):
            novas_linhas.append(nova_linha)
            encontrou = True
        else:
            novas_linhas.append(linha)
    if not encontrou:
        novas_linhas.append(nova_linha)
    ENV_PATH.write_text("\n".join(novas_linhas) + "\n")


def main() -> None:
    print()
    print("=== Katalyzer Vega — Autenticacao ChatGPT ===")
    print()
    print("Passo 1 — Faca login no ChatGPT:")
    print()
    print("  https://chat.openai.com")
    print()
    print("Passo 2 — Apos o login, abra esta URL em nova aba e copie o JSON:")
    print()
    print("  https://chat.openai.com/api/auth/session")
    print()
    print("Passo 3 — Cole o JSON aqui e pressione Enter:")
    print()

    try:
        raw = input("> ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelado.")
        sys.exit(0)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("Erro: JSON invalido. Verifique o conteudo copiado.")
        sys.exit(1)

    token = data.get("accessToken")
    if not token:
        print("Erro: accessToken nao encontrado no JSON.")
        sys.exit(1)

    _atualizar_env(token)
    print()
    print(f"Token salvo em {ENV_PATH}")
    print("Reinicie o app: python -m vega.app.app")


if __name__ == "__main__":
    main()
