"""Testes da aplicação e funções puras de preparação e apresentação, sem rede."""

import io
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from dashboard_utils import (
    calcular_variacoes,
    exportar_csv,
    formatar_indicador,
    formatar_percentual,
    formatar_valor,
    numero_br,
    preparar_series,
    validar_snapshot,
)
from excecoes import ErroValidacaoDados

RAIZ = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "valor,esperado",
    [
        (89.452669e9, "R$ 89,45 bi"),
        (-1234567, "R$ -1,23 mi"),
        (12.5, "R$ 12,50"),
        (np.nan, "n/d"),
        (np.inf, "n/d"),
    ],
)
def test_formatacao_pt_br(valor, esperado):
    assert formatar_valor(valor) == esperado
    assert formatar_percentual(18.125) == "18,12%"
    assert numero_br(1234567.89) == "1.234.567,89"
    assert formatar_indicador("liquidez_seca", 0.73) == "0,73 ×"


def test_delta_exige_ano_calendario_anterior():
    base = pd.DataFrame({"ano_analise": [2022, 2025], "receita_liquida": [100, 120]})
    assert np.isnan(calcular_variacoes(base, "receita_liquida", 2025)[2])


def test_preparacao_e_exportacao_preservam_valores():
    base = pd.DataFrame({"ano_analise": [2025], "receita_liquida": [88242467000.0]})
    antes = base.copy(deep=True)
    long = preparar_series(base, ["receita_liquida"])
    assert long.valor.iloc[0] == base.receita_liquida.iloc[0]
    volta = pd.read_csv(io.BytesIO(exportar_csv(base)), sep=";", decimal=",")
    assert volta["Receita líquida"].iloc[0] == base.receita_liquida.iloc[0]
    pd.testing.assert_frame_equal(base, antes)


def test_snapshot_rejeita_duplicatas():
    df = pd.read_csv(RAIZ / "dados_tratados/indicadores_financeiros_ambev.csv")
    with pytest.raises(ErroValidacaoDados, match="linha por exercício"):
        validar_snapshot(pd.concat([df, df.iloc[[0]]]))


def test_dashboard_abre_filtra_limpa_e_trata_vazio():
    app = AppTest.from_file(str(RAIZ / "code/04_visualizacao.py")).run(timeout=30)
    assert not app.exception
    assert not app.error
    assert len(app.metric) == 4
    assert len(app.tabs) == 7
    delta = app.metric[0].delta
    app.sidebar.multiselect[0].set_value([2025]).run()
    assert not app.exception
    assert app.metric[0].delta == delta
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception
    assert "Selecione ao menos" in app.info[0].value
    app.sidebar.button[0].click().run()
    assert app.sidebar.multiselect[0].value == [2022, 2023, 2024, 2025]
    app.sidebar.selectbox[0].select("Claro").run()
    assert not app.exception


def test_dashboard_base_ausente_sem_traceback(monkeypatch, tmp_path):
    import config

    monkeypatch.setattr(config, "PASTA_DADOS_TRATADOS", tmp_path)
    app = AppTest.from_file(str(RAIZ / "code/04_visualizacao.py")).run(timeout=30)
    assert not app.exception
    assert "Não foi possível" in app.error[0].value
