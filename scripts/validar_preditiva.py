"""Auditoria das saídas salvas do estágio 5; não baixa dados e não treina modelos."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "code"))
import config  # noqa: E402


def main() -> None:
    """Verifica manifesto, calendário, reserva temporal, faixas e identidades publicadas."""
    p = config.PASTA_PREDITIVA
    meta = json.loads((p / "metadados.json").read_text())
    for nome, sha in meta["sha256_arquivos"].items():
        assert hashlib.sha256((p / nome).read_bytes()).hexdigest() == sha, nome
    antigo = config.PASTA_DADOS_TRATADOS / "indicadores_financeiros_ambev.csv"
    assert hashlib.sha256(antigo.read_bytes()).hexdigest() == meta["sha256_historico_estagio3"]
    bt = pd.read_csv(p / "backtest.csv")
    assert (pd.to_datetime(bt.treino_fim) < pd.to_datetime(bt.data_teste)).all()
    for f, corte in [("anual", "2024-01-01"), ("trimestral", "2025-01-01")]:
        d = bt.loc[bt.frequencia.eq(f)]
        assert (
            pd.to_datetime(d.loc[d.conjunto.eq("desenvolvimento"), "data_teste"])
            .lt(pd.Timestamp(corte))
            .all()
        )
        assert pd.to_datetime(d.loc[d.conjunto.eq("teste_final"), "data_teste"]).ge(pd.Timestamp(corte)).all()
        assert d.loc[d.conjunto.eq("teste_final"), "treino_fim"].nunique() == 1
    proj = pd.read_csv(p / "projecoes.csv")
    assert np.isfinite(proj[["valor", "inferior", "superior"]]).all().all()
    assert (proj.inferior <= proj.valor).all() and (proj.valor <= proj.superior).all()
    assert (proj.loc[proj.variavel.eq("receita_liquida"), "inferior"] > 0).all()
    saldo = pd.read_csv(p / "balancos_projetados.csv")
    np.testing.assert_allclose(
        saldo.ativo_total,
        saldo.passivo_circulante + saldo.passivo_nao_circulante + saldo.patrimonio_liquido,
        rtol=1e-12,
    )
    conciliacao = pd.read_csv(p / "conciliacao_trimestres.csv")
    assert conciliacao.status.eq("OK").all()
    print(
        f"Auditoria preditiva aprovada: {len(bt)} erros registrados, {len(proj)} projeções com faixas, {len(saldo)} balanços coerentes."
    )


if __name__ == "__main__":
    main()
