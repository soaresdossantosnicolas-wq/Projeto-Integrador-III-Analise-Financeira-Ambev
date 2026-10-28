"""Verifica que a interface usa apenas os CSVs salvos, sem ajustar modelos."""

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parents[1]


def test_aba_projecoes_consume_csv_sem_treinar(monkeypatch):
    import modelos_preditivos

    monkeypatch.setattr(
        modelos_preditivos, "prever_bases", lambda *a, **k: pytest.fail("Interface não deve treinar")
    )
    app = AppTest.from_file(str(RAIZ / "code/04_visualizacao.py")).run(timeout=30)
    assert not app.exception and not app.error
    assert any(t.label == "Projeções" for t in app.tabs)
    assert any("não constituem recomendação" in a.value for a in app.warning)
    next(s for s in app.selectbox if s.label == "Frequência das projeções").set_value("trimestral").run()
    next(s for s in app.selectbox if s.label == "Cenário").set_value("pessimista").run()
    assert not app.exception and not app.error


@pytest.mark.parametrize("frequencia,ultimo_rotulo", [("anual", "2027"), ("trimestral", "2026T4")])
def test_rotulos_do_grafico_correspondem_ao_periodo_contabil(frequencia, ultimo_rotulo):
    import pandas as pd
    from dashboard_projecoes import grafico_projecao

    historico = pd.read_csv(RAIZ / f"outputs/preditiva/historico_{frequencia}.csv")
    projecoes = pd.read_csv(RAIZ / "outputs/preditiva/projecoes.csv")
    previsto = projecoes.loc[
        projecoes.frequencia.eq(frequencia)
        & projecoes.modelo.eq("ingenuo")
        & projecoes.cenario.eq("base")
        & projecoes.variavel.eq("receita_liquida")
    ]
    fig = grafico_projecao(historico, previsto, "receita_liquida", "Escuro")
    assert fig.layout.xaxis.ticktext[-1] == ultimo_rotulo
    assert len(fig.layout.xaxis.ticktext) == len(fig.layout.xaxis.tickvals)
    for data, rotulo in zip(fig.layout.xaxis.tickvals, fig.layout.xaxis.ticktext):
        assert rotulo.startswith(str(pd.Timestamp(data).year))
