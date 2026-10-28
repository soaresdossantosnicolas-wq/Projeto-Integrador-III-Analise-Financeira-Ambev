# Publicação no Streamlit Community Cloud

## Preparação

Use Python 3.12. Instale `requirements.txt`, execute `python code/preparar_deploy.py` e confira se o dashboard abre localmente.

O deploy depende de `dados_tratados/indicadores_financeiros_ambev.csv` e `dados_tratados/metadados.json`. O código valida os campos e a correspondência do hash antes de apresentar os números. As evidências adicionais de proveniência, qualidade e ausências ficam disponíveis no repositório.

## Configuração

No Streamlit Community Cloud, escolha este repositório, a branch que contém a revisão e o arquivo principal **`code/04_visualizacao.py`**. Configure Python **3.12**. O tema está em `.streamlit/config.toml`. A aplicação não precisa baixar os ZIPs na inicialização e não exige credenciais.

A revisão não publicou um novo aplicativo e não confirmou uma URL pública existente. Após a publicação, inclua a URL real no README; não use um endereço de exemplo como se estivesse ativo.

## Atualizar dados

Execute o pipeline localmente, confira os testes e a conciliação e publique juntos o CSV e os metadados correspondentes. Consulte [dados.md](dados.md). O validador não executa Git, não altera dependências e não faz push.

Não adicione segredos a `.streamlit/config.toml`. Se integrações futuras exigirem credenciais, use os mecanismos de secrets do serviço; `.streamlit/secrets.toml` e `.env` são ignorados.

## Camada preditiva

Publique também `outputs/preditiva/` com CSVs e manifesto. A aba Projeções não baixa ITRs nem ajusta modelos no servidor. Reproduza localmente com `python code/05_modelagem_preditiva.py --offline`, usando as séries compactas versionadas.
