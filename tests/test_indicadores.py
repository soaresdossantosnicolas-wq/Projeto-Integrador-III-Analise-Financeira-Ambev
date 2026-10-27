"""Casos contábeis de resultado conhecido e entradas incompletas."""

import numpy as np
import pandas as pd
import pytest


def test_liquidez_e_rentabilidade(analise):
    base = pd.DataFrame([{
        "ativo_circulante": 200, "passivo_circulante": 100, "estoques": 50,
        "receita_liquida": 1000, "lucro_bruto": 400, "lucro_liquido": 100,
        "resultado_operacional": 200, "ativo_total": 500, "patrimonio_liquido": 250,
    }])
    df = analise.calcular_rentabilidade(analise.calcular_liquidez(base))
    esperado = {
        "liquidez_corrente": 2, "liquidez_seca": 1.5, "margem_bruta": 40,
        "margem_operacional": 20, "margem_liquida": 10, "roa": 20, "roe": 40,
    }
    for coluna, valor in esperado.items():
        assert df.loc[0, coluna] == pytest.approx(valor)
    assert "roe" not in base.columns


def test_endividamento_exclui_patrimonio(analise):
    base = pd.DataFrame([{
        "ativo_total": 1000, "passivo_total": 1000, "patrimonio_liquido": 600,
        "passivo_circulante": 250, "passivo_nao_circulante": 150,
    }])
    df = analise.calcular_endividamento(base)
    assert df.loc[0, "endividamento_geral"] == pytest.approx(40)
    assert df.loc[0, "capital_terceiros_patrimonio"] == pytest.approx(400 / 600 * 100)
    assert pd.isna(df.loc[0, "divida_liquida_ebitda"])


def test_zero_e_ausencias_nao_viram_indicadores_falsos(analise):
    denominador = pd.Series([0, np.nan, 2])
    resultado = analise.calcular_razao(pd.Series([10, 10, 10]), denominador)
    np.testing.assert_allclose(resultado, [np.nan, np.nan, 5], equal_nan=True)
    base = pd.DataFrame({"ativo_circulante": [200], "passivo_circulante": [100]})
    assert pd.isna(analise.calcular_liquidez(base).loc[0, "liquidez_seca"])


def test_crescimento_usa_ordem_cronologica(analise):
    base = pd.DataFrame({"ano_analise": [2023, 2022], "receita_liquida": [120, 100]})
    df = analise.calcular_crescimento(base).reset_index(drop=True)
    assert df["ano_analise"].tolist() == [2022, 2023]
    assert pd.isna(df.loc[0, "crescimento_receita_liquida"])
    assert df.loc[1, "crescimento_receita_liquida"] == pytest.approx(20)
