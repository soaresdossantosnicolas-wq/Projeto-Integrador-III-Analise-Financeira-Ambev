import logging
import zipfile

import pandas as pd
import requests

import config


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)


ANOS = config.ANOS
PASTA_DADOS = config.PASTA_DADOS_CVM
PASTA_SAIDA = config.PASTA_SAIDA_ETAPA1
COD_CVM_AMBEV = config.COD_CVM_AMBEV
NOME_EMPRESA = config.NOME_EMPRESA


# ============================================================
# DOWNLOAD DOS ARQUIVOS DA CVM
# ============================================================

def baixar_dfp(ano):
    """
    Baixa o ZIP da DFP da CVM referente ao ano informado.
    """

    url = (
        f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/"
        f"DADOS/dfp_cia_aberta_{ano}.zip"
    )

    caminho = PASTA_DADOS / f"dfp_cia_aberta_{ano}.zip"

    if caminho.exists():
        log.info("Arquivo %d já existe.", ano)
        return caminho

    log.info("Baixando DFP %d...", ano)

    try:
        resposta = requests.get(url, timeout=120)
        resposta.raise_for_status()

    except requests.RequestException as erro:

        log.error("Falha ao baixar DFP %d: %s", ano, erro)
        raise

    caminho.write_bytes(resposta.content)

    log.info("DFP %d baixada.", ano)

    return caminho


# ============================================================
# LEITURA DOS CSVs DENTRO DO ZIP
# ============================================================

def ler_csv_zip(caminho_zip, nome_arquivo):
    """
    Lê um CSV diretamente de dentro do ZIP.
    """

    with zipfile.ZipFile(caminho_zip) as z:

        arquivos = z.namelist()

        arquivo = next(
            (
                x for x in arquivos
                if x.lower().endswith(nome_arquivo.lower())
            ),
            None
        )

        if arquivo is None:
            raise FileNotFoundError(
                f"{nome_arquivo} não encontrado no ZIP."
            )

        with z.open(arquivo) as f:

            return pd.read_csv(
                f, sep=";", encoding="latin1", low_memory=False,
                dtype={"CD_CONTA": str}  # evita "3.10" virar 3.1
            )


# ============================================================
# FILTRO DA AMBEV
# ============================================================

def filtrar_ambev(df):
    """
    Seleciona apenas registros da Ambev.
    """

    if "CD_CVM" in df.columns:

        resultado = df[
            pd.to_numeric(df["CD_CVM"], errors="coerce")
            == COD_CVM_AMBEV
        ].copy()

    else:

        resultado = df[
            df["DENOM_CIA"]
            .astype(str)
            .str.contains("AMBEV", case=False, na=False)
        ].copy()

    return resultado


# ============================================================
# IDENTIFICAÇÃO DAS CONTAS
# ============================================================
#
# Nesta etapa 1 mantemos a busca textual apenas para fins de
# INSPEÇÃO/exportação bruta (é útil ver todas as contas que
# contêm essas palavras, para conferência manual). A seleção
# definitiva das contas usadas nos indicadores acontece na
# Etapa 2, por CD_CONTA exato (ver config.CONTAS_DRE /
# CONTAS_ATIVO / CONTAS_PASSIVO) — não por este texto livre.

def procurar_contas(df, palavras):
    """
    Procura contas cujo nome contenha alguma das palavras.
    Uso: inspeção/exportação bruta, não seleção de indicadores.
    """

    coluna = "DS_CONTA"

    if coluna not in df.columns:
        raise ValueError(f"A coluna {coluna} não foi encontrada.")

    mascara = pd.Series(False, index=df.index)

    for palavra in palavras:

        mascara |= (
            df[coluna]
            .astype(str)
            .str.contains(palavra, case=False, na=False)
        )

    return df[mascara].copy()


# ============================================================
# PROCESSAMENTO DA DRE
# ============================================================

def processar_dre(caminho_zip, ano):

    log.info("[DRE] Processando %d...", ano)

    df = ler_csv_zip(caminho_zip, f"dfp_cia_aberta_DRE_con_{ano}.csv")

    df = filtrar_ambev(df)

    if df.empty:
        log.warning("Ambev não encontrada na DRE %d", ano)
        return pd.DataFrame()

    # CORREÇÃO: antes, a DRE era filtrada por palavras-chave em
    # DS_CONTA ("Lucro Bruto", "Lucro", ...). A conta 3.03 se chama
    # "Resultado Bruto" na DFP, então caía fora e Margem Bruta ficava
    # NaN. Agora salvamos TODAS as contas da Ambev; a seleção dos
    # indicadores é feita na Etapa 2, por CD_CONTA exato.
    contas = df.copy()

    contas.to_csv(
        PASTA_SAIDA / f"ambev_dre_{ano}.csv",
        index=False,
        encoding="utf-8-sig"
    )

    return contas


# ============================================================
# PROCESSAMENTO DO BALANÇO
# ============================================================

def processar_balanco(caminho_zip, ano):

    log.info("[BALANÇO] Processando %d...", ano)

    ativo = ler_csv_zip(caminho_zip, f"dfp_cia_aberta_BPA_con_{ano}.csv")
    passivo = ler_csv_zip(caminho_zip, f"dfp_cia_aberta_BPP_con_{ano}.csv")

    ativo = filtrar_ambev(ativo)
    passivo = filtrar_ambev(passivo)

    ativo.to_csv(
        PASTA_SAIDA / f"ambev_ativo_{ano}.csv",
        index=False, encoding="utf-8-sig"
    )

    passivo.to_csv(
        PASTA_SAIDA / f"ambev_passivo_{ano}.csv",
        index=False, encoding="utf-8-sig"
    )

    return ativo, passivo


# ============================================================
# FLUXO DE CAIXA
# ============================================================

def processar_fluxo_caixa(caminho_zip, ano):

    log.info("[DFC] Processando %d...", ano)

    try:

        df = ler_csv_zip(
            caminho_zip, f"dfp_cia_aberta_DFC_MI_con_{ano}.csv"
        )

    except FileNotFoundError:

        log.warning("Fluxo de caixa não encontrado para %d.", ano)
        return pd.DataFrame()

    df = filtrar_ambev(df)

    df.to_csv(
        PASTA_SAIDA / f"ambev_fluxo_caixa_{ano}.csv",
        index=False, encoding="utf-8-sig"
    )

    return df


# ============================================================
# EXECUÇÃO
# ============================================================

def main():

    log.info("=" * 60)
    log.info("ANÁLISE FINANCEIRA - AMBEV (Fonte: CVM - DFP)")
    log.info("=" * 60)

    todos_dre = []
    todos_ativo = []
    todos_passivo = []

    for ano in ANOS:

        try:

            zip_path = baixar_dfp(ano)

            dre = processar_dre(zip_path, ano)
            ativo, passivo = processar_balanco(zip_path, ano)
            processar_fluxo_caixa(zip_path, ano)

            if not dre.empty:
                dre["ANO_ANALISE"] = ano
                todos_dre.append(dre)

            if not ativo.empty:
                ativo["ANO_ANALISE"] = ano
                todos_ativo.append(ativo)

            if not passivo.empty:
                passivo["ANO_ANALISE"] = ano
                todos_passivo.append(passivo)

        except (requests.RequestException, FileNotFoundError,
                zipfile.BadZipFile, ValueError) as erro:

            # Exceções esperadas (rede, arquivo ausente, layout
            # inesperado) são logadas e o pipeline segue para o
            # próximo ano. Erros de programação (ex: NameError,
            # KeyError por bug) NÃO são silenciados aqui — vão
            # estourar normalmente, para não mascarar bugs.
            log.error("Não foi possível processar %d: %s", ano, erro)

    if todos_dre:
        pd.concat(todos_dre, ignore_index=True).to_csv(
            PASTA_SAIDA / "ambev_dre_2022_2025.csv",
            index=False, encoding="utf-8-sig"
        )

    if todos_ativo:
        pd.concat(todos_ativo, ignore_index=True).to_csv(
            PASTA_SAIDA / "ambev_ativo_2022_2025.csv",
            index=False, encoding="utf-8-sig"
        )

    if todos_passivo:
        pd.concat(todos_passivo, ignore_index=True).to_csv(
            PASTA_SAIDA / "ambev_passivo_2022_2025.csv",
            index=False, encoding="utf-8-sig"
        )

    log.info("=" * 60)
    log.info("PROCESSAMENTO FINALIZADO")
    log.info("Dados brutos: %s", PASTA_DADOS)
    log.info("Resultados:   %s", PASTA_SAIDA)


if __name__ == "__main__":
    main()