# Metodologia e indicadores

Margens, ROA, ROE, endividamento e capital de terceiros / PL são expressos em porcentagem (a razão da tabela multiplicada por 100). Liquidez é expressa como razão.


| Grupo | Indicador | Fórmula |
|---|---|---|
| Liquidez | Liquidez corrente | Ativo circulante ÷ Passivo circulante |
| Liquidez | Liquidez seca | (Ativo circulante − Estoques) ÷ Passivo circulante |
| Rentabilidade | Margem bruta | Lucro bruto ÷ Receita líquida |
| Rentabilidade | Margem operacional | Resultado operacional (EBIT) ÷ Receita líquida |
| Rentabilidade | Margem líquida | Lucro líquido ÷ Receita líquida |
| Rentabilidade | ROA | Lucro líquido ÷ Ativo total |
| Rentabilidade | ROE | Lucro líquido ÷ Patrimônio líquido |
| Endividamento | Endividamento geral | Passivo exigível (circulante + não circulante) ÷ Ativo total |
| Endividamento | Capital de terceiros / PL | Passivo exigível ÷ Patrimônio líquido |
| Crescimento | Crescimento anual | Variação percentual ano contra ano (receita, lucro bruto, lucro líquido, ativo e PL) |

Além disso, o pipeline gera:

- **Análise horizontal:** variação percentual de cada conta entre anos consecutivos;
- **Análise vertical:** peso do lucro bruto, do resultado operacional e do lucro líquido sobre a receita líquida;
- **Resumo do período:** valor inicial, valor final e variação acumulada de cada indicador-chave.

## Decisões metodológicas e controles de qualidade

**Exercício correto.** Cada DFP traz, na mesma tabela, o exercício atual (`ORDEM_EXERC = "ÚLTIMO"`) e o comparativo do ano anterior (`"PENÚLTIMO"`). O pipeline mantém somente o `ÚLTIMO`; sem esse filtro, os valores de um ano são substituídos pelos do ano anterior.

**Seleção de contas por código, não por texto.** As contas são localizadas pelo `CD_CONTA` do plano de contas padronizado da CVM, e não por busca em `DS_CONTA` (que pode casar várias contas com a mesma palavra):

| Indicador | `CD_CONTA` | Conta |
|---|---|---|
| `receita_liquida` | 3.01 | Receita de venda de bens e/ou serviços |
| `custo_vendas` | 3.02 | Custo dos bens e/ou serviços vendidos |
| `lucro_bruto` | 3.03 | Resultado bruto |
| `resultado_operacional` | 3.05 | Resultado antes do resultado financeiro e dos tributos (EBIT) |
| `lucro_liquido` | 3.11 | Lucro/prejuízo consolidado do período |
| `ativo_total` | 1 | Ativo total |
| `ativo_circulante` | 1.01 | Ativo circulante |
| `caixa_equivalentes` | 1.01.01 | Caixa e equivalentes de caixa |
| `estoques` | 1.01.04 | Estoques |
| `passivo_total` | 2 | Passivo total (inclui o patrimônio líquido) |
| `passivo_circulante` | 2.01 | Passivo circulante |
| `passivo_nao_circulante` | 2.02 | Passivo não circulante |
| `patrimonio_liquido` | 2.03 | Patrimônio líquido consolidado |

Os códigos seguem a estrutura padronizada da CVM; a conta de estoques (1.01.04) deve ser conferida a cada novo ano de dados.

**Escala monetária.** As DFPs informam os valores em R$ mil (`ESCALA_MOEDA = MIL`). A Etapa 2 converte tudo para **reais**, de modo que receita e lucro apareçam corretamente (por exemplo, R$ 79,7 bi, e não R$ 79,7 mi).

**Demonstrações consolidadas.** Apenas o grupo consolidado é utilizado.

**Lucro bruto derivado.** Se a linha 3.03 não vier na DFP, o lucro bruto é calculado como `receita_liquida + custo_vendas` (o custo já é negativo na CVM), com aviso no log.

**Validações contábeis automáticas (Etapa 2):**

- `Ativo total ≈ Passivo total` (tolerância de 1%);
- `Passivo circulante + Passivo não circulante + Patrimônio líquido ≈ Passivo total`;
- alerta quando uma conta não é encontrada ou quando sobra mais de um valor por ano e indicador.

**Endividamento.** O numerador usa o **passivo exigível** (circulante + não circulante). O passivo total da CVM inclui o patrimônio líquido e, por identidade contábil, é sempre igual ao ativo, o que resultaria em 100% em todos os anos.


## Limitações e próximos passos


**Limitações**

- **Amostra pequena:** são apenas quatro observações anuais; a análise é descritiva e não sustenta inferência estatística ou projeções.
- **Valores nominais:** não há ajuste pela inflação (IPCA), o que pode superestimar o crescimento real.
- **ROA e ROE sobre saldo final:** o cálculo usa o saldo de fim de período, e não a média entre o início e o fim do ano.
- **EBITDA e dívida líquida/EBITDA** não são calculados, pois dependem da depreciação e amortização (DFC) e da abertura da dívida bruta.
- **Sem modelagem preditiva:** o projeto é de análise fundamentalista; não há modelo de previsão.

**Próximos passos**

- Incorporar as ITRs (dados trimestrais) para aumentar a granularidade da série.
- Deflacionar os valores pelo IPCA e calcular crescimento real.
- Adicionar o fluxo de caixa (DFC) para EBITDA, dívida líquida e geração de caixa.
- Integrar preços de ABEV3 (retornos logarítmicos, volatilidade, índice de Sharpe e *drawdown* máximo) e confrontá-los com os fundamentos.
- Comparar com empresas pares do setor.
- Cobrir as etapas do pipeline com testes automatizados.
