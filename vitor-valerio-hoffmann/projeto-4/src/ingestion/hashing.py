"""Assinatura única de arquivos para idempotência (SHA-256)."""
from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    """SHA-256 do conteúdo em bytes (ex.: PDF baixado em memória)."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    """SHA-256 de um arquivo em disco, lido em blocos."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloco in iter(lambda: f.read(8192), b""):
            h.update(bloco)
    return h.hexdigest()
