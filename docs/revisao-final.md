# Revisão final — 27/10/2026

## Parecer e alcance

A revisão reforçou o contrato financeiro e temporal, redesenhou a apresentação e produziu evidências executáveis. O projeto foi validado localmente e no GitHub Actions. A publicação de um aplicativo no Streamlit Community Cloud e a integração da branch de trabalho na principal são etapas distintas e não foram executadas por esta revisão.

A branch remota `feat` mencionada na solicitação não existia no início. Foi criada a partir da `main` vigente. As classes `ErroColetaCVM` e `ErroValidacaoDados` também não existiam nessa versão e foram implementadas. O projeto não foi avaliado com base em uma suposta versão anterior não disponível.

## Problemas prioritários: estado encontrado e decisão

| Problema | Evidência lida/executada | Resultado |
|---|---|---|
| Anos deslocados | HTML histórico atribuía aproximadamente R$ 89,45 bi a 2025; DFPs e CSV atual atribuem esse valor a 2024 | O erro não estava no snapshot atual. O tratamento, entretanto, aceitava rotular o ano sem conferir datas. Agora DT_REFER, início/fim do exercício, ÚLTIMO e ANO_ANALISE preexistente são validados estritamente |
| Margens, retornos e liquidez seca totalmente NaN | Códigos 3.03, 3.11 e 1.01.04 encontrados nos demonstrativos consolidados dos quatro anos; snapshot atual já preenchido | Mantidos os códigos verificados. Removidos fallbacks inseguros e incluídos erros para contas obrigatórias ausentes, fallback contábil documentado do bruto e diagnóstico de ausências |
| Endividamento em 100% | Resultado histórico de 100%; código/snapshot atuais já usavam PC + PNC | Fórmula correta preservada e coberta por teste que impede inclusão do PL. Resultados atuais entre aproximadamente 38,72% e 39,60% |
| Valor monetário em R$ mil apresentado como reais | Corrigido antes desta revisão na main; os valores existentes foram comparados com a nova execução | Confirmados e preservados. 31 colunas comuns × 4 anos coincidem numericamente com a versão de entrada, admitindo NaN iguais |
| Diferença entre EBIT CVM e EBIT do RI | CVM 3.05 inclui equivalência patrimonial 3.04.06 | Reconciliação por conceito, sem substituir os dados CVM por valores arredondados do RI |
| Duplicatas conflitantes | Tratamento anterior usava pivot com média após aviso | Agora são erro. Linhas idênticas podem ser removidas com log; versões são escolhidas antes de exigir uma conta única |
| Crescimento com lacunas e bases negativas | Uso anterior de pct_change podia preencher nulos e discordava da análise horizontal para negativos | Convenção única: (atual − anterior) / valor absoluto do anterior, com ano consecutivo e sem preenchimento automático |
| Delta dos cards após filtro | Comparava linhas anteriores do recorte, que podiam ser anos não consecutivos | Compara o ano calendário anterior na base completa. Variações de percentuais são p.p.; endividamento usa cor inversa |
| Exposição de resultados antigos como atuais | HTMLs preservados com números incorretos e sem gerador atual | Arquivados em reports/historico/, com aviso explícito de inadequação para a entrega atual |

## Itens A–J

| Item | Estado | Resultado verificado e limite |
|---|---|---|
| A. Dados e ETL | Implementado e executado | Download real dos quatro anos; retries e falhas simuladas em testes; cache com CRC e membros exatos; escrita .part; moeda/escala/empresa/período/versão validados; leitura Latin-1 e código textual. Os hashes dos novos ZIPs globais diferem dos antigos, registrados em downloads.json |
| B. Tratamento e contas | Implementado e executado | Códigos confirmados nos CSVs brutos; seleção exata; fallback do bruto com log; 244 validações de identidades e subtotais; 84 registros de proveniência. Ausência obrigatória ou conflito impede publicação |
| C. Indicadores | Executado com limites explícitos | 28 comparações com publicação oficial do RI, todas dentro do arredondamento após reconciliar o EBIT. Mais 51 contraprovas independentes lendo os ZIPs: nove indicadores em cada ano e cinco crescimentos para cada um dos três pares anuais. Não se afirma que o RI publique todos os indicadores calculados |
| D. Dashboard funcional | Testado | Inicialização real no GitHub Actions; quatro KPIs, sete abas, filtro, limpeza, estados vazio/erro, exportação pt-BR e cache por conteúdo. O hash impede mistura de CSV e metadados |
| E. Dashboard visual | Capturas reais e testes | Tema, paleta única, pt-BR, cascata, margens/retornos, liquidez, estrutura de capital e análises vertical/horizontal. Capturas em desktop claro/escuro e móvel de 390 px; cards empilham em móvel. Teste de contraste cobre paleta ≥3:1 para elementos gráficos nos dois fundos e texto principal ≥4,5:1. Não equivale a certificação completa de acessibilidade |
| F. Código | Revisado | Contrato CVM compartilhado, exceções de domínio, funções puras para cálculos/apresentação, tipagem e docstrings, constantes centralizadas, logging, remoção de busca textual e agregação conflitante, vetorização dos cálculos. A função principal da interface segue procedural; não se afirma cobertura completa de tipos |
| G. Testes | Aprovados | 49 testes sem rede, cobrindo schema real sintético, anos, versões, duplicatas, conta ausente, fórmula de endividamento, zero/nulos, sinais, lacunas, unidade, exportação, preservação dos dados nos gráficos, contraste e AppTest. Verificar a execução do commit final no GitHub Actions |
| H. Reprodutibilidade | Validada no ambiente disponível | Python 3.12 indicado; seis dependências diretas em requirements.in e 37 pacotes do runtime com versões fixadas em requirements.txt; desenvolvimento separado; pip check aprovado; instalação limpa e CI executadas. Download futuro da CVM pode mudar; não há garantia byte a byte sem preservar o cache |
| I. Segurança e higiene | Verificada com limites | Histórico completo acessível foi buscado. Varredura heurística de 12 commits e 136 blobs únicos não encontrou assinaturas conhecidas de credenciais ou arquivos sensíveis. Não é prova universal de ausência. Autores e metadados normais dos commits não são classificados como segredo. Não houve reescrita do histórico |
| J. Documentação | Atualizada | README, metodologia, arquitetura, dados, deploy, colaboração, capturas reais, resultados, limitações, autores e licença MIT. Nenhuma URL pública de dashboard foi inventada |

## Evidências reproduzíveis

| Verificação | Comando / arquivo |
|---|---|
| Pipeline com ZIPs em cache | `python code/run_pipeline.py --offline` |
| Pipeline com download | `python code/run_pipeline.py` |
| Testes | `python -m pytest` |
| Análise estática | `python -m ruff check .` |
| Dependências instaladas | `python -m pip check` |
| Preflight de deploy | `python code/preparar_deploy.py` |
| Publicação oficial congelada | `python scripts/validar_referencia.py` |
| Contraprova sem importar cálculos do projeto | `python scripts/conferir_zip_independente.py` — exige ZIPs locais |
| Histórico Git acessível | `python scripts/verificar_segredos.py` |
| Identidades e tolerâncias | `dados_tratados/relatorio_qualidade.csv` |
| Origem exata das contas | `dados_tratados/proveniencia_contas.csv` |
| Motivo de cada n/d | `dados_tratados/diagnostico_indicadores.csv` |
| Comparação externa | `reports/validacao/conciliacao_ambev.csv` |
| Contraprovas CVM | `reports/validacao/contraprova_zip.csv` |
| Capturas e QA visual | `docs/images/` e artefato `dashboard-capturas` no GitHub Actions |

O diagnóstico atual contém 13 ausências explicadas: oito campos/anos relacionados a dívida financeira/EBITDA fora do escopo e cinco crescimentos do primeiro ano, sem base anterior. Os indicadores financeiros obrigatórios não estão vazios.

## Divergências com a publicação oficial

Receita, lucro bruto, lucro líquido consolidado, ativo total, patrimônio líquido e ROE coincidem com a publicação do RI dentro de sua precisão de arredondamento. Para EBIT, a comparação só é válida após excluir equivalência patrimonial da CVM 3.05; veja a tabela e o cálculo em metodologia.md. A margem operacional do dashboard é identificada como margem CVM e pode diferir de uma margem operacional de release com outro conceito.

Os 51 testes numéricos independentes dos ZIPs não encontraram diferença com o snapshot nos indicadores e crescimentos cobertos. As séries nominais e os retornos sobre saldos finais não foram alterados por preferência estética.

## Pendências de publicação e limites

- Não houve deploy no Streamlit Community Cloud, validação de URL pública ou configuração de domínio.
- A referência externa usa a tabela oficial publicada pelo RI, além dos arquivos originais da CVM; não foi feita leitura integral de todas as notas de quatro relatórios anuais.
- A busca de segredos é heurística e não uma auditoria especializada de todas as classes de dados pessoais. O histórico original continua acessível e volumoso.
- As capturas cobrem desktop e um viewport móvel. Não houve teste em aparelhos físicos, leitores de tela ou todos os navegadores.
- O pipeline não implementa transação única para todas as saídas; o contrato de hash protege o par final CSV/metadados consumido pelo dashboard.
- Os HTMLs históricos continuam errados por definição de arquivo histórico; estão isolados e identificados, não recalculados para aparentar serem originais corrigidos.

Autores: Arthur Almeida, Nicolas Soares e Pedro Barreto. Código sob licença MIT.
