"""Valida runtime, snapshot e metadados para deploy, sem modificar arquivos nem executar Git."""

import argparse
import hashlib
import importlib.metadata
import json
import logging
import sys
from pathlib import Path

import pandas as pd

import config
from dashboard_utils import validar_snapshot

log = logging.getLogger(__name__)
PACOTES = ("numpy", "pandas", "plotly", "requests", "streamlit", "urllib3")
COLUNAS_OBRIGATORIAS = tuple(["ano_analise", *config.FORMULAS.keys()])


def conferir_csv(caminho: Path) -> pd.DataFrame:
    """Valida todo o contrato do snapshot que será consumido pelo dashboard."""
    if not caminho.is_file():
        raise ValueError(f"CSV não encontrado: {caminho}. Execute code/run_pipeline.py.")
    return validar_snapshot(pd.read_csv(caminho, encoding="utf-8-sig"))


def main() -> int:
    """Verifica correspondência entre dados, metadados, Python e dependências fixadas."""
    argparse.ArgumentParser(description=__doc__).parse_args()
    pasta = config.PASTA_DADOS_TRATADOS
    caminho = pasta / "indicadores_financeiros_ambev.csv"
    try:
        if sys.version_info[:2] != (3, 12):
            raise ValueError("Use Python 3.12, conforme .python-version e pyproject.toml.")
        df = conferir_csv(caminho)
        metadados = json.loads((pasta / "metadados.json").read_text(encoding="utf-8"))
        if metadados.get("status") != "validado" or hashlib.sha256(
            caminho.read_bytes()
        ).hexdigest() != metadados.get("indicadores_sha256"):
            raise ValueError("O CSV não corresponde aos metadados da execução validada.")
        pins = dict(
            linha.split("==")
            for linha in (config.RAIZ_PROJETO / "requirements.txt").read_text().splitlines()
            if "==" in linha
        )
        versoes = {pacote: importlib.metadata.version(pacote) for pacote in PACOTES}
        divergentes = [p for p, v in versoes.items() if pins.get(p) != v]
        if divergentes:
            raise ValueError(f"Versões diferentes das validadas: {divergentes}. Reinstale requirements.txt.")
    except (ValueError, OSError, importlib.metadata.PackageNotFoundError) as erro:
        log.error("Deploy não validado: %s", erro)
        return 1
    log.info("Snapshot validado: %d exercícios; hash e dependências correspondem.", len(df))
    log.info("Streamlit Cloud: arquivo principal code/04_visualizacao.py; Python 3.12.")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    raise SystemExit(main())
