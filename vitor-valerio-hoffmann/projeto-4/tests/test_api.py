"""Testes da API: variações calculadas a partir de valores absolutos."""
from src.api.main import _com_variacoes, _variacao


def test_variacao_percentual():
    assert _variacao(120, 100) == 20.0
    assert _variacao(80, 100) == -20.0


def test_variacao_indefinida_quando_base_ausente():
    assert _variacao(100, None) is None
    assert _variacao(100, 0) is None
    assert _variacao(None, 100) is None


def test_com_variacoes_calcula_tt_e_aa():
    # Histórico: 2T25, 3T24 e 3T25 (atual) para a mesma empresa.
    historico = [
        {"empresa": "MRV", "ano": 2025, "trimestre": 2, "lancamentos_vgv": 100.0},
        {"empresa": "MRV", "ano": 2024, "trimestre": 3, "lancamentos_vgv": 200.0},
        {"empresa": "MRV", "ano": 2025, "trimestre": 3, "lancamentos_vgv": 150.0},
    ]
    atual = historico[2]
    resultado = _com_variacoes(atual, historico)

    lvgv = resultado["lancamentos_vgv"]
    assert lvgv["valor_absoluto"] == 150.0
    assert lvgv["var_trimestral_pct"] == 50.0   # 150 vs 100 (2T25)
    assert lvgv["var_anual_pct"] == -25.0        # 150 vs 200 (3T24)
