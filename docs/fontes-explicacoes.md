# Fontes consultadas — explicação dos resultados

Autores: Arthur Almeida, Nicolas Soares e Pedro Barreto. Acesso: 29/10/2026. Licença MIT aplica-se ao código do projeto; os PDFs são documentos da companhia e não são redistribuídos no Git.

Os quatro PDFs fornecidos pelo usuário foram lidos localmente. As URLs abaixo foram localizadas pelos links da central oficial de RI (https://ri.ambev.com.br/). O título de catálogo preserva o nome do arquivo recebido sem a extensão; o título interno consta em `documentos.csv`. Páginas são numeradas a partir de 1 e coincidem com a paginação impressa.

| Exercício | Documento | Publicação | Páginas consultadas | DRE anual | Fonte |
|---|---|---|---|---|---|
| 2022 | Divulgação de Resultados do 4T22 | 2023-03-02 | 1;2;13;14;18;26 | 26 | [RI / PDF](https://api.mziq.com/mzfilemanager/v2/d/c8182463-4b7e-408c-9d0f-42797662435e/7983151b-cdd4-aaa9-09d9-1d1c4bd82063?origin=2) |
| 2023 | Divulgação de Resultados do 4T23 | 2024-02-29 | 1;2;10;15;23 | 23 | [RI / PDF](https://api.mziq.com/mzfilemanager/v2/d/c8182463-4b7e-408c-9d0f-42797662435e/c69834fd-2291-4866-9dc8-5afb99a88f3c?origin=2) |
| 2024 | Divulgação de Resultados 4T24 | 2025-02-26 | 1;2;3;11;15;16;23 | 23 | [RI / PDF](https://api.mziq.com/mzfilemanager/v2/d/c8182463-4b7e-408c-9d0f-42797662435e/55a30c54-a040-7d6e-52e0-16cddd357cc7?origin=2) |
| 2025 | Divulgação de Resultados 4T25 | 2026-02-12 | 1;2;3;11;12;15;16;25 | 25 | [RI / PDF](https://api.mziq.com/mzfilemanager/v2/d/c8182463-4b7e-408c-9d0f-42797662435e/80e48392-1c87-1b44-0e14-399a854471d6?origin=2) |

## Rastreabilidade dos arquivos recebidos

Os SHA-256 dos PDFs estão em `dados/explicacoes/documentos.csv`. Eles identificam os anexos fornecidos, não uma promessa de identidade binária com futuras revisões da URL. A seleção de páginas e a transcrição dos totais anuais foram conferidas também nas imagens renderizadas das quatro DREs.

## Sustentabilidade

`Apresentação Sustainability Update 2023.pdf` está disponível (38 páginas; SHA-256 `4666fd69a3e32b244c05e09423876436978d0e9fbecb1a1bbcb3f91fa5c575ac`). Não foi usada para atribuir causas financeiras, nem para preencher lacunas nas explicações anuais. Não se inferiu a data de publicação a partir do nome.

## Registro das afirmações

| ID | Exercício | Tema | Página | Medida | Comparabilidade |
|---|---|---|---|---|---|
| C2022-01 | 2022 | receita | 2 | receita líquida orgânica e volume (12M22) | parcial |
| C2022-02 | 2022 | custos/margem bruta | 2 | CPV e SG&A orgânicos, excluindo depreciação e amortização (12M22) | não |
| C2022-03 | 2022 | itens não recorrentes | 14 | itens não usuais antes do EBITDA (12M22) | parcial |
| C2022-04 | 2022 | caixa/dívida | 1 | fluxo de caixa das atividades operacionais (12M22) | não |
| C2023-01 | 2023 | receita | 2 | receita líquida orgânica e desempenho da LAS (12M23) | parcial |
| C2023-02 | 2023 | custos/margem bruta | 2 | margens bruta e EBITDA ajustado, variações orgânicas (12M23) | parcial |
| C2023-03 | 2023 | lucro líquido | 15 | lucro líquido reportado; impacto IAS 29/CPC 42 (12M23) | sim |
| C2023-04 | 2023 | caixa/dívida | 1 | fluxo de caixa operacional; comentário do 4T23 (4T23) | não |
| C2024-01 | 2024 | receita | 2 | receita líquida e receita por hectolitro orgânicas (12M24) | parcial |
| C2024-02 | 2024 | custos/margem bruta | 3 | CPV e SG&A orgânicos, excluindo depreciação e amortização (12M24) | não |
| C2024-03 | 2024 | lucro líquido | 1 | lucro líquido ajustado (12M24) | não |
| C2024-04 | 2024 | impostos | 3 | despesa tributária no contexto do lucro ajustado (12M24) | parcial |
| C2025-01 | 2025 | receita | 1 | receita líquida orgânica, receita por hectolitro e volume (12M25) | parcial |
| C2025-02 | 2025 | custos/margem bruta | 3 | CPV e SG&A excluindo depreciação e amortização; EBITDA ajustado (12M25) | não |
| C2025-03 | 2025 | lucro líquido | 1 | lucro líquido ajustado (12M25) | não |
| C2025-04 | 2025 | itens não recorrentes | 12 | itens não usuais antes do EBITDA (12M25) | parcial |
| C2025-05 | 2025 | caixa/dívida | 3 | fluxo de caixa das atividades operacionais (12M25) | não |

## Pendências editoriais — não são afirmações oficiais

Os releases dos quatro anos estão disponíveis. As entradas abaixo aguardam seleção/revisão de uma explicação com escopo anual; não significam que o documento esteja ausente. Onde a página não foi selecionada, ela permanece vazia no CSV. Não atribuir ao ano uma explicação de 4T.

| ID | Exercício | Tema pendente | Material a revisar | Página |
|---|---|---|---|---|
| C2022-05 | 2022 | despesas | Release 2022; se insuficiente, notas e relatório da administração da DFP 2022 | A localizar |
| C2022-06 | 2022 | lucro líquido | Release 2022; se insuficiente, notas e relatório da administração da DFP 2022 | A localizar |
| C2022-07 | 2022 | resultado financeiro | Release 2022; se insuficiente, notas e relatório da administração da DFP 2022 | A localizar |
| C2022-08 | 2022 | impostos | Release 2022; se insuficiente, notas e relatório da administração da DFP 2022 | A localizar |
| C2023-05 | 2023 | despesas | Release 2023; se insuficiente, notas e relatório da administração da DFP 2023 | A localizar |
| C2023-06 | 2023 | resultado financeiro | Release 2023; se insuficiente, notas e relatório da administração da DFP 2023 | A localizar |
| C2023-07 | 2023 | impostos | Release 2023; se insuficiente, notas e relatório da administração da DFP 2023 | A localizar |
| C2023-08 | 2023 | itens não recorrentes | Release 2023; se insuficiente, notas e relatório da administração da DFP 2023 | A localizar |
| C2024-05 | 2024 | despesas | Release 2024; se insuficiente, notas e relatório da administração da DFP 2024 | A localizar |
| C2024-06 | 2024 | resultado financeiro | Release 2024; se insuficiente, notas e relatório da administração da DFP 2024 | A localizar |
| C2024-07 | 2024 | itens não recorrentes | Release 2024; se insuficiente, notas e relatório da administração da DFP 2024 | A localizar |
| C2024-08 | 2024 | caixa/dívida | Release 2024; se insuficiente, notas e relatório da administração da DFP 2024 | A localizar |
| C2025-06 | 2025 | despesas | Release 2025; se insuficiente, notas e relatório da administração da DFP 2025 | A localizar |
| C2025-07 | 2025 | resultado financeiro | Release 2025; se insuficiente, notas e relatório da administração da DFP 2025 | A localizar |
| C2025-08 | 2025 | impostos | Release 2025; se insuficiente, notas e relatório da administração da DFP 2025 | A localizar |

Não é necessário reenviar os releases. Para investigar itens que os releases não expliquem, o grupo pode fornecer as DFPs completas de 2022–2025 com notas e relatório da administração em `fontes/`. As páginas específicas das notas ainda não foram verificadas e não são inventadas neste anexo.

Todos os quatro textos de interpretação permanecem **rascunho (a revisar pelo grupo)**. Alterar para `revisado` exige leitura e decisão dos autores, não a execução do código.
