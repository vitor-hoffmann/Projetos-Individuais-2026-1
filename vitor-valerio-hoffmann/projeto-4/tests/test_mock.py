"""Testes do modo offline (--mock): a fixture passa pelo Contrato Semântico."""
import json

import pytest
from pydantic import ValidationError

from src.config import PROJECT_ROOT
from src.extraction.llm_extractor import carregar_previa_mock

FIXTURE_PADRAO = PROJECT_ROOT / "data" / "fixtures" / "boletim_demo.json"


def test_fixture_demo_valida_pelo_contrato():
    previa = carregar_previa_mock(FIXTURE_PADRAO, fonte_url="http://x/demo.pdf")
    assert previa.documento_tipo == "boletim_conjuntura"
    assert len(previa.metricas) == 18
    # Linhagem anexada a todas as métricas
    assert all(m.fonte_url == "http://x/demo.pdf" for m in previa.metricas)


def test_fixture_invalida_e_rejeitada(tmp_path):
    # trimestre 7 viola o Contrato Semântico -> deve falhar na validação
    ruim = tmp_path / "ruim.json"
    ruim.write_text(
        json.dumps(
            {
                "documento_tipo": "previa_operacional",
                "metricas": [{"empresa": "MRV", "ano": 2025, "trimestre": 7}],
            }
        )
    )
    with pytest.raises(ValidationError):
        carregar_previa_mock(ruim)
