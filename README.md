# Análise Financeira da Ambev S.A. (ABEV3)

Projeto Integrador III — análise descritiva das demonstrações financeiras consolidadas da Ambev, de 2022 a 2025, com dados abertos da CVM, pipeline em Python e dashboard Streamlit.

[![Qualidade](https://github.com/soaresdossantosnicolas-wq/Projeto-Integrador-III-Analise-Financeira-Ambev/actions/workflows/quality.yml/badge.svg)](https://github.com/soaresdossantosnicolas-wq/Projeto-Integrador-III-Analise-Financeira-Ambev/actions/workflows/quality.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)

## Início rápido

Requer Python 3.10 ou superior. A integração contínua verifica Python 3.10 e 3.12.

```bash
git clone https://github.com/soaresdossantosnicolas-wq/Projeto-Integrador-III-Analise-Financeira-Ambev.git
cd Projeto-Integrador-III-Analise-Financeira-Ambev
python -m venv .venv
```

Ative o ambiente:

```powershell
# Windows — PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
source .venv/bin/activate
```

Instale as dependências e abra o dashboard com o CSV já incluído:

```bash
python -m pip install -r requirements.txt
python -m streamlit run code/04_visualizacao.py
```

Acesse <http://localhost:8501>. O dashboard permite filtrar anos, comparar resultados, explorar margens, liquidez e endividamento e baixar os dados exibidos.

## Reproduzir a análise

```bash
# Coleta na CVM, tratamento e cálculo de indicadores
python code/run_pipeline.py

# Reutilizar os CSVs da etapa de coleta já gerados localmente
python code/run_pipeline.py --sem-coleta
```

A coleta exige internet. Os ZIPs ficam em cache; as etapas seguintes funcionam sem rede. Em um clone novo, execute o pipeline completo antes de usar `--sem-coleta`.

| Etapa | Código | Entrada | Destino local |
|---|---|---|---|
| Coleta | `code/analise_ambev_cvm.py` | DFPs anuais da CVM | `dados_cvm/` e `saida/` |
| Tratamento | `code/02_tratamento_ambev.py` | CSVs de `saida/` | `dados_tratados/` |
| Indicadores | `code/03_analise_financeira.py` | Base financeira tratada | `dados_tratados/` |
| Dashboard | `code/04_visualizacao.py` | CSV de indicadores | Interface Streamlit |

As etapas podem ser executadas individualmente com `python caminho/do/script.py`, na ordem da tabela; o dashboard usa o comando Streamlit acima.

## Organização

| Caminho | Responsabilidade |
|---|---|
| `code/` | Etapas do pipeline, configuração compartilhada e entrada do dashboard |
| `dados_tratados/indicadores_financeiros_ambev.csv` | Snapshot versionado necessário para abrir o dashboard sem coleta |
| `docs/` | Metodologia, arquitetura, política de dados e instruções de deploy |
| `reports/visualizacoes/` | Relatórios HTML históricos preservados do projeto |
| `tests/` | Testes dos indicadores, tratamento, deploy e abertura do dashboard |
| `.github/` | Integração contínua e modelos de colaboração |
| `requirements.txt` | Dependências de execução com intervalos de compatibilidade |
| `requirements-dev.txt` | Dependências para testes e análise estática |

Os caminhos de execução existentes foram mantidos para preservar o uso local e o deploy. ZIPs, intermediários e caches são gerados localmente e ignorados pelo Git. Consulte a [política de dados](docs/dados.md).

## Desenvolvimento

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest
```

As mesmas verificações rodam em pull requests e pushes para `main`. Os testes usam dados sintéticos e o snapshot do dashboard, sem baixar dados da CVM. Consulte [CONTRIBUTING.md](CONTRIBUTING.md).

## Documentação

- [Metodologia, fórmulas e limitações](docs/metodologia.md)
- [Arquitetura e configuração](docs/arquitetura.md)
- [Origem, versionamento e atualização dos dados](docs/dados.md)
- [Deploy do dashboard](docs/deploy.md)

## Contexto acadêmico

Projeto Integrador III de Ciência de Dados — Fatec Cotia. Os nomes dos demais integrantes devem ser incluídos pelos autores responsáveis.

Fonte: [CVM — Demonstrações Financeiras Padronizadas](https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp), empresa de código CVM `23264`, demonstrações consolidadas de 2022–2025. Valores monetários são convertidos para reais; margens e retornos são expressos em porcentagem.

As análises têm finalidade educacional e não constituem recomendação de investimento. O repositório ainda não define uma licença de software; essa decisão cabe aos autores.
