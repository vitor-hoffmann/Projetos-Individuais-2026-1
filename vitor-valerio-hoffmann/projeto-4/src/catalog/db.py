"""Catálogo de Dados — schema e conexão SQLite.

Três tabelas:
- ``documents``: 1 linha por PDF ingerido. Guarda o ``sha256`` (idempotência) e o
  status de processamento.
- ``metrics``: dados estruturados extraídos (valores absolutos por empresa/trimestre).
- ``lineage``: linhagem — liga cada métrica ao documento/URL/página de origem.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from src.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa       TEXT,
    url           TEXT,
    sha256        TEXT NOT NULL UNIQUE,
    documento_tipo TEXT,
    periodo_referencia TEXT,
    status        TEXT NOT NULL DEFAULT 'pending',   -- pending | processed | error
    erro          TEXT,
    processed_at  TEXT
);

CREATE TABLE IF NOT EXISTS metrics (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id          INTEGER NOT NULL REFERENCES documents(id),
    empresa              TEXT NOT NULL,
    ano                  INTEGER NOT NULL,
    trimestre            INTEGER NOT NULL,
    lancamentos_vgv      REAL,
    lancamentos_unidades INTEGER,
    vendas_vgv           REAL,
    vendas_unidades      INTEGER,
    vso                  REAL,
    UNIQUE(empresa, ano, trimestre, document_id)
);

CREATE TABLE IF NOT EXISTS lineage (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_id    INTEGER NOT NULL REFERENCES metrics(id),
    source_url   TEXT,
    pagina       INTEGER,
    extracted_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_metrics_empresa_periodo
    ON metrics(empresa, ano, trimestre);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Abre uma conexão SQLite com row factory por nome e FKs habilitadas."""
    path = db_path or settings.db_file
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | None = None) -> None:
    """Cria as tabelas do catálogo se ainda não existirem."""
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Banco inicializado em: {settings.db_file}")
