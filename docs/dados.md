# Dados, versionamento e rastreabilidade

## Origem e identidade

DFPs consolidadas da Ambev, código CVM `23264`, CNPJ `07.526.557/0001-00`, exercícios anuais 2022–2025. URL: `https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip`.

Cada ZIP contém várias empresas e os exercícios atual e comparativo. O ano do nome do arquivo não é aceito como prova do ano do valor: DT_REFER e datas do exercício são verificados antes de atribuir ANO_ANALISE. A maior VERSAO é escolhida por demonstrativo e ano; não se misturam versões por conta.

Os CSVs originais são lidos com `sep=';'`, `encoding='latin1'` e CD_CONTA textual. Exportações do pipeline usam UTF-8 com BOM. A interface exporta CSV pt-BR com ponto e vírgula e vírgula decimal, mantendo valores monetários em reais.

## O que fica no Git

| Caminho | Política |
|---|---|
| `dados_cvm/` | Ignorado; ZIPs baixados e verificados localmente |
| `saida/` | Ignorado; extratos da empresa com todas as contas e manifesto da coleta |
| `dados_tratados/indicadores_financeiros_ambev.csv` | Versionado; abre o dashboard sem coleta |
| `dados_tratados/metadados.json` | Versionado; momento da geração, fontes, hashes, versão do status e hash do CSV |
| `dados_tratados/proveniencia_contas.csv` | Versionado; ano, indicador, código, datas, versão e valor em reais |
| `dados_tratados/relatorio_qualidade.csv` | Versionado; identidades/subtotais, diferença e tolerância por ano |
| `dados_tratados/diagnostico_indicadores.csv` | Versionado; motivo de cada valor indisponível |
| Demais arquivos de `dados_tratados/` | Ignorados; bases auxiliares e análises regeneradas pelo pipeline |
| `reports/validacao/` | Versionado; evidências externas e alcance das verificações |
| `reports/historico/` | Versionado como arquivo histórico, explicitamente inadequado para resultados atuais |

## Atualização

1. Execute `python code/run_pipeline.py` ou `--offline` se todos os ZIPs estiverem no cache.
2. Leia os logs e confira as evidências de qualidade e proveniência.
3. Execute testes e `python scripts/validar_referencia.py`.
4. Revise o diff do CSV, dos metadados e das evidências. Alterações de dados reais devem ter explicação de período, versão e origem.
5. Publique na branch de trabalho para revisão antes da integração na principal.

A coleta reutiliza o cache válido. Para conferir uma republicação da CVM, mova o ZIP local correspondente para fora do cache e execute novamente a coleta. Não apague arquivos versionados para forçar essa operação.

## Download verificado na revisão

Os quatro ZIPs foram baixados novamente em 27/10/2026, validados e usados para uma nova execução completa. Seus hashes diferiam do cache anterior: a atualização do arquivo global não comprova, por si, que as contas da Ambev mudaram. As versões da Ambev encontradas eram 1 e as datas finais eram 31/12 do respectivo ano. O snapshot final foi conciliado com a referência oficial; os hashes estão em `metadados.json` e `reports/validacao/downloads.json`.

A CVM pode republicar arquivos e valores. Downloads futuros não são garantidos byte a byte; preserve o cache e os hashes para reproduzir uma execução específica.

Os ZIPs grandes antigos permanecem no histórico Git. A revisão não reescreveu o histórico. Um clone completo pode continuar pesado; `git clone --depth 1 --branch feat URL` obtém apenas a ponta recente.
