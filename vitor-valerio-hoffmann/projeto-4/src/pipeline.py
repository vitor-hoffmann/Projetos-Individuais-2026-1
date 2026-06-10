"""Orquestrador do pipeline de UDA.

Fluxo: detectar PDF -> calcular hash -> checar catálogo (idempotência) ->
parse (PyMuPDF) -> extração via LLM (Contrato Semântico) -> persistir métricas +
linhagem no catálogo.

Pode ser usado como módulo (`from src.pipeline import processar_pdf`) ou via CLI:

    python -m src.pipeline caminho/para/arquivo.pdf [--url URL_DE_ORIGEM]
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from src.catalog import repository
from src.catalog.db import init_db
from src.config import PROJECT_ROOT
from src.extraction.llm_extractor import carregar_previa_mock, extrair_previa
from src.extraction.parser import parse_pdf
from src.ingestion.hashing import sha256_file
from src.models import MetricaEmpresa

FIXTURES_DIR = PROJECT_ROOT / "data" / "fixtures"


@dataclass
class ResultadoProcessamento:
    sha256: str
    status: str  # 'ignorado' | 'processado' | 'erro'
    metricas_salvas: int = 0
    detalhe: str = ""


def resolver_fixture(caminho_pdf: Path, fixture: str | None) -> Path:
    """Resolve qual fixture usar no modo --mock.

    - fixture explícito -> usa esse caminho.
    - "__auto__" -> procura data/fixtures/<nome-do-pdf>.json e, se não houver,
      cai no fixture de demonstração padrão (boletim_demo.json).
    """
    if fixture and fixture != "__auto__":
        return Path(fixture)
    candidato = FIXTURES_DIR / f"{caminho_pdf.stem}.json"
    return candidato if candidato.exists() else FIXTURES_DIR / "boletim_demo.json"


def processar_pdf(
    caminho: str | Path,
    url: str | None = None,
    mock_fixture: str | None = None,
) -> ResultadoProcessamento:
    """Processa um único PDF respeitando a idempotência por hash.

    Se ``mock_fixture`` for informado, a etapa de extração via LLM é substituída
    pelo carregamento de uma fixture JSON (modo offline, sem chave de API). Todo
    o resto do fluxo — hash, idempotência, catálogo e linhagem — é idêntico.
    """
    caminho = Path(caminho)
    init_db()

    # 1. Assinatura única do arquivo
    sha = sha256_file(caminho)
    fonte = url or str(caminho)

    # 2. Idempotência: já processado? então ignora (não gasta API).
    if repository.documento_ja_processado(sha):
        return ResultadoProcessamento(
            sha256=sha, status="ignorado", detalhe="PDF já processado anteriormente"
        )

    # 3. Registra o documento no catálogo (status pending)
    document_id = repository.registrar_documento(sha256=sha, url=fonte)

    try:
        # 4. Extração: caminho real (LLM) ou modo mock (fixture).
        if mock_fixture is not None:
            previa = carregar_previa_mock(
                resolver_fixture(caminho, mock_fixture), fonte_url=fonte
            )
        else:
            doc = parse_pdf(caminho)
            previa = extrair_previa(doc, fonte_url=fonte)

        # 5. Garante a linhagem em cada métrica antes de persistir
        metricas: list[MetricaEmpresa] = []
        for m in previa.metricas:
            if not m.fonte_url:
                m.fonte_url = fonte
            metricas.append(m)

        salvos = repository.salvar_metricas(document_id, metricas)
        repository.marcar_processado(
            document_id, previa.documento_tipo, previa.periodo_referencia
        )
        return ResultadoProcessamento(
            sha256=sha, status="processado", metricas_salvas=salvos
        )
    except Exception as exc:  # noqa: BLE001 - registra o erro no catálogo
        repository.marcar_erro(document_id, str(exc))
        return ResultadoProcessamento(sha256=sha, status="erro", detalhe=str(exc))


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Processa um PDF no pipeline de UDA.")
    parser.add_argument("pdf", help="Caminho do PDF a processar.")
    parser.add_argument("--url", help="URL de origem do PDF (linhagem).", default=None)
    parser.add_argument(
        "--mock",
        nargs="?",
        const="__auto__",
        default=None,
        metavar="FIXTURE.json",
        help="Modo offline: usa uma fixture JSON em vez de chamar o LLM. "
        "Sem valor, resolve automaticamente em data/fixtures/.",
    )
    args = parser.parse_args(argv)

    res = processar_pdf(args.pdf, url=args.url, mock_fixture=args.mock)
    print(f"[{res.status.upper()}] sha256={res.sha256[:12]}...")
    if res.status == "processado":
        print(f"  métricas salvas: {res.metricas_salvas}")
    elif res.detalhe:
        print(f"  {res.detalhe}")
    return 0 if res.status != "erro" else 1


if __name__ == "__main__":
    sys.exit(_main())
