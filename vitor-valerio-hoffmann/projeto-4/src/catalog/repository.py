"""Repositório do Catálogo — operações de leitura/escrita + idempotência."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from src.catalog.db import get_connection
from src.models import MetricaEmpresa


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Idempotência
# --------------------------------------------------------------------------- #
def documento_ja_processado(sha256: str) -> bool:
    """True se já existe um documento com este hash e status 'processed'."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT status FROM documents WHERE sha256 = ?", (sha256,)
        ).fetchone()
        return row is not None and row["status"] == "processed"
    finally:
        conn.close()


def registrar_documento(
    sha256: str,
    url: Optional[str] = None,
    empresa: Optional[str] = None,
) -> int:
    """Cria (ou recupera) o registro do documento. Retorna o document_id.

    Usa INSERT OR IGNORE no sha256 único para garantir uma única linha por PDF.
    """
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO documents (sha256, url, empresa, status) "
            "VALUES (?, ?, ?, 'pending')",
            (sha256, url, empresa),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM documents WHERE sha256 = ?", (sha256,)
        ).fetchone()
        return int(row["id"])
    finally:
        conn.close()


def marcar_processado(
    document_id: int, documento_tipo: str, periodo_referencia: Optional[str]
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE documents SET status='processed', documento_tipo=?, "
            "periodo_referencia=?, processed_at=?, erro=NULL WHERE id=?",
            (documento_tipo, periodo_referencia, _now(), document_id),
        )
        conn.commit()
    finally:
        conn.close()


def marcar_erro(document_id: int, erro: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE documents SET status='error', erro=? WHERE id=?",
            (erro[:1000], document_id),
        )
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Persistência de métricas + linhagem
# --------------------------------------------------------------------------- #
def salvar_metricas(document_id: int, metricas: list[MetricaEmpresa]) -> int:
    """Insere métricas e a respectiva linhagem. Retorna quantas linhas salvou."""
    conn = get_connection()
    salvos = 0
    try:
        for m in metricas:
            cur = conn.execute(
                "INSERT OR REPLACE INTO metrics "
                "(document_id, empresa, ano, trimestre, lancamentos_vgv, "
                " lancamentos_unidades, vendas_vgv, vendas_unidades, vso) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    document_id,
                    m.empresa,
                    m.ano,
                    m.trimestre,
                    m.lancamentos_vgv,
                    m.lancamentos_unidades,
                    m.vendas_vgv,
                    m.vendas_unidades,
                    m.vso,
                ),
            )
            metric_id = cur.lastrowid
            conn.execute(
                "INSERT INTO lineage (metric_id, source_url, pagina, extracted_at) "
                "VALUES (?, ?, ?, ?)",
                (metric_id, m.fonte_url, m.pagina, _now()),
            )
            salvos += 1
        conn.commit()
    finally:
        conn.close()
    return salvos


# --------------------------------------------------------------------------- #
# Consultas (usadas pela API)
# --------------------------------------------------------------------------- #
def consultar_metricas(
    empresa: Optional[str] = None,
    ano: Optional[int] = None,
    trimestre: Optional[int] = None,
) -> list[dict]:
    """Retorna métricas filtradas, com a URL de origem (linhagem) anexada."""
    conn = get_connection()
    try:
        sql = (
            "SELECT m.*, l.source_url, l.pagina "
            "FROM metrics m LEFT JOIN lineage l ON l.metric_id = m.id WHERE 1=1"
        )
        params: list = []
        if empresa:
            sql += " AND LOWER(m.empresa) = LOWER(?)"
            params.append(empresa)
        if ano is not None:
            sql += " AND m.ano = ?"
            params.append(ano)
        if trimestre is not None:
            sql += " AND m.trimestre = ?"
            params.append(trimestre)
        sql += " ORDER BY m.empresa, m.ano, m.trimestre"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def listar_empresas() -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT empresa FROM metrics ORDER BY empresa"
        ).fetchall()
        return [r["empresa"] for r in rows]
    finally:
        conn.close()


def listar_documentos() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, empresa, url, sha256, documento_tipo, periodo_referencia, "
            "status, processed_at FROM documents ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
