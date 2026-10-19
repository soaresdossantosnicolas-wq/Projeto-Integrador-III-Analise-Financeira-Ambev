import logging

import numpy as np
import pandas as pd

import config


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)


PASTA_ENTRADA = config.PASTA_DADOS_TRATADOS
PASTA_SAIDA = config.PASTA_DADOS_TRATADOS

ARQUIVO_BASE = PASTA_ENTRADA / "ambev_financeiro_2022_2025.csv"
ARQUIVO_INDICADORES = PASTA_SAIDA / "indicadores_financeiros_ambev.csv"
ARQUIVO_ANALISE_HORIZONTAL = PASTA_SAIDA / "analise_horizontal_ambev.csv"
ARQUIVO_ANALISE_VERTICAL = PASTA_SAIDA / "analise_vertical_ambev.csv"
ARQUIVO_RESUMO = PASTA_SAIDA / "resumo_analise_ambev.csv"


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def carregar_base():

    if not ARQUIVO_BASE.exists():

        raise FileNotFoundError(
            f"Arquivo não encontrado:\n{ARQUIVO_BASE}\n\n"
            "Execute primeiro a Etapa 2."
        )

    df = pd.read_csv(ARQUIVO_BASE, encoding="utf-8-sig")

    df.columns = df.columns.str.strip().str.lower()

    return df


def converter_colunas_numericas(df):

    df = df.copy()

    for coluna in df.columns:

        if coluna == "ano_analise":
            continue

        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    return df


def verificar_colunas(df):

    colunas_necessarias = ["ano_analise"]

    faltantes = [
        coluna for coluna in colunas_necessarias
        if coluna not in df.columns
    ]

    if faltantes:
        raise ValueError(f"Colunas obrigatórias ausentes: {faltantes}")


def obter_coluna(df, nome):

    if nome in df.columns:
        return df[nome]

    return pd.Series(np.nan, index=df.index)


def calcular_percentual(numerador, denominador):

    return np.where(
        denominador != 0,
        (numerador / denominador) * 100,
        np.nan
    )


def calcular_razao(numerador, denominador):

    return np.where(
        denominador != 0,
        numerador / denominador,
        np.nan
    )


# ============================================================
# INDICADORES DE LIQUIDEZ
# ============================================================

def calcular_liquidez(df):

    df = df.copy()

    ativo_circulante = obter_coluna(df, "ativo_circulante")
    passivo_circulante = obter_coluna(df, "passivo_circulante")

    df["liquidez_corrente"] = calcular_razao(
        ativo_circulante, passivo_circulante
    )

    estoque = obter_coluna(df, "estoques")

    if estoque.isna().all():
        log.warning(
            "Coluna 'estoques' ausente/vazia — liquidez_seca "
            "ficará NaN. Confira config.CONTAS_ATIVO na Etapa 2."
        )

    df["liquidez_seca"] = calcular_razao(
        ativo_circulante - estoque, passivo_circulante
    )

    return df


# ============================================================
# INDICADORES DE RENTABILIDADE
# ============================================================

def calcular_rentabilidade(df):

    df = df.copy()

    receita = obter_coluna(df, "receita_liquida")
    lucro_bruto = obter_coluna(df, "lucro_bruto")
    lucro_liquido = obter_coluna(df, "lucro_liquido")
    ativo_total = obter_coluna(df, "ativo_total")
    patrimonio = obter_coluna(df, "patrimonio_liquido")
    resultado_operacional = obter_coluna(df, "resultado_operacional")

    df["margem_bruta"] = calcular_percentual(lucro_bruto, receita)
    df["margem_operacional"] = calcular_percentual(
        resultado_operacional, receita
    )
    df["margem_liquida"] = calcular_percentual(lucro_liquido, receita)
    df["roa"] = calcular_percentual(lucro_liquido, ativo_total)
    df["roe"] = calcular_percentual(lucro_liquido, patrimonio)

    return df


# ============================================================
# INDICADORES DE ENDIVIDAMENTO
# ============================================================

def calcular_endividamento(df):

    df = df.copy()

    ativo_total = obter_coluna(df, "ativo_total")
    passivo_total = obter_coluna(df, "passivo_total")
    patrimonio = obter_coluna(df, "patrimonio_liquido")

    passivo_circulante = obter_coluna(df, "passivo_circulante")
    passivo_nao_circulante = obter_coluna(df, "passivo_nao_circulante")

    # CORREÇÃO: passivo_total (código 2 da CVM) = Passivo + PL e, por
    # identidade contábil, é sempre igual ao ativo_total — usá-lo no
    # numerador dava 100% em todos os anos. O endividamento usa o
    # passivo EXIGÍVEL (circulante + não circulante, sem o PL).
    passivo_exigivel = (
        passivo_circulante + passivo_nao_circulante
    ).fillna(passivo_total - patrimonio)

    df["passivo_exigivel"] = passivo_exigivel

    df["endividamento_geral"] = calcular_percentual(
        passivo_exigivel, ativo_total
    )

    df["capital_terceiros_patrimonio"] = calcular_percentual(
        passivo_exigivel, patrimonio
    )

    divida_total = obter_coluna(df, "divida_total")
    caixa = obter_coluna(df, "caixa_equivalentes")
    ebitda = obter_coluna(df, "ebitda_normalizado")

    df["divida_liquida"] = divida_total - caixa

    df["divida_liquida_ebitda"] = calcular_razao(
        df["divida_liquida"], ebitda
    )

    return df


# ============================================================
# CRESCIMENTO
# ============================================================

def calcular_crescimento(df):

    df = df.copy()

    df = df.sort_values("ano_analise")

    colunas = [
        "receita_liquida",
        "lucro_liquido",
        "lucro_bruto",
        "ativo_total",
        "patrimonio_liquido"
    ]

    for coluna in colunas:

        if coluna not in df.columns:
            continue

        df[f"crescimento_{coluna}"] = df[coluna].pct_change() * 100

    return df


# ============================================================
# ANÁLISE HORIZONTAL (vetorizada)
# ============================================================
#
# Versão original percorria o DataFrame com um loop Python
# (`for i in range(1, len(tabela))`) e indexação posicional via
# `.iloc`, recalculando a variação linha a linha. Com pandas,
# a mesma conta sai de `pct_change()` sobre a série já ordenada
# por ano — sem loop, sem risco de desalinhamento de índice, e
# ordens de grandeza mais rápido para séries maiores.

def criar_analise_horizontal(df):

    colunas = [
        "receita_liquida",
        "lucro_bruto",
        "lucro_liquido",
        "ativo_total",
        "ativo_circulante",
        "passivo_circulante",
        "passivo_total",
        "patrimonio_liquido",
        "caixa_equivalentes"
    ]

    existentes = [c for c in colunas if c in df.columns]

    if not existentes:
        return pd.DataFrame()

    tabela = (
        df[["ano_analise"] + existentes]
        .sort_values("ano_analise")
        .set_index("ano_analise")
    )

    valor_atual = tabela.stack().rename("valor_atual")
    valor_anterior = tabela.shift(1).stack().rename("valor_anterior")

    combinado = pd.concat([valor_atual, valor_anterior], axis=1)
    combinado.index.names = ["ano_atual", "indicador"]
    combinado = combinado.reset_index()

    combinado["ano_anterior"] = (
        combinado.groupby("indicador")["ano_atual"].shift(1)
    )

    # Remove a primeira ocorrência de cada indicador (não tem
    # ano anterior para comparar).
    combinado = combinado.dropna(subset=["ano_anterior"]).copy()

    variacao = np.where(
        combinado["valor_anterior"].isna()
        | combinado["valor_atual"].isna()
        | (combinado["valor_anterior"] == 0),
        np.nan,
        (
            (combinado["valor_atual"] - combinado["valor_anterior"])
            / combinado["valor_anterior"].abs()
        ) * 100
    )

    combinado["variacao_percentual"] = variacao

    combinado["ano_anterior"] = combinado["ano_anterior"].astype(int)
    combinado["ano_atual"] = combinado["ano_atual"].astype(int)

    return combinado[
        [
            "indicador",
            "ano_anterior",
            "ano_atual",
            "valor_anterior",
            "valor_atual",
            "variacao_percentual"
        ]
    ].sort_values(["indicador", "ano_atual"]).reset_index(drop=True)


# ============================================================
# ANÁLISE VERTICAL - DRE (vetorizada)
# ============================================================

def criar_analise_vertical(df):

    receita = obter_coluna(df, "receita_liquida")

    contas = ["lucro_bruto", "resultado_operacional", "lucro_liquido"]

    existentes = [c for c in contas if c in df.columns]

    if not existentes:
        return pd.DataFrame()

    base = df[["ano_analise"] + existentes].copy()

    for conta in existentes:
        base[f"{conta}__pct"] = calcular_percentual(df[conta], receita)

    resultado = base.melt(
        id_vars="ano_analise",
        value_vars=existentes,
        var_name="indicador",
        value_name="valor"
    )

    percentuais = base.melt(
        id_vars="ano_analise",
        value_vars=[f"{c}__pct" for c in existentes],
        var_name="indicador",
        value_name="percentual_receita"
    )
    percentuais["indicador"] = percentuais["indicador"].str.replace(
        "__pct", "", regex=False
    )

    resultado = resultado.merge(
        percentuais, on=["ano_analise", "indicador"]
    )

    resultado["ano"] = resultado["ano_analise"].astype(int)

    return resultado[
        ["ano", "indicador", "valor", "percentual_receita"]
    ].sort_values(["indicador", "ano"]).reset_index(drop=True)


# ============================================================
# RESUMO DA ANÁLISE
# ============================================================

def criar_resumo(df):

    resumo = []

    indicadores = [
        "receita_liquida", "lucro_liquido", "margem_bruta",
        "margem_liquida", "roa", "roe", "liquidez_corrente",
        "liquidez_seca", "endividamento_geral"
    ]

    for indicador in indicadores:

        if indicador not in df.columns:
            continue

        serie = df[["ano_analise", indicador]].dropna()

        if serie.empty:
            continue

        primeiro = serie.iloc[0]
        ultimo = serie.iloc[-1]

        valor_inicial = primeiro[indicador]
        valor_final = ultimo[indicador]

        if valor_inicial != 0:
            variacao = (
                (valor_final - valor_inicial) / abs(valor_inicial)
            ) * 100
        else:
            variacao = np.nan

        resumo.append({
            "indicador": indicador,
            "primeiro_ano": int(primeiro["ano_analise"]),
            "ultimo_ano": int(ultimo["ano_analise"]),
            "valor_inicial": valor_inicial,
            "valor_final": valor_final,
            "variacao_periodo_percentual": variacao
        })

    return pd.DataFrame(resumo)


# ============================================================
# ORGANIZAÇÃO FINAL
# ============================================================

def organizar_resultado(df):

    ordem = [
        "ano_analise",
        "receita_liquida", "lucro_bruto", "resultado_operacional",
        "lucro_liquido",
        "ativo_total", "ativo_circulante", "caixa_equivalentes",
        "passivo_circulante", "passivo_total", "patrimonio_liquido",
        "liquidez_corrente", "liquidez_seca",
        "margem_bruta", "margem_operacional", "margem_liquida",
        "roa", "roe",
        "endividamento_geral", "capital_terceiros_patrimonio",
        "divida_total", "divida_liquida", "ebitda_normalizado",
        "divida_liquida_ebitda"
    ]

    existentes = [c for c in ordem if c in df.columns]
    restante = [c for c in df.columns if c not in existentes]

    return df[existentes + restante]


# ============================================================
# MAIN
# ============================================================

def main():

    log.info("=" * 70)
    log.info("ETAPA 3 - ANÁLISE FINANCEIRA DA AMBEV")
    log.info("=" * 70)

    df = carregar_base()

    verificar_colunas(df)

    log.info("Registros carregados: %d", len(df))
    log.info("Anos encontrados: %s", sorted(df["ano_analise"].unique()))

    df = converter_colunas_numericas(df)

    df = calcular_liquidez(df)
    df = calcular_rentabilidade(df)
    df = calcular_endividamento(df)
    df = calcular_crescimento(df)

    df = organizar_resultado(df)

    df.to_csv(ARQUIVO_INDICADORES, index=False, encoding="utf-8-sig")

    horizontal = criar_analise_horizontal(df)
    horizontal.to_csv(
        ARQUIVO_ANALISE_HORIZONTAL, index=False, encoding="utf-8-sig"
    )

    vertical = criar_analise_vertical(df)
    vertical.to_csv(
        ARQUIVO_ANALISE_VERTICAL, index=False, encoding="utf-8-sig"
    )

    resumo = criar_resumo(df)
    resumo.to_csv(ARQUIVO_RESUMO, index=False, encoding="utf-8-sig")

    log.info("=" * 70)
    log.info("INDICADORES")
    log.info("=" * 70)

    colunas_exibir = [
        c for c in [
            "ano_analise", "liquidez_corrente", "liquidez_seca",
            "margem_bruta", "margem_liquida", "roa", "roe",
            "endividamento_geral"
        ]
        if c in df.columns
    ]

    print(df[colunas_exibir].round(2).to_string(index=False))

    log.info("=" * 70)
    log.info("ARQUIVOS GERADOS")
    log.info("Indicadores:        %s", ARQUIVO_INDICADORES)
    log.info("Análise horizontal: %s", ARQUIVO_ANALISE_HORIZONTAL)
    log.info("Análise vertical:   %s", ARQUIVO_ANALISE_VERTICAL)
    log.info("Resumo:             %s", ARQUIVO_RESUMO)
    log.info("ETAPA 3 CONCLUÍDA.")


if __name__ == "__main__":
    main()
