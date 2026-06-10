"""Catálogo de fontes — Centrais de Resultados (RI) das incorporadoras.

Mapeia empresa -> URL da página onde as prévias operacionais são publicadas.
O crawler varre essas páginas em busca de novos PDFs. As URLs podem mudar; por
isso o pipeline também aceita PDFs locais/manuais (modo de demonstração).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FonteRI:
    empresa: str
    url_central_resultados: str


# Centrais de Resultados conhecidas. Ajustar conforme os portais de RI mudarem.
FONTES: list[FonteRI] = [
    FonteRI("MRV", "https://ri.mrv.com.br/informacoes-financeiras/central-de-resultados/"),
    FonteRI("Cury", "https://ri.cury.net/informacoes-aos-investidores/central-de-resultados/"),
    FonteRI("Tenda", "https://ri.tenda.com/informacoes-financeiras/central-de-resultados/"),
    FonteRI("Direcional", "https://ri.direcional.com.br/informacoes-financeiras/central-de-resultados/"),
    FonteRI("Plano & Plano", "https://ri.planoeplano.com.br/informacoes-financeiras/central-de-resultados/"),
    FonteRI("Pacaembu", "https://ri.pacaembu.com/informacoes-financeiras/central-de-resultados/"),
]
