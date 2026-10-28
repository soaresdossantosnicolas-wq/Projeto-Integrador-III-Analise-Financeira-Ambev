# Arquitetura e contratos

## Etapas

1. **Coleta:** `analise_ambev_cvm.py` baixa um ZIP por ano, com até três retries adicionais para GETs em falhas transitórias, espera crescente e timeout de conexão/leitura de 15/120 segundos. O download usa `.part`, valida CRC e os membros exatos e só então promove o arquivo ao cache.
2. **Contrato:** `cvm.py` seleciona a empresa por código CVM ou CNPJ exato. Exige o grupo consolidado correto, DT_REFER igual a 31/12 do ano, exercício ÚLTIMO, data final correspondente e, na DRE, início em 01/01. Seleciona a maior VERSAO do demonstrativo antes de validar a unicidade das contas.
3. **Tratamento:** `02_tratamento_ambev.py` extrai os códigos exatos do `config.py`. Duplica apenas linhas contábeis necessárias à base; não agrega conflitos. Valida contas obrigatórias, identidades e filhos imediatos dos subtotais do balanço e da conta DRE 3.04.
4. **Indicadores:** `03_analise_financeira.py` calcula razões e percentuais vetorizados. Variações anuais exigem anos consecutivos e não preenchem lacunas. Gera diagnóstico para cada NaN exportado. Metadados finais incluem o hash do CSV dos indicadores.
5. **Apresentação:** `04_visualizacao.py` carrega apenas snapshots locais. O cache usa o conteúdo do CSV como chave e valida seu hash contra os metadados. `dashboard_utils.py` contém formatação, exportação e preparação sem efeitos colaterais nos valores.

`config.py` não cria diretórios ao ser importado. Cada etapa chama `preparar_pastas()` explicitamente. Caminhos usam a localização do código, sem caminhos pessoais ou dependência do diretório atual.

## Comportamento em falhas

`ErroColetaCVM` representa problemas de rede/ZIP/membro. `ErroValidacaoDados` representa problemas de identidade, schema, período, escala ou consistência financeira. O orquestrador usa o mesmo interpretador e interrompe ao receber retorno diferente de zero.

A coleta valida todos os anos antes de gravar os CSVs da execução. O tratamento valida as entradas antes de exportar a base. Não existe uma transação atômica envolvendo todos os arquivos de todas as etapas: se a etapa 3 falhar, pode haver intermediários novos e um snapshot anterior. Não trate a existência de arquivos como prova de execução bem-sucedida. O dashboard recusa snapshots cujo hash não corresponde ao metadado final.

## Escopo e extensões

O período, os mapas de contas, a moeda, os autores e a paleta são centralizados. Para ampliar os anos, revise também referências oficiais congeladas, testes, validação do snapshot e os textos explícitos de 2022–2025 da interface. Alterar apenas ANOS não é suficiente.

Os nomes dos pontos de entrada em `code/` foram mantidos para compatibilidade. O projeto é executado por scripts; os metadados de `pyproject.toml` não prometem uma CLI instalada.
