"""Testes do catálogo SQLite: idempotência, persistência e linhagem."""
import pytest

from src.catalog import db, repository
from src.models import MetricaEmpresa


@pytest.fixture(autouse=True)
def banco_temporario(tmp_path, monkeypatch):
    """Redireciona o banco para um arquivo temporário em cada teste."""
    caminho = tmp_path / "catalog.db"
    monkeypatch.setattr(db.settings, "db_path", str(caminho))
    # repository importa settings via db.get_connection, que lê settings.db_file
    db.init_db(caminho)
    monkeypatch.setattr(
        repository, "get_connection", lambda: db.get_connection(caminho)
    )
    yield


def test_idempotencia_por_hash():
    repository.registrar_documento(sha256="hash-1", url="http://x/a.pdf")
    assert repository.documento_ja_processado("hash-1") is False  # ainda pending

    doc_id = repository.registrar_documento(sha256="hash-1", url="http://x/a.pdf")
    repository.marcar_processado(doc_id, "previa_operacional", "3T25")
    assert repository.documento_ja_processado("hash-1") is True


def test_registrar_documento_idempotente():
    id1 = repository.registrar_documento(sha256="hash-2")
    id2 = repository.registrar_documento(sha256="hash-2")
    assert id1 == id2  # mesmo hash -> mesma linha


def test_salvar_metricas_grava_linhagem():
    doc_id = repository.registrar_documento(sha256="hash-3", url="http://x/mrv.pdf")
    salvos = repository.salvar_metricas(
        doc_id,
        [
            MetricaEmpresa(
                empresa="MRV",
                ano=2025,
                trimestre=3,
                lancamentos_vgv=1000.0,
                fonte_url="http://x/mrv.pdf",
                pagina=1,
            )
        ],
    )
    assert salvos == 1
    linhas = repository.consultar_metricas(empresa="MRV", ano=2025, trimestre=3)
    assert len(linhas) == 1
    assert linhas[0]["source_url"] == "http://x/mrv.pdf"  # linhagem presente
    assert linhas[0]["lancamentos_vgv"] == 1000.0


def test_listar_empresas():
    doc_id = repository.registrar_documento(sha256="hash-4")
    repository.salvar_metricas(
        doc_id, [MetricaEmpresa(empresa="Tenda", ano=2025, trimestre=2)]
    )
    assert "Tenda" in repository.listar_empresas()
