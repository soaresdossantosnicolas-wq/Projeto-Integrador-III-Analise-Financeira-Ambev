import logging

import numpy as np
import pandas as pd

import config


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)


PASTA_ENTRADA = config.PASTA_SAIDA_ETAPA1
PASTA_SAIDA = config.PASTA_DADOS_TRATADOS

ANOS = config.ANOS
COD_CVM_AMBEV = config.COD_CVM_AMBEV


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
            low_memory=False,
            dtype={"CD_CONTA": str}
        )

    except UnicodeDecodeError:

        df = pd.read_csv(
            caminho,
            encoding="latin1",
            low_memory=False,
            dtype={"CD_CONTA": str}
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

    if "GRUPO_DFP" in df.columns:

        valores = (
            df["GRUPO_DFP"]
            .astype(str)
            .str.upper()
        )

        mascara = valores.str.contains("CONSOLIDADO", na=False)

        if mascara.any():
            df = df[mascara].copy()

    return df


def filtrar_ultimo_exercicio(df):
    """
    CORREÇÃO CRÍTICA: as DFPs da CVM trazem, na mesma tabela,
    o exercício atual E o comparativo (ano anterior) — coluna
    ORDEM_EXERC com valores "ÚLTIMO" / "PENÚLTIMO".

    Sem este filtro, os dois períodos ficam misturados: uma
    mesma conta (ex: receita_liquida) aparece duas vezes na
    mesma consulta de "ano X" — o valor do próprio ano X e o
    valor comparativo do ano X-1 — e o pivot_table mais adiante
    pegava um dos dois de forma arbitrária (aggfunc="first").

    Se a coluna não existir no layout do arquivo, mantemos o
    DataFrame como está e avisamos no log, em vez de falhar
    silenciosamente.
    """

    df = df.copy()

    if "ORDEM_EXERC" not in df.columns:

        log.warning(
            "Coluna ORDEM_EXERC ausente — não foi possível "
            "isolar o exercício atual. Risco de mistura de "
            "períodos nesta base."
        )

        return df

    valores = (
        df["ORDEM_EXERC"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    mascara = valores == config.ORDEM_EXERC_VALIDA

    if not mascara.any():

        log.warning(
            "Nenhuma linha com ORDEM_EXERC == '%s' encontrada "
            "— mantendo dados sem filtrar (verifique o layout).",
            config.ORDEM_EXERC_VALIDA
        )

        return df

    return df[mascara].copy()


def remover_duplicidades(df):
    """
    Remove registros exatamente duplicados.
    """

    antes = len(df)

    df = df.drop_duplicates()

    depois = len(df)

    log.info("Duplicidades removidas: %d", antes - depois)

    return df


# ============================================================
# FILTRO AMBEV
# ============================================================

def filtrar_ambev(df):

    df = df.copy()

    if "CD_CVM" in df.columns:

        codigo = pd.to_numeric(df["CD_CVM"], errors="coerce")

        df = df[codigo == COD_CVM_AMBEV].copy()

    elif "DENOM_CIA" in df.columns:

        df = df[
            df["DENOM_CIA"]
            .astype(str)
            .str.contains("AMBEV", case=False, na=False)
        ].copy()

    else:

        raise ValueError(
            "Não foi encontrada coluna CD_CVM ou DENOM_CIA."
        )

    return df


# ============================================================
# LOCALIZAÇÃO DE CONTAS — POR CÓDIGO (CD_CONTA), NÃO POR TEXTO
# ============================================================

def localizar_conta_por_codigo(df, codigo):
    """
    Localiza uma conta pelo código padronizado da CVM
    (CD_CONTA), em vez de casar texto livre em DS_CONTA.

    Isso evita o problema de uma busca por palavra (ex:
    "Lucro") casar múltiplas contas diferentes (Lucro Bruto,
    Lucro Líquido, Lucro por Ação...) e deixar o pivot_table
    escolher uma delas arbitrariamente.

    Se o código não existir na base (layout divergente em
    algum ano) ou se, mesmo com o código certo, sobrar mais de
    uma linha (o que não deveria acontecer após o filtro de
    ORDEM_EXERC), um aviso é logado para investigação manual —
    em vez de o erro passar despercebido.
    """

    if "CD_CONTA" not in df.columns:

        log.warning(
            "Coluna CD_CONTA ausente — não é possível "
            "localizar a conta '%s' com segurança.",
            codigo
        )

        return df.iloc[0:0]

    codigos = df["CD_CONTA"].astype(str).str.strip()

    encontrados = df[codigos == codigo].copy()

    if encontrados.empty:

        log.warning("Conta CD_CONTA='%s' não encontrada.", codigo)

        return encontrados

    if "ANO_ANALISE" in encontrados.columns:
        por_ano = encontrados.groupby("ANO_ANALISE").size()
        anos_dup = por_ano[por_ano > 1]
    else:
        anos_dup = pd.Series([len(encontrados)]) if len(encontrados) > 1 \
            else pd.Series(dtype=int)

    if not anos_dup.empty:

        log.warning(
            "Conta CD_CONTA='%s' com mais de 1 linha no mesmo ano "
            "(esperado 1 após filtro de ORDEM_EXERC): %s",
            codigo, anos_dup.to_dict()
        )

    return encontrados


# ============================================================
# PREPARAÇÃO DOS DEMONSTRATIVOS
# ============================================================

def preparar_demonstrativo(df, ano, tipo):

    df = limpar_colunas(df)

    df = filtrar_ambev(df)

    df = filtrar_consolidado(df)

    df = filtrar_ultimo_exercicio(df)

    df = converter_numerico(df)

    df = remover_duplicidades(df)

    df["ANO_ANALISE"] = ano

    df["TIPO_DEMONSTRATIVO"] = tipo

    return df


# ============================================================
# CARREGAMENTO GENÉRICO POR TIPO DE DEMONSTRATIVO
# ============================================================

def _carregar_demonstrativo(tipo, nomes_arquivo_por_ano):

    lista = []

    for ano in ANOS:

        caminho = None

        for nome in nomes_arquivo_por_ano(ano):

            candidato = PASTA_ENTRADA / nome

            if candidato.exists():
                caminho = candidato
                break

        if caminho is None:

            log.warning("%s %d não encontrado.", tipo, ano)

            continue

        log.info("[%s] Tratando %d...", tipo, ano)

        df = carregar_csv(caminho)

        df = preparar_demonstrativo(df, ano, tipo)

        lista.append(df)

    if not lista:
        return pd.DataFrame()

    return pd.concat(lista, ignore_index=True)


def carregar_dre():

    return _carregar_demonstrativo(
        "DRE",
        lambda ano: (
            f"ambev_dre_{ano}.csv",
            f"ambev_dre_contas_{ano}.csv",
        )
    )


def carregar_ativo():

    return _carregar_demonstrativo(
        "BPA",
        lambda ano: (f"ambev_ativo_{ano}.csv",)
    )


def carregar_passivo():

    return _carregar_demonstrativo(
        "BPP",
        lambda ano: (f"ambev_passivo_{ano}.csv",)
    )


# ============================================================
# SELEÇÃO DAS CONTAS IMPORTANTES (via CD_CONTA)
# ============================================================

def _extrair_contas(df, mapa_contas):

    registros = []

    if df.empty:
        return registros

    for nome_indicador, codigo in mapa_contas.items():

        encontrados = localizar_conta_por_codigo(df, codigo)

        if encontrados.empty:
            continue

        encontrados = encontrados.copy()

        encontrados["INDICADOR"] = nome_indicador

        registros.append(encontrados)

    return registros


def criar_base_principal(dre, ativo, passivo):

    registros = []

    registros += _extrair_contas(dre, config.CONTAS_DRE)
    registros += _extrair_contas(ativo, config.CONTAS_ATIVO)
    registros += _extrair_contas(passivo, config.CONTAS_PASSIVO)

    if not registros:
        return pd.DataFrame()

    return pd.concat(registros, ignore_index=True)


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
        c for c in colunas_desejadas if c in base.columns
    ]

    base = base[colunas_existentes].copy()

    base = base.drop_duplicates()

    if "VL_CONTA" in base.columns:

        base["VL_CONTA"] = pd.to_numeric(
            base["VL_CONTA"], errors="coerce"
        )

    if "ANO_ANALISE" in base.columns:

        base = base.sort_values(["ANO_ANALISE", "INDICADOR"])

    return base


# ============================================================
# CRIAÇÃO DA TABELA FINAL
# ============================================================

def criar_tabela_financeira(base):

    if base.empty:
        return pd.DataFrame()

    # Agora que a base já vem filtrada por ORDEM_EXERC e por
    # CD_CONTA exato, não deveria haver mais de um valor por
    # (ANO_ANALISE, INDICADOR). Usar aggfunc="mean" em vez de
    # "first" faz qualquer duplicata remanescente aparecer como
    # média (em vez de escolha arbitrária) — e o teste abaixo
    # avisa se isso realmente aconteceu.
    contagem = base.groupby(["ANO_ANALISE", "INDICADOR"]).size()
    duplicados = contagem[contagem > 1]

    if not duplicados.empty:

        log.warning(
            "Combinações (ano, indicador) com mais de um "
            "valor após todos os filtros:\n%s",
            duplicados.to_string()
        )

    tabela = (
        base
        .pivot_table(
            index="ANO_ANALISE",
            columns="INDICADOR",
            values="VL_CONTA",
            aggfunc="mean"
        )
        .reset_index()
    )

    tabela.columns.name = None

    tabela = derivar_lucro_bruto(tabela)

    return tabela


def derivar_lucro_bruto(tabela):
    """
    Se a linha 3.03 (Resultado Bruto) não vier na DFP, deriva
    lucro_bruto = receita_liquida + custo_vendas (o custo já vem
    negativo na CVM) e registra isso no log.
    """

    if "receita_liquida" not in tabela.columns:
        return tabela

    if "custo_vendas" not in tabela.columns:
        return tabela

    tabela = tabela.copy()

    if "lucro_bruto" not in tabela.columns:
        tabela["lucro_bruto"] = np.nan

    faltando = tabela["lucro_bruto"].isna()

    if faltando.any():

        log.warning(
            "lucro_bruto (3.03) ausente em %d ano(s) — derivado de "
            "receita_liquida + custo_vendas.", int(faltando.sum())
        )

        tabela.loc[faltando, "lucro_bruto"] = (
            tabela.loc[faltando, "receita_liquida"]
            + tabela.loc[faltando, "custo_vendas"]
        )

    return tabela


def verificar_composicao_passivo(tabela):
    """
    passivo_circulante + passivo_nao_circulante + patrimonio_liquido
    deve ser igual a passivo_total (código 2).
    """

    colunas = ["passivo_circulante", "passivo_nao_circulante",
               "patrimonio_liquido", "passivo_total"]

    if not all(c in tabela.columns for c in colunas):
        return

    for _, linha in tabela.iterrows():

        soma = (linha["passivo_circulante"]
                + linha["passivo_nao_circulante"]
                + linha["patrimonio_liquido"])

        total = linha["passivo_total"]

        if pd.isna(soma) or pd.isna(total) or total == 0:
            continue

        dif = abs(soma - total) / abs(total)

        nivel = log.warning if dif > config.TOLERANCIA_IDENTIDADE_CONTABIL \
            else log.info

        nivel("Ano %s: PC + PNC + PL vs passivo_total — divergência de "
              "%.3f%%.", int(linha["ANO_ANALISE"]), dif * 100)


# ============================================================
# TESTE DE SANIDADE CONTÁBIL
# ============================================================

def verificar_identidade_contabil(tabela):
    """
    O código CVM "2" (passivo_total) já representa o Passivo +
    Patrimônio Líquido, e por definição contábil deve ser igual
    ao código "1" (ativo_total). Divergência acima da tolerância
    indica erro de captura/filtro de conta.
    """

    if "ativo_total" not in tabela.columns:
        return

    if "passivo_total" not in tabela.columns:
        return

    for _, linha in tabela.iterrows():

        ativo = linha["ativo_total"]
        passivo = linha["passivo_total"]

        if pd.isna(ativo) or pd.isna(passivo) or ativo == 0:
            continue

        diferenca_relativa = abs(ativo - passivo) / abs(ativo)

        if diferenca_relativa > config.TOLERANCIA_IDENTIDADE_CONTABIL:

            log.warning(
                "Ano %s: ativo_total (%.2f) != passivo_total "
                "(%.2f) — divergência de %.2f%%. Verifique a "
                "captura das contas.",
                int(linha["ANO_ANALISE"]), ativo, passivo,
                diferenca_relativa * 100
            )

        else:

            log.info(
                "Ano %s: identidade contábil OK "
                "(divergência de %.3f%%).",
                int(linha["ANO_ANALISE"]), diferenca_relativa * 100
            )


# ============================================================
# RELATÓRIO DE QUALIDADE
# ============================================================

def gerar_relatorio_qualidade(dre, ativo, passivo, base):

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

        anos = sorted(df["ANO_ANALISE"].dropna().unique())

        nulos = 0

        if "VL_CONTA" in df.columns:
            nulos = df["VL_CONTA"].isna().sum()

        relatorio.append({
            "demonstrativo": nome,
            "linhas": len(df),
            "anos": ", ".join(str(int(a)) for a in anos),
            "nulos_vl_conta": nulos
        })

    qualidade = pd.DataFrame(relatorio)

    qualidade.to_csv(
        PASTA_SAIDA / "relatorio_qualidade.csv",
        index=False,
        encoding="utf-8-sig"
    )

    return qualidade


# ============================================================
# MAIN
# ============================================================

def main():

    log.info("=" * 70)
    log.info("ETAPA 2 - TRATAMENTO DOS DADOS DA AMBEV")
    log.info("=" * 70)

    dre = carregar_dre()
    ativo = carregar_ativo()
    passivo = carregar_passivo()

    log.info("Dados carregados:")
    log.info("DRE:     %d linhas", len(dre))
    log.info("Ativo:   %d linhas", len(ativo))
    log.info("Passivo: %d linhas", len(passivo))

    if not dre.empty:
        dre.to_csv(
            PASTA_SAIDA / "dre_ambev_limpa.csv",
            index=False, encoding="utf-8-sig"
        )

    if not ativo.empty:
        ativo.to_csv(
            PASTA_SAIDA / "ativo_ambev_limpo.csv",
            index=False, encoding="utf-8-sig"
        )

    if not passivo.empty:
        passivo.to_csv(
            PASTA_SAIDA / "passivo_ambev_limpo.csv",
            index=False, encoding="utf-8-sig"
        )

    base = criar_base_principal(dre, ativo, passivo)
    base = organizar_base(base)

    if not base.empty:
        base.to_csv(
            PASTA_SAIDA / "base_financeira_ambev.csv",
            index=False, encoding="utf-8-sig"
        )

    tabela = criar_tabela_financeira(base)

    if not tabela.empty:

        verificar_identidade_contabil(tabela)
        verificar_composicao_passivo(tabela)

        tabela.to_csv(
            PASTA_SAIDA / "ambev_financeiro_2022_2025.csv",
            index=False, encoding="utf-8-sig"
        )

    qualidade = gerar_relatorio_qualidade(dre, ativo, passivo, base)

    log.info("=" * 70)
    log.info("BASE FINANCEIRA")
    log.info("=" * 70)

    if not tabela.empty:
        print(tabela.to_string(index=False))

    log.info("=" * 70)
    log.info("RELATÓRIO DE QUALIDADE")
    log.info("=" * 70)

    print(qualidade.to_string(index=False))

    log.info("Arquivos salvos em: %s", PASTA_SAIDA.resolve())


if __name__ == "__main__":
    main()
