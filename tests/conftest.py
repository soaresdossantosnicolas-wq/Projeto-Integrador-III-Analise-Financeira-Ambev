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
