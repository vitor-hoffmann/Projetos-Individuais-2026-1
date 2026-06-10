"""Parsing de PDF com PyMuPDF + decisão de estratégia (full-scan vs chunking).

Não usamos regras rígidas de layout (coordenadas/regex). Apenas extraímos o texto
bruto de cada página e deixamos a compreensão semântica para o LLM. A única
heurística aqui é de CUSTO: decidir se o documento cabe inteiro no prompt
(full-scan) ou se precisa ser segmentado (chunking).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

from src.config import settings


@dataclass
class PaginaPDF:
    numero: int  # 1-indexed
    texto: str


@dataclass
class DocumentoParseado:
    paginas: list[PaginaPDF]

    @property
    def texto_completo(self) -> str:
        return "\n\n".join(
            f"[PÁGINA {p.numero}]\n{p.texto}" for p in self.paginas
        )

    def tokens_estimados(self) -> int:
        # Heurística simples: ~4 caracteres por token.
        return len(self.texto_completo) // 4


def parse_pdf(caminho: str | Path) -> DocumentoParseado:
    """Lê todas as páginas do PDF e retorna o texto por página."""
    paginas: list[PaginaPDF] = []
    with fitz.open(caminho) as doc:
        for i, page in enumerate(doc, start=1):
            paginas.append(PaginaPDF(numero=i, texto=page.get_text("text")))
    return DocumentoParseado(paginas=paginas)


def usar_fullscan(doc: DocumentoParseado) -> bool:
    """Decide a estratégia: full-scan para docs curtos, chunking para longos."""
    return doc.tokens_estimados() <= settings.fullscan_token_limit
