from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]


def test_snapshot_versionado_valido_e_em_reais(deploy):
    df = deploy.conferir_csv(RAIZ / "dados_tratados/indicadores_financeiros_ambev.csv")
    # Receita histórica da Ambev em dezenas de bilhões, nunca milhões.
    assert df["receita_liquida"].between(50e9, 150e9).all()
    assert not df["ano_analise"].duplicated().any()


@pytest.mark.parametrize("problema", ["vazio", "coluna", "duplicado", "ano", "infinito", "texto"])
def test_deploy_rejeita_snapshot_invalido(deploy, tmp_path, problema):
    df = pd.DataFrame({coluna: [1.0] * 4 for coluna in deploy.COLUNAS_OBRIGATORIAS})
    df["ano_analise"] = [2022, 2023, 2024, 2025]
    if problema == "vazio":
        df = df.iloc[:0]
    elif problema == "coluna":
        df = df.drop(columns="roe")
    elif problema == "duplicado":
        df.loc[1, "ano_analise"] = 2022
    elif problema == "ano":
        df.loc[0, "ano_analise"] = 2021
    elif problema == "infinito":
        df.loc[0, "receita_liquida"] = np.inf
    elif problema == "texto":
        df["roe"] = "erro"
    caminho = tmp_path / "snapshot.csv"
    df.to_csv(caminho, index=False)
    with pytest.raises(ValueError):
        deploy.conferir_csv(caminho)
