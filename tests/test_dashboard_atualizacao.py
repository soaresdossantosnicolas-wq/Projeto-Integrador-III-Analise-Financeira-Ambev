"""Regressão: atualização com o módulo de tema anterior ainda em memória."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

import dashboard_design


def test_dashboard_com_modulo_design_sem_nova_funcao(monkeypatch):
    monkeypatch.delattr(dashboard_design, "mostrar_figura", raising=False)
    caminho = Path(__file__).resolve().parents[1] / "code" / "04_visualizacao.py"
    app = AppTest.from_file(str(caminho)).run(timeout=30)
    assert not app.exception
    assert len(app.tabs) == 9
    assert any(t.value == "Como os ativos são financiados" for t in app.subheader)
