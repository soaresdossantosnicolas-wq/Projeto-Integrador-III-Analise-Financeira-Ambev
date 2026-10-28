"""Contrato de dados CVM: identidade da empresa, exercício, escala e unicidade."""

import logging
import re

import numpy as np
import pandas as pd

import config
from excecoes import ErroValidacaoDados

log = logging.getLogger(__name__)


def filtrar_ambev(df: pd.DataFrame) -> pd.DataFrame:
    """Seleciona pelo código CVM ou, na ausência dele, CNPJ exato; nunca por nome."""
    if "CD_CVM" in df:
        selecionado = df.loc[pd.to_numeric(df.CD_CVM, errors="coerce") == config.COD_CVM_AMBEV]
    elif "CNPJ_CIA" in df:
        selecionado = df.loc[df.CNPJ_CIA.astype(str).str.replace(r"\D", "", regex=True) == config.CNPJ_AMBEV]
    else:
        raise ErroValidacaoDados("Faltam CD_CVM e CNPJ_CIA para identificar a empresa.")
    if selecionado.empty:
        raise ErroValidacaoDados("Empresa não encontrada pelo código CVM/CNPJ.")
    if "CNPJ_CIA" in selecionado:
        cnpj = selecionado.CNPJ_CIA.astype(str).str.replace(r"\D", "", regex=True)
        if not cnpj.eq(config.CNPJ_AMBEV).all():
            raise ErroValidacaoDados("CNPJ não corresponde ao código CVM da Ambev.")
    return selecionado.copy()


def converter_numerico(df: pd.DataFrame, coluna: str = "VL_CONTA") -> pd.DataFrame:
    """Converte escala uma única vez e rejeita moedas, escalas ou valores inválidos."""
    resultado = df.copy()
    for campo in (coluna, "ESCALA_MOEDA"):
        if campo not in resultado:
            raise ErroValidacaoDados(f"Coluna obrigatória ausente: {campo}.")
    if "MOEDA" in resultado and not resultado.MOEDA.astype(str).str.strip().str.upper().eq("REAL").all():
        raise ErroValidacaoDados("A análise aceita apenas moeda REAL.")
    escala = resultado.ESCALA_MOEDA.astype(str).str.strip().str.upper()
    fator = escala.map(config.ESCALAS_MOEDA)
    valores = pd.to_numeric(resultado[coluna], errors="coerce")
    if fator.isna().any() or not np.isfinite(valores).all():
        raise ErroValidacaoDados("Escala desconhecida ou VL_CONTA nulo/não numérico/infinito.")
    resultado[coluna] = valores * fator
    resultado["ESCALA_MOEDA"] = "UNIDADE"
    return resultado


def filtrar_ultimo_exercicio(df: pd.DataFrame) -> pd.DataFrame:
    """Exige explicitamente o exercício atual; não reutiliza o comparativo como fallback."""
    if "ORDEM_EXERC" not in df:
        raise ErroValidacaoDados("ORDEM_EXERC ausente; não é seguro atribuir um ano.")
    mascara = df.ORDEM_EXERC.astype(str).str.strip().str.upper().eq(config.ORDEM_EXERC_VALIDA)
    if not mascara.any():
        raise ErroValidacaoDados("Não há exercício ÚLTIMO; o comparativo não pode ser reaproveitado.")
    return df.loc[mascara].copy()


def preparar_demonstrativo(df: pd.DataFrame, ano: int, tipo: str) -> pd.DataFrame:
    """Valida a origem temporal antes de rotular o ano e selecionar a última versão."""
    df = df.copy()
    df.columns = df.columns.str.strip().str.upper()
    obrigatorias = {"GRUPO_DFP", "DT_REFER", "DT_FIM_EXERC", "CD_CONTA", "MOEDA", "VERSAO"}
    if tipo == "DRE":
        obrigatorias.add("DT_INI_EXERC")
    faltam = obrigatorias - set(df)
    if faltam:
        raise ErroValidacaoDados(f"{tipo}/{ano}: colunas ausentes: {sorted(faltam)}.")
    df = filtrar_ambev(df)
    grupo = df.GRUPO_DFP.astype(str).str.casefold()
    mascara = grupo.str.strip().eq(config.GRUPOS_DFP[tipo].casefold())
    df = df.loc[mascara].copy()
    if df.empty:
        raise ErroValidacaoDados(f"{tipo}/{ano}: demonstração consolidada não encontrada.")
    # DT_REFER descreve o arquivo, inclusive nas linhas de exercícios comparativos.
    referencia = pd.to_datetime(df.DT_REFER, errors="coerce")
    if not referencia.eq(pd.Timestamp(ano, 12, 31)).all():
        raise ErroValidacaoDados(f"{tipo}/{ano}: DT_REFER diverge do ano do arquivo.")
    df = filtrar_ultimo_exercicio(df)
    fim = pd.to_datetime(df.DT_FIM_EXERC, errors="coerce")
    if not fim.eq(pd.Timestamp(ano, 12, 31)).all():
        raise ErroValidacaoDados(f"{tipo}/{ano}: DT_FIM_EXERC não corresponde ao exercício atual.")
    if tipo == "DRE":
        inicio = pd.to_datetime(df.DT_INI_EXERC, errors="coerce")
        if not inicio.eq(pd.Timestamp(ano, 1, 1)).all():
            raise ErroValidacaoDados(f"DRE/{ano}: período não anual (esperado janeiro–dezembro).")
    if "ANO_ANALISE" in df and not pd.to_numeric(df.ANO_ANALISE, errors="coerce").eq(ano).all():
        raise ErroValidacaoDados("ANO_ANALISE pré-existente diverge das datas reais.")
    versoes = pd.to_numeric(df.VERSAO, errors="coerce")
    if versoes.isna().any() or (versoes % 1 != 0).any() or (versoes < 1).any():
        raise ErroValidacaoDados("VERSAO inválida.")
    df = df.loc[versoes == versoes.max()].copy()
    df["CD_CONTA"] = df.CD_CONTA.astype(str).str.strip()
    if not df.CD_CONTA.map(lambda v: bool(re.fullmatch(r"[123467](?:\.\d{2})*", v))).all():
        raise ErroValidacaoDados("CD_CONTA inválido; leia esta coluna como texto.")
    df = converter_numerico(df)
    antes = len(df)
    df = df.drop_duplicates()
    if len(df) != antes:
        log.info("%s/%s: removidas %d linhas idênticas.", tipo, ano, antes - len(df))
    if df.CD_CONTA.duplicated().any():
        raise ErroValidacaoDados(
            f"{tipo}/{ano}: conta duplicada na mesma versão/exercício; agregação proibida."
        )
    df["ANO_ANALISE"] = pd.to_datetime(df.DT_FIM_EXERC).dt.year.astype(int)
    df["TIPO_DEMONSTRATIVO"] = tipo
    return df.reset_index(drop=True)
