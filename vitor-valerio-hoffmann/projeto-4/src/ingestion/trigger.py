"""Gatilho de ingestão orientada a eventos (polling agendado).

Usa APScheduler para varrer periodicamente as Centrais de Resultados. Para cada
PDF descoberto, baixa, calcula o hash e dispara o pipeline SOMENTE se for inédito
(a checagem de idempotência acontece dentro de `processar_pdf`).

Uso:
    python -m src.ingestion.trigger          # roda o scheduler (Ctrl+C para sair)
    python -m src.ingestion.trigger --once   # executa uma única varredura e sai
"""
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

from src.config import settings
from src.ingestion.crawler import baixar_pdf, descobrir_pdfs
from src.pipeline import processar_pdf

DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "uda_downloads"


def varrer_e_processar() -> None:
    """Uma rodada de polling: descobre PDFs novos e dispara o pipeline."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print("[trigger] iniciando varredura das Centrais de Resultados...")

    descobertas = descobrir_pdfs()
    total = sum(len(v) for v in descobertas.values())
    print(f"[trigger] {total} PDFs encontrados em {len(descobertas)} fontes.")

    for empresa, urls in descobertas.items():
        for url in urls:
            nome = url.split("/")[-1].split("?")[0] or "documento.pdf"
            destino = DOWNLOAD_DIR / f"{empresa.replace(' ', '_')}__{nome}"
            try:
                baixar_pdf(url, str(destino))
            except Exception as exc:  # noqa: BLE001
                print(f"[trigger] falha ao baixar {url}: {exc}")
                continue

            res = processar_pdf(destino, url=url)
            print(f"[trigger] {empresa}: [{res.status}] {url}")


def iniciar_scheduler() -> None:
    """Agenda a varredura no intervalo configurado e roda indefinidamente."""
    scheduler = BlockingScheduler()
    scheduler.add_job(
        varrer_e_processar,
        "interval",
        hours=settings.poll_interval_hours,
        next_run_time=None,  # primeira execução no próximo intervalo
        id="polling_ri",
    )
    print(
        f"[trigger] scheduler iniciado (a cada {settings.poll_interval_hours}h). "
        "Ctrl+C para parar."
    )
    # Roda uma vez imediatamente, depois entra no ciclo agendado.
    varrer_e_processar()
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n[trigger] scheduler encerrado.")


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gatilho de ingestão (polling).")
    parser.add_argument(
        "--once", action="store_true", help="Executa uma única varredura e sai."
    )
    args = parser.parse_args(argv)

    if args.once:
        varrer_e_processar()
    else:
        iniciar_scheduler()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
