from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURAÇÕES
# ============================================================

PASTA_ENTRADA = Path("saida")
PASTA_SAIDA = Path("dados_tratados")

PASTA_SAIDA.mkdir(exist_ok=True)

ANOS = [2022, 2023, 2024, 2025]

# Código CVM da Ambev
COD_CVM_AMBEV = 23264


# ============================================================
# FUNÇÕES GERAIS
# ============================================================

def carregar_csv(caminho):
    """
    Carrega um CSV tentando diferentes codificações.
    """

    try:
        df = pd.read_csv(
            caminho,
            encoding="utf-8-sig",
            low_memory=False
        )

    except UnicodeDecodeError:

        df = pd.read_csv(
            caminho,
            encoding="latin1",
            low_memory=False
        )

    return df


def limpar_colunas(df):
    """
    Padroniza nomes das colunas.
    """

    df = df.copy()

    df.columns = (
        df.columns
        .str.strip()
        .str.upper()
    )

    return df


def converter_numerico(df, coluna="VL_CONTA"):
    """
    Converte a coluna VL_CONTA para número.
    """

    if coluna not in df.columns:
        return df

    df = df.copy()

    df[coluna] = pd.to_numeric(
        df[coluna],
        errors="coerce"
    )

    return df


def filtrar_consolidado(df):
    """
    Mantém somente demonstrações consolidadas quando
    a coluna de tipo de demonstração estiver disponível.
    """

    df = df.copy()

    colunas_possiveis = [
        "GRUPO_DFP",
        "ORDEM_EXERC",
        "CD_CONTA"
    ]

    # Algumas versões dos arquivos podem possuir
    # campos diferentes. Por isso não forçamos uma
    # coluna específica aqui.

    if "GRUPO_DFP" in df.columns:

        valores = (
            df["GRUPO_DFP"]
            .astype(str)
            .str.upper()
        )

        mascara = (
            valores.str.contains(
                "CONSOLIDADO",
                na=False
            )
        )

        if mascara.any():

            df = df[mascara].copy()

    return df


def remover_duplicidades(df):
    """
    Remove registros exatamente duplicados.
    """

    antes = len(df)

    df = df.drop_duplicates()

    depois = len(df)

    print(
        f"Duplicidades removidas: "
        f"{antes - depois}"
    )

    return df


# ============================================================
# FILTRO AMBEV
# ============================================================

def filtrar_ambev(df):

    df = df.copy()

    if "CD_CVM" in df.columns:

        codigo = pd.to_numeric(
            df["CD_CVM"],
            errors="coerce"
        )

        df = df[
            codigo == COD_CVM_AMBEV
        ].copy()

    elif "DENOM_CIA" in df.columns:

        df = df[
            df["DENOM_CIA"]
            .astype(str)
            .str.contains(
                "AMBEV",
                case=False,
                na=False
            )
        ].copy()

    else:

        raise ValueError(
            "Não foi encontrada coluna "
            "CD_CVM ou DENOM_CIA."
        )

    return df


# ============================================================
# LOCALIZAÇÃO DE CONTAS
# ============================================================

def localizar_conta(df, palavras):

    df = df.copy()

    if "DS_CONTA" not in df.columns:
        raise ValueError(
            "Coluna DS_CONTA não encontrada."
        )

    texto = (
        df["DS_CONTA"]
        .astype(str)
        .str.upper()
    )

    mascara = pd.Series(
        False,
        index=df.index
    )

    for palavra in palavras:

        mascara |= texto.str.contains(
            palavra.upper(),
            regex=False,
            na=False
        )

    return df[mascara].copy()


# ============================================================
# PREPARAÇÃO DOS DEMONSTRATIVOS
# ============================================================

def preparar_demonstrativo(df, ano, tipo):

    df = limpar_colunas(df)

    df = filtrar_ambev(df)

    df = filtrar_consolidado(df)

    df = converter_numerico(df)

    df = remover_duplicidades(df)

    df["ANO_ANALISE"] = ano

    df["TIPO_DEMONSTRATIVO"] = tipo

    return df


# ============================================================
# CARREGAMENTO DA DRE
# ============================================================

def carregar_dre():

    lista = []

    for ano in ANOS:

        caminho = (
            PASTA_ENTRADA /
            f"ambev_dre_{ano}.csv"
        )

        # Caso o nome original da etapa 1 seja usado
        if not caminho.exists():

            caminho = (
                PASTA_ENTRADA /
                f"ambev_dre_contas_{ano}.csv"
            )

        if not caminho.exists():

            print(
                f"[AVISO] DRE {ano} não encontrada."
            )

            continue

        print(
            f"[DRE] Tratando {ano}..."
        )

        df = carregar_csv(caminho)

        df = preparar_demonstrativo(
            df,
            ano,
            "DRE"
        )

        lista.append(df)

    if not lista:
        return pd.DataFrame()

    return pd.concat(
        lista,
        ignore_index=True
    )


# ============================================================
# CARREGAMENTO DO ATIVO
# ============================================================

def carregar_ativo():

    lista = []

    for ano in ANOS:

        caminho = (
            PASTA_ENTRADA /
            f"ambev_ativo_{ano}.csv"
        )

        if not caminho.exists():

            print(
                f"[AVISO] Ativo {ano} não encontrado."
            )

            continue

        print(
            f"[ATIVO] Tratando {ano}..."
        )

        df = carregar_csv(caminho)

        df = preparar_demonstrativo(
            df,
            ano,
            "BPA"
        )

        lista.append(df)

    if not lista:
        return pd.DataFrame()

    return pd.concat(
        lista,
        ignore_index=True
    )


# ============================================================
# CARREGAMENTO DO PASSIVO
# ============================================================

def carregar_passivo():

    lista = []

    for ano in ANOS:

        caminho = (
            PASTA_ENTRADA /
            f"ambev_passivo_{ano}.csv"
        )

        if not caminho.exists():

            print(
                f"[AVISO] Passivo {ano} não encontrado."
            )

            continue

        print(
            f"[PASSIVO] Tratando {ano}..."
        )

        df = carregar_csv(caminho)

        df = preparar_demonstrativo(
            df,
            ano,
            "BPP"
        )

        lista.append(df)

    if not lista:
        return pd.DataFrame()

    return pd.concat(
        lista,
        ignore_index=True
    )


# ============================================================
# SELEÇÃO DAS CONTAS IMPORTANTES
# ============================================================

def criar_base_principal(dre, ativo, passivo):

    registros = []

    # --------------------------------------------------------
    # DRE
    # --------------------------------------------------------

    if not dre.empty:

        contas_dre = {
            "receita_liquida": [
                "RECEITA LÍQUIDA",
                "RECEITA DE VENDA DE BENS E/OU SERVIÇOS"
            ],

            "lucro_bruto": [
                "LUCRO BRUTO"
            ],

            "resultado_operacional": [
                "RESULTADO ANTES DO RESULTADO FINANCEIRO"
            ],

            "lucro_liquido": [
                "LUCRO LÍQUIDO"
            ]
        }

        for nome, palavras in contas_dre.items():

            encontrados = localizar_conta(
                dre,
                palavras
            )

            if encontrados.empty:
                continue

            encontrados = encontrados.copy()

            encontrados["INDICADOR"] = nome

            registros.append(
                encontrados
            )

    # --------------------------------------------------------
    # ATIVO
    # --------------------------------------------------------

    if not ativo.empty:

        contas_ativo = {

            "ativo_total": [
                "ATIVO TOTAL"
            ],

            "ativo_circulante": [
                "ATIVO CIRCULANTE"
            ],

            "caixa_equivalentes": [
                "CAIXA E EQUIVALENTES DE CAIXA"
            ]
        }

        for nome, palavras in contas_ativo.items():

            encontrados = localizar_conta(
                ativo,
                palavras
            )

            if encontrados.empty:
                continue

            encontrados = encontrados.copy()

            encontrados["INDICADOR"] = nome

            registros.append(
                encontrados
            )

    # --------------------------------------------------------
    # PASSIVO
    # --------------------------------------------------------

    if not passivo.empty:

        contas_passivo = {

            "passivo_circulante": [
                "PASSIVO CIRCULANTE"
            ],

            "passivo_total": [
                "PASSIVO TOTAL"
            ],

            "patrimonio_liquido": [
                "PATRIMÔNIO LÍQUIDO"
            ]
        }

        for nome, palavras in contas_passivo.items():

            encontrados = localizar_conta(
                passivo,
                palavras
            )

            if encontrados.empty:
                continue

            encontrados = encontrados.copy()

            encontrados["INDICADOR"] = nome

            registros.append(
                encontrados
            )

    if not registros:
        return pd.DataFrame()

    base = pd.concat(
        registros,
        ignore_index=True
    )

    return base


# ============================================================
# ORGANIZAÇÃO DA BASE ANALÍTICA
# ============================================================

def organizar_base(base):

    if base.empty:
        return base

    colunas_desejadas = [

        "ANO_ANALISE",

        "INDICADOR",

        "DS_CONTA",

        "CD_CONTA",

        "VL_CONTA",

        "DT_FIM_EXERC",

        "ORDEM_EXERC",

        "GRUPO_DFP",

        "DENOM_CIA",

        "CD_CVM",

        "TIPO_DEMONSTRATIVO"
    ]

    colunas_existentes = [
        c for c in colunas_desejadas
        if c in base.columns
    ]

    base = base[
        colunas_existentes
    ].copy()

    base = base.drop_duplicates()

    if "VL_CONTA" in base.columns:

        base["VL_CONTA"] = pd.to_numeric(
            base["VL_CONTA"],
            errors="coerce"
        )

    if "ANO_ANALISE" in base.columns:

        base = base.sort_values(
            [
                "ANO_ANALISE",
                "INDICADOR"
            ]
        )

    return base


# ============================================================
# CRIAÇÃO DA TABELA FINAL
# ============================================================

def criar_tabela_financeira(base):

    if base.empty:
        return pd.DataFrame()

    tabela = (
        base
        .pivot_table(
            index="ANO_ANALISE",
            columns="INDICADOR",
            values="VL_CONTA",
            aggfunc="first"
        )
        .reset_index()
    )

    tabela.columns.name = None

    return tabela


# ============================================================
# RELATÓRIO DE QUALIDADE
# ============================================================

def gerar_relatorio_qualidade(
    dre,
    ativo,
    passivo,
    base
):

    relatorio = []

    demonstrativos = {
        "DRE": dre,
        "BPA": ativo,
        "BPP": passivo
    }

    for nome, df in demonstrativos.items():

        if df.empty:

            relatorio.append({
                "demonstrativo": nome,
                "linhas": 0,
                "anos": "",
                "nulos_vl_conta": 0
            })

            continue

        anos = sorted(
            df["ANO_ANALISE"]
            .dropna()
            .unique()
        )

        nulos = 0

        if "VL_CONTA" in df.columns:

            nulos = df["VL_CONTA"].isna().sum()

        relatorio.append({
            "demonstrativo": nome,
            "linhas": len(df),
            "anos": ", ".join(
                str(int(a))
                for a in anos
            ),
            "nulos_vl_conta": nulos
        })

    qualidade = pd.DataFrame(
        relatorio
    )

    qualidade.to_csv(
        PASTA_SAIDA /
        "relatorio_qualidade.csv",
        index=False,
        encoding="utf-8-sig"
    )

    return qualidade


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("ETAPA 2 - TRATAMENTO DOS DADOS DA AMBEV")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. CARREGAR
    # --------------------------------------------------------

    dre = carregar_dre()

    ativo = carregar_ativo()

    passivo = carregar_passivo()

    print()
    print("Dados carregados:")
    print(f"DRE:     {len(dre)} linhas")
    print(f"Ativo:   {len(ativo)} linhas")
    print(f"Passivo: {len(passivo)} linhas")

    # --------------------------------------------------------
    # 2. SALVAR DADOS LIMPOS
    # --------------------------------------------------------

    if not dre.empty:

        dre.to_csv(
            PASTA_SAIDA /
            "dre_ambev_limpa.csv",
            index=False,
            encoding="utf-8-sig"
        )

    if not ativo.empty:

        ativo.to_csv(
            PASTA_SAIDA /
            "ativo_ambev_limpo.csv",
            index=False,
            encoding="utf-8-sig"
        )

    if not passivo.empty:

        passivo.to_csv(
            PASTA_SAIDA /
            "passivo_ambev_limpo.csv",
            index=False,
            encoding="utf-8-sig"
        )

    # --------------------------------------------------------
    # 3. CRIAR BASE PRINCIPAL
    # --------------------------------------------------------

    base = criar_base_principal(
        dre,
        ativo,
        passivo
    )

    base = organizar_base(
        base
    )

    # --------------------------------------------------------
    # 4. SALVAR BASE PRINCIPAL
    # --------------------------------------------------------

    if not base.empty:

        base.to_csv(
            PASTA_SAIDA /
            "base_financeira_ambev.csv",
            index=False,
            encoding="utf-8-sig"
        )

    # --------------------------------------------------------
    # 5. TABELA ANALÍTICA
    # --------------------------------------------------------

    tabela = criar_tabela_financeira(
        base
    )

    if not tabela.empty:

        tabela.to_csv(
            PASTA_SAIDA /
            "ambev_financeiro_2022_2025.csv",
            index=False,
            encoding="utf-8-sig"
        )

    # --------------------------------------------------------
    # 6. QUALIDADE
    # --------------------------------------------------------

    qualidade = gerar_relatorio_qualidade(
        dre,
        ativo,
        passivo,
        base
    )

    # --------------------------------------------------------
    # 7. EXIBIÇÃO
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("BASE FINANCEIRA")
    print("=" * 70)

    if not tabela.empty:

        print(
            tabela.to_string(
                index=False
            )
        )

    print()
    print("=" * 70)
    print("RELATÓRIO DE QUALIDADE")
    print("=" * 70)

    print(
        qualidade.to_string(
            index=False
        )
    )

    print()
    print("Arquivos salvos em:")
    print(PASTA_SAIDA.resolve())


if __name__ == "__main__":
    main()