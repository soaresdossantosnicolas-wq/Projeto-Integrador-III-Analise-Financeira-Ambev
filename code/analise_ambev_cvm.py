import io
import zipfile
from pathlib import Path

import pandas as pd
import requests


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ANOS = [2022, 2023, 2024, 2025]

PASTA_DADOS = Path("dados_cvm")
PASTA_SAIDA = Path("saida")

PASTA_DADOS.mkdir(exist_ok=True)
PASTA_SAIDA.mkdir(exist_ok=True)


# Código CVM da Ambev
COD_CVM_AMBEV = 23264

# Nome da companhia
NOME_EMPRESA = "AMBEV S.A."


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
        print(f"[OK] Arquivo {ano} já existe.")
        return caminho

    print(f"[DOWNLOAD] Baixando DFP {ano}...")

    resposta = requests.get(url, timeout=120)

    resposta.raise_for_status()

    caminho.write_bytes(resposta.content)

    print(f"[OK] DFP {ano} baixada.")

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
                f,
                sep=";",
                encoding="latin1",
                low_memory=False
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
            pd.to_numeric(
                df["CD_CVM"],
                errors="coerce"
            ) == COD_CVM_AMBEV
        ].copy()

    else:

        resultado = df[
            df["DENOM_CIA"]
            .astype(str)
            .str.contains(
                "AMBEV",
                case=False,
                na=False
            )
        ].copy()

    return resultado


# ============================================================
# IDENTIFICAÇÃO DAS CONTAS
# ============================================================

def procurar_contas(df, palavras):
    """
    Procura contas cujo nome contenha alguma das palavras.
    """

    coluna = "DS_CONTA"

    if coluna not in df.columns:
        raise ValueError(
            f"A coluna {coluna} não foi encontrada."
        )

    mascara = pd.Series(False, index=df.index)

    for palavra in palavras:

        mascara |= (
            df[coluna]
            .astype(str)
            .str.contains(
                palavra,
                case=False,
                na=False
            )
        )

    return df[mascara].copy()


# ============================================================
# CONVERSÃO DOS VALORES
# ============================================================

def converter_valor(valor):

    if pd.isna(valor):
        return None

    try:
        return float(valor)
    except (ValueError, TypeError):
        return None


# ============================================================
# PROCESSAMENTO DA DRE
# ============================================================

def processar_dre(caminho_zip, ano):

    print(f"[DRE] Processando {ano}...")

    df = ler_csv_zip(
        caminho_zip,
        f"dfp_cia_aberta_DRE_con_{ano}.csv"
    )

    df = filtrar_ambev(df)

    if df.empty:
        print(f"[AVISO] Ambev não encontrada na DRE {ano}")
        return pd.DataFrame()

    # Mostra as contas encontradas
    contas = procurar_contas(
        df,
        [
            "Receita de Venda",
            "Receita Líquida",
            "Custo",
            "Lucro Bruto",
            "Resultado Antes",
            "Lucro",
            "Resultado Líquido"
        ]
    )

    contas.to_csv(
        PASTA_SAIDA / f"ambev_dre_contas_{ano}.csv",
        index=False,
        encoding="utf-8-sig"
    )

    return contas


# ============================================================
# PROCESSAMENTO DO BALANÇO
# ============================================================

def processar_balanco(caminho_zip, ano):

    print(f"[BALANÇO] Processando {ano}...")

    ativo = ler_csv_zip(
        caminho_zip,
        f"dfp_cia_aberta_BPA_con_{ano}.csv"
    )

    passivo = ler_csv_zip(
        caminho_zip,
        f"dfp_cia_aberta_BPP_con_{ano}.csv"
    )

    ativo = filtrar_ambev(ativo)
    passivo = filtrar_ambev(passivo)

    ativo.to_csv(
        PASTA_SAIDA / f"ambev_ativo_{ano}.csv",
        index=False,
        encoding="utf-8-sig"
    )

    passivo.to_csv(
        PASTA_SAIDA / f"ambev_passivo_{ano}.csv",
        index=False,
        encoding="utf-8-sig"
    )

    return ativo, passivo


# ============================================================
# FLUXO DE CAIXA
# ============================================================

def processar_fluxo_caixa(caminho_zip, ano):

    print(f"[DFC] Processando {ano}...")

    try:

        df = ler_csv_zip(
            caminho_zip,
            f"dfp_cia_aberta_DFC_MI_con_{ano}.csv"
        )

    except FileNotFoundError:

        print(
            f"[AVISO] Fluxo de caixa não encontrado "
            f"para {ano}."
        )

        return pd.DataFrame()

    df = filtrar_ambev(df)

    df.to_csv(
        PASTA_SAIDA / f"ambev_fluxo_caixa_{ano}.csv",
        index=False,
        encoding="utf-8-sig"
    )

    return df


# ============================================================
# EXECUÇÃO
# ============================================================

def main():

    print("=" * 60)
    print("ANÁLISE FINANCEIRA - AMBEV")
    print("Fonte: CVM - DFP")
    print("=" * 60)

    todos_dre = []
    todos_ativo = []
    todos_passivo = []

    for ano in ANOS:

        try:

            zip_path = baixar_dfp(ano)

            dre = processar_dre(
                zip_path,
                ano
            )

            ativo, passivo = processar_balanco(
                zip_path,
                ano
            )

            processar_fluxo_caixa(
                zip_path,
                ano
            )

            if not dre.empty:
                dre["ANO_ANALISE"] = ano
                todos_dre.append(dre)

            if not ativo.empty:
                ativo["ANO_ANALISE"] = ano
                todos_ativo.append(ativo)

            if not passivo.empty:
                passivo["ANO_ANALISE"] = ano
                todos_passivo.append(passivo)

        except Exception as erro:

            print(
                f"[ERRO] Não foi possível processar "
                f"{ano}: {erro}"
            )

    # ========================================================
    # CONSOLIDAÇÃO
    # ========================================================

    if todos_dre:

        dre_final = pd.concat(
            todos_dre,
            ignore_index=True
        )

        dre_final.to_csv(
            PASTA_SAIDA / "ambev_dre_2022_2025.csv",
            index=False,
            encoding="utf-8-sig"
        )

    if todos_ativo:

        ativo_final = pd.concat(
            todos_ativo,
            ignore_index=True
        )

        ativo_final.to_csv(
            PASTA_SAIDA / "ambev_ativo_2022_2025.csv",
            index=False,
            encoding="utf-8-sig"
        )

    if todos_passivo:

        passivo_final = pd.concat(
            todos_passivo,
            ignore_index=True
        )

        passivo_final.to_csv(
            PASTA_SAIDA / "ambev_passivo_2022_2025.csv",
            index=False,
            encoding="utf-8-sig"
        )

    print()
    print("=" * 60)
    print("PROCESSAMENTO FINALIZADO")
    print("=" * 60)

    print(f"Dados brutos: {PASTA_DADOS}")
    print(f"Resultados:   {PASTA_SAIDA}")


if __name__ == "__main__":
    main()