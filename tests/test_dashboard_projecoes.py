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
