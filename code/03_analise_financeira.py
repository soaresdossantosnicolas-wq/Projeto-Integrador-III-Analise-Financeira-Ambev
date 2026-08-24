from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURAÇÕES
# ============================================================

PASTA_ENTRADA = Path("dados_tratados")
PASTA_SAIDA = Path("dados_tratados")

ARQUIVO_BASE = (
    PASTA_ENTRADA /
    "ambev_financeiro_2022_2025.csv"
)

ARQUIVO_INDICADORES = (
    PASTA_SAIDA /
    "indicadores_financeiros_ambev.csv"
)

ARQUIVO_ANALISE_HORIZONTAL = (
    PASTA_SAIDA /
    "analise_horizontal_ambev.csv"
)

ARQUIVO_ANALISE_VERTICAL = (
    PASTA_SAIDA /
    "analise_vertical_ambev.csv"
)

ARQUIVO_RESUMO = (
    PASTA_SAIDA /
    "resumo_analise_ambev.csv"
)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def carregar_base():

    if not ARQUIVO_BASE.exists():

        raise FileNotFoundError(
            f"Arquivo não encontrado:\n{ARQUIVO_BASE}\n\n"
            "Execute primeiro a Etapa 2."
        )

    df = pd.read_csv(
        ARQUIVO_BASE,
        encoding="utf-8-sig"
    )

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )

    return df


def converter_colunas_numericas(df):

    df = df.copy()

    for coluna in df.columns:

        if coluna == "ano_analise":
            continue

        df[coluna] = pd.to_numeric(
            df[coluna],
            errors="coerce"
        )

    return df


def verificar_colunas(df):

    colunas_necessarias = [
        "ano_analise"
    ]

    faltantes = [
        coluna
        for coluna in colunas_necessarias
        if coluna not in df.columns
    ]

    if faltantes:

        raise ValueError(
            f"Colunas obrigatórias ausentes: {faltantes}"
        )


def obter_coluna(df, nome):

    if nome in df.columns:
        return df[nome]

    return pd.Series(
        np.nan,
        index=df.index
    )


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

    ativo_circulante = obter_coluna(
        df,
        "ativo_circulante"
    )

    passivo_circulante = obter_coluna(
        df,
        "passivo_circulante"
    )

    df["liquidez_corrente"] = calcular_razao(
        ativo_circulante,
        passivo_circulante
    )

    # A liquidez seca exige estoque.
    # Caso a Etapa 2 ainda não tenha essa conta,
    # o resultado permanecerá NaN.

    estoque = obter_coluna(
        df,
        "estoques"
    )

    df["liquidez_seca"] = calcular_razao(
        ativo_circulante - estoque,
        passivo_circulante
    )

    return df


# ============================================================
# INDICADORES DE RENTABILIDADE
# ============================================================

def calcular_rentabilidade(df):

    df = df.copy()

    receita = obter_coluna(
        df,
        "receita_liquida"
    )

    lucro_bruto = obter_coluna(
        df,
        "lucro_bruto"
    )

    lucro_liquido = obter_coluna(
        df,
        "lucro_liquido"
    )

    ativo_total = obter_coluna(
        df,
        "ativo_total"
    )

    patrimonio = obter_coluna(
        df,
        "patrimonio_liquido"
    )

    resultado_operacional = obter_coluna(
        df,
        "resultado_operacional"
    )

    df["margem_bruta"] = calcular_percentual(
        lucro_bruto,
        receita
    )

    df["margem_operacional"] = calcular_percentual(
        resultado_operacional,
        receita
    )

    df["margem_liquida"] = calcular_percentual(
        lucro_liquido,
        receita
    )

    df["roa"] = calcular_percentual(
        lucro_liquido,
        ativo_total
    )

    df["roe"] = calcular_percentual(
        lucro_liquido,
        patrimonio
    )

    return df


# ============================================================
# INDICADORES DE ENDIVIDAMENTO
# ============================================================

def calcular_endividamento(df):

    df = df.copy()

    ativo_total = obter_coluna(
        df,
        "ativo_total"
    )

    passivo_total = obter_coluna(
        df,
        "passivo_total"
    )

    patrimonio = obter_coluna(
        df,
        "patrimonio_liquido"
    )

    df["endividamento_geral"] = calcular_percentual(
        passivo_total,
        ativo_total
    )

    df["capital_terceiros_patrimonio"] = calcular_percentual(
        passivo_total,
        patrimonio
    )

    # Se a base possuir dívida total e caixa,
    # calculamos dívida líquida.

    divida_total = obter_coluna(
        df,
        "divida_total"
    )

    caixa = obter_coluna(
        df,
        "caixa_equivalentes"
    )

    ebitda = obter_coluna(
        df,
        "ebitda_normalizado"
    )

    df["divida_liquida"] = (
        divida_total - caixa
    )

    df["divida_liquida_ebitda"] = calcular_razao(
        df["divida_liquida"],
        ebitda
    )

    return df


# ============================================================
# CRESCIMENTO
# ============================================================

def calcular_crescimento(df):

    df = df.copy()

    df = df.sort_values(
        "ano_analise"
    )

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

        df[f"crescimento_{coluna}"] = (
            df[coluna]
            .pct_change()
            * 100
        )

    return df


# ============================================================
# ANÁLISE HORIZONTAL
# ============================================================

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

    existentes = [
        coluna
        for coluna in colunas
        if coluna in df.columns
    ]

    tabela = df[
        ["ano_analise"] + existentes
    ].copy()

    tabela = tabela.sort_values(
        "ano_analise"
    )

    resultado = []

    for coluna in existentes:

        for i in range(1, len(tabela)):

            ano_atual = tabela.iloc[i]["ano_analise"]
            ano_anterior = tabela.iloc[i - 1]["ano_analise"]

            valor_atual = tabela.iloc[i][coluna]
            valor_anterior = tabela.iloc[i - 1][coluna]

            if pd.isna(valor_atual) or pd.isna(valor_anterior):
                variacao = np.nan

            elif valor_anterior == 0:
                variacao = np.nan

            else:
                variacao = (
                    (valor_atual - valor_anterior)
                    / abs(valor_anterior)
                ) * 100

            resultado.append({
                "indicador": coluna,
                "ano_anterior": int(ano_anterior),
                "ano_atual": int(ano_atual),
                "valor_anterior": valor_anterior,
                "valor_atual": valor_atual,
                "variacao_percentual": variacao
            })

    return pd.DataFrame(resultado)


# ============================================================
# ANÁLISE VERTICAL - DRE
# ============================================================

def criar_analise_vertical(df):

    resultado = []

    receita = obter_coluna(
        df,
        "receita_liquida"
    )

    contas = [
        "lucro_bruto",
        "resultado_operacional",
        "lucro_liquido"
    ]

    for conta in contas:

        if conta not in df.columns:
            continue

        percentual = calcular_percentual(
            df[conta],
            receita
        )

        for i in range(len(df)):

            resultado.append({
                "ano": int(
                    df.iloc[i]["ano_analise"]
                ),
                "indicador": conta,
                "valor": df.iloc[i][conta],
                "percentual_receita": percentual[i]
            })

    return pd.DataFrame(resultado)


# ============================================================
# RESUMO DA ANÁLISE
# ============================================================

def criar_resumo(df):

    resumo = []

    indicadores = [
        "receita_liquida",
        "lucro_liquido",
        "margem_bruta",
        "margem_liquida",
        "roa",
        "roe",
        "liquidez_corrente",
        "liquidez_seca",
        "endividamento_geral"
    ]

    anos = sorted(
        df["ano_analise"]
        .dropna()
        .unique()
    )

    for indicador in indicadores:

        if indicador not in df.columns:
            continue

        serie = df[
            ["ano_analise", indicador]
        ].dropna()

        if serie.empty:
            continue

        primeiro = serie.iloc[0]
        ultimo = serie.iloc[-1]

        valor_inicial = primeiro[indicador]
        valor_final = ultimo[indicador]

        if valor_inicial != 0:

            variacao = (
                (valor_final - valor_inicial)
                / abs(valor_inicial)
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

        # Demonstrações
        "receita_liquida",
        "lucro_bruto",
        "resultado_operacional",
        "lucro_liquido",

        "ativo_total",
        "ativo_circulante",
        "caixa_equivalentes",

        "passivo_circulante",
        "passivo_total",
        "patrimonio_liquido",

        # Indicadores
        "liquidez_corrente",
        "liquidez_seca",

        "margem_bruta",
        "margem_operacional",
        "margem_liquida",

        "roa",
        "roe",

        "endividamento_geral",
        "capital_terceiros_patrimonio",

        "divida_total",
        "divida_liquida",
        "ebitda_normalizado",
        "divida_liquida_ebitda"
    ]

    existentes = [
        coluna
        for coluna in ordem
        if coluna in df.columns
    ]

    restante = [
        coluna
        for coluna in df.columns
        if coluna not in existentes
    ]

    return df[
        existentes + restante
    ]


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("ETAPA 3 - ANÁLISE FINANCEIRA DA AMBEV")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. CARREGAR
    # --------------------------------------------------------

    df = carregar_base()

    verificar_colunas(df)

    print(
        f"\nRegistros carregados: {len(df)}"
    )

    print(
        f"Anos encontrados: "
        f"{sorted(df['ano_analise'].unique())}"
    )

    # --------------------------------------------------------
    # 2. CONVERSÃO
    # --------------------------------------------------------

    df = converter_colunas_numericas(
        df
    )

    # --------------------------------------------------------
    # 3. INDICADORES
    # --------------------------------------------------------

    df = calcular_liquidez(df)

    df = calcular_rentabilidade(df)

    df = calcular_endividamento(df)

    df = calcular_crescimento(df)

    # --------------------------------------------------------
    # 4. ORGANIZAÇÃO
    # --------------------------------------------------------

    df = organizar_resultado(df)

    # --------------------------------------------------------
    # 5. SALVAR INDICADORES
    # --------------------------------------------------------

    df.to_csv(
        ARQUIVO_INDICADORES,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # 6. ANÁLISE HORIZONTAL
    # --------------------------------------------------------

    horizontal = criar_analise_horizontal(
        df
    )

    horizontal.to_csv(
        ARQUIVO_ANALISE_HORIZONTAL,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # 7. ANÁLISE VERTICAL
    # --------------------------------------------------------

    vertical = criar_analise_vertical(
        df
    )

    vertical.to_csv(
        ARQUIVO_ANALISE_VERTICAL,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # 8. RESUMO
    # --------------------------------------------------------

    resumo = criar_resumo(
        df
    )

    resumo.to_csv(
        ARQUIVO_RESUMO,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # 9. RESULTADOS
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("INDICADORES")
    print("=" * 70)

    colunas_exibir = [
        "ano_analise",
        "liquidez_corrente",
        "liquidez_seca",
        "margem_bruta",
        "margem_liquida",
        "roa",
        "roe",
        "endividamento_geral"
    ]

    colunas_exibir = [
        coluna
        for coluna in colunas_exibir
        if coluna in df.columns
    ]

    print(
        df[colunas_exibir]
        .round(2)
        .to_string(index=False)
    )

    print()
    print("=" * 70)
    print("ARQUIVOS GERADOS")
    print("=" * 70)

    print(
        f"Indicadores:       {ARQUIVO_INDICADORES}"
    )

    print(
        f"Análise horizontal: {ARQUIVO_ANALISE_HORIZONTAL}"
    )

    print(
        f"Análise vertical:   {ARQUIVO_ANALISE_VERTICAL}"
    )

    print(
        f"Resumo:             {ARQUIVO_RESUMO}"
    )

    print()
    print("ETAPA 3 CONCLUÍDA.")


if __name__ == "__main__":
    main()