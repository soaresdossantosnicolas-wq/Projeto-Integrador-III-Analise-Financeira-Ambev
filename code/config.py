"""Constantes compartilhadas do pipeline e da apresentação, sem efeitos ao importar."""

from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
PASTA_DADOS_CVM = RAIZ_PROJETO / "dados_cvm"
PASTA_SAIDA_ETAPA1 = RAIZ_PROJETO / "saida"
PASTA_DADOS_TRATADOS = RAIZ_PROJETO / "dados_tratados"
PASTA_REPORTS = RAIZ_PROJETO / "reports"
ANOS = [2022, 2023, 2024, 2025]
PERIODO = f"{min(ANOS)}_{max(ANOS)}"
COD_CVM_AMBEV = 23264
CNPJ_AMBEV = "07526557000100"
NOME_EMPRESA = "AMBEV S.A."
AUTORES = ("Arthur Almeida", "Nicolas Soares", "Pedro Barreto")
REPOSITORIO = "https://github.com/soaresdossantosnicolas-wq/Projeto-Integrador-III-Analise-Financeira-Ambev"
LICENCA = "MIT"
FONTE_CVM = "https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp"
URL_DFP = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip"
ORDEM_EXERC_VALIDA = "ÚLTIMO"
ESCALAS_MOEDA = {"UNIDADE": 1, "MIL": 1000}
TOLERANCIA_IDENTIDADE_CONTABIL = 1e-6
TOLERANCIA_ABSOLUTA = 1000  # arredondamento de R$ mil das DFPs

CONTAS_DRE = {
    "receita_liquida": "3.01",
    "custo_vendas": "3.02",
    "lucro_bruto": "3.03",
    "despesas_receitas_operacionais": "3.04",
    "resultado_operacional": "3.05",
    "resultado_financeiro": "3.06",
    "resultado_antes_tributos": "3.07",
    "tributos_lucro": "3.08",
    "resultado_continuado": "3.09",
    "resultado_descontinuado": "3.10",
    "lucro_liquido": "3.11",
    "equivalencia_patrimonial": "3.04.06",
}
CONTAS_ATIVO = {
    "ativo_total": "1",
    "ativo_circulante": "1.01",
    "ativo_nao_circulante": "1.02",
    "caixa_equivalentes": "1.01.01",
    "estoques": "1.01.04",
}
CONTAS_PASSIVO = {
    "passivo_total": "2",
    "passivo_circulante": "2.01",
    "passivo_nao_circulante": "2.02",
    "patrimonio_liquido": "2.03",
}
PALETA = {
    "primaria": "#2874F0",
    "secundaria": "#168C80",
    "destaque": "#A66BE0",
    "positivo": "#23A375",
    "negativo": "#D55E68",
    "neutro": "#77869E",
    "receita_liquida": "#2874F0",
    "lucro_bruto": "#168C80",
    "resultado_operacional": "#A66BE0",
    "lucro_liquido": "#B57D12",
    "margem_bruta": "#168C80",
    "margem_operacional": "#A66BE0",
    "margem_liquida": "#B57D12",
    "roa": "#2874F0",
    "roe": "#168C80",
    "liquidez_corrente": "#2874F0",
    "liquidez_seca": "#168C80",
    "endividamento_geral": "#2874F0",
    "capital_terceiros_patrimonio": "#A66BE0",
    "passivo_circulante": "#2874F0",
    "passivo_nao_circulante": "#A66BE0",
    "patrimonio_liquido": "#168C80",
}
NOMES = {
    "receita_liquida": "Receita líquida",
    "lucro_bruto": "Lucro bruto",
    "custo_vendas": "Custo das vendas",
    "resultado_operacional": "EBIT — CVM (3.05)",
    "lucro_liquido": "Lucro líquido consolidado",
    "margem_bruta": "Margem bruta",
    "margem_operacional": "Margem operacional — CVM",
    "margem_liquida": "Margem líquida",
    "roa": "ROA",
    "roe": "ROE",
    "liquidez_corrente": "Liquidez corrente",
    "liquidez_seca": "Liquidez seca",
    "endividamento_geral": "Endividamento geral",
    "capital_terceiros_patrimonio": "Capital de terceiros / PL",
    "ativo_total": "Ativo total",
    "ativo_circulante": "Ativo circulante",
    "ativo_nao_circulante": "Ativo não circulante",
    "caixa_equivalentes": "Caixa e equivalentes",
    "estoques": "Estoques",
    "passivo_total": "Passivo + PL (CVM 2)",
    "passivo_circulante": "Passivo circulante",
    "passivo_nao_circulante": "Passivo não circulante",
    "patrimonio_liquido": "Patrimônio líquido",
    "passivo_exigivel": "Passivo exigível",
    "despesas_receitas_operacionais": "Despesas/receitas operacionais",
    "resultado_financeiro": "Resultado financeiro",
    "tributos_lucro": "Tributos sobre lucro",
    "equivalencia_patrimonial": "Equivalência patrimonial",
}
PERCENTUAIS = {
    "margem_bruta",
    "margem_operacional",
    "margem_liquida",
    "roa",
    "roe",
    "endividamento_geral",
    "capital_terceiros_patrimonio",
}
RAZOES = {"liquidez_corrente", "liquidez_seca", "divida_liquida_ebitda"}
FORMULAS = {
    "receita_liquida": "Receita consolidada da DFP, conta 3.01, convertida para reais.",
    "lucro_liquido": "Lucro consolidado do período (3.11), incluindo não controladores.",
    "margem_bruta": "Lucro bruto / receita líquida × 100.",
    "margem_operacional": "Resultado CVM 3.05 / receita líquida × 100. Inclui equivalência patrimonial.",
    "margem_liquida": "Lucro líquido consolidado / receita líquida × 100.",
    "roa": "Lucro líquido / ativo total de encerramento × 100; não usa saldo médio.",
    "roe": "Lucro líquido consolidado / PL consolidado de encerramento × 100.",
    "liquidez_corrente": "Ativo circulante / passivo circulante.",
    "liquidez_seca": "(Ativo circulante − estoques) / passivo circulante.",
    "endividamento_geral": "(Passivo circulante + não circulante) / ativo total × 100.",
    "capital_terceiros_patrimonio": "Passivo exigível / patrimônio líquido × 100.",
}


def preparar_pastas() -> None:
    """Cria somente os diretórios de saída quando uma etapa é executada."""
    for pasta in (PASTA_DADOS_CVM, PASTA_SAIDA_ETAPA1, PASTA_DADOS_TRATADOS):
        pasta.mkdir(parents=True, exist_ok=True)


GRUPOS_DFP = {
    "DRE": "DF Consolidado - Demonstração do Resultado",
    "BPA": "DF Consolidado - Balanço Patrimonial Ativo",
    "BPP": "DF Consolidado - Balanço Patrimonial Passivo",
}
