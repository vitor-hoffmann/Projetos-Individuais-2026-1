"""Descoberta de PDFs nas Centrais de Resultados (RI).

Estratégia de gatilho: polling. O scheduler chama `descobrir_pdfs()` em intervalos
definidos; para cada link de PDF encontrado, o pipeline decide por hash se é novo.
Não sobrecarrega os servidores: uma varredura leve por execução.
"""
from __future__ import annotations

from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from src.ingestion.sources import FONTES, FonteRI

# Palavras que indicam que o link é uma prévia operacional (foco do desafio).
TERMOS_PREVIA = ("previa", "prévia", "operacional", "resultado")

HEADERS = {"User-Agent": "UDA-Pipeline/1.0 (academic project)"}


def _e_pdf(href: str) -> bool:
    return href.lower().split("?")[0].endswith(".pdf")


def descobrir_pdfs_em(fonte: FonteRI, timeout: int = 20) -> list[str]:
    """Retorna URLs absolutas de PDFs (preferindo prévias) de uma fonte."""
    try:
        resp = requests.get(fonte.url_central_resultados, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    previas: list[str] = []
    outros: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not _e_pdf(href):
            continue
        url_abs = urljoin(fonte.url_central_resultados, href)
        texto = (a.get_text() or "").lower()
        # Prioriza prévias operacionais; ainda assim coleta os demais PDFs.
        if any(t in texto or t in href.lower() for t in TERMOS_PREVIA):
            previas.append(url_abs)
        else:
            outros.append(url_abs)
    # Prévias primeiro; remove duplicatas preservando ordem.
    return list(dict.fromkeys(previas + outros))


def descobrir_pdfs() -> dict[str, list[str]]:
    """Varre todas as fontes. Retorna {empresa: [urls de pdf]}."""
    return {f.empresa: descobrir_pdfs_em(f) for f in FONTES}


def baixar_pdf(url: str, destino: str, timeout: int = 60) -> str:
    """Baixa um PDF para o caminho `destino` e retorna esse caminho."""
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    with open(destino, "wb") as f:
        f.write(resp.content)
    return destino
