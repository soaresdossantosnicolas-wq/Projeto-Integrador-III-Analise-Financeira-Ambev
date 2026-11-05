# Diagnóstico e limites — O que explica os resultados?

Autores: Arthur Almeida, Nicolas Soares e Pedro Barreto. Data: 29/10/2026.

## Pré-requisito de calendário

A receita do snapshot local foi comparada com o CSV da branch `feat` obtido por consulta de leitura ao GitHub e com os releases fornecidos dos mesmos exercícios. O CSV remoto consultado contém os mesmos valores. As colunas 12M de cada ano foram conferidas visualmente nas quatro DREs. O deslocamento antigo de rótulos não está presente.

O CSV interno está em **R$**, conforme `config.py`, metadados e estágio 3. A origem CVM era R$ mil. A tabela da nova aba converte o dashboard para R$ mil e mantém a unidade original do release; jamais relê o CSV como se ainda estivesse em milhares.

| Exercício | Dashboard (R$ milhões) | Release (R$ milhões) | Diferença em reais | Página |
|---|---|---|---|---|
| 2022 | 79708.827 | 79708.8 | 27000 | 26 |
| 2023 | 79736.856 | 79736.9 | -44000 | 23 |
| 2024 | 89452.669 | 89452.7 | -31000 | 23 |
| 2025 | 88242.467 | 88242.5 | -33000 | 25 |

Tolerância: R$ 50 mil, meia unidade da precisão de 0,1 milhão do release. Não é tolerância percentual nem autorização para alterar números. O release de 2025 existe e foi publicado em 12/02/2026.

## Três camadas e critérios

1. **Cálculo:** variações do ano contra exatamente ano−1, sem usar valores do release ou projeções. Ausência do anterior, conta ausente ou base zero tem motivo explícito e n/d. Custos são exibidos em magnitude; conta 3.04 é descrita como despesa operacional líquida e não SG&A bruto. Textos descrevem relações contábeis e não atribuem motivos econômicos.
2. **Companhia:** 17 paráfrases verificadas, com documento, data, página, período, medida, unidade, URL oficial e acesso. Nenhuma frase desta camada é sintetizada a partir do CSV contábil. As outras 15 entradas têm status pendente e texto factual vazio. A revisão é manual; o script comprova estrutura e conciliação numérica, não o sentido de uma paráfrase.
3. **Grupo:** quatro propostas de leitura, todas rascunhos. Referências às camadas anteriores são rastreáveis; autoria e responsabilidade pela aprovação estão explícitas. Não se executa mudança automática para revisado.

## Reconciliação e diferenças de base

São 32 referências: 24 comparações monetárias conciliadas e 8 deliberadamente não comparáveis (lucro ajustado e crescimento orgânico, por ano). O anexo `reconciliacao-resultados.csv` contém valores originais, escala e diferenças.

O lucro operacional do release vem antes da equivalência patrimonial, apresentada em linha separada. A conta CVM 3.05 a inclui. Por ano, a reconciliação soma à medida do release a equivalência do próprio release; mantém visível a diferença antes e depois da classificação. A precisão conjunta admite até R$ 100 mil de arredondamento. Não se substitui o EBIT CVM por EBITDA ou lucro ajustado.

O crescimento orgânico não é a variação nominal consolidada. Os releases explicitam conversão, escopo e IAS 29; em 2024 houve mudança da metodologia argentina, com teto de preços para o cálculo orgânico. Nenhum percentual orgânico foi aplicado ao valor contábil para tentar conciliá-lo. Em 2025 receita orgânica positiva e receita nominal negativa são bases diferentes, não evidência de calendário errado. As divergências não explicadas bloqueiam a validação; não se escolhe uma fonte silenciosamente.

A explicação de caixa de 2023 refere-se explicitamente ao 4T23. Não é apresentada como causa anual da liquidez. Fluxos de caixa não equivalem a saldos de caixa, passivo exigível ou liquidez corrente. A menção a pagamentos de capex na narrativa de fluxo operacional do release 2022 não é usada para reclassificar capex na DFC.

## Ponte de margem

Margem operacional = 100 + CPV/receita × 100 + conta 3.04/receita × 100. A soma da margem anterior e das duas mudanças de razões fecha a margem atual. A primeira contribuição corresponde à mudança da margem bruta. Não é uma decomposição causal de preço, volume, insumos ou câmbio; cada razão agrega simultaneamente numerador e denominador. Em 2022, a ponte e variações anuais ficam n/d porque 2021 não integra o snapshot do dashboard. Não se importou silenciosamente 2021 de outro arquivo.

## Riscos e revisão do grupo

- Confirmar as quatro interpretações e o uso dos termos contábil, orgânico e ajustado na apresentação.
- Revisar os 15 temas ainda pendentes, enumerados em `fontes-explicacoes.md`. Nenhum release falta; podem ser necessárias notas e relatório da administração das DFPs 2022–2025, que não foram anexados nesta tarefa. Páginas das notas a localizar.
- Uma explicação da administração é uma atribuição da companhia, não prova econométrica de causa. Não há contrafactual ou estimação causal nesta seção.
- A documentação de sustentabilidade está disponível, mas não sustenta explicações financeiras desta entrega.
- Os PDFs ficam em `fontes/` ignorada pelo Git; no deploy só os CSVs curados são necessários. Não há download nem modelo executado na aba.

## Integração e reprodutibilidade

A cópia de trabalho iniciou em `994c8de` na branch `feat`, anterior aos merges e ao ajuste de hash feitos pelo usuário no Windows. O CSV remoto foi consultado para confirmar os valores, sem reconstituir ou sobrescrever o histórico remoto. Os commits desta entrega são incrementais e devem ser integrados preservando os dois históricos. Sem push direto em `main` e sem reescrita de histórico.

Comandos: `python -m pytest -q`; `python scripts/verificar_explicacoes.py --hashes-inicio docs/explicacoes-hashes-inicio.json`; `python scripts/verificar_links_readme.py`. O manifesto cobre os 30 arquivos históricos/preditivos existentes no início. O modo `--exigir-revisao` retorna erro enquanto restarem pendências ou rascunhos; o modo normal aceita pendências claramente rotuladas e rejeita fontes inválidas ou divergências.

## Verificação desta entrega

- `python -m pytest -q`: **115 passed in 13.03s** (88 testes anteriores e 27 novos; expectativa de quantidade de abas atualizada de 8 para 9).
- `python -m ruff check code tests scripts`: **All checks passed!**
- Auditoria normal: **30/30 hashes idênticos**, quatro anos alinhados, 17 afirmações verificadas, 15 temas pendentes, quatro rascunhos; 24 linhas monetárias conciliadas, oito medidas não comparáveis e zero divergências.
- Verificador do README: **21 alvos locais, três imagens locais, zero links quebrados**. URLs externas não são testadas por esse script; as URLs dos releases foram obtidas pela consulta à central oficial.
- `streamlit run code/04_visualizacao.py`: processo iniciado, healthcheck HTTP 200 (`ok`), sem ERROR ou Traceback no console. Renderização e interação da nova aba, anos 2022–2025, comparação, rascunhos, pendências e ausência de dados verificadas por AppTest; não foi feita nova matriz de screenshots nesta tarefa.
- PDFs de apoio ignorados pelo Git. Nenhum arquivo dos estágios históricos/preditivos foi regravado.
- `git fetch origin feat` por SSH falhou: `Could not resolve hostname github.com: Temporary failure in name resolution`. Esta entrega não foi publicada no remoto nem no aplicativo; não há declaração de sucesso do deploy.

## Como integrar os commits incrementais

O ZIP de entrega contém `explicacoes-resultados-feat.bundle` e instruções. O bundle requer o commit `994c8de7889617201322d342adc2bbe5a7abc24e`, já contido no bundle anterior, e contém somente os quatro novos commits desta seção. Em uma cópia limpa do repositório, na branch `feat`, importe com `git fetch /caminho/explicacoes-resultados-feat.bundle feat`. Se o avanço rápido não for possível, faça a integração com `git merge --no-ff --no-commit FETCH_HEAD`, confira eventuais conflitos e rode os testes antes de concluir o merge. Preserve correções remotas do usuário, incluindo o hash LF; não use `reset --hard`, rebase de histórico publicado nem push forçado. Só então publique com `git push origin feat`. Os arquivos do bundle não entram no commit.
