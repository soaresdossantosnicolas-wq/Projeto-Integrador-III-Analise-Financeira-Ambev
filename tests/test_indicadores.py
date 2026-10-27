"""Casos contábeis de resultado conhecido e entradas incompletas."""

import numpy as np
import pandas as pd
import pytest


def test_liquidez_e_rentabilidade(analise):
    base = pd.DataFrame(
        [
            {
                "ativo_circulante": 200,
                "passivo_circulante": 100,
                "estoques": 50,
                "receita_liquida": 1000,
                "lucro_bruto": 400,
                "lucro_liquido": 100,
                "resultado_operacional": 200,
                "ativo_total": 500,
                "patrimonio_liquido": 250,
            }
        ]
    )
    df = analise.calcular_rentabilidade(analise.calcular_liquidez(base))
    esperado = {
        "liquidez_corrente": 2,
        "liquidez_seca": 1.5,
        "margem_bruta": 40,
        "margem_operacional": 20,
        "margem_liquida": 10,
        "roa": 20,
        "roe": 40,
    }
    for coluna, valor in esperado.items():
        assert df.loc[0, coluna] == pytest.approx(valor)
    assert "roe" not in base.columns


def test_endividamento_exclui_patrimonio(analise):
    base = pd.DataFrame(
        [
            {
                "ativo_total": 1000,
                "passivo_total": 1000,
                "patrimonio_liquido": 600,
                "passivo_circulante": 250,
                "passivo_nao_circulante": 150,
            }
        ]
    )
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


def test_crescimento_sem_preencher_nulos_ou_pular_ano(analise):
    base = pd.DataFrame({"ano_analise": [2022, 2023, 2024], "receita_liquida": [100, np.nan, 120]})
    assert analise.calcular_crescimento(base).crescimento_receita_liquida.isna().all()
    gap = pd.DataFrame({"ano_analise": [2022, 2024], "receita_liquida": [100, 120]})
    assert analise.calcular_crescimento(gap).crescimento_receita_liquida.isna().all()


def test_horizontal_negativo_coerente_com_crescimento(analise):
    base = pd.DataFrame({"ano_analise": [2022, 2023], "lucro_liquido": [-100, -50]})
    df = analise.calcular_crescimento(base)
    assert df.crescimento_lucro_liquido.iloc[-1] == 50
    assert analise.criar_analise_horizontal(base).variacao_percentual.iloc[0] == 50


def test_vertical_preserva_sinais_e_escala(analise):
    base = pd.DataFrame(
        {"ano_analise": [2025], "receita_liquida": [1000], "custo_vendas": [-600], "lucro_bruto": [400]}
    )
    vertical = analise.criar_analise_vertical(base).set_index("indicador")
    assert vertical.loc["custo_vendas", "percentual_receita"] == -60
    assert vertical.loc["lucro_bruto", "percentual_receita"] == 40


def test_denominador_infinito_e_zero_sem_warning(analise):
    with np.errstate(all="raise"):
        resultado = analise.calcular_percentual(pd.Series([10, 10, np.inf]), pd.Series([0, np.inf, 10]))
    assert np.isnan(resultado).all()


def test_diagnostico_explicita_todo_nan(analise):
    base = pd.DataFrame(
        {
            "ano_analise": [2022],
            "crescimento_receita_liquida": [np.nan],
            "divida_liquida_ebitda": [np.nan],
            "roe": [np.nan],
        }
    )
    relatorio = analise.diagnosticar_ausencias(base)
    assert len(relatorio) == 3
    assert relatorio.motivo.str.len().gt(20).all()
