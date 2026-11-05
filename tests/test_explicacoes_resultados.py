"""Fontes, reconciliação e leitura descritiva, com arquivos locais e séries sintéticas."""

import io
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import config
import dashboard_explicacoes as painel
from analise_explicacoes import (
    CAMPOS_CALCULADOS,
    calcular_camada1,
    ponte_margem,
    reconciliar,
    validar_alinhamento,
    validar_catalogo,
    validar_companhia,
    validar_grupo,
    validar_referencias,
    verificar_pendencias,
)
from excecoes import ErroValidacaoDados

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def historico():
    return pd.read_csv(RAIZ / "dados_tratados/indicadores_financeiros_ambev.csv")


@pytest.fixture
def curadoria():
    return tuple(pd.read_csv(config.PASTA_EXPLICACOES / nome).fillna("") for nome in painel.ARQUIVOS)


def test_curadoria_schema_e_vinculos(curadoria):
    c, g, r, d = curadoria
    validar_companhia(c)
    validar_grupo(g)
    validar_referencias(r)
    validar_catalogo(c, r, d)
    pendencias = verificar_pendencias(c, r, d, g)
    assert len(pendencias) == 19
    assert (c.status == "verificado").sum() == 17
    assert set(g.status) == {"rascunho"}


@pytest.mark.parametrize(
    "campo", ["documento", "pagina", "medida", "url", "data_publicacao", "data_acesso", "unidade", "periodo"]
)
def test_bloqueia_afirmacao_sem_fonte(curadoria, campo):
    c = curadoria[0].copy()
    c.loc[0, campo] = ""
    with pytest.raises(ErroValidacaoDados):
        validar_companhia(c)


def test_pendente_nao_pode_afirmar_fato(curadoria):
    c = curadoria[0].copy()
    i = c.index[c.status == "pendente"][0]
    c.loc[i, "afirmacao_parafraseada"] = "A receita mudou por uma causa sem evidência."
    with pytest.raises(ErroValidacaoDados, match="pendente"):
        validar_companhia(c)


@pytest.mark.parametrize("valor", [0, -1, 1.5, "nan"])
def test_pagina_invalida(curadoria, valor):
    c = curadoria[0].copy()
    c.loc[0, "pagina"] = valor
    with pytest.raises(ErroValidacaoDados, match="Página"):
        validar_companhia(c)


def test_catalogo_pagina_fora_pdf_e_fonte_nao_oficial(curadoria):
    c, _, r, d = curadoria
    c.loc[0, "pagina"] = 999
    with pytest.raises(ErroValidacaoDados, match="Página fora"):
        validar_catalogo(c, r, d)
    c.loc[0, "url"] = "https://blog.example/ambev"
    with pytest.raises(ErroValidacaoDados, match="domínios oficiais"):
        validar_companhia(c)


def test_schema_ausente(curadoria):
    with pytest.raises(ErroValidacaoDados, match="Schema"):
        validar_companhia(curadoria[0].drop(columns="medida"))


def test_status_e_evidencias_interpretacao(curadoria):
    c, g, r, d = curadoria
    g.loc[0, "status"] = "final"
    with pytest.raises(ErroValidacaoDados):
        validar_grupo(g)
    g.loc[0, "status"] = "rascunho"
    g.loc[0, "evidencias"] = "C2022-99"
    with pytest.raises(ErroValidacaoDados, match="desconhecida"):
        verificar_pendencias(c, r, d, g)


def test_alinhamento_anos_e_reconciliacao(historico, curadoria):
    r = reconciliar(historico, curadoria[2])
    assert len(validar_alinhamento(historico, curadoria[2])) == 4
    assert (r.resultado == "conciliado").sum() == 24
    assert (r.resultado == "não comparável").sum() == 8
    diferente = r[r.comparavel_dashboard == "não"]
    assert diferente.diferenca_reais.isna().all()
    assert diferente.diferenca_reconciliada_reais.isna().all()
    ebit = r[r.indicador_release == "resultado_operacional"]
    assert (ebit.diferenca_reais.abs() > 1e6).all()
    assert (ebit.diferenca_reconciliada_reais.abs() <= 100000).all()
    deslocado = historico.copy()
    deslocado["receita_liquida"] = historico.receita_liquida.shift(1)
    with pytest.raises(ErroValidacaoDados, match="alinhamento"):
        validar_alinhamento(deslocado, curadoria[2])


def test_referencia_nao_aceita_escala_ou_medida_errada(curadoria):
    r = curadoria[2].copy()
    r.loc[0, "fator_reais"] = 1000
    with pytest.raises(ErroValidacaoDados, match="Escala"):
        validar_referencias(r)
    r.loc[0, "fator_reais"] = 1e6
    r.loc[0, "medida"] = "orgânica"
    with pytest.raises(ErroValidacaoDados, match="Medida diferente"):
        validar_referencias(r)


def test_camada1_igual_estagio3_sem_mutacao(historico, analise):
    antes = historico.copy(deep=True)
    recalculado = analise.calcular_endividamento(
        analise.calcular_rentabilidade(analise.calcular_liquidez(historico))
    )
    for ano in config.ANOS:
        dados = calcular_camada1(historico, ano).set_index("indicador")
        linha = recalculado[recalculado.ano_analise == ano].iloc[0]
        for campo in CAMPOS_CALCULADOS:
            sinal = -1 if campo in {"custo_vendas", "despesas_receitas_operacionais"} else 1
            assert dados.loc[campo, "valor"] == pytest.approx(sinal * linha[campo])
        if ano > 2022:
            a = historico[historico.ano_analise == ano].iloc[0]
            p = historico[historico.ano_analise == ano - 1].iloc[0]
            assert dados.loc["receita_liquida", "variacao_percentual"] == pytest.approx(
                (a.receita_liquida / p.receita_liquida - 1) * 100
            )
    pd.testing.assert_frame_equal(antes, historico)


def test_ponte_fecha_e_isola_razoes_contabeis(historico):
    for ano in [2023, 2024, 2025]:
        p = ponte_margem(historico, ano)
        assert p.contribuicao_pp.iloc[0] + p.contribuicao_pp.iloc[1:3].sum() == pytest.approx(
            p.contribuicao_pp.iloc[-1]
        )
        a, ant = (
            historico[historico.ano_analise == ano].iloc[0],
            historico[historico.ano_analise == ano - 1].iloc[0],
        )
        assert p.contribuicao_pp.iloc[1] == pytest.approx(a.margem_bruta - ant.margem_bruta)
    assert ponte_margem(historico, 2022).empty
    ruim = historico.copy()
    ruim.loc[ruim.ano_analise == 2025, "resultado_operacional"] += 10000
    with pytest.raises(ErroValidacaoDados, match="Identidade"):
        ponte_margem(ruim, 2025)


def test_camada1_sintetica_e_ausencias():
    base = pd.DataFrame(
        {
            "ano_analise": [2022, 2023],
            "receita_liquida": [100.0, 110.0],
            "custo_vendas": [-50.0, -66.0],
            "despesas_receitas_operacionais": [-20.0, -22.0],
            "lucro_liquido": [0.0, 4.0],
        }
    )
    out = calcular_camada1(base, 2023).set_index("indicador")
    assert out.loc["receita_liquida", "variacao"] == 10
    assert out.loc["custo_vendas", "variacao_percentual"] == 32
    assert "superior" in out.loc["custo_vendas", "texto"]
    assert np.isnan(out.loc["lucro_liquido", "variacao_percentual"])
    assert "zero" in out.loc["lucro_liquido", "motivo_nd"]
    assert "ausente" in out.loc["margem_bruta", "motivo_nd"]
    lacuna = base.copy()
    lacuna.loc[0, "ano_analise"] = 2021
    assert calcular_camada1(lacuna, 2023).variacao.isna().all()


def test_ausencia_de_linguagem_causal(historico):
    proibidas = [
        "devido a",
        "por causa de",
        "em razão de",
        "causado por",
        "impulsionado por",
        "provocado por",
    ]
    for ano in config.ANOS:
        texto = " ".join(calcular_camada1(historico, ano).texto).lower()
        assert not any(p in texto for p in proibidas)


def test_exports_incluem_fontes_e_nao_misturam_camadas(historico, curadoria):
    c, g, r, d = curadoria
    tabelas = painel.preparar_exportacoes(historico, [2024, 2025], c, g, r, d)
    csv, excel = painel.exportar_camadas(tabelas)
    volta = pd.read_csv(io.BytesIO(csv), sep=";", decimal=",")
    assert set(volta.camada) == set(tabelas)
    assert set(pd.ExcelFile(io.BytesIO(excel)).sheet_names) == set(tabelas)
    fontes = volta[volta.camada == "companhia"]
    verificadas = fontes[fontes.status == "verificado"]
    assert verificadas.documento.notna().all()
    assert verificadas.pagina.notna().all()
    assert verificadas.medida.notna().all()
    assert set(volta.ano.dropna()) == {2024, 2025}


def _app(codigo=""):
    return AppTest.from_string(
        "import pandas as pd\nimport config\nfrom dashboard_explicacoes import renderizar_explicacoes\n"
        "df = pd.read_csv(config.PASTA_DADOS_TRATADOS / 'indicadores_financeiros_ambev.csv')\n"
        + codigo
        + "\nrenderizar_explicacoes(df, 'Escuro')\n"
    ).run(timeout=30)


def test_render_todos_anos_comparacao_e_rascunhos():
    app = _app()
    assert not app.exception and not app.error
    assert any("Rascunho" in w.value for w in app.warning)
    for ano in [2023, 2024, 2025]:
        app.selectbox(key="exercicio_explicado").select(ano).run()
        assert not app.exception and not app.error
    app.selectbox(key="exercicio_explicado").select(2022).run()
    assert not app.exception
    assert any("Ponte de margem 2022: n/d" in i.value for i in app.info)
    app.toggle(key="comparar_explicacoes").set_value(True).run()
    assert not app.exception
    assert len(app.get("download_button")) == 2


def test_render_ano_todo_pendente(monkeypatch, curadoria):
    c, g, r, d = curadoria
    c = c.copy()
    c["status"] = "pendente"
    c["afirmacao_parafraseada"] = ""
    c["observacao"] = "Revisão oficial ainda pendente."
    monkeypatch.setattr(painel, "carregar_curadoria", lambda _: (c, g, r, d))
    app = _app()
    assert not app.exception and not app.error
    assert any("Explicação oficial ainda não registrada" in i.value for i in app.info)


def test_render_sem_dados_e_fonte_invalida(monkeypatch, curadoria):
    app = _app("df = df.iloc[0:0]")
    assert not app.exception
    assert any("Sem dados" in i.value for i in app.info)
    c, g, r, d = curadoria
    r = r.copy()
    r.loc[r.ano == 2025, "valor_release"] = 0
    monkeypatch.setattr(painel, "carregar_curadoria", lambda _: (c, g, r, d))
    app = _app()
    assert not app.exception
    assert any("bloqueada" in e.value for e in app.error)
