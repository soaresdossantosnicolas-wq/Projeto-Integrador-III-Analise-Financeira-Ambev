# Dados e reprodutibilidade

## Origem

- Portal: [CVM — DFP](https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp).
- Empresa: Ambev S.A., código CVM `23264`.
- Período configurado: 2022 a 2025.
- URL de coleta: `https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip`.

| Diretório | Conteúdo | Versionamento |
|---|---|---|
| `dados_cvm/` | Cache dos ZIPs originais | Ignorado; recriado pela coleta |
| `saida/` | CSVs extraídos e filtrados | Ignorado; recriado pela coleta |
| `dados_tratados/` | Bases limpas, análises e relatório de qualidade | Ignorado, exceto o CSV de indicadores |
| `reports/visualizacoes/` | HTMLs históricos | Preservados; não são regenerados pelo pipeline atual |

`indicadores_financeiros_ambev.csv` é um snapshot, suficiente para abrir o dashboard sem downloads. Colunas de dívida líquida e EBITDA podem estar vazias porque as entradas necessárias não são extraídas. Não substitua ausências por zero.

## Correção do snapshot em 27/10/2026

O CSV anteriormente versionado ainda continha valores monetários em milhares de reais, embora a etapa de tratamento já aplicasse a conversão de `MIL` para `UNIDADE`. O snapshot foi regenerado com o pipeline existente usando as entradas locais: por exemplo, a receita de 2022 passou de `79708827` para `79708827000` reais. Margens, retornos, liquidez e taxas de crescimento permanecem iguais. Um teste protege a ordem de grandeza do snapshot para o período atual.

## Atualizar o snapshot

1. Execute `python code/run_pipeline.py` e confira logs e relatório de qualidade.
2. Revise o diff de `dados_tratados/indicadores_financeiros_ambev.csv` e verifique mudanças inesperadas de escala ou período.
3. Execute `python -m pytest` e abra o dashboard.
4. Faça commit explícito do CSV e das alterações de código relacionadas em uma branch.

Para baixar novamente um ZIP atualizado na CVM, remova apenas o ZIP local correspondente de `dados_cvm/` antes da coleta. A coleta reutiliza arquivos já existentes. A CVM pode republicar demonstrativos; não há garantia de reprodução byte a byte após novos downloads.

Os ZIPs, CSVs intermediários e o bytecode que antes eram rastreados foram retirados da versão atual do Git. Permanecem acessíveis no histórico. Não houve reescrita do histórico; clones completos ainda podem transferir os arquivos antigos. Para obter apenas a versão recente, use `git clone --depth 1 URL_DO_REPOSITORIO`.

Os HTMLs são snapshots históricos e podem divergir do dashboard ou conter rótulos de versões anteriores. A referência de execução atual é o CSV de indicadores junto com o código e a metodologia.
