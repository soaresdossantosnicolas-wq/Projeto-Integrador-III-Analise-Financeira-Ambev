# Análise preditiva — diagnóstico, método e interpretação

## Resposta defensável

A pergunta é qual trajetória receita, EBIT, lucro e indicadores podem seguir em 2026–2027, e quanta confiança há nessa projeção. A conclusão é **evidência insuficiente para precisão robusta**, sobretudo anual. O padrão anual mantém o último valor; o trimestral repete o mesmo trimestre anterior. Não foi usado um modelo mais complexo apenas por parecer avançado.

O corte é **contábil em 31/12/2025**. Trata-se de exercício retrospectivo para 2026–2027, não previsão em tempo real de outubro de 2026. ITRs de 2026 já disponíveis não foram incorporados. Os demonstrativos são divulgados após o encerramento do período; as origens contábeis não representam necessariamente datas em que todos os dados estavam publicados.

## Diagnóstico e estratégia usada

A base inicial tinha 4 anos (2022–2025). Antes de modelar, passaram os 51 testes existentes, as 28 comparações com a referência oficial e as 51 contraprovas dos ZIPs. A nova camada verifica o SHA-256 do histórico do estágio 3 antes e depois: seus números não foram alterados.

A rede permitiu baixar **22 ZIPs**, DFP e ITR de 2015–2025. Foram auditados 11 anos e 44 trimestres. Os códigos de empresa/CNPJ e contas, demonstrações consolidadas, moeda, escala, versões e datas foram conferidos. Contas inexistentes, valores não finitos e duplicatas conflitantes interrompem a preparação. `versoes_contas.csv` e os manifestos preservam origem e hashes; ZIPs ficam ignorados em `dados_modelagem/`.

**Corte principal: 2019–2025, 7 anos e 28 trimestres.** A Ambev adotou IFRS 16 em 2019 com reapresentação de 2018/2017. Não misturamos as DFPs originais anteriores com comparativos posteriormente reapresentados. O corte fica após o início da aplicação de IAS 29 à Argentina em 2018. Isso reduz uma quebra conhecida, mas não elimina pandemia, inflação, câmbio e outras alterações. 2015–2018 foram auditados, mas não usados para ajustar o modelo principal. Não se afirma leitura integral de todas as notas de cada relatório.

A DRE acumulada é selecionada por DT_INI_EXERC/DT_FIM_EXERC: Q1=3m, Q2=6m−3m, Q3=9m−6m, Q4=DFP−9m. Os três primeiros trimestres foram conferidos contra os trimestres diretos, sem divergências materiais. A soma dos quatro fecha com o anual. O fechamento do Q4 é parcialmente uma identidade por construção e pode incorporar ajustes/reexpressões de encerramento; não substitui a conferência dos demais. Balanços são saldos, nunca somas.

Fontes primárias:

- [CVM — ITR](https://dados.cvm.gov.br/dataset/cia_aberta-doc-itr).
- [Ambev — Form 20-F 2019: IFRS 16 e balanço](https://www.sec.gov/Archives/edgar/data/1565025/000129281420000888/ambevsaform20f_2019.htm).
- [Ambev — release 2018: IAS 29](https://www.sec.gov/Archives/edgar/data/1565025/000129281419000487/ambevsapr4q18_6k.htm).
- [RI — destaques financeiros](https://ri.ambev.com.br/visao-geral/destaques-financeiros/).

### Divergência externa preservada

Foram comparados 49 valores oficiais (receita, bruto, líquido, ativo, PL, ROE e EBIT nos 7 anos). 48 coincidem dentro da precisão do painel, após excluir equivalência patrimonial somente para comparar o EBIT. O ativo de 2019 no painel é R$ 101.742 milhões; a CVM informa R$ 101.742,944 milhões. A diferença de R$ 0,944 milhão excede a tolerância de R$ 0,5 milhão e permanece registrada. A demonstração anual completa publicada na SEC informa R$ 101.742,9 milhões, confirmando a CVM dentro de sua precisão de uma casa decimal. Não se ampliou a tolerância para esconder o problema nem se alterou o valor CVM. Evidências e referência alternativa estão nos arquivos de validação.

## Modelos e protocolo temporal

Baselines: último valor, ingênuo sazonal, média móvel, drift aditivo e crescimento médio. Foram comparados tendência linear, tendência com dummies sazonais, Holt amortecido, Holt-Winters aditivo e direcionadores quando elegíveis. Média móvel usa 3 anos ou 4 trimestres; crescimento trimestral usa variações contra o mesmo trimestre anterior. Drift aditivo e crescimento multiplicativo são métodos diferentes.

| Frequência | Desenvolvimento expansivo | Reserva final, sem seleção | Nº de erros por horizonte |
|---|---|---|---|
| Anual | Treino inicial 2019–2021; alvos 2022/2023 | 2024/2025, previstos na origem fixa 2023 | Desenvolvimento: 2 em h1, 1 em h2; final: 1 por horizonte |
| Trimestral | Treino inicial de 16 trimestres; alvos em 2023/2024 | 2025T1–T4, previstos na origem fixa 2024T4 | Desenvolvimento: 8/7/6/5 em h1/h2/h3/h4; final: 1 por horizonte |

Não há embaralhamento nem estatísticas globais antes da divisão. Escalas, médias, razões e premissas são calculadas somente no treino de cada origem. Baselines são comparados nas mesmas origens válidas, inclusive se outro modelo falhar em alguma janela. O teste final é um bloco de origem fixa, sem atualização durante esse bloco.

O padrão usa menor MASE médio dos três alvos primários e horizontes no **desenvolvimento**, exigindo pelo menos cinco erros por combinação e amostras completas comparáveis. O anual não cumpre essa regra e conserva o ingênuo. O limiar é uma política operacional conservadora, não teste universal de significância. O teste final não serve para reescolher o modelo. Depois da avaliação, o método é reajustado com dados até 2025 para o exercício futuro.

ARIMA/SARIMA não foram ajustados: a política exige ao menos 32 pontos trimestrais de treino mais reserva, ou 20 anuais. Esses mínimos são escolhas do projeto, não requisitos matemáticos universais. Holt anual foi descartado por menos de 8 pontos; ML complexo não foi treinado por amostra insuficiente e ausência de avaliação independente defensável. BCB não foi avaliado — não se afirma que suas variáveis não ajudariam. Preços de ações ficaram fora do escopo.

### Limite de vintages

Os arquivos são as versões disponíveis na coleta atual. O backtest respeita a ordem das observações, mas não reconstitui integralmente revisões posteriores ou os atrasos de divulgação. Portanto é uma validação **retrospectiva sobre a base congelada**, não comprovação de desempenho investível em tempo real. Essa limitação não foi ocultada sob a expressão “sem vazamento”.

## Resultados calculados

MAE/RMSE estão na unidade do alvo. sMAPE/MAPE são percentuais; o MAPE exclui bases zero e pode distorcer com valores pequenos. MASE usa variação do ingênuo no treino, com lag 1 anual ou 4 trimestral. MASE < 1 não prova vitória contra o baseline no teste.

Resumo: média dos MASEs dos **três alvos primários × horizontes**, com peso igual. A tabela completa por variável/horizonte, inclusive indicadores derivados, MAE, RMSE, sMAPE/MAPE e comparações com baselines, está em `outputs/preditiva/metricas.csv`.

| Frequência | Modelo | MASE desenvolvimento | MASE final |
|---|---|---|---|
| Anual | Crescimento médio | 3,247 | 1,673 |
| Anual | Direcionadores | 5,626 | 1,470 |
| Anual | Drift aditivo | 1,981 | 1,726 |
| Anual | Ingênuo | 1,382 | 2,517 |
| Anual | Média móvel | 2,467 | 3,237 |
| Anual | Tendência linear | 1,823 | 1,652 |
| Trimestral | Crescimento médio | 0,906 | 0,866 |
| Trimestral | Direcionadores | 0,915 | 1,031 |
| Trimestral | Drift aditivo | 1,064 | 2,223 |
| Trimestral | Holt amortecido | 0,925 | 0,855 |
| Trimestral | Holt-Winters | 0,811 | 0,880 |
| Trimestral | Ingênuo | 1,004 | 1,755 |
| Trimestral | Ingênuo sazonal | 0,712 | 0,657 |
| Trimestral | Média móvel | 0,840 | 0,862 |
| Trimestral | Tendência linear | 0,966 | 0,955 |
| Trimestral | Tendência + sazonalidade | 0,748 | 0,753 |

O sazonal teve menor escore trimestral agregado no desenvolvimento e nessa avaliação final. Modelos alternativos podem vencer em combinações isoladas; isso não estabelece superioridade estatística com um único ano reservado. Na série anual, métodos como direcionadores tiveram menor erro final que o ingênuo, mas **não foram escolhidos depois de olhar esse resultado**. Não se declara que o ingênuo seja o melhor modelo universal.

Há 2.640 registros de backtest, não 2.640 observações independentes: eles repetem alvos, modelos e horizontes sobrepostos. Resíduos têm viés e autocorrelação registrados; Ljung–Box é apenas exploratório onde há pelo menos 8 erros. Diagnósticos sem suporte ficam n/d com justificativa. Viés positivo indica subestimação.

## Coerência e cenários

Receita, EBIT CVM e lucro são as bases; margens derivam por fórmula. Ativo é projetado por sua razão histórica com receita anual ou de 12 meses; AC/PC/PNC usam proporções históricas. PL é residual: Ativo−PC−PNC. A identidade fecha em cada ponto e em cada caminho simulado. Isso não substitui um modelo de caixa/capital de giro.

Direcionadores usam crescimento histórico e margens com reversão AR(1) à média, com persistência estimada no treino e limitada a [0,1]. Margens trimestrais usam o mesmo trimestre. Receita não positiva recebe fallback explícito ao mínimo positivo observado; margens são limitadas à faixa do treino. Os ajustes centrais e simulados são contabilizados. As métricas avaliam esse pipeline completo com restrições, não modelos brutos sem limites. As restrições podem truncar riscos reais fora da história.

Pessimista/base/otimista usam quantis históricos 25/50/75, editáveis no config. Os quantis são decisões de desenho, não probabilidades estimadas. Cada override exige valor e fonte/justificativa. O crescimento usa anos completos disponíveis no treino; as margens trimestrais usam quantis do respectivo trimestre.

**Referência histórica não é necessariamente taxa efetiva aplicada.** O fator de choque de receita é [(1+g_cenário)/(1+g_mediana)] elevado ao horizonte em anos. A base conserva a previsão do modelo. Assim, o ingênuo tem crescimento efetivo zero mesmo com mediana histórica positiva. As linhas `crescimento_receita_efetivo` e `margem_*_efetiva` mostram o que realmente resulta após método, choque e limites. A sensibilidade varia uma premissa por vez entre quartis no modelo de direcionadores, sem alterar as demais.

Frequências são exercícios separados. No cenário base dos modelos padrão, as quatro receitas/lucros trimestrais de 2026 somam os valores anuais, salvo arredondamento numérico; a conferência está salva. **Outros cenários/modelos e seus balanços não são reconciliados automaticamente entre frequências.** Não devem ser combinados como um orçamento único sem política de reconciliação validada pelo grupo.

## Projeções de referência e incerteza

O padrão anual repete 2025; isso não afirma que a empresa ficará estável. Valores do cenário base abaixo em **R$ bilhões**:

| Ano | Variável | Central | Faixa exploratória |
|---|---|---|---|
| 2026 | Receita líquida | 88,24 | 77,01 a 103,80 |
| 2026 | EBIT CVM | 23,42 | 20,56 a 28,17 |
| 2026 | Lucro consolidado | 15,99 | 13,62 a 19,15 |
| 2027 | Receita líquida | 88,24 | 70,71 a 113,17 |
| 2027 | EBIT CVM | 23,42 | 18,51 a 28,92 |
| 2027 | Lucro consolidado | 15,99 | 12,69 a 20,50 |

Os CSVs incluem os 3 cenários, modelos elegíveis, indicadores e quatro trimestres de 2026: 1.248 linhas de projeção e 156 balanços centrais. Esses totais não aumentam a amostra histórica.

Faixas são quantis 10º–90º de 1.000 simulações com semente 42: resíduos fora da amostra do desenvolvimento, centrados em zero, mais estados históricos de crescimento, margens e razões patrimoniais. Os erros dos três resultados e as razões patrimoniais são amostrados conjuntamente. Identidades valem por caminho; quantis marginais de itens distintos não devem ser somados como um balanço simultâneo.

**Não há garantia de cobertura de 80%.** Mil simulações não equivalem a mil observações. O anual tem somente 2/1 resíduos por horizonte; intervalos estreitos ou limites históricos não provam segurança. A cobertura futura não foi demonstrada. Chame essas saídas de faixas exploratórias de sensibilidade, não de “80% de chance”.

ROE anual usa lucro anual / PL final. ROE trimestral usa lucro dos últimos 12 meses / PL final. Os primeiros três trimestres do corte ficam sem ROE de 12 meses, sem importar valores pré-2019 para preencher artificialmente a lacuna.

## Reproduzir e interpretar na apresentação

```bash
python -m pip install -r requirements-dev.txt
# Usa séries compactas congeladas já versionadas; não acessa a CVM:
python code/05_modelagem_preditiva.py --offline
# Reconstrói das fontes; --offline adicional exige todos os ZIPs em cache:
python code/05_modelagem_preditiva.py --preparar-dados
python code/run_pipeline.py --com-projecoes
python scripts/validar_preditiva.py
python -m pytest
```

As versões estão fixadas. A repetição no mesmo ambiente confirmou igualdade bit a bit de seis CSVs numéricos. O estágio 3 foi preservado. `outputs/preditiva/` versiona séries, referências, resultados, diagnósticos, descartes e manifesto; ZIPs grandes ficam fora do Git. O dashboard verifica hashes e usa cache por conteúdo, sem ajustar modelos. As capturas reais ficam em `docs/img/`.

Texto sugerido: “O histórico ampliado permite comparar alternativas, mas é pequeno. A referência anual mais defensável conserva o último valor e a trimestral conserva a sazonalidade. As faixas mostram sensibilidade, não precisão garantida. Algumas alternativas anuais acertaram melhor o teste reservado, mas não foram escolhidas olhando esse resultado. O estudo ajuda a discutir premissas, não determina o resultado futuro.”

Confiança qualitativa: baixa para 2026 anual; muito baixa para 2027; limitada para os trimestres, com um só ano reservado; adicionalmente dependente de razões históricas para liquidez/endividamento/ROE. Não são probabilidades estimadas.

Dados públicos atribuídos à CVM e Ambev; o portal CVM informa ODbL. A licença MIT do código não relicencia fontes nem marcas. Autores: Arthur Almeida, Nicolas Soares e Pedro Barreto.
