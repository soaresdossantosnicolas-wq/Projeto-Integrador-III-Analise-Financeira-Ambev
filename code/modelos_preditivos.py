"""Previsores simples e projeções coerentes; todas as estatísticas usam somente o treino recebido."""

import logging
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing, Holt

import config
from excecoes import ErroValidacaoDados

log = logging.getLogger(__name__)
ALVOS = config.PREDITIVA_ALVOS + config.PREDITIVA_INDICADORES


def validar_historico(df: pd.DataFrame, frequencia: str, minimo: int = 3) -> pd.DataFrame:
    """Exige calendário regular, bases financeiras finitas e identidade contábil."""
    df = df.copy().sort_values("data").reset_index(drop=True)
    df["data"] = pd.to_datetime(df.data)
    if len(df) < minimo:
        raise ErroValidacaoDados(f"Série {frequencia} insuficiente: {len(df)} observações; mínimo {minimo}.")
    periodo = df.data.dt.to_period("Y" if frequencia == "anual" else "Q")
    if periodo.duplicated().any() or (np.diff(periodo.astype("int64")) != 1).any():
        raise ErroValidacaoDados("Série com períodos duplicados ou lacunas; imputação proibida.")
    if not df.data.eq(periodo.dt.to_timestamp(how="end").dt.normalize()).all():
        raise ErroValidacaoDados("Datas não correspondem ao encerramento anual/trimestral.")
    bases = config.PREDITIVA_ALVOS + [
        "ativo_total",
        "ativo_circulante",
        "passivo_circulante",
        "passivo_nao_circulante",
        "patrimonio_liquido",
    ]
    if not np.isfinite(df[bases].to_numpy(dtype=float)).all() or (df.receita_liquida <= 0).any():
        raise ErroValidacaoDados("Bases financeiras inválidas para projetar.")
    if (
        (df.ativo_total <= 0).any()
        or (df.patrimonio_liquido <= 0).any()
        or (df.passivo_circulante <= 0).any()
    ):
        raise ErroValidacaoDados("Ativo, PL e PC devem ser positivos para este contrato de projeção.")
    soma = df.passivo_circulante + df.passivo_nao_circulante + df.patrimonio_liquido
    if not np.allclose(soma, df.ativo_total, rtol=1e-6, atol=4000):
        raise ErroValidacaoDados("Identidade contábil inválida no treino.")
    return df


def datas_futuras(treino: pd.DataFrame, h: int, frequencia: str) -> pd.DatetimeIndex:
    """Cria períodos posteriores ao último treino, sem consultar o teste."""
    freq = "Y" if frequencia == "anual" else "Q"
    ultimo = pd.Period(pd.Timestamp(treino.data.iloc[-1]), freq=freq)
    return pd.PeriodIndex([ultimo + i for i in range(1, h + 1)]).to_timestamp(how="end").normalize()


def parametros_historicos(treino: pd.DataFrame, frequencia: str, quantil: float = 0.5) -> dict:
    """Premissas de receita, margens e balanço calculadas apenas com observações disponíveis."""
    receita = treino.receita_liquida
    if frequencia == "trimestral":
        completos = treino.groupby(treino.data.dt.year).filter(lambda g: len(g) == 4)
        receita_anual = completos.groupby(completos.data.dt.year).receita_liquida.sum()
        ttm = receita.rolling(4).sum()
    else:
        receita_anual = receita
        ttm = receita
    crescimentos = receita_anual.pct_change(fill_method=None).dropna()
    if crescimentos.empty:
        raise ErroValidacaoDados("Sem variações anuais completas para as premissas.")
    razoes = pd.DataFrame(
        {
            "ativo_receita": treino.ativo_total / ttm,
            "ac_ativo": treino.ativo_circulante / treino.ativo_total,
            "pc_ativo": treino.passivo_circulante / treino.ativo_total,
            "pnc_ativo": treino.passivo_nao_circulante / treino.ativo_total,
        }
    ).dropna()
    if razoes.empty:
        raise ErroValidacaoDados("Sem razões patrimoniais observadas suficientes.")
    return {
        "crescimento": float(crescimentos.quantile(quantil)),
        "margem_operacional": float((treino.resultado_operacional / receita).quantile(quantil)),
        "margem_liquida": float((treino.lucro_liquido / receita).quantile(quantil)),
        "razoes": razoes,
        "n_crescimentos": len(crescimentos),
        "crescimentos": crescimentos.to_numpy(),
    }


def reverter_margem(valores: np.ndarray, horizonte: int) -> np.ndarray:
    """Reversão AR(1) à média, com persistência estimada e limitada a [0,1], sem extrapolar explosivamente."""
    mu = float(np.mean(valores))
    x = valores[:-1] - mu
    phi = float(np.dot(x, valores[1:] - mu) / np.dot(x, x)) if np.dot(x, x) > 1e-12 else 0.0
    phi = np.clip(phi, 0, 1)
    return np.array([mu + phi**i * (valores[-1] - mu) for i in range(1, horizonte + 1)])


def prever_univariada(y: np.ndarray, h: int, modelo: str, sazonalidade: int) -> np.ndarray:
    """Ajusta especificações fixas; sem busca de ordens nem seleção pelo teste final."""
    y = np.asarray(y, dtype=float)
    minimo = config.PREDITIVA_MIN_MODELOS.get(modelo, 2)
    if len(y) < minimo:
        log.warning(
            "%s: %d observações; mínimo operacional %d. Use o baseline em vez de forçar ajuste.",
            modelo,
            len(y),
            minimo,
        )
        raise ErroValidacaoDados(f"{modelo}: dados insuficientes; baseline é a alternativa documentada.")
    if not np.isfinite(y).all():
        raise ErroValidacaoDados("Série-alvo não finita.")
    if modelo == "ingenuo":
        return np.repeat(y[-1], h)
    if modelo == "ingenuo_sazonal":
        if len(y) < sazonalidade:
            raise ErroValidacaoDados("Sem ciclo sazonal completo.")
        return np.resize(y[-sazonalidade:], h)
    if modelo == "media_movel":
        return np.repeat(y[-min(len(y), sazonalidade if sazonalidade > 1 else 3) :].mean(), h)
    if modelo == "drift":
        return y[-1] + np.arange(1, h + 1) * (y[-1] - y[0]) / (len(y) - 1)
    if modelo == "crescimento_medio":
        if (y[:-sazonalidade] <= 0).any():
            raise ErroValidacaoDados("Crescimento multiplicativo não admite base não positiva.")
        taxas = y[sazonalidade:] / y[:-sazonalidade] - 1
        if len(taxas) == 0:
            raise ErroValidacaoDados("Sem taxa observada para crescimento médio.")
        taxa = float(taxas.mean())
        if taxa <= -1:
            raise ErroValidacaoDados("Taxa média inviável para extrapolação.")
        if sazonalidade == 1:
            return y[-1] * (1 + taxa) ** np.arange(1, h + 1)
        return np.array(
            [y[-sazonalidade + (i % sazonalidade)] * (1 + taxa) ** (i // sazonalidade + 1) for i in range(h)]
        )
    escala = max(float(np.abs(y).mean()), 1)
    z = y / escala
    if modelo in ("tendencia", "tendencia_sazonal"):
        t = np.arange(len(y))
        futuro = np.arange(len(y), len(y) + h)
        x, xf = [np.ones(len(y)), t], [np.ones(h), futuro]
        if modelo == "tendencia_sazonal":
            for estacao in range(1, sazonalidade):
                x.append((t % sazonalidade == estacao).astype(float))
                xf.append((futuro % sazonalidade == estacao).astype(float))
        beta = np.linalg.lstsq(np.array(x).T, z, rcond=None)[0]
        return np.array(xf).T @ beta * escala
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        if modelo == "holt":
            ajustado = Holt(z, damped_trend=True, initialization_method="estimated").fit(optimized=True)
        elif modelo == "holt_winters":
            ajustado = ExponentialSmoothing(
                z,
                trend="add",
                damped_trend=True,
                seasonal="add",
                seasonal_periods=sazonalidade,
                initialization_method="estimated",
            ).fit(optimized=True)
        else:
            raise ErroValidacaoDados(f"Modelo desconhecido: {modelo}.")
        for aviso in avisos:
            log.warning("%s: %s", modelo, aviso.message)
        convergiu = (
            ajustado.mle_retvals.get("success", True) if isinstance(ajustado.mle_retvals, dict) else True
        )
        if not convergiu:
            raise ErroValidacaoDados(f"{modelo}: otimizador não convergiu; sem fallback silencioso.")
        return np.asarray(ajustado.forecast(h)) * escala


def prever_bases(treino: pd.DataFrame, h: int, modelo: str, frequencia: str) -> dict[str, np.ndarray]:
    """Receita e dois resultados; direcionadores revertem margens em vez de extrapolar indicadores isolados."""
    s = 1 if frequencia == "anual" else 4
    if modelo != "direcionadores":
        return {c: prever_univariada(treino[c].to_numpy(), h, modelo, s) for c in config.PREDITIVA_ALVOS}
    params = parametros_historicos(treino, frequencia)
    if s == 1:
        receitas = treino.receita_liquida.iloc[-1] * (1 + params["crescimento"]) ** np.arange(1, h + 1)
        op = reverter_margem((treino.resultado_operacional / treino.receita_liquida).to_numpy(), h)
        liq = reverter_margem((treino.lucro_liquido / treino.receita_liquida).to_numpy(), h)
    else:
        receitas = np.array(
            [
                treino.receita_liquida.iloc[-s + i % s] * (1 + params["crescimento"]) ** (i // s + 1)
                for i in range(h)
            ]
        )
        op, liq = [], []
        futuros = datas_futuras(treino, h, frequencia)
        for i, data in enumerate(futuros):
            por_quarter = treino.loc[treino.data.dt.quarter == data.quarter]
            op.append(
                reverter_margem(
                    (por_quarter.resultado_operacional / por_quarter.receita_liquida).to_numpy(), i // s + 1
                )[-1]
            )
            liq.append(
                reverter_margem(
                    (por_quarter.lucro_liquido / por_quarter.receita_liquida).to_numpy(), i // s + 1
                )[-1]
            )
        op, liq = np.array(op), np.array(liq)
    return {
        "receita_liquida": receitas,
        "resultado_operacional": receitas * op,
        "lucro_liquido": receitas * liq,
    }


def montar_projecao(
    treino: pd.DataFrame, bases: dict, frequencia: str, *, razoes: pd.DataFrame | None = None
) -> tuple[dict, dict]:
    """Deriva balanço/indicadores por caminho, preservando Ativo=PC+PNC+PL em cada simulação."""
    r = {k: np.atleast_2d(np.asarray(v, dtype=float)).copy() for k, v in bases.items()}
    n, h = r["receita_liquida"].shape
    ajustes = {"receita_nao_positiva": int((r["receita_liquida"] <= 0).sum()), "margens_limitadas": 0}
    r["receita_liquida"] = np.where(
        r["receita_liquida"] > 0, r["receita_liquida"], treino.receita_liquida.min()
    )
    for alvo in ("resultado_operacional", "lucro_liquido"):
        historico = treino[alvo] / treino.receita_liquida
        margem = r[alvo] / r["receita_liquida"]
        limitado = np.clip(margem, historico.min(), historico.max())
        ajustes["margens_limitadas"] += int(np.sum(np.abs(margem - limitado) > 1e-12))
        r[alvo] = r["receita_liquida"] * limitado
    if razoes is None:
        razoes = parametros_historicos(treino, frequencia)["razoes"].median().to_frame().T

    def fator(nome):
        return np.asarray(razoes[nome], dtype=float).reshape(-1, 1)

    if frequencia == "anual":
        ttm_receita, ttm_lucro = r["receita_liquida"], r["lucro_liquido"]
    else:
        anteriores_r = np.tile(treino.receita_liquida.iloc[-3:].to_numpy(), (n, 1))
        anteriores_l = np.tile(treino.lucro_liquido.iloc[-3:].to_numpy(), (n, 1))
        todos_r = np.concatenate([anteriores_r, r["receita_liquida"]], axis=1)
        todos_l = np.concatenate([anteriores_l, r["lucro_liquido"]], axis=1)
        ttm_receita = np.stack([todos_r[:, i : i + 4].sum(axis=1) for i in range(h)], axis=1)
        ttm_lucro = np.stack([todos_l[:, i : i + 4].sum(axis=1) for i in range(h)], axis=1)
    r["ativo_total"] = ttm_receita * fator("ativo_receita")
    r["ativo_circulante"] = r["ativo_total"] * fator("ac_ativo")
    r["ativo_nao_circulante"] = r["ativo_total"] - r["ativo_circulante"]
    r["passivo_circulante"] = r["ativo_total"] * fator("pc_ativo")
    r["passivo_nao_circulante"] = r["ativo_total"] * fator("pnc_ativo")
    r["patrimonio_liquido"] = r["ativo_total"] - r["passivo_circulante"] - r["passivo_nao_circulante"]
    if (r["patrimonio_liquido"] <= 0).any() or (r["passivo_circulante"] <= 0).any():
        raise ErroValidacaoDados("Razões históricas geraram PL ou PC não positivo.")
    r["margem_operacional"] = r["resultado_operacional"] / r["receita_liquida"] * 100
    r["margem_liquida"] = r["lucro_liquido"] / r["receita_liquida"] * 100
    r["liquidez_corrente"] = r["ativo_circulante"] / r["passivo_circulante"]
    r["endividamento_geral"] = (
        (r["passivo_circulante"] + r["passivo_nao_circulante"]) / r["ativo_total"] * 100
    )
    r["roe"] = ttm_lucro / r["patrimonio_liquido"] * 100
    return r, ajustes


def aplicar_cenario(
    treino: pd.DataFrame,
    bases: dict,
    frequencia: str,
    cenario: str,
    overrides: dict | None = None,
    somente_parametro: str | None = None,
) -> tuple[dict, list]:
    """Quantis 25/50/75 do treino; margens trimestrais usam o mesmo trimestre do calendário."""
    q = config.PREDITIVA_CENARIOS[cenario]
    base = parametros_historicos(treino, frequencia, 0.5)
    premissa = parametros_historicos(treino, frequencia, q)
    opcoes = config.PREDITIVA_OVERRIDES.get(cenario, {}) if overrides is None else overrides
    h = len(bases["receita_liquida"])
    registros = []

    def valor(campo, observado):
        override = opcoes.get(campo)
        if override is None:
            return observado, "quantil do histórico de treino"
        if not isinstance(override, dict) or not override.get("justificativa"):
            raise ErroValidacaoDados("Override sem justificativa/fonte não é permitido.")
        return float(override["valor"]), override["justificativa"]

    crescimento, origem = valor(
        "crescimento",
        premissa["crescimento"] if somente_parametro in (None, "crescimento") else base["crescimento"],
    )
    if crescimento <= -1:
        raise ErroValidacaoDados("Crescimento de cenário deve ser maior que -100%.")
    registros.append(
        {
            "cenario": cenario,
            "parametro": "crescimento",
            "valor": crescimento,
            "referencia_base": base["crescimento"],
            "quantil": q,
            "origem": origem,
            "treino_fim": str(treino.data.max().date()),
            "n_observacoes": base["n_crescimentos"],
            "trimestre": 0,
        }
    )
    exposicao = np.arange(1, h + 1) / (4 if frequencia == "trimestral" else 1)
    fator = ((1 + crescimento) / (1 + base["crescimento"])) ** exposicao
    receita = np.asarray(bases["receita_liquida"]) * fator
    resultado = {"receita_liquida": receita}
    datas = datas_futuras(treino, h, frequencia)
    for campo, alvo in [("margem_operacional", "resultado_operacional"), ("margem_liquida", "lucro_liquido")]:
        margens = []
        for i, data in enumerate(datas):
            subset = treino if frequencia == "anual" else treino.loc[treino.data.dt.quarter.eq(data.quarter)]
            serie = subset[alvo] / subset.receita_liquida
            mediana = float(serie.median())
            prem, origem = valor(
                campo, float(serie.quantile(q if somente_parametro in (None, campo) else 0.5))
            )
            margens.append(bases[alvo][i] / bases["receita_liquida"][i] + prem - mediana)
            registros.append(
                {
                    "cenario": cenario,
                    "parametro": campo,
                    "valor": prem,
                    "referencia_base": mediana,
                    "quantil": q,
                    "origem": origem,
                    "treino_fim": str(treino.data.max().date()),
                    "n_observacoes": len(serie),
                    "trimestre": data.quarter if frequencia == "trimestral" else 0,
                    "horizonte": i + 1,
                }
            )
        resultado[alvo] = receita * np.array(margens)
    return resultado, registros
