"""Carregamento dos scripts legados sem executar seus pontos de entrada."""

import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CODE = RAIZ / "code"
sys.path.insert(0, str(CODE))


def carregar_script(nome):
    spec = importlib.util.spec_from_file_location(nome, CODE / f"{nome}.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="session")
def analise():
    return carregar_script("03_analise_financeira")


@pytest.fixture(scope="session")
def tratamento():
    return carregar_script("02_tratamento_ambev")


@pytest.fixture(scope="session")
def deploy():
    return carregar_script("preparar_deploy")


@pytest.fixture(scope="session")
def coleta():
    return carregar_script("analise_ambev_cvm")


@pytest.fixture
def cvm_dre():
    """DFP sintética com schema real, comparativo e valores que fecham a DRE."""
    import pandas as pd
    import config

    valores = [1000, -600, 400, -200, 200, -40, 160, -60, 100, 0, 100, 10]
    registros = []
    for ordem, ano, fator in (("ÚLTIMO", 2025, 1), ("PENÚLTIMO", 2024, 0.9)):
        for codigo, valor in zip(config.CONTAS_DRE.values(), valores):
            registros.append(
                {
                    "CD_CVM": 23264,
                    "CNPJ_CIA": "07.526.557/0001-00",
                    "DENOM_CIA": "AMBEV S.A.",
                    "GRUPO_DFP": config.GRUPOS_DFP["DRE"],
                    "DT_REFER": "2025-12-31",
                    "DT_INI_EXERC": f"{ano}-01-01",
                    "DT_FIM_EXERC": f"{ano}-12-31",
                    "ORDEM_EXERC": ordem,
                    "VERSAO": 1,
                    "MOEDA": "REAL",
                    "ESCALA_MOEDA": "MIL",
                    "CD_CONTA": codigo,
                    "DS_CONTA": "Nome deliberadamente irrelevante",
                    "VL_CONTA": valor * fator,
                }
            )
    return pd.DataFrame(registros)
