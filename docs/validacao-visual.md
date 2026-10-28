# Validação visual e capturas

O AppTest verifica abertura, sete abas, quatro KPIs, filtro, limpeza, tema de gráficos, estado vazio e dados ausentes. As funções de preparação e exportação têm testes de preservação de valores. Isso verifica comportamento, mas não substitui inspeção de pixels, contraste e responsividade.

O job `visual` de `.github/workflows/quality.yml` inicia o Streamlit real em Ubuntu 24.04 (fixado para evitar incompatibilidade com novas imagens de runner), executa `scripts/capturar_dashboard.mjs` e disponibiliza o artefato `dashboard-capturas` com telas da visão geral escura, DRE, visão geral clara e largura móvel de 390 px. A ferramenta de QA é opcional e não entra nas dependências do aplicativo:

```bash
npm install --no-save playwright@1.56.1
npx playwright install --with-deps chromium
# Em outro terminal: python -m streamlit run code/04_visualizacao.py
# Para capturar a versão clara, inicie também o segundo servidor em outro terminal:
# python -m streamlit run code/04_visualizacao.py --server.port 8502 --theme.base light --theme.backgroundColor '#F7F9FC' --theme.secondaryBackgroundColor '#FFFFFF' --theme.textColor '#17253C' --theme.primaryColor '#2167D6'
node scripts/capturar_dashboard.mjs
```

As imagens devem vir dessa aplicação real. Não se usa ilustração gerada nem imagem de uma versão anterior como prova de funcionamento.

O tema padrão é escuro. O controle de contraste dos gráficos permite uma versão clara; a interface usa as cores do tema do Streamlit e não força fundos claros/escuros com CSS. A confirmação visual de ambos os temas e das capturas finais é registrada em `revisao-final.md`.
