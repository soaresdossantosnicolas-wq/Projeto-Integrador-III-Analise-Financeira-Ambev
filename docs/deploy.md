# Deploy do dashboard

O dashboard usa `dados_tratados/indicadores_financeiros_ambev.csv`, incluído no repositório. Não precisa baixar as DFPs durante a inicialização.

1. Instale `requirements.txt` no ambiente de trabalho.
2. Execute `python code/preparar_deploy.py` para validar o snapshot e as dependências locais. O comando não altera arquivos e não executa operações Git.
3. Revise e publique suas alterações por uma branch e pull request.
4. No Streamlit Community Cloud, selecione este repositório e a branch de publicação.
5. Informe `code/04_visualizacao.py` como arquivo principal e Python 3.12 como versão do ambiente.

Para testar localmente:

```bash
python -m streamlit run code/04_visualizacao.py
```

Para atualizar os dados, siga [dados.md](dados.md) e publique o novo CSV após a revisão. Os relatórios HTML históricos não são necessários para o deploy.

O antigo `preparar_deploy.py --sim` fazia commit e push. Essa automação foi removida: o script agora só valida e apresenta os próximos passos. A opção `--sim` não é mais aceita.
