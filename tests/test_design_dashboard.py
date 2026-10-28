"""Contratos de apresentação: mesma base, unidades explícitas, links e exportações numéricas."""

import io
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import config
from dashboard_interacoes import exportar_excel, figura_exploracao

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def base():
    return pd.read_csv(RAIZ / "dados_tratados/indicadores_financeiros_ambev.csv")


@pytest.mark.parametrize("unidade,divisor", [("Bilhões", 1e9), ("Milhões", 1e6), ("Mil", 1e3)])
@pytest.mark.parametrize("forma", ["Linha", "Barras"])
def test_unidades_sao_apenas_apresentacao(base, unidade, divisor, forma):
    antes = base.copy(deep=True)
    recorte = base.loc[base.ano_analise.eq(2025)]
    fig = figura_exploracao(base, recorte, "receita_liquida", "Claro", unidade, "Valores", forma, 2025)
    np.testing.assert_array_equal(fig.data[0].y, recorte.receita_liquida / divisor)
    assert fig.data[0].customdata[0][0] == "R$ 88,24 bi"
    # O ano oculto ainda é usado como referência, nunca o extremo do recorte.
    esperado = (base.iloc[-1].receita_liquida / base.iloc[-2].receita_liquida - 1) * 100
    assert fig.data[0].customdata[0][1] == f"{esperado:.2f}".replace(".", ",") + "%"
    pd.testing.assert_frame_equal(base, antes)


def test_percentual_da_receita_e_indicadores_nao_sao_reescalados(base):
    fig = figura_exploracao(base, base, "lucro_liquido", "Escuro", "Mil", "% da receita", "Barras", 2025)
    np.testing.assert_allclose(fig.data[0].y, base.lucro_liquido / base.receita_liquida * 100)
    for campo in ["roe", "liquidez_corrente"]:
        fig = figura_exploracao(base, base, campo, "Escuro", "Mil", "% da receita", "Linha", 2025)
        np.testing.assert_array_equal(fig.data[0].y, base[campo])


def test_excel_mantem_dados_numericos_e_recorte(base):
    dados = base.loc[base.ano_analise.isin([2022, 2025])].reset_index(drop=True)
    volta = pd.read_excel(io.BytesIO(exportar_excel(dados)))
    esperado = dados.rename(columns={"ano_analise": "Ano", **config.NOMES})
    pd.testing.assert_frame_equal(volta, esperado, check_dtype=False, rtol=1e-14)
    assert volta.Ano.tolist() == [2022, 2025]


def test_url_restaurada_e_filtros_inesperados_tratados():
    app = AppTest.from_file(str(RAIZ / "code/04_visualizacao.py"))
    app.query_params["anos"] = ["2025"]
    app.query_params["aba"] = "DRE"
    app.query_params["tema"] = "Claro"
    app.run(timeout=30)
    assert not app.exception
    assert app.sidebar.multiselect[0].value == [2025]
    assert app.session_state["aba"] == "DRE"
    assert app.session_state["tema"] == "Claro"
    assert app.metric[0].value == "R$ 88,24 bi"
    app.sidebar.multiselect[0].set_value([2022]).run()
    assert app.metric[0].delta == ""
    assert not app.exception


def test_projecoes_persistem_cenario_e_frequencia_sem_treino(monkeypatch):
    import modelos_preditivos

    monkeypatch.setattr(
        modelos_preditivos, "prever_bases", lambda *args, **kwargs: pytest.fail("Treino vedado no dashboard")
    )
    app = AppTest.from_file(str(RAIZ / "code/04_visualizacao.py")).run(timeout=30)
    next(s for s in app.selectbox if s.label == "Frequência das projeções").set_value("trimestral").run()
    next(s for s in app.selectbox if s.label == "Cenário").set_value("pessimista").run()
    assert not app.exception
    # Atualização da URL é feita pelo navegador; coberta pelo roteiro Playwright.
    assert app.session_state["frequencia"] == "trimestral"
    assert app.session_state["cenario"] == "pessimista"


def test_apresentacao_e_glossario_preservam_kpis():
    app = AppTest.from_file(str(RAIZ / "code/04_visualizacao.py")).run(timeout=30)
    antes = [(m.value, m.delta) for m in app.metric]
    app.toggle[0].set_value(True).run()
    assert not app.exception
    assert [(m.value, m.delta) for m in app.metric] == antes
    assert any(e.label == "Margem líquida" for e in app.expander)
    app.toggle[0].set_value(False).run()
    assert not app.exception
