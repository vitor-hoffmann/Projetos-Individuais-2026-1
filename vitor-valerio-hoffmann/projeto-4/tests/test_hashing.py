"""Testes de idempotência por hash (SHA-256)."""
from src.ingestion.hashing import sha256_bytes, sha256_file


def test_sha256_bytes_deterministico():
    assert sha256_bytes(b"abc") == sha256_bytes(b"abc")


def test_sha256_bytes_difere_por_conteudo():
    assert sha256_bytes(b"abc") != sha256_bytes(b"abd")


def test_sha256_file_igual_a_bytes(tmp_path):
    p = tmp_path / "x.pdf"
    p.write_bytes(b"conteudo-do-pdf")
    assert sha256_file(p) == sha256_bytes(b"conteudo-do-pdf")
