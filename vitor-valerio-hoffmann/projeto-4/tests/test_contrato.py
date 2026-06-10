"""Testes do Contrato Semântico (validação Pydantic blinda o banco)."""
import pytest
from pydantic import ValidationError

from src.models import MetricaEmpresa, PreviaOperacional


def test_metrica_valida():
    m = MetricaEmpresa(empresa="MRV", ano=2025, trimestre=3, lancamentos_vgv=1200.5)
    assert m.empresa == "MRV"
    assert m.vendas_vgv is None  # ausente -> None


def test_trimestre_invalido_rejeitado():
    with pytest.raises(ValidationError):
        MetricaEmpresa(empresa="MRV", ano=2025, trimestre=5)


def test_empresa_vazia_rejeitada():
    with pytest.raises(ValidationError):
        MetricaEmpresa(empresa="   ", ano=2025, trimestre=3)


def test_ano_fora_de_faixa_rejeitado():
    with pytest.raises(ValidationError):
        MetricaEmpresa(empresa="MRV", ano=1800, trimestre=1)


def test_previa_agrega_varias_empresas():
    previa = PreviaOperacional(
        documento_tipo="boletim_conjuntura",
        periodo_referencia="3T25",
        metricas=[
            MetricaEmpresa(empresa="MRV", ano=2025, trimestre=3),
            MetricaEmpresa(empresa="Cury", ano=2025, trimestre=3),
        ],
    )
    assert len(previa.metricas) == 2
