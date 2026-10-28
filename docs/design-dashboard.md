# Dashboard — diagnóstico, direção visual e validação

Autores: Arthur Almeida, Nicolas Soares e Pedro Barreto. Projeto Integrador III — Ciência de Dados — Fatec Cotia. Código sob licença MIT.

## Diagnóstico antes das alterações

A aplicação da branch `feat` foi executada antes das alterações da interface. Foram registradas as oito abas em dois temas e duas larguras: 1440 px e 390 px. As 32 capturas iniciais estão preservadas no ZIP local descrito abaixo; a seleção otimizada e o relatório da execução estão em [`img/antes/`](img/antes/). Não houve exceções nem transbordamento horizontal nessa matriz.

| Aspecto | O que foi observado | Efeito na leitura |
|---|---|---|
| Tipografia | Fonte Arial nas figuras; pouca diferenciação entre metadados, contexto e descrição | O dado principal disputa atenção com texto de apoio |
| Paleta | Tema azul e cores próximas dos padrões do Plotly/Streamlit | Identidade própria pouco evidente |
| Espaçamento | Grande divisor entre KPIs e análise; seções com pouca delimitação | A página transmite uma sequência de componentes independentes |
| KPIs | Quatro métricas nativas com deltas e ajuda, mas sem minigráfico | Há comparação anual, mas a trajetória de quatro anos não aparece no card |
| Gráficos | Legendas abaixo das figuras, grade recorrente e estilo baseado nos templates padrão | O leitor precisa alternar entre série e legenda fora da área principal |
| Tabelas | Muitos valores convertidos em texto para garantir pt-BR | Perde-se parte da ordenação numérica e não há tendência por linha |
| Interatividade | Filtros globais, sem estado compartilhável na URL; controles disparam execução da página | Explorar uma hipótese exige mais contexto e navegação |
| Narrativa | Título, fonte e período disponíveis, sem frase inicial sobre os resultados | É preciso encontrar e relacionar receita, variação e margem manualmente |
| Celular | KPIs e textos ocupam grande parte da rolagem | A análise começa longe da abertura |

O dashboard já tinha cascata da DRE, linhas de referência, formatação pt-BR, ajuda e avisos metodológicos. Essas capacidades foram preservadas.

## Duas direções apresentadas

| Direção | Paleta e fontes | Visão Geral |
|---|---|---|
| **Executivo moderno — escolhida** | Grafite `#141719`, âmbar, teal `#278577`, azul `#477FA8`; Manrope e fallback sans-serif | Abertura com leitura do último exercício, quatro cards de tendência e exploração coordenada |
| Editorial financeiro | Papel `#F5F1E8`, tinta `#202823`, verde `#277568`; Libre Baskerville nos títulos e Manrope no corpo | Composição de reportagem, grandes números e gráficos minimalistas |

A direção executiva foi recomendada e aplicada. O âmbar dos elementos gráficos foi ajustado para `#AE7F32` para manter contraste em ambos os fundos. Texto/acento usam variantes próprias: `#E2B566` no escuro e `#835B20` no claro. A proposta editorial não foi carregada como fonte adicional. Há apenas uma família externa, com fallback local seguro; bloquear Google Fonts não impede usar a aplicação.

Não há logotipo nem identidade gráfica oficial da Ambev. O nome identifica a empresa analisada, enquanto a apresentação pertence ao projeto.

## Compatibilidade técnica

Foi mantido **Streamlit 1.66.1**, já fixado no projeto. As assinaturas instaladas foram inspecionadas e os recursos utilizados foram exercitados em testes e/ou navegador. Essa versão oferece `st.fragment`, `st.dialog`, `st.popover`, `st.segmented_control`, `st.pills`, `st.column_config`, métricas com sparklines, seleção em Plotly e abas/widgets com estado vinculado à URL. Não foi necessário atualizar o Streamlit.

Referências primárias consultadas: [fragments](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment), [abas e estado](https://docs.streamlit.io/develop/api-reference/layout/st.tabs), [eventos Plotly](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart).

## O que mudou

- **Identidade:** tema em `.streamlit/config.toml`; tokens em `code/config.py`; CSS em `assets/estilo.css`, lido uma vez por processo; uma única função `aplicar_tema()` injeta o estilo. Cores gráficas têm sequência limitada a seis entradas; linhas também usam padrões e marcadores distintos.
- **Abertura:** resumo calculado a partir do último exercício filtrado, origem CVM, período e data real do snapshot convertida para BRT. A data do snapshot não é apresentada como data de divulgação da DFP.
- **KPIs:** valor, variação anual, fórmula e sparkline até o exercício selecionado. A comparação continua usando exatamente o ano calendário anterior, mesmo oculto pelo filtro.
- **Exploração:** um indicador atualiza figura, valor em foco e leitura da mudança anual. O usuário pode escolher linha/barras, exercício em foco, unidade monetária e percentual da receita. Percentuais e razões não recebem reescala monetária.
- **Detalhes:** um clique em ponto/barra ou o botão de contas abre um diálogo com as contas efetivamente disponíveis. A seleção é consumida uma vez, evitando reabrir o diálogo ao trocar outro controle. O botão oferece alternativa ao clique no gráfico.
- **DRE e balanço:** cascata preservada, análise vertical com mapa de calor/barras e roscas de composição com categorias mutuamente exclusivas. Subtotais da DRE continuam explicitamente identificados como sobrepostos.
- **Comparação:** dois anos explícitos, deltas absolutos e relativos e barras de mudança dos três resultados principais. A leitura não é chamada de crescimento anualizado.
- **Tabelas:** números ordenáveis, formatação pt-BR, indicador fixo, maior valor de cada linha destacado, sparkline e barra último/maior valor do recorte. A barra não é meta nem classificação de qualidade financeira.
- **Exportação:** CSV e Excel do recorte original em reais; HTML autocontido do gráfico atual. O Excel mantém células numéricas. O feedback confirma a solicitação ao navegador, sem alegar saber se o usuário concluiu a gravação.
- **Estado:** abas, anos, séries, indicador, cenário, frequência, modelo, unidade e controles de exploração usam `session_state` e o vínculo nativo `bind="query-params"`. É possível copiar a URL e abrir a mesma visão em outra sessão. Valores inválidos são tratados pelo Streamlit.
- **Atualização parcial:** fragments isolam exploração, comparação, análise vertical, projeções e exportações. Dados, preparação e exportações reutilizáveis têm cache; nenhum modelo é ajustado na interface.
- **Apresentação:** controle no topo oculta a barra lateral e amplia a leitura. O mesmo controle restaura o modo normal.

A unidade monetária altera os gráficos monetários e a tabela executiva; os KPIs/insights mantêm abreviação automática pt-BR. Margens, ROE e liquidez mantêm suas próprias unidades. Downloads mantêm a escala original, independentemente da unidade de exibição.

## Verificações e evidências

**Resultado final:** 88 testes pytest aprovados; lint aprovado; 32 capturas antes e 32 depois, mais 5 imagens complementares; nenhuma exceção ou transbordamento horizontal na matriz final. Os 30 arquivos históricos/preditivos conferidos mantiveram seus hashes.

Os testes de apresentação verificam conversões de unidade, razões sem reescala, deltas com anos ocultos, retorno numérico do Excel, restauração de URL, projeções sem treino e preservação dos KPIs no modo apresentação. Os testes anteriores permanecem ativos, incluindo validação financeira e preditiva.

A auditoria de navegador está em `scripts/auditar_visual.py` e `scripts/auditar_visual.cjs`. O roteiro cobre as oito abas, ambos os temas e larguras de desktop/celular; testa também diálogo, seleção Plotly, exportações, restauração de cenário/frequência/aba em nova sessão, troca de tema e modo apresentação. O resultado final e a lista de entradas do ZIP ficam em [`img/depois/qa.json`](img/depois/qa.json). Novas execuções gravam em `outputs/qa-visual/`, ignorado pelo Git.

As capturas finais mantêm a largura real e ampliam a altura para registrar o conteúdo das abas. As imagens `capa-*` preservam o viewport de 1440×1050 ou 390×844. Não se trata de comparação automática de pixels com o layout anterior.

As cores da paleta gráfica são testadas com contraste mínimo 3:1 nos fundos claro e escuro. Texto, apoio e acento dos tokens são testados com pelo menos 4,5:1. Isso não equivale a uma certificação completa WCAG, inspeção por leitor de tela ou validação de todas as formas de daltonismo; padrões, rótulos, números e ajuda reduzem a dependência exclusiva de cor.

A inspeção final confronta os hashes dos arquivos em `dados_tratados/` e `outputs/preditiva/` com os registrados antes do trabalho. O resultado está em [`qa-redesign.json`](qa-redesign.json). Não houve reprocessamento financeiro, nova modelagem ou modificação das premissas.

## Executar

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check code tests scripts
python -m streamlit run code/04_visualizacao.py
```

QA visual opcional, fora do deploy:

```bash
npm install --no-save playwright@1.56.1
npx playwright install chromium
python scripts/auditar_visual.py
```

Se o navegador de QA já estiver instalado em outro caminho, use `PLAYWRIGHT_CHROMIUM_EXECUTABLE`. O navegador não é dependência do aplicativo publicado.

Para o Streamlit Community Cloud, basta Python 3.12, `requirements.txt`, os arquivos locais já versionados, `assets/` e `.streamlit/`. Foi acrescentado apenas `openpyxl` com sua dependência pequena `et-xmlfile` para a exportação XLSX. Não há Kaleido, navegador ou dependência de sistema no runtime da aplicação. O HTML exportado incorpora o Plotly; o dashboard não busca fontes financeiras pela rede.

## Escolhas e limites

Não foram inventadas metas para gauges nem implementado autoplay sobre quatro anos de dados. A referência de liquidez em 1,0 é comparativa, não uma meta aprovada. As faixas preditivas, limites de evidência e aviso de investimento continuam visíveis. A reformulação não torna a previsão mais precisa.

O CSS usa seletores da versão fixada do Streamlit; uma atualização futura requer repetir a matriz visual.

A interface mantém todas as abas preparadas na navegação; fragments reduzem a execução de controles locais, mas uma mudança global de anos/unidade/tema requer atualizar os blocos dependentes. Não foi alegado um ganho de desempenho percentual sem benchmark.

A publicação no Streamlit Community Cloud depende da configuração da conta e do apontamento para a branch de entrega; não foi criada uma URL pública de aplicativo nesta revisão.


## Fechamento da publicação e política de imagens

A árvore atual mantém somente **13 imagens WebP sem perdas** em `docs/img/`: oito abas depois/escuro/desktop, três variantes adicionais da Visão Geral e duas comparações anteriores. São **1.404.618 bytes** no total; a maior tem **164.716 bytes**. Todas têm largura de até 1440 px.

A matriz completa de 64 capturas, cinco complementares, duas capturas antigas de projeções e os dois manifestos originais foram preservados em `outputs/dashboard-capturas-completas-2026-10-28.zip` (**10.205.379 bytes**). O arquivo está ignorado pelo Git. CRC e hashes das 71 imagens originais foram conferidos; nenhuma estava corrompida. A otimização não exigiu refazer a matriz validada.

As 69 imagens novas já haviam sido incluídas no commit local `ebadd58` antes desta revisão. Em respeito à proibição de reescrever o histórico, sua remoção foi feita por novos commits. Por isso os PNGs continuam acessíveis no histórico, embora não estejam na árvore atual. O peso histórico não foi eliminado; reduzir os objetos já commitados exigiria reescrever esse histórico, o que não foi feito.

A branch remota foi conferida por leitura e continua em `45e8907`, anterior ao redesign. Os objetos avulsos criados pela tentativa anterior não constituem commits publicados na branch. O `git fsck` local não encontrou corrupção; indicou somente um commit antigo sem referência, que não foi removido.

O envio agora usa o remoto SSH. As tentativas em `github.com` e `ssh.github.com:443` falharam na resolução de nomes deste ambiente; o agente SSH também não estava disponível. Não houve uso do conector para publicar blobs ou binários nesta revisão, nem push na `main`.

Para concluir de uma máquina com DNS e autenticação SSH funcionais, execute `git fetch origin feat` e `git push origin feat`. Não use `--force`. Se a branch remota avançar antes do envio, confira as alterações e integre-as preservando o histórico.
