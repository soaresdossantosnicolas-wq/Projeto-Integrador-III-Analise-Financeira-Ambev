"""Contratos preditivos com dados sintéticos; nenhuma chamada de rede."""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import config
from dados_preditivos import derivar_indicadores, desagregar_trimestres, preparar_itr
from excecoes import ErroValidacaoDados
from modelos_preditivos import (
    aplicar_cenario,
    montar_projecao,
    parametros_historicos,
    prever_bases,
    prever_univariada,
    validar_historico,
)

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def etapa5():
    spec = importlib.util.spec_from_file_location("etapa5", RAIZ / "code/05_modelagem_preditiva.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def sintetico(n=28, frequencia="trimestral"):
    periodos = pd.period_range(
        "2019Q1" if frequencia == "trimestral" else "2019",
        periods=n,
        freq="Q" if frequencia == "trimestral" else "Y",
    )
    t = np.arange(n)
    receita = 1000 + 30 * t + (np.array([-40, 0, 50, 100])[t % 4] if frequencia == "trimestral" else 0)
    ativo = receita * (8 if frequencia == "trimestral" else 2)
    df = pd.DataFrame(
        {
            "data": periodos.to_timestamp(how="end").normalize(),
            "receita_liquida": receita,
            "resultado_operacional": receita * 0.25,
            "lucro_liquido": receita * 0.15,
            "ativo_total": ativo,
            "ativo_circulante": ativo * 0.35,
            "ativo_nao_circulante": ativo * 0.65,
            "passivo_circulante": ativo * 0.25,
            "passivo_nao_circulante": ativo * 0.15,
            "patrimonio_liquido": ativo * 0.60,
        }
    )
    return derivar_indicadores(df, frequencia)


def test_tendencia_conhecida_e_baselines():
    y = np.arange(10) * 25.0 + 100
    esperado = [350, 375, 400]
    np.testing.assert_allclose(prever_univariada(y, 3, "tendencia", 1), esperado)
    np.testing.assert_allclose(prever_univariada(y, 3, "drift", 1), esperado)
    np.testing.assert_allclose(prever_univariada(y, 3, "ingenuo", 1), [325] * 3)
    np.testing.assert_allclose(
        prever_univariada(np.array([10, 20, 30, 40]), 6, "ingenuo_sazonal", 4), [10, 20, 30, 40, 10, 20]
    )


def test_q4_derivado_sem_somar_balancos():
    cum = pd.DataFrame({"trimestre": [3, 1, 2], "receita_liquida": [400, 100, 250]})
    r = desagregar_trimestres(cum, pd.Series({"receita_liquida": 580}), ["receita_liquida"])
    assert r.receita_liquida.tolist() == [100, 150, 150, 180]
    assert r.receita_liquida.sum() == 580
    with pytest.raises(ErroValidacaoDados):
        desagregar_trimestres(cum.iloc[:2], pd.Series({"receita_liquida": 580}), ["receita_liquida"])


def test_itr_nao_confunde_trimestre_e_acumulado(cvm_dre):
    acumulado = cvm_dre.loc[cvm_dre.ORDEM_EXERC.eq("ÚLTIMO")].copy()
    acumulado["DT_REFER"] = "2025-06-30"
    acumulado["DT_FIM_EXERC"] = "2025-06-30"
    direto = acumulado.copy()
    direto["DT_INI_EXERC"] = "2025-04-01"
    direto["VL_CONTA"] *= 0.4
    todos = pd.concat([acumulado, direto], ignore_index=True)
    a = preparar_itr(todos, 2025, 2, "DRE")
    q = preparar_itr(todos, 2025, 2, "DRE", acumulado=False)
    assert a.loc[a.CD_CONTA.eq("3.01"), "VL_CONTA"].iloc[0] == 1000000
    assert q.loc[q.CD_CONTA.eq("3.01"), "VL_CONTA"].iloc[0] == 400000


def test_janelas_e_teste_final_intocado(etapa5):
    j = etapa5.janelas_temporais(28, 16, 4, 4)
    assert j[-1] == (24, 4, "teste_final")
    assert all(fim + h <= 24 for fim, h, tipo in j if tipo == "desenvolvimento")
    with pytest.raises(ErroValidacaoDados, match="origens"):
        etapa5.janelas_temporais(4, 3, 2, 2)


def test_futuro_nao_altera_previsao_do_passado(etapa5, monkeypatch):
    monkeypatch.setitem(
        config.PREDITIVA_MODELOS, "trimestral", ["ingenuo", "ingenuo_sazonal", "direcionadores"]
    )
    a = sintetico()
    p, _, _ = etapa5.executar_backtest(a, "trimestral")
    b = a.copy()
    for campo in config.PREDITIVA_ALVOS:
        b.loc[24:, campo] *= 1.3
    alterado, _, _ = etapa5.executar_backtest(b, "trimestral")
    colunas = ["modelo", "variavel", "horizonte", "treino_fim", "projetado", "escala_mase"]
    pd.testing.assert_frame_equal(
        p.loc[p.conjunto.eq("desenvolvimento"), colunas].reset_index(drop=True),
        alterado.loc[alterado.conjunto.eq("desenvolvimento"), colunas].reset_index(drop=True),
    )
    # Mesmo as previsões de teste final são feitas na origem fixa anterior ao bloco.
    np.testing.assert_allclose(
        p.loc[p.conjunto.eq("teste_final"), "projetado"],
        alterado.loc[alterado.conjunto.eq("teste_final"), "projetado"],
    )
    assert (pd.to_datetime(p.treino_fim) < pd.to_datetime(p.data_teste)).all()


def test_selecao_nao_usa_erros_do_teste_final(etapa5, monkeypatch):
    monkeypatch.setitem(config.PREDITIVA_MODELOS, "trimestral", ["ingenuo", "ingenuo_sazonal"])
    monkeypatch.setitem(config.PREDITIVA_MODELOS, "anual", ["ingenuo", "drift"])
    quadros = []
    for f, n in [("anual", 7), ("trimestral", 28)]:
        p, _, _ = etapa5.executar_backtest(sintetico(n, f), f)
        quadros.append(p)
    m = etapa5.resumir_backtest(pd.concat(quadros))
    primeira = etapa5.selecionar_modelos(m)
    alterada = m.copy()
    mask = alterada.conjunto.eq("teste_final")
    alterada.loc[mask, ["mae", "mase"]] = 1e12
    segunda = etapa5.selecionar_modelos(alterada)
    assert primeira.modelo.tolist() == segunda.modelo.tolist()
    assert primeira.loc[primeira.frequencia.eq("anual"), "modelo"].iloc[0] == "ingenuo"


def test_identidade_e_indicadores_em_cada_caminho():
    treino = validar_historico(sintetico(), "trimestral", 16)
    bases = prever_bases(treino, 4, "direcionadores", "trimestral")
    p, _ = montar_projecao(treino, bases, "trimestral")
    np.testing.assert_allclose(
        p["ativo_total"], p["passivo_circulante"] + p["passivo_nao_circulante"] + p["patrimonio_liquido"]
    )
    np.testing.assert_allclose(
        p["endividamento_geral"],
        (p["passivo_circulante"] + p["passivo_nao_circulante"]) / p["ativo_total"] * 100,
    )
    np.testing.assert_allclose(p["liquidez_corrente"], p["ativo_circulante"] / p["passivo_circulante"])
    assert (p["receita_liquida"] > 0).all()


def test_poucos_dados_explicitos_e_baseline_disponivel(caplog):
    with pytest.raises(ErroValidacaoDados, match="insuficientes"):
        prever_univariada(np.array([100, 110, 120, 130]), 2, "holt", 1)
    assert "Use o baseline" in caplog.text
    np.testing.assert_array_equal(
        prever_univariada(np.array([100, 110, 120, 130]), 2, "ingenuo", 1), [130, 130]
    )


def test_premissas_so_treino_override_exige_fonte():
    treino = sintetico(7, "anual")
    params = parametros_historicos(treino, "anual")
    assert params["n_crescimentos"] == 6
    bases = prever_bases(treino, 2, "ingenuo", "anual")
    with pytest.raises(ErroValidacaoDados, match="justificativa"):
        aplicar_cenario(treino, bases, "anual", "base", overrides={"crescimento": {"valor": 0.4}})
    ponto, premissas = aplicar_cenario(treino, bases, "anual", "otimista")
    assert all(r["treino_fim"] == str(treino.data.max().date()) for r in premissas)
    assert ponto["receita_liquida"][0] > bases["receita_liquida"][0]


def test_metricas_zero_e_escala_so_treino(etapa5):
    g = pd.DataFrame({"observado": [100.0, 0.0], "projetado": [90.0, 0.0], "escala_mase": [10.0, 10.0]})
    m = etapa5.calcular_metricas(g)
    assert m["mae"] == 5
    assert m["rmse"] == pytest.approx(np.sqrt(50))
    assert m["mape"] == 10
    assert m["mase"] == 0.5
    assert m["n_mape"] == 1


def test_saidas_publicadas_e_intervalos():
    p = config.PASTA_PREDITIVA
    proj = pd.read_csv(p / "projecoes.csv")
    assert np.isfinite(proj[["valor", "inferior", "superior"]]).all().all()
    assert (proj.inferior <= proj.valor).all() and (proj.valor <= proj.superior).all()
    assert set(proj.loc[proj.frequencia.eq("anual"), "data"]) == {"2026-12-31", "2027-12-31"}
    assert set(proj.loc[proj.frequencia.eq("trimestral"), "data"]) == {
        "2026-03-31",
        "2026-06-30",
        "2026-09-30",
        "2026-12-31",
    }
    saldos = pd.read_csv(p / "balancos_projetados.csv")
    np.testing.assert_allclose(
        saldos.ativo_total,
        saldos.passivo_circulante + saldos.passivo_nao_circulante + saldos.patrimonio_liquido,
        rtol=1e-12,
    )


def test_bootstrap_reprodutivel_e_balanco_por_simulacao(etapa5, monkeypatch):
    monkeypatch.setattr(config, "PREDITIVA_SIMULACOES", 50)
    monkeypatch.setitem(config.PREDITIVA_MODELOS, "anual", ["ingenuo"])
    treino = sintetico(7, "anual")
    residuos, _, _ = etapa5.executar_backtest(treino, "anual")
    residuos = residuos.loc[
        residuos.conjunto.eq("desenvolvimento") & residuos.variavel.isin(config.PREDITIVA_ALVOS)
    ]
    bases = prever_bases(treino, 2, "ingenuo", "anual")
    a, _ = etapa5.simular_faixa(treino, bases, "anual", residuos, np.random.default_rng(42))
    b, _ = etapa5.simular_faixa(treino, bases, "anual", residuos, np.random.default_rng(42))
    for campo in a:
        np.testing.assert_array_equal(a[campo], b[campo])
    np.testing.assert_allclose(
        a["ativo_total"], a["passivo_circulante"] + a["passivo_nao_circulante"] + a["patrimonio_liquido"]
    )


def test_baseline_comparado_somente_nas_mesmas_origens(etapa5):
    linhas = []
    for origem, erro in [("2021-12-31", 10), ("2022-12-31", 1000)]:
        linhas.append(
            dict(
                frequencia="anual",
                modelo="ingenuo",
                variavel="receita_liquida",
                horizonte=1,
                conjunto="desenvolvimento",
                treino_fim=origem,
                data_teste=str(int(origem[:4]) + 1) + "-12-31",
                observado=2000,
                projetado=2000 - erro,
                escala_mase=100,
            )
        )
    outro = linhas[0].copy()
    outro.update(modelo="tendencia", projetado=1980)
    m = etapa5.resumir_backtest(pd.DataFrame(linhas + [outro]))
    r = m.loc[m.modelo.eq("tendencia")].iloc[0]
    assert r.mae == 20
    assert r.mae_ingenuo == 10  # não a média de 10 e 1000 de origens diferentes
    assert not r.supera_ingenuo
