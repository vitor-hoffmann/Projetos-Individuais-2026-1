"""Contrato Semântico dos Dados.

Estes modelos Pydantic são o coração da blindagem do banco: eles definem
EXATAMENTE quais campos o LLM pode devolver e com quais tipos. Qualquer saída
fora deste contrato é rejeitada e o documento é re-processado com a mensagem de
erro, evitando que alucinações ou variações de layout contaminem o banco.

Regra de negócio central: armazenamos sempre VALORES ABSOLUTOS (R$ e unidades),
nunca as variações percentuais destacadas pelo marketing de RI. As variações
(T/T, A/A) são calculadas pela camada de serviço a partir do histórico.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MetricaEmpresa(BaseModel):
    """Métricas operacionais absolutas de uma empresa em um trimestre.

    Todos os valores monetários estão em R$ milhões (normalizados na extração).
    Campos ausentes no documento devem vir como ``None`` — nunca inventados.
    """

    empresa: str = Field(..., description="Nome da incorporadora (ex.: MRV, Cury, Tenda).")
    ano: int = Field(..., ge=2000, le=2100, description="Ano de referência do dado.")
    trimestre: int = Field(..., ge=1, le=4, description="Trimestre (1 a 4).")

    # --- Lançamentos (valores absolutos) ---
    lancamentos_vgv: Optional[float] = Field(
        None, description="VGV lançado no trimestre, em R$ milhões. None se ausente."
    )
    lancamentos_unidades: Optional[int] = Field(
        None, description="Unidades lançadas no trimestre. None se ausente."
    )

    # --- Vendas (valores absolutos) ---
    vendas_vgv: Optional[float] = Field(
        None, description="VGV de vendas (líquidas) no trimestre, em R$ milhões. None se ausente."
    )
    vendas_unidades: Optional[int] = Field(
        None, description="Unidades vendidas no trimestre. None se ausente."
    )
    vso: Optional[float] = Field(
        None,
        description="Vendas Sobre Oferta (VSO) em %, se reportado como métrica operacional bruta.",
    )

    # --- Linhagem (preenchida pelo pipeline, não pelo LLM) ---
    fonte_url: Optional[str] = Field(
        None, description="URL/origem do PDF de onde o dado foi extraído (data lineage)."
    )
    pagina: Optional[int] = Field(
        None, description="Página do PDF onde a métrica foi localizada."
    )

    @field_validator("empresa")
    @classmethod
    def empresa_nao_vazia(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("empresa não pode ser vazia")
        return v


class PreviaOperacional(BaseModel):
    """Documento extraído: uma prévia operacional pode conter uma ou mais empresas.

    O Boletim de Conjuntura, por exemplo, traz várias empresas; já a prévia de uma
    incorporadora específica normalmente traz apenas uma.
    """

    documento_tipo: str = Field(
        ...,
        description="Tipo do documento: 'previa_operacional', 'boletim_conjuntura' ou 'release_resultados'.",
    )
    periodo_referencia: Optional[str] = Field(
        None, description="Período textual como aparece no doc (ex.: '3T25', '9M25')."
    )
    metricas: list[MetricaEmpresa] = Field(
        default_factory=list,
        description="Lista de métricas por empresa/trimestre encontradas no documento.",
    )


# JSON Schema usado como ferramenta (tool use) na chamada ao Claude.
EXTRACTION_TOOL_SCHEMA = PreviaOperacional.model_json_schema()
