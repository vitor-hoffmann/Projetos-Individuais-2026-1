"""Camada de Serviço (API REST) do pipeline de UDA.

Expõe os dados absolutos extraídos + as variações percentuais CALCULADAS a partir
do histórico (T/T e A/A). As variações nunca são extraídas dos PDFs — atende ao
critério "Extração de Valores Absolutos" (o banco calcula o histórico real).

Rodar:
    uvicorn src.api.main:app --reload
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Query

from src.catalog import repository

app = FastAPI(
    title="API de Conjuntura do Setor Habitacional",
    description="Serve dados operacionais absolutos de incorporadoras + variações calculadas.",
    version="1.0.0",
)


def _variacao(atual: Optional[float], base: Optional[float]) -> Optional[float]:
    """Variação percentual de `atual` sobre `base`, em %. None se indefinida."""
    if atual is None or base is None or base == 0:
        return None
    return round((atual - base) / base * 100, 1)


def _trimestre_anterior(ano: int, trimestre: int) -> tuple[int, int]:
    return (ano - 1, 4) if trimestre == 1 else (ano, trimestre - 1)


def _buscar(metricas: list[dict], ano: int, trimestre: int) -> Optional[dict]:
    for m in metricas:
        if m["ano"] == ano and m["trimestre"] == trimestre:
            return m
    return None


def _com_variacoes(registro: dict, historico: list[dict]) -> dict:
    """Anexa variações T/T (trimestre anterior) e A/A (mesmo trim. ano anterior)."""
    ano, tri = registro["ano"], registro["trimestre"]
    ano_tt, tri_tt = _trimestre_anterior(ano, tri)
    anterior_tt = _buscar(historico, ano_tt, tri_tt)
    anterior_aa = _buscar(historico, ano - 1, tri)

    def par(campo: str) -> dict:
        return {
            "valor_absoluto": registro.get(campo),
            "var_trimestral_pct": _variacao(
                registro.get(campo), anterior_tt.get(campo) if anterior_tt else None
            ),
            "var_anual_pct": _variacao(
                registro.get(campo), anterior_aa.get(campo) if anterior_aa else None
            ),
        }

    return {
        "empresa": registro["empresa"],
        "ano": ano,
        "trimestre": tri,
        "lancamentos_vgv": par("lancamentos_vgv"),
        "lancamentos_unidades": par("lancamentos_unidades"),
        "vendas_vgv": par("vendas_vgv"),
        "vendas_unidades": par("vendas_unidades"),
        "vso": registro.get("vso"),
        "fonte": registro.get("source_url"),
        "pagina": registro.get("pagina"),
    }


@app.get("/api/conjuntura")
def conjuntura(
    empresa: Optional[str] = Query(None, description="Nome da empresa, ex.: MRV"),
    ano: Optional[int] = Query(None, description="Ano de referência, ex.: 2025"),
    trimestre: Optional[int] = Query(None, ge=1, le=4, description="Trimestre (1-4)"),
):
    """Métricas absolutas + variações calculadas, filtráveis por empresa/ano/trimestre."""
    resultados = repository.consultar_metricas(empresa, ano, trimestre)
    saida = []
    for r in resultados:
        # Histórico da mesma empresa para calcular as variações.
        historico = repository.consultar_metricas(empresa=r["empresa"])
        saida.append(_com_variacoes(r, historico))
    return {"total": len(saida), "dados": saida}


@app.get("/api/empresas")
def empresas():
    """Lista as empresas com dados no banco."""
    return {"empresas": repository.listar_empresas()}


@app.get("/api/documentos")
def documentos():
    """Catálogo + linhagem: documentos ingeridos e seu status (auditoria)."""
    return {"documentos": repository.listar_documentos()}


@app.get("/")
def raiz():
    return {
        "servico": "API de Conjuntura do Setor Habitacional",
        "endpoints": [
            "/api/conjuntura?empresa=MRV&ano=2025&trimestre=3",
            "/api/empresas",
            "/api/documentos",
        ],
    }
