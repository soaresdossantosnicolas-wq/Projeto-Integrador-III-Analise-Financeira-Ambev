"""Backtest temporal, cenários e projeções exploratórias; não altera históricos do estágio 3."""

import argparse
import importlib.metadata
import hashlib
import json
import logging
import warnings

import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox

import config
from dados_preditivos import preparar_series, validar_referencia_oficial
from excecoes import ErroValidacaoDados
from modelos_preditivos import (
    ALVOS,
    aplicar_cenario,
    datas_futuras,
    montar_projecao,
    parametros_historicos,
    prever_bases,
    validar_historico,
)

log = logging.getLogger(__name__)


def janelas_temporais(n: int, minimo: int, horizonte: int, reserva: int) -> list[tuple]:
    """Desenvolvimento expansivo até a reserva; teste final em uma origem fixa e intocada."""
    corte = n - reserva
    if corte <= minimo:
        raise ErroValidacaoDados("Não há origens suficientes separadas do teste final.")
    janelas = [(fim, min(horizonte, corte - fim), "desenvolvimento") for fim in range(minimo, corte)]
    janelas.append((corte, min(horizonte, reserva), "teste_final"))
    return janelas


def calcular_metricas(grupo: pd.DataFrame) -> dict:
    """MAE, RMSE, sMAPE, MAPE e MASE com denominador calculado exclusivamente no treino."""
    erro = grupo.observado.to_numpy(dtype=float) - grupo.projetado.to_numpy(dtype=float)
    soma = np.abs(grupo.observado.to_numpy(dtype=float)) + np.abs(grupo.projetado.to_numpy(dtype=float))
    smape = np.divide(200 * np.abs(erro), soma, out=np.zeros_like(erro), where=soma != 0)
    nz = grupo.observado.to_numpy() != 0
    escalas = grupo.escala_mase.to_numpy()
    validas = np.isfinite(escalas) & (escalas > 0)
    mase = float(np.mean(np.abs(erro[validas]) / escalas[validas])) if validas.any() else np.nan
    return {
        "n": len(grupo),
        "mae": float(np.abs(erro).mean()),
        "rmse": float(np.sqrt(np.mean(erro**2))),
        "smape": float(smape.mean()),
        "mape": float((100 * np.abs(erro[nz] / grupo.observado.to_numpy()[nz])).mean())
        if nz.any()
        else np.nan,
        "mase": mase,
        "n_mape": int(nz.sum()),
        "n_mase": int(validas.sum()),
        "motivo_mase": ""
        if validas.all()
        else "Escala ingênua de treino nula ou indisponível em parte das origens",
    }


def executar_backtest(df: pd.DataFrame, frequencia: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Mesmo treino/teste/horizonte para cada modelo; nenhuma estatística consulta o bloco futuro."""
    h = config.PREDITIVA_HORIZONTES[frequencia]
    s = 1 if frequencia == "anual" else 4
    reserva = config.PREDITIVA_FINAL_ANOS[frequencia] * s
    janelas = janelas_temporais(len(df), config.PREDITIVA_MIN_TREINO[frequencia], h, reserva)
    linhas, falhas, ajustes = [], [], []
    for fim, passos, conjunto in janelas:
        treino = df.iloc[:fim].copy()
        teste = df.iloc[fim : fim + passos]
        if treino.data.max() >= teste.data.min():
            raise ErroValidacaoDados("Vazamento temporal detectado.")
        for modelo in config.PREDITIVA_MODELOS[frequencia]:
            try:
                bases = prever_bases(treino, passos, modelo, frequencia)
                matriz, ajustado = montar_projecao(treino, bases, frequencia)
                ajustes.append(
                    {
                        "frequencia": frequencia,
                        "modelo": modelo,
                        "origem": str(treino.data.max().date()),
                        "etapa": conjunto,
                        **ajustado,
                    }
                )
                for alvo in ALVOS:
                    y = treino[alvo].to_numpy()
                    escala = float(np.nanmean(np.abs(y[s:] - y[:-s]))) if len(y) > s else np.nan
                    for i, observado in enumerate(teste[alvo]):
                        if not np.isfinite(observado):
                            raise ErroValidacaoDados("Alvo de teste ausente.")
                        linhas.append(
                            {
                                "frequencia": frequencia,
                                "modelo": modelo,
                                "variavel": alvo,
                                "horizonte": i + 1,
                                "conjunto": conjunto,
                                "n_treino": fim,
                                "treino_fim": str(treino.data.max().date()),
                                "data_teste": str(teste.data.iloc[i].date()),
                                "observado": observado,
                                "projetado": float(matriz[alvo][0, i]),
                                "escala_mase": escala,
                            }
                        )
            except (ErroValidacaoDados, ValueError, FloatingPointError, np.linalg.LinAlgError) as erro:
                log.warning("Backtest %s/%s/%s: %s", frequencia, modelo, treino.data.max(), erro)
                falhas.append(
                    {
                        "frequencia": frequencia,
                        "modelo": modelo,
                        "origem": str(treino.data.max().date()),
                        "conjunto": conjunto,
                        "motivo": str(erro),
                    }
                )
    return (
        pd.DataFrame(linhas),
        pd.DataFrame(falhas, columns=["frequencia", "modelo", "origem", "conjunto", "motivo"]),
        pd.DataFrame(ajustes),
    )


def resumir_backtest(predicoes: pd.DataFrame) -> pd.DataFrame:
    """Métricas por variável, horizonte e conjunto; comparação com baselines no MESMO subconjunto."""
    chaves = ["frequencia", "modelo", "variavel", "horizonte", "conjunto"]
    linhas = [{**dict(zip(chaves, chave)), **calcular_metricas(g)} for chave, g in predicoes.groupby(chaves)]
    tabela = pd.DataFrame(linhas)
    origens = ["frequencia", "variavel", "horizonte", "conjunto", "treino_fim", "data_teste"]
    for baseline in ["ingenuo", "ingenuo_sazonal"]:
        base = predicoes.loc[predicoes.modelo.eq(baseline), origens + ["projetado"]].rename(
            columns={"projetado": "previsao_baseline"}
        )
        pares = predicoes.merge(base, on=origens, how="left", validate="many_to_one")
        pares["erro_baseline"] = (pares.observado - pares.previsao_baseline).abs()
        resumo = pares.groupby(chaves, as_index=False).agg(
            **{
                f"mae_{baseline}": ("erro_baseline", "mean"),
                f"n_pares_{baseline}": ("erro_baseline", "count"),
            }
        )
        tabela = tabela.merge(resumo, on=chaves, how="left", validate="one_to_one")
        tabela[f"supera_{baseline}"] = (
            tabela[f"n_pares_{baseline}"].eq(tabela.n)
            & tabela[f"mae_{baseline}"].notna()
            & (tabela.mae < tabela[f"mae_{baseline}"])
        )
    return tabela


def selecionar_modelos(metricas: pd.DataFrame) -> pd.DataFrame:
    """Seleção só no desenvolvimento; amostra anual pequena impõe baseline, sem declarar vencedor."""
    saida = []
    for frequencia in ("anual", "trimestral"):
        dev = metricas.loc[
            metricas.frequencia.eq(frequencia)
            & metricas.conjunto.eq("desenvolvimento")
            & metricas.variavel.isin(config.PREDITIVA_ALVOS)
        ]
        base = "ingenuo" if frequencia == "anual" else "ingenuo_sazonal"
        candidatos = []
        esperadas = dev.loc[dev.modelo.eq(base), "n"].sum()
        for modelo, grupo in dev.groupby("modelo"):
            if (
                grupo.n.sum() == esperadas
                and grupo.n.min() >= config.PREDITIVA_MIN_ERROS_SELECAO
                and grupo.mase.notna().all()
            ):
                candidatos.append((float(grupo.mase.mean()), modelo))
        if candidatos:
            escolhido = min(candidatos)[1]
            evidencia = "Seleção provisória por menor MASE médio no desenvolvimento; não é evidência de superioridade estatística."
        else:
            escolhido = base
            evidencia = "Evidência insuficiente para seleção: menos de cinco erros por alvo/horizonte; baseline mantido."
        final = metricas.loc[
            metricas.frequencia.eq(frequencia)
            & metricas.conjunto.eq("teste_final")
            & metricas.modelo.eq(escolhido)
            & metricas.variavel.isin(config.PREDITIVA_ALVOS)
        ]
        referencia = "mae_ingenuo" if frequencia == "anual" else "mae_ingenuo_sazonal"
        ganha = int((final.mae < final[referencia]).sum())
        saida.append(
            {
                "frequencia": frequencia,
                "modelo": escolhido,
                "regra": evidencia,
                "casos_finais_supera_baseline": ganha,
                "casos_finais": len(final),
                "conclusao_final": f"No teste reservado, supera o baseline em {ganha}/{len(final)} combinações alvo/horizonte. Não reescolher pelo teste.",
            }
        )
    return pd.DataFrame(saida)


def diagnosticar_residuos(predicoes: pd.DataFrame) -> pd.DataFrame:
    """Viés e autocorrelação descritivos; p-valor só com ao menos oito erros, sem validar normalidade."""
    linhas = []
    for chave, g in predicoes.groupby(["frequencia", "modelo", "variavel", "horizonte", "conjunto"]):
        erros = (g.observado - g.projetado).to_numpy()
        n = len(erros)
        acf = (
            float(np.corrcoef(erros[:-1], erros[1:])[0, 1])
            if n >= 4 and np.std(erros[:-1]) > 0 and np.std(erros[1:]) > 0
            else np.nan
        )
        p = np.nan
        if n >= 8 and np.std(erros) > 0:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                p = float(acorr_ljungbox(erros, lags=[1], return_df=True).lb_pvalue.iloc[0])
        linhas.append(
            {
                **dict(zip(["frequencia", "modelo", "variavel", "horizonte", "conjunto"], chave)),
                "n": n,
                "vies_observado_menos_previsto": float(erros.mean()),
                "autocorrelacao_lag1": acf,
                "ljung_box_p_exploratorio": p,
                "limite": "Poucos erros e horizontes sobrepostos; não comprova resíduos independentes. Estatísticas indefinidas permanecem n/d.",
            }
        )
    return pd.DataFrame(linhas)


def simular_faixa(
    treino: pd.DataFrame, bases: dict, frequencia: str, residuos: pd.DataFrame, rng: np.random.Generator
) -> tuple[dict, dict]:
    """Bootstrap exploratório conjunto de erros e regimes históricos, sem alegar cobertura futura."""
    n = config.PREDITIVA_SIMULACOES
    h = len(bases["receita_liquida"])
    estado = treino.iloc[rng.integers(0, len(treino), size=n)]
    historico = parametros_historicos(treino, frequencia)
    razoes = (
        historico["razoes"].iloc[rng.integers(0, len(historico["razoes"]), size=n)].reset_index(drop=True)
    )
    r = {k: np.tile(v, (n, 1)) for k, v in bases.items()}
    taxas = historico["crescimentos"]
    taxas_sorteadas = taxas[rng.integers(0, len(taxas), size=n)]
    mediana_taxas = float(np.median(taxas))
    for i in range(h):
        pool = residuos.loc[residuos.horizonte.eq(i + 1)]
        erros = pool.assign(erro=pool.observado - pool.projetado).pivot(
            index="treino_fim", columns="variavel", values="erro"
        )
        erros = erros.reindex(columns=config.PREDITIVA_ALVOS).dropna()
        if erros.empty:
            raise ErroValidacaoDados(
                "Sem resíduos fora da amostra para a faixa; projeção sem faixa não será exibida."
            )
        centrados = erros.to_numpy() - erros.mean().to_numpy()
        amostras = centrados[rng.integers(0, len(erros), size=n)]
        for j, alvo in enumerate(config.PREDITIVA_ALVOS):
            r[alvo][:, i] += amostras[:, j]
        fator_regime = ((1 + taxas_sorteadas) / (1 + mediana_taxas)) ** (
            (i + 1) / (4 if frequencia == "trimestral" else 1)
        )
        for alvo in config.PREDITIVA_ALVOS:
            r[alvo][:, i] *= fator_regime
        # Regimes de margens observados: amostragem conjunta, não limites de confiança.
        for alvo in ("resultado_operacional", "lucro_liquido"):
            margem_estado = estado[alvo].to_numpy() / estado.receita_liquida.to_numpy()
            centro = float((treino[alvo] / treino.receita_liquida).median())
            r[alvo][:, i] += r["receita_liquida"][:, i] * (margem_estado - centro)
    return montar_projecao(treino, r, frequencia, razoes=razoes)


def projetar_todos(historicos: dict, residuos: pd.DataFrame) -> tuple:
    """Reajusta até 2025; exporta cenários, faixas, saldos coerentes e ajustes de plausibilidade."""
    rng = np.random.default_rng(config.PREDITIVA_SEMENTE)
    linhas, saldos, premissas, ajustes = [], [], [], []
    for frequencia, treino in historicos.items():
        h = config.PREDITIVA_HORIZONTES[frequencia]
        datas = datas_futuras(treino, h, frequencia)
        for modelo in config.PREDITIVA_MODELOS[frequencia]:
            pool = residuos.loc[
                residuos.frequencia.eq(frequencia)
                & residuos.modelo.eq(modelo)
                & residuos.conjunto.eq("desenvolvimento")
                & residuos.variavel.isin(config.PREDITIVA_ALVOS)
            ]
            if pool.empty:
                log.warning("Sem desenvolvimento válido: %s/%s não será projetado.", frequencia, modelo)
                continue
            bases = prever_bases(treino, h, modelo, frequencia)
            for cenario in config.PREDITIVA_CENARIOS:
                pontos, p = aplicar_cenario(treino, bases, frequencia, cenario)
                central, ajuste = montar_projecao(treino, pontos, frequencia)
                caminhos, ajuste_sim = simular_faixa(treino, pontos, frequencia, pool, rng)
                ajustes.extend(
                    [
                        {
                            "frequencia": frequencia,
                            "modelo": modelo,
                            "cenario": cenario,
                            "etapa": "central",
                            **ajuste,
                        },
                        {
                            "frequencia": frequencia,
                            "modelo": modelo,
                            "cenario": cenario,
                            "etapa": "simulacao",
                            **ajuste_sim,
                        },
                    ]
                )
                sem_choque, _ = montar_projecao(treino, bases, frequencia)
                for i, data in enumerate(datas):
                    if frequencia == "anual":
                        anterior = (
                            treino.receita_liquida.iloc[-1]
                            if i == 0
                            else central["receita_liquida"][0, i - 1]
                        )
                        anterior_base = (
                            treino.receita_liquida.iloc[-1]
                            if i == 0
                            else sem_choque["receita_liquida"][0, i - 1]
                        )
                    else:
                        anterior = anterior_base = treino.receita_liquida.iloc[-4 + i]
                    efetivos = [
                        (
                            "crescimento_receita_efetivo",
                            central["receita_liquida"][0, i] / anterior - 1,
                            sem_choque["receita_liquida"][0, i] / anterior_base - 1,
                        ),
                        (
                            "margem_operacional_efetiva",
                            central["margem_operacional"][0, i] / 100,
                            sem_choque["margem_operacional"][0, i] / 100,
                        ),
                        (
                            "margem_liquida_efetiva",
                            central["margem_liquida"][0, i] / 100,
                            sem_choque["margem_liquida"][0, i] / 100,
                        ),
                    ]
                    for campo, valor, referencia in efetivos:
                        p.append(
                            {
                                "cenario": cenario,
                                "parametro": campo,
                                "valor": valor,
                                "referencia_base": referencia,
                                "quantil": np.nan,
                                "origem": "resultado efetivo após modelo, choque relativo e limites; não é a taxa histórica bruta",
                                "treino_fim": str(treino.data.max().date()),
                                "n_observacoes": np.nan,
                                "trimestre": data.quarter if frequencia == "trimestral" else 0,
                                "horizonte": i + 1,
                            }
                        )
                premissas.extend([{**r, "frequencia": frequencia, "modelo": modelo} for r in p])
                for i, data in enumerate(datas):
                    for alvo in ALVOS:
                        baixo, alto = np.quantile(caminhos[alvo][:, i], config.PREDITIVA_QUANTIS_FAIXA)
                        valor = central[alvo][0, i]
                        linhas.append(
                            {
                                "frequencia": frequencia,
                                "modelo": modelo,
                                "cenario": cenario,
                                "variavel": alvo,
                                "data": str(data.date()),
                                "horizonte": i + 1,
                                "valor": valor,
                                "inferior": min(baixo, valor),
                                "superior": max(alto, valor),
                                "tipo_faixa": "Faixa exploratória: quantis 10–90% de simulações; cobertura futura não validada",
                                "n_residuos_horizonte": pool.loc[
                                    pool.horizonte.eq(i + 1), "treino_fim"
                                ].nunique(),
                            }
                        )
                    saldos.append(
                        {
                            "frequencia": frequencia,
                            "modelo": modelo,
                            "cenario": cenario,
                            "data": str(data.date()),
                            **{
                                c: central[c][0, i]
                                for c in [
                                    "receita_liquida",
                                    "resultado_operacional",
                                    "lucro_liquido",
                                    "ativo_total",
                                    "ativo_circulante",
                                    "ativo_nao_circulante",
                                    "passivo_circulante",
                                    "passivo_nao_circulante",
                                    "patrimonio_liquido",
                                ]
                            },
                        }
                    )
    return pd.DataFrame(linhas), pd.DataFrame(saldos), pd.DataFrame(premissas), pd.DataFrame(ajustes)


def analisar_sensibilidade(historicos: dict) -> pd.DataFrame:
    """Varia um direcionador por vez entre quartis históricos, mantendo os demais na base."""
    linhas = []
    for f, treino in historicos.items():
        h = config.PREDITIVA_HORIZONTES[f]
        bases = prever_bases(treino, h, "direcionadores", f)
        ponto, _ = aplicar_cenario(treino, bases, f, "base", overrides={})
        referencia, _ = montar_projecao(treino, ponto, f)
        for campo in ("crescimento", "margem_operacional", "margem_liquida"):
            for cenario in ("pessimista", "otimista"):
                ponto, _ = aplicar_cenario(treino, bases, f, cenario, overrides={}, somente_parametro=campo)
                sens, _ = montar_projecao(treino, ponto, f)
                for alvo in ALVOS:
                    for i, data in enumerate(datas_futuras(treino, h, f)):
                        linhas.append(
                            {
                                "frequencia": f,
                                "modelo": "direcionadores",
                                "premissa": campo,
                                "choque": config.PREDITIVA_CENARIOS[cenario],
                                "variavel": alvo,
                                "data": str(data.date()),
                                "valor_base": referencia[alvo][0, i],
                                "valor_sensibilidade": sens[alvo][0, i],
                                "diferenca": sens[alvo][0, i] - referencia[alvo][0, i],
                            }
                        )
    return pd.DataFrame(linhas)


def resumir_modelos(metricas: pd.DataFrame) -> pd.DataFrame:
    """Resumo normalizado, sem substituir a tabela por alvo/horizonte nem escolher pelo teste."""
    primarias = metricas.loc[metricas.variavel.isin(config.PREDITIVA_ALVOS)]
    return primarias.groupby(["frequencia", "modelo", "conjunto"], as_index=False).agg(
        mase_medio=("mase", "mean"), mae_medio_reais=("mae", "mean"), n_min_por_alvo_horizonte=("n", "min")
    )


def conferir_projecoes_base(projecoes: pd.DataFrame, selecao: pd.DataFrame) -> pd.DataFrame:
    """Registra conciliação do cenário base padrão; alternativas não são reconciliadas por imposição."""
    modelos = selecao.set_index("frequencia").modelo
    a = projecoes.loc[
        projecoes.frequencia.eq("anual")
        & projecoes.modelo.eq(modelos["anual"])
        & projecoes.cenario.eq("base")
    ]
    q = (
        projecoes.loc[
            projecoes.frequencia.eq("trimestral")
            & projecoes.modelo.eq(modelos["trimestral"])
            & projecoes.cenario.eq("base")
            & projecoes.variavel.isin(config.PREDITIVA_ALVOS)
        ]
        .groupby("variavel")
        .valor.sum()
    )
    linhas = []
    for variavel, valor in q.items():
        anual = a.loc[a.data.eq("2026-12-31") & a.variavel.eq(variavel), "valor"].iloc[0]
        linhas.append(
            {
                "variavel": variavel,
                "ano": 2026,
                "cenario": "base",
                "modelo_anual": modelos["anual"],
                "modelo_trimestral": modelos["trimestral"],
                "valor_anual": anual,
                "soma_trimestres": valor,
                "diferenca": valor - anual,
                "observacao": "Conferência do cenário base dos modelos padrão; demais modelos/cenários são exercícios independentes por frequência.",
            }
        )
    return pd.DataFrame(linhas)


def main() -> None:
    """Executa estágio opcional com dados auditados e parâmetros fixos, sem modificar a análise histórica."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preparar-dados", action="store_true", help="baixar/validar DFPs e ITRs antes do backtest"
    )
    parser.add_argument("--offline", action="store_true", help="proíbe downloads; exige arquivos locais")
    args = parser.parse_args()
    pasta = config.PASTA_PREDITIVA
    pasta.mkdir(parents=True, exist_ok=True)
    original = config.PASTA_DADOS_TRATADOS / "indicadores_financeiros_ambev.csv"
    hash_antes = hashlib.sha256(original.read_bytes()).hexdigest()
    if args.preparar_dados:
        preparar_series(offline=args.offline)
    historicos = {
        f: validar_historico(pd.read_csv(pasta / f"historico_{f}.csv"), f, config.PREDITIVA_MIN_TREINO[f])
        for f in ["anual", "trimestral"]
    }
    for f, df in historicos.items():
        if df.data.max() > pd.Timestamp(config.PREDITIVA_DATA_CORTE):
            raise ErroValidacaoDados("Informação posterior ao corte declarado.")
    validar_referencia_oficial(historicos["anual"])
    preds, falhas, plausibilidade = [], [], []
    for f, df in historicos.items():
        pred, falha, ajuste = executar_backtest(df, f)
        preds.append(pred)
        falhas.append(falha)
        plausibilidade.append(ajuste)
    pred = pd.concat(preds, ignore_index=True)
    metricas = resumir_backtest(pred)
    selecao = selecionar_modelos(metricas)
    proj, saldos, premissas, ajustes = projetar_todos(historicos, pred)
    for nome, tabela in [
        ("backtest", pred),
        ("resumo_modelos", resumir_modelos(metricas)),
        ("conciliacao_projecoes_base", conferir_projecoes_base(proj, selecao)),
        ("metricas", metricas),
        ("selecao", selecao),
        ("projecoes", proj),
        ("balancos_projetados", saldos),
        ("premissas_cenarios", premissas),
        ("diagnostico_residuos", diagnosticar_residuos(pred)),
        ("sensibilidade", analisar_sensibilidade(historicos)),
        ("falhas_modelos", pd.concat(falhas, ignore_index=True)),
        ("ajustes_plausibilidade", pd.concat(plausibilidade + [ajustes], ignore_index=True)),
    ]:
        tabela.to_csv(pasta / f"{nome}.csv", index=False)
    descartados = [
        {
            "modelo": "ARIMA/SARIMA",
            "motivo": "Corte comparável tem 28 trimestres e 7 anos. Política conservadora exige >=32 pontos de treino mais reserva para ordens ARIMA e >=20 anuais; não há desenvolvimento suficiente para comparação comum.",
        },
        {
            "modelo": "Holt anual",
            "motivo": "Somente 7 observações anuais; abaixo do mínimo operacional de 8 para esta família no projeto.",
        },
        {
            "modelo": "Random forest, boosting e redes neurais",
            "motivo": "Amostra pequena, sem conjunto independente suficiente nem demonstração de ganho frente aos baselines. Não implementados.",
        },
        {
            "modelo": "Variáveis BCB e preços de ações",
            "motivo": "Não incluídos: sem demonstração de ganho fora da amostra; preços de ações estão fora do escopo.",
        },
    ]
    pd.DataFrame(descartados).to_csv(pasta / "modelos_descartados.csv", index=False)
    metadata = {
        "data_corte": config.PREDITIVA_DATA_CORTE,
        "autores": config.AUTORES,
        "semente": config.PREDITIVA_SEMENTE,
        "n_simulacoes": config.PREDITIVA_SIMULACOES,
        "n_observacoes": {f: len(df) for f, df in historicos.items()},
        "teste_final": {
            "anual": "2024–2025; origem fixa em 2023",
            "trimestral": "2025T1–T4; origem fixa em 2024T4",
        },
        "incerteza": "Quantis de simulações exploratórias; não são intervalos calibrados com garantia de cobertura.",
        "evidencia": "Evidência insuficiente para precisão robusta, especialmente 2027 e indicadores patrimoniais.",
        "vintages": "Backtest retrospectivo com arquivos atuais e datas contábeis; não comprova disponibilidade em tempo real na origem. Divulgação ocorre após o encerramento do período.",
        "sha256_historico_estagio3": hash_antes,
    }
    metadata["versoes_execucao"] = {
        p: importlib.metadata.version(p) for p in ["numpy", "pandas", "scipy", "statsmodels"]
    }
    metadata["politicas_amostra"] = {
        "janelas": config.PREDITIVA_MIN_TREINO,
        "modelos": config.PREDITIVA_MIN_MODELOS,
        "erros_selecao": config.PREDITIVA_MIN_ERROS_SELECAO,
    }
    metadata["sha256_arquivos"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in pasta.glob("*.csv")
    }
    (pasta / "metadados.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    if hashlib.sha256(original.read_bytes()).hexdigest() != hash_antes:
        raise ErroValidacaoDados("O estágio 3 foi alterado indevidamente.")
    log.info(
        "Modelagem concluída. %d previsões de backtest; %d projeções com faixas. Seleção: %s",
        len(pred),
        len(proj),
        selecao[["frequencia", "modelo"]].to_dict("records"),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    main()
