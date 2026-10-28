# Auditoria da camada preditiva — 28/10/2026

Autores: Arthur Almeida, Nicolas Soares e Pedro Barreto. Código sob licença MIT.

## Diagnóstico inicial e plano

A branch `feat`, no commit inicial `5457f2c0f125cdd0f4c80c5274e30f0cf1d8e79a`, já continha a implementação preditiva, resultados, documentação e capturas. Esta revisão auditou e reforçou essa implementação, sem recriá-la nem atribuir os resultados anteriores a uma coleta nova.

O plano comunicado antes de executar os modelos foi: validar históricos e testes; conferir ampliação e conciliações; revisar divisão temporal e seleção; reproduzir resultados; corrigir falhas e registrar evidências.

| Base disponível | Período | Observações | Uso |
|---|---|---:|---|
| Estágio 3 | 2022–2025 | 4 anos | Histórico preservado |
| DFP ampliada congelada | 2015–2025 | 11 anos | Auditoria de comparabilidade |
| ITR/DFP ampliados congelados | 2015–2025 | 44 trimestres | Auditoria e derivação do Q4 |
| Série anual de modelagem | 2019–2025 | 7 anos | Baselines e modelos simples elegíveis |
| Série trimestral de modelagem | 2019T1–2025T4 | 28 trimestres | Comparação temporal com sazonalidade |

Estratégia mantida: ITR trimestral mais DFP anual, com corte conservador em 2019. A justificativa contábil e suas limitações estão em [análise preditiva](analise-preditiva.md). Ampliar com demonstrações originais anteriores ao corte sem reconstruir comparativos reapresentados não garante comparabilidade.

O acesso HTTP direto ao ZIP ITR de 2025 retornou 200 e assinatura ZIP. A rede não exigiu fallback para apenas quatro anos. Entretanto, **não foram baixados nem reextraídos os 22 ZIPs nesta revisão**: usaram-se as séries congeladas versionadas, com referências oficiais e conciliações conferidas. Os manifestos da coleta anterior continuam identificando fontes e hashes. Esta execução não afirma verificar novamente todos os documentos e notas das fontes originais.

## Pré-requisitos verificados antes de reproduzir os modelos

- Os 67 testes preexistentes passaram; a suíte passou a 77 testes com os novos casos de validação.
- Lucro bruto, lucro líquido e estoques de 2022–2025 não têm NaN.
- A referência independente detecta deslocamento de valores entre anos; as 28 comparações anuais de 2022–2025 passaram.
- Liquidez corrente e endividamento foram recalculados por fórmula. Endividamento usa (PC + PNC) / ativo total.
- Todas as contas de fluxo trimestrais conciliam com as anuais. O balanço do quarto trimestre corresponde ao saldo anual, sem somar saldos.
- As identidades e os indicadores derivados foram conferidos antes do treino, inclusive no modo offline.

A página atual de [destaques financeiros da Ambev](https://ri.ambev.com.br/visao-geral/destaques-financeiros/) foi lida por código. Os 49 valores publicados usados na referência congelada continuam iguais aos da página nesta consulta. Evidência em [CSV da conciliação atual](../reports/validacao/conciliacao_ri_2026-10-28.csv), com URL, diferenças, tolerâncias e data.

48 comparações ficam dentro da tolerância. A exceção preservada é o ativo de 2019: R$ 101.742,944 milhões na CVM versus R$ 101.742 milhões no painel resumido. A referência alternativa à demonstração completa já versionada continua sendo verificada pelo código. Nesta revisão não foi repetida a leitura integral dessa demonstração. Não se aumentou a tolerância nem se modificou o histórico para suprimir a diferença.

O EBIT comparável ao painel desconta a equivalência patrimonial da conta CVM 3.05, conforme a conciliação existente. As projeções continuam identificadas como EBIT CVM 3.05.

## Correções desta revisão

1. A execução offline agora reconcilia todas as contas entre frequências, recalcula os indicadores para conferência e exige concordância com o estágio 3 antes de qualquer backtest. Um CSV com fórmula desatualizada ou valores incompatíveis interrompe a execução com `ErroValidacaoDados`.
2. A comparação oficial rejeita explicitamente valores não finitos: comparar `abs(NaN)` com uma tolerância não detectava a falha.
3. Foram acrescentados dez casos de teste, incluindo DRE internamente coerente que diverge da soma anual, balanço de Q4 divergente, estoques diferentes do estágio 3 e indicadores derivados inconsistentes.

## Reprodução e resultados

Executados com as versões fixadas:

```bash
python -m pytest -q
python -m ruff check code tests scripts
python scripts/validar_referencia.py
python code/05_modelagem_preditiva.py --offline
python scripts/validar_preditiva.py
```

Resultado: 77 testes aprovados; lint aprovado; 2.640 registros de backtest, 1.248 projeções com faixas e 156 balanços centrais coerentes. Todos os CSVs numéricos reproduzidos ficaram idênticos aos da branch inicial; o histórico do estágio 3 permaneceu intacto. O manifesto só apresentou ordem diferente de chaves JSON e foi preservado na ordem anterior.

Os modelos são selecionados no desenvolvimento. O bloco final permanece separado: anual 2024–2025 a partir de 2023; trimestral 2025T1–T4 a partir de 2024T4. A política de amostra conserva o ingênuo anual; o menor escore agregado trimestral no desenvolvimento é do ingênuo sazonal. Os resultados completos por modelo, alvo e horizonte estão em [métricas](../outputs/preditiva/metricas.csv). Não se escolheu novamente pelo erro final.

| Frequência | Modelo padrão | MASE médio no desenvolvimento | MASE médio final |
|---|---|---:|---:|
| Anual | Ingênuo | 1,382 | 2,517 |
| Trimestral | Ingênuo sazonal | 0,712 | 0,657 |

São médias dos três resultados primários e horizontes, não uma demonstração de significância. Há somente um erro por alvo/horizonte no teste final. Métodos anuais alternativos tiveram erro final menor em algumas comparações; isso não autoriza escolhê-los usando a mesma reserva.

As projeções e cenários foram reproduzidos, incluindo 2026–2027 e 2026T1–T4. Valores centrais e faixas exploratórias do cenário base anual, em R$ bilhões:

| Ano | Receita | EBIT CVM | Lucro consolidado |
|---|---|---|---|
| 2026 | 88,24 [77,01; 103,80] | 23,42 [20,56; 28,17] | 15,99 [13,62; 19,15] |
| 2027 | 88,24 [70,71; 113,17] | 23,42 [18,51; 28,92] | 15,99 [12,69; 20,50] |

O valor central constante é consequência do baseline; não constitui evidência de estabilidade futura. Os cenários pessimista e otimista, indicadores e premissas estão nos [CSV de projeções](../outputs/preditiva/projecoes.csv) e [premissas](../outputs/preditiva/premissas_cenarios.csv).

## Dashboard e interpretação

Os testes funcionais verificaram o consumo de CSV sem treinar, troca de frequência/cenário, rótulos e aviso de investimento. As capturas existentes em `docs/img/` foram preservadas. A captura anual foi inspecionada visualmente. Não foram gerados novos prints: o navegador local não estava instalado e seu download falhou; isso não foi apresentado como nova validação visual completa.

O corte permanece contábil em 31/12/2025: os números são um exercício retrospectivo. Não incorporam ITRs de 2026 e não respondem qual seria a melhor estimativa com toda a informação disponível em outubro de 2026.

Para a apresentação: “O histórico ampliado permite comparar métodos simples, mas ainda oferece evidência insuficiente para precisão robusta. A referência conserva o último ano e o padrão sazonal trimestral. As faixas são exploratórias, sem cobertura futura comprovada.”

As pendências do grupo estão no [relatório de riscos](riscos-preditiva.md): confirmar o corte, validar premissas com o professor, decidir atualização com 2026, reconstruir vintages e definir reconciliação entre frequências. Mil simulações não substituem novas observações; identidade contábil não comprova capacidade preditiva.
