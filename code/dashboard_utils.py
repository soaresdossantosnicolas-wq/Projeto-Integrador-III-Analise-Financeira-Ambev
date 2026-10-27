"""Funções puras de apresentação: nunca alteram a escala ou os dados do pipeline."""

import numpy as np
import pandas as pd

import config
from excecoes import ErroValidacaoDados


def numero_br(valor: float, casas: int = 2) -> str:
    """Decimal com vírgula e milhar com ponto; ausências recebem n/d."""
    if valor is None or not np.isfinite(float(valor)):
        return "n/d"
    return f"{float(valor):,.{casas}f}".translate(str.maketrans({",": ".", ".": ","}))


def formatar_valor(valor: float) -> str:
    """Reais abreviados, sem perder o sinal."""
    if valor is None or not np.isfinite(float(valor)):
        return "n/d"
    for limite, sufixo in ((1e9, "bi"), (1e6, "mi"), (1e3, "mil")):
        if abs(valor) >= limite:
            return f"R$ {numero_br(valor / limite)} {sufixo}"
    return f"R$ {numero_br(valor)}"


def formatar_percentual(valor: float, casas: int = 2) -> str:
    """Formata percentuais já calculados na escala 0–100."""
    texto = numero_br(valor, casas)
    return texto if texto == "n/d" else texto + "%"


def formatar_indicador(nome: str, valor: float) -> str:
    """Escolhe a unidade contábil centralizada no config."""
    if nome in config.PERCENTUAIS or nome.startswith("crescimento_"):
        return formatar_percentual(valor)
    if nome in config.RAZOES:
        texto = numero_br(valor)
        return texto if texto == "n/d" else texto + " ×"
    return formatar_valor(valor)


def validar_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """Rejeita calendário ambíguo, escala ausente ou infinidades antes de desenhar."""
    df = df.copy()
    obrigatorias = {"ano_analise", *config.FORMULAS.keys()}
    faltam = obrigatorias - set(df)
    if faltam:
        raise ErroValidacaoDados(f"Base incompleta: faltam {', '.join(sorted(faltam))}.")
    for coluna in df:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")
    if df.empty or df.ano_analise.isna().any() or (df.ano_analise % 1 != 0).any():
        raise ErroValidacaoDados("Base vazia ou anos inválidos.")
    df["ano_analise"] = df.ano_analise.astype(int)
    if df.ano_analise.duplicated().any() or set(df.ano_analise) != set(config.ANOS):
        raise ErroValidacaoDados("Esperada uma linha por exercício, de 2022 a 2025.")
    if np.isinf(df.to_numpy()).any():
        raise ErroValidacaoDados("Base contém valores infinitos.")
    if df[list(obrigatorias)].isna().any().any():
        raise ErroValidacaoDados(
            "Indicador obrigatório ausente; reexecute o pipeline e confira o diagnóstico."
        )
    return df.sort_values("ano_analise").reset_index(drop=True)


def calcular_variacoes(df: pd.DataFrame, coluna: str, ano: int) -> tuple:
    """Compara exatamente ano e ano−1; filtro não transforma 2022→2025 em variação anual."""
    serie = df.set_index("ano_analise")[coluna]
    atual, anterior = serie.get(ano, np.nan), serie.get(ano - 1, np.nan)
    delta = np.nan
    if np.isfinite(atual) and np.isfinite(anterior) and anterior != 0:
        delta = (atual - anterior) / abs(anterior) * 100
    return atual, anterior, delta


def preparar_series(df: pd.DataFrame, colunas: list[str], *, percentual: bool = False) -> pd.DataFrame:
    """Formato longo para Plotly, mantendo cópia exata do valor para tooltip/exportação."""
    colunas = [c for c in colunas if c in df]
    long = df.melt(id_vars="ano_analise", value_vars=colunas, var_name="indicador", value_name="valor")
    long["rotulo"] = long.indicador.map(config.NOMES).fillna(long.indicador)
    long["exibicao"] = [
        formatar_percentual(v) if percentual else formatar_indicador(c, v)
        for c, v in zip(long.indicador, long.valor)
    ]
    return long


def exportar_csv(df: pd.DataFrame) -> bytes:
    """CSV pt-BR legível no Excel: BOM UTF-8, ponto e vírgula e decimal com vírgula."""
    renomear = {"ano_analise": "Ano", **config.NOMES}
    return (
        df.rename(columns=renomear)
        .to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig")
        .encode("utf-8-sig")
    )
