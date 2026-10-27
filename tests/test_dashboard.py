"""Abertura e filtro do dashboard usando apenas o snapshot versionado."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_dashboard_abre_e_filtra_ano():
    caminho = Path(__file__).resolve().parents[1] / "code/04_visualizacao.py"
    app = AppTest.from_file(str(caminho)).run(timeout=30)
    assert not app.exception
    assert not app.error
    assert len(app.metric) >= 4
    app.sidebar.checkbox[0].uncheck().run()
    app.sidebar.multiselect[0].set_value([2025]).run()
    assert not app.exception
    assert not app.error
    assert app.sidebar.multiselect[0].value == [2025]
