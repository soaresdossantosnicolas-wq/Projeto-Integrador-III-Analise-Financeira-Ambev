.PHONY: install pipeline offline dashboard test check
PYTHON ?= python
install:
	$(PYTHON) -m pip install -r requirements-dev.txt
pipeline:
	$(PYTHON) code/run_pipeline.py
offline:
	$(PYTHON) code/run_pipeline.py --offline
dashboard:
	$(PYTHON) -m streamlit run code/04_visualizacao.py
test:
	$(PYTHON) -m pytest
check:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m pytest
	$(PYTHON) scripts/validar_referencia.py

.PHONY: projecoes
projecoes:
	$(PYTHON) code/05_modelagem_preditiva.py --preparar-dados
