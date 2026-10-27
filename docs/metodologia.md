# Metodologia financeira e limites

## Contas e escala

Somente DRE, BPA e BPP consolidados. Empresa identificada por código CVM/CNPJ. Seleção exclusiva de ÚLTIMO e período anual correspondente ao arquivo. Valores de MIL são multiplicados por 1.000 e marcados como UNIDADE para evitar dupla conversão. Moeda desconhecida, escala desconhecida e valores não finitos são rejeitados.

| Indicador-base | CD_CONTA | Tratamento |
|---|---|---|
| Receita líquida | 3.01 | Obrigatório |
| Custo das vendas | 3.02 | Custo negativo, conforme a DFP |
| Lucro bruto | 3.03 | Fallback explícito: 3.01 + 3.02, registrado em log |
| Despesas/receitas operacionais | 3.04 | Total assinado |
| Resultado operacional CVM | 3.05 | Inclui equivalência patrimonial |
| Resultado financeiro | 3.06 | Total assinado |
| Resultado antes dos tributos | 3.07 | Validação com EBIT + financeiro |
| Tributos sobre lucro | 3.08 | Sinal preservado |
| Resultado continuado/descontinuado | 3.09 / 3.10 | Conciliação até o lucro |
| Lucro líquido consolidado | 3.11 | Inclui não controladores; não é somente atribuível aos acionistas |
| Equivalência patrimonial | 3.04.06 | Usada na conciliação de conceito do EBIT |
| Ativo total / AC / ANC | 1 / 1.01 / 1.02 | Resumo patrimonial |
| Caixa / estoques | 1.01.01 / 1.01.04 | Confirmados nos dados dos quatro anos |
| Passivo + PL / PC / PNC / PL | 2 / 2.01 / 2.02 / 2.03 | Código 2 inclui patrimônio líquido |

A seleção usa CD_CONTA exato, nunca DS_CONTA. Contas obrigatórias ausentes interrompem a etapa com explicação. Não há fallback por nome nem preenchimento arbitrário por zero.

## Fórmulas

| Indicador | Definição e unidade |
|---|---|
| Liquidez corrente | AC / PC, em vezes |
| Liquidez seca | (AC − estoques) / PC, em vezes; não exclui outras contas de menor liquidez |
| Margem bruta | Lucro bruto / receita × 100, em % |
| Margem operacional CVM | CVM 3.05 / receita × 100, em % |
| Margem líquida | Lucro consolidado / receita × 100, em % |
| ROA | Lucro consolidado / ativo final × 100, em % |
| ROE | Lucro consolidado / PL consolidado final × 100, em % |
| Endividamento geral | (PC + PNC) / ativo × 100, em % |
| Capital de terceiros / PL | (PC + PNC) / PL × 100, em % |
| Crescimento/análise horizontal | (Atual − anterior) / valor absoluto do anterior × 100 |
| Análise vertical | Conta da DRE / receita do mesmo ano × 100 |

O fallback do passivo exigível, se PC/PNC estiverem ausentes no uso isolado da função, é passivo CVM 2 − PL, com log. O pipeline completo exige as contas originais e valida sua identidade.

Zero e valores não finitos no denominador produzem n/d. A ausência de dívida financeira ou EBITDA normalizado é explicitamente registrada: passivo exigível não substitui dívida financeira e EBIT não substitui EBITDA ajustado. Esses indicadores não são apresentados como resultados calculados.

Crescimento anual só compara anos consecutivos, sem forward fill. Uma base anterior negativa usa o valor absoluto para manter o sentido da mudança — passar de prejuízo de 100 para prejuízo de 50 representa aumento de 50 nesta convenção. A análise continua exigindo interpretação econômica. Base zero é indefinida, não crescimento zero.

Os cards usam o ano calendário anterior da base completa. Margens e retornos variam em pontos percentuais, e valores monetários variam em porcentagem. A comparação dos extremos selecionados é identificada como comparação de períodos, sem fingir ser anualizada.

## Identidades e subtotais

Antes de exportar, são testados: Ativo = Passivo + PL; Ativo = AC + ANC; passivo CVM 2 = PC + PNC + PL; bruto = receita + custo; EBIT = bruto + operacionais; LAIR = EBIT + financeiro; continuado = LAIR + tributos; líquido = continuado + descontinuado. Também são comparados os pais com seus filhos imediatos no balanço e na conta DRE 3.04.

Tolerância: maior entre R$ 1.000 e 1e-6 do valor absoluto da referência (0,0001%). Cada resultado, diferença e tolerância fica no relatório de qualidade. A etapa falha se a tolerância for excedida.

## Conferência com o RI da Ambev

Referência: [Destaques Financeiros](https://ri.ambev.com.br/visao-geral/destaques-financeiros/), consultada em 27/10/2026. Foram congelados 28 valores: receita, bruto, líquido, ativo, PL, ROE e EBIT para os quatro exercícios. O portal informa valores monetários em milhões e ROE com uma casa decimal.

Tolerância de comparação: R$ 0,5 milhão para os valores arredondados e 0,05 p.p. para ROE. A conciliação pode ser reproduzida sem rede com `python scripts/validar_referencia.py`. Não se trata de validar todos os indicadores contra um cálculo independente publicado: liquidez, estoques e subtotais são conferidos nos dados originais e nas identidades; suas fórmulas têm testes sintéticos.

O resultado CVM 3.05 difere do EBIT do RI. Nos quatro anos, subtrair a equivalência patrimonial CVM 3.04.06 reconcilia a diferença dentro do arredondamento da página. O valor CVM não foi substituído pelo valor arredondado do RI:

| Ano | CVM 3.05 (R$ mi) | Equivalência patrimonial (R$ mi) | Comparável ao EBIT RI (R$ mi) | RI (R$ mi) |
|---|---|---|---|---|
| 2022 | 17.658,840 | −29,106 | 17.687,946 | 17.688 |
| 2023 | 18.645,692 | −185,406 | 18.831,098 | 18.831 |
| 2024 | 21.805,576 | 3,918 | 21.801,658 | 21.802 |
| 2025 | 23.423,386 | 105,785 | 23.317,601 | 23.318 |

As demais diferenças nessa amostra externa são compatíveis com o arredondamento do RI. A página oficial foi usada como segunda publicação para conferência; a referência congelada não é um substituto para os demonstrativos completos.

## Limitações

Amostra de quatro anos, valores nominais, sem ajustes de inflação ou câmbio, sem inferência causal e sem modelagem preditiva. ROA/ROE usam saldos de encerramento; calcular retornos sobre saldos médios exigiria um saldo de abertura adicional e outro contrato de dados. O lucro consolidado inclui não controladores. Menor endividamento ou liquidez maior não significa automaticamente melhor desempenho. Dados podem ser reapresentados pela CVM. O projeto é educacional e não recomenda investimento.
