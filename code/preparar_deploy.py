"""Valida o dashboard para deploy, sem alterar arquivos ou executar comandos Git."""

import argparse
import importlib.metadata
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import config

PACOTES = ("numpy", "pandas", "plotly", "requests", "streamlit")
COLUNAS_OBRIGATORIAS = (
    "ano_analise", "receita_liquida", "lucro_liquido", "roe", "liquidez_corrente",
)


def conferir_csv(caminho: Path) -> pd.DataFrame:
    """Rejeita snapshots incompletos antes de publicar o dashboard."""
    if not caminho.is_file():
        raise ValueError(f"CSV não encontrado: {caminho}. Execute code/run_pipeline.py.")
    df = pd.read_csv(caminho, encoding="utf-8-sig")
    faltantes = sorted(set(COLUNAS_OBRIGATORIAS) - set(df.columns))
    if faltantes:
        raise ValueError(f"Colunas obrigatórias ausentes: {faltantes}")
    if df.empty:
        raise ValueError("O CSV está vazio.")
    valores = df[list(COLUNAS_OBRIGATORIAS)].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(valores.to_numpy()).all():
        raise ValueError("Há valores ausentes, não numéricos ou infinitos em campos obrigatórios.")
    anos = valores["ano_analise"]
    if anos.duplicated().any() or set(anos) != set(config.ANOS):
        raise ValueError(f"O CSV deve conter exatamente uma linha por ano: {config.ANOS}.")
    return df


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    caminho = config.PASTA_DADOS_TRATADOS / "indicadores_financeiros_ambev.csv"
    try:
        df = conferir_csv(caminho)
        versoes = {pacote: importlib.metadata.version(pacote) for pacote in PACOTES}
    except (ValueError, OSError, importlib.metadata.PackageNotFoundError) as erro:
        print(f"[ERRO] {erro}", file=sys.stderr)
        return 1
    print(f"[OK] Snapshot: {len(df)} anos; campos obrigatórios válidos.")
    print(f"[OK] Dependências instaladas: {versoes}")
    print("Arquivo principal no Streamlit Cloud: code/04_visualizacao.py")
    print("Próximo passo: revise o diff e publique as alterações pela sua branch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
