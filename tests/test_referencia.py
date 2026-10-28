"""Valores oficiais congelados: nenhum acesso HTTP na suíte."""

import importlib.util
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]


def carregar_script(nome):
    spec = importlib.util.spec_from_file_location(nome, RAIZ / "scripts" / f"{nome}.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_conciliacao_28_referencias():
    conciliar = carregar_script("validar_referencia").conciliar
    df = pd.read_csv(RAIZ / "dados_tratados/indicadores_financeiros_ambev.csv")
    ref = pd.read_csv(RAIZ / "reports/validacao/referencia_ambev.csv")
    resultado = conciliar(df, ref)
    assert len(resultado) == 28
    assert resultado.status.eq("OK").all()
    # Deslocar os valores um ano deve ser detectado pela referência independente.
    errado = df.copy()
    errado["receita_liquida"] = errado.receita_liquida.shift().fillna(0)
    assert conciliar(errado, ref).status.eq("DIVERGENTE").any()


def test_scanner_identifica_assinaturas_sem_expor_valores():
    modulo = carregar_script("verificar_segredos")
    assert modulo.detectar(("gh" + "p_" + "A" * 36).encode()) == ["token_github"]
    assert modulo.detectar(b"texto inofensivo") == []
