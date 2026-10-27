# Como contribuir

## Preparar o ambiente

Siga o README para criar o ambiente virtual e instale `python -m pip install -r requirements-dev.txt`.

## Fluxo de trabalho

1. Crie uma branch a partir de `main`: `git switch -c feat/descricao-curta` (ou `fix/` e `docs/`).
2. Faça alterações com escopo definido e atualize a documentação afetada.
3. Rode `python -m ruff check .` e `python -m pytest`.
4. Se alterar o cálculo ou tratamento, rode também o pipeline e confira as identidades contábeis e o diff do snapshot.
5. Se alterar a interface, abra o dashboard e confira filtros e downloads.
6. Faça commits descritivos e abra um pull request explicando o problema, a solução e a validação.

Não versione ambientes virtuais, credenciais, ZIPs da CVM, caches ou intermediários. O snapshot de indicadores é a exceção documentada em `docs/dados.md`. Não inclua arquivos gerados com `git add -f` para contornar essa política.

## Critérios de revisão

- Preserve os códigos de contas, a escala monetária e a distinção entre percentual e razão.
- Cubra mudanças de cálculo com casos sintéticos de resultado conhecido e denominadores zero ou ausentes.
- Registre alterações de período, fonte e limitações na metodologia.
- Evite reformatação ampla em mudanças de lógica; facilite a revisão do diff.

A licença do projeto ainda deve ser definida pelos autores; não adicione uma licença em nome do grupo sem essa decisão.
