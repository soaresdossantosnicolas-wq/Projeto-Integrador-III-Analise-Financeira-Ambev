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
    assert len(app.tabs) == 8
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


def test_tracos_plotly_preservam_valores_e_rotulos():
    from conftest import carregar_script

    dash = carregar_script("04_visualizacao")
    df = pd.DataFrame({"ano_analise": [2024, 2025], "receita_liquida": [89452669000.0, 88242467000.0]})
    antes = df.copy(deep=True)
    for tema in ["Claro", "Escuro"]:
        fig = dash.grafico_series(df, ("receita_liquida",), "Receita", tema)
        np.testing.assert_allclose(fig.data[0].y, df.receita_liquida / 1e9)
        assert fig.data[0].customdata[1][0] == "R$ 88,24 bi"
        assert fig.layout.yaxis.title.text == "R$ bilhões"
        assert fig.layout.legend.title.text == ""
    pd.testing.assert_frame_equal(df, antes)


def test_contraste_paleta_grafica_em_ambos_fundos():
    import config

    def luminancia(cor):
        canais = [int(cor[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in canais]
        return sum(v * peso for v, peso in zip(linear, [0.2126, 0.7152, 0.0722]))

    def contraste(a, b):
        menor, maior = sorted([luminancia(a), luminancia(b)])
        return (maior + 0.05) / (menor + 0.05)

    for cor in set(config.PALETA.values()):
        for fundo in ["#0B1220", "#F7F9FC"]:
            assert contraste(cor, fundo) >= 3  # elementos gráficos não textuais
    assert contraste("#E5EDF8", "#0B1220") >= 4.5
    assert contraste("#17253C", "#F7F9FC") >= 4.5


def test_explicacoes_opcionais_preservam_numeros_filtros_e_avisos():
    import json

    app = AppTest.from_file(str(RAIZ / "code/04_visualizacao.py")).run(timeout=30)
    assert not app.exception
    assert app.sidebar.checkbox[0].label == "Mostrar explicações"
    assert app.sidebar.checkbox[0].value is True
    assert any(c.value.startswith("Como ler:") for c in app.caption)
    assert any(e.label == "Margem líquida" for e in app.expander)
    assert "Ainda não é lucro" in app.metric[0].proto.help
    app.sidebar.multiselect[0].set_value([2025]).run()
    metricas = [(m.value, m.delta) for m in app.metric]
    tracos = [json.loads(g.proto.spec)["data"] for g in app.get("plotly_chart")]
    app.sidebar.checkbox[0].uncheck().run()
    assert not app.exception
    assert not any(c.value.startswith("Como ler:") for c in app.caption)
    assert [(m.value, m.delta) for m in app.metric] == metricas
    assert [json.loads(g.proto.spec)["data"] for g in app.get("plotly_chart")] == tracos
    assert app.sidebar.multiselect[0].value == [2025]
    assert any(e.label == "Margem líquida" for e in app.expander)
    assert any("EBIT CVM (3.05)" in i.value for i in app.info)
    app.sidebar.checkbox[0].check().run()
    assert any(c.value.startswith("Como ler:") for c in app.caption)


def test_glossario_cobre_todos_os_campos_publicados():
    from explicacoes import GLOSSARIO

    df = pd.read_csv(RAIZ / "dados_tratados/indicadores_financeiros_ambev.csv")
    assert set(df.columns) <= set(GLOSSARIO)
    assert all(len(entrada) == 4 and all(entrada) for entrada in GLOSSARIO.values())
