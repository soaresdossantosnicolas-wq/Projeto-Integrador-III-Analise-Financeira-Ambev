"""
Configurações e constantes compartilhadas entre as etapas do
pipeline de análise financeira da Ambev.

Centralizar isso aqui evita que COD_CVM_AMBEV, ANOS e caminhos
fiquem duplicados (e possivelmente divergentes) em cada script.
"""

from pathlib import Path

# ============================================================
# EMPRESA
# ============================================================

COD_CVM_AMBEV = 23264
NOME_EMPRESA = "AMBEV S.A."

# ============================================================
# PERÍODO
# ============================================================

ANOS = [2022, 2023, 2024, 2025]

# ============================================================
# CAMINHOS (relativos à raiz do projeto, e não ao diretório de
# onde o script é chamado). Este arquivo fica em code/, então a
# raiz do projeto é a pasta acima (parent.parent) — a mesma onde
# estão .venv, code/ e data/.
# ============================================================

RAIZ_PROJETO = Path(__file__).resolve().parent.parent

PASTA_DADOS_CVM = RAIZ_PROJETO / "dados_cvm"
PASTA_SAIDA_ETAPA1 = RAIZ_PROJETO / "saida"
PASTA_DADOS_TRATADOS = RAIZ_PROJETO / "dados_tratados"

for _pasta in (PASTA_DADOS_CVM, PASTA_SAIDA_ETAPA1, PASTA_DADOS_TRATADOS):
    _pasta.mkdir(exist_ok=True, parents=True)

# ============================================================
# PLANO DE CONTAS PADRONIZADO (CVM)
# ============================================================
# A CVM exige que toda DFP siga uma estrutura de códigos fixa
# (CD_CONTA), a mesma para qualquer empresa e qualquer ano.
# Filtrar por CD_CONTA é muito mais confiável do que casar
# texto livre em DS_CONTA: um termo como "Lucro" casa com
# "Lucro Bruto", "Lucro Líquido" e "Lucro por Ação" ao mesmo
# tempo, produzindo múltiplas linhas para o mesmo indicador
# (e o pivot_table("first") descartava isso silenciosamente).
#
# Fonte: Manual de Preenchimento das DFPs da CVM.

CONTAS_DRE = {
    "receita_liquida": "3.01",
    "custo_vendas": "3.02",           # negativo na DFP; usado p/ derivar lucro bruto
    "lucro_bruto": "3.03",            # "Resultado Bruto" (nem toda DFP traz esta linha)
    "resultado_operacional": "3.05",  # EBIT: antes do result. financeiro/tributos
    "lucro_liquido": "3.11",          # Lucro/Prejuízo consolidado do período
}

CONTAS_ATIVO = {
    "ativo_total": "1",
    "ativo_circulante": "1.01",
    "caixa_equivalentes": "1.01.01",
    "estoques": "1.01.04",
}

CONTAS_PASSIVO = {
    "passivo_total": "2",       # Já inclui o Patrimônio Líquido (= Ativo Total)
    "passivo_circulante": "2.01",
    "passivo_nao_circulante": "2.02",
    "patrimonio_liquido": "2.03",
}

# A CVM traz, na MESMA tabela, o exercício atual e o exercício
# comparativo (ano anterior) — coluna ORDEM_EXERC. Sem filtrar
# por isso, os dois períodos ficam misturados na mesma consulta
# e o pivot pega um valor arbitrário entre eles (bug corrigido
# nesta versão).
ORDEM_EXERC_VALIDA = "ÚLTIMO"

# Tolerância para o teste de sanidade contábil
# (ativo_total ≈ passivo_total, já que o código "2" da CVM é o
# passivo total incluindo PL).
TOLERANCIA_IDENTIDADE_CONTABIL = 0.01  # 1%