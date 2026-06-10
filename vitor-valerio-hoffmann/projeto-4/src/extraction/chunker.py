"""Chunking semântico para documentos longos.

Estratégia: segmentar por página (unidade semântica natural de prévias/relatórios)
e manter apenas os chunks que contêm sinais de tabelas operacionais/financeiras.
Isso recupera só os pedaços relevantes antes de acionar o LLM, otimizando tokens
e latência — sem depender de coordenadas fixas.
"""
from __future__ import annotations

from src.extraction.parser import DocumentoParseado, PaginaPDF

# Sinais de que a página contém métricas operacionais relevantes.
PALAVRAS_CHAVE = (
    "lançament",
    "lancament",
    "vendas",
    "vgv",
    "unidades",
    "vso",
    "vendas líquidas",
    "vendas liquidas",
    "trimestre",
    "operacional",
)


def pagina_relevante(pagina: PaginaPDF) -> bool:
    texto = pagina.texto.lower()
    return any(p in texto for p in PALAVRAS_CHAVE)


def selecionar_chunks(doc: DocumentoParseado) -> str:
    """Retorna apenas o texto das páginas relevantes, preservando a numeração.

    Se nenhuma página casar com as palavras-chave (layout muito diferente),
    devolve o documento inteiro como fallback seguro.
    """
    relevantes = [p for p in doc.paginas if pagina_relevante(p)]
    if not relevantes:
        relevantes = doc.paginas
    return "\n\n".join(f"[PÁGINA {p.numero}]\n{p.texto}" for p in relevantes)
