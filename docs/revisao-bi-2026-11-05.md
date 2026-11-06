# Revisão de BI, ambiente e coleta — 05/11/2026

Autores do projeto: Arthur Almeida, Nicolas Soares e Pedro Barreto. Licença MIT.

## Referência e escopo

Base: main `9f28e37ea477376afa3747d431a55c705d23947e`, que já inclui
a integração da aba de explicações. Trabalho publicado somente na feat.
Nenhum modelo foi retreinado e nenhum CSV histórico/preditivo foi regravado.
Comparação SHA-256 com os objetos Git dessa base: 30/30 arquivos idênticos.

## Etapas

1. Repositório e referência confirmados. A branch/commit efetivamente executados
   no Streamlit Cloud dependem de conferência do administrador nas configurações.
2. Dev Container alinhado a Python 3.12, instalação interrompe em caso de erro,
   sem flags para desativar CORS/XSRF. Dependências instaladas em ambiente Python
   3.12 isolado e `pip check` sem conflitos. Docker não disponível: reconstrução
   integral do container ainda precisa ser verificada no Codespaces/VS Code.
3. Integração das explicações preservada; aba posicionada antes de Projeções.
   Permanecem 17 afirmações verificadas, 15 pendências oficiais e 4 rascunhos.
   Verificador: anos 2022–2025 alinhados, 24 conciliações, 8 medidas não comparáveis,
   zero divergências. Isso não equivale a nova leitura independente de todos os PDFs.
4. Baseline identificado na interface e na tabela; sem comparação enganosa consigo
   mesmo. Faixa P10–P90 exploratória e corte temporal explícito.
5. Quinto KPI de liquidez, ROE sobre PL final, títulos descritivos, retirada da barra
   último/máximo e do destaque indiscriminado do maior valor.
6. Limites de download/ZIP aplicados a DFP e ampliação DFP/ITR, antes da descompressão.
   Testes sintéticos cobrem tamanho recebido, total descompactado, quantidade,
   tamanho comprimido e nomes com travessia de diretório.
7. Testes funcionais, estilo, hashes e auditorias executados. Matriz visual atualizada
   para nove abas, mas execução bloqueada: Chromium ausente e download inválido.
   Capturas anteriores não representam aprovação visual desta revisão.

## Segurança

`pip-audit 2.10.1 -r requirements.txt --no-deps --disable-pip --timeout 10`:
nenhuma vulnerabilidade conhecida encontrada nas versões consultadas.
`detect-secrets 1.5.0 scan --all-files code scripts tests .devcontainer .streamlit README.md`:
nenhum candidato nos caminhos examinados. Não constitui varredura de todo o
histórico Git nem prova de ausência de segredos em outros arquivos.

## Pendências externas

- Confirmar branch/arquivo/versão no Community Cloud e a nova aba em produção.
- Executar `python scripts/auditar_visual.py` com Playwright/Chromium disponível;
  inspecionar desktop/celular nos dois temas, principalmente os cinco KPIs.
- Reconstruir Dev Container em ambiente com Docker.
- Autores revisarem interpretações e completar fontes ainda pendentes.
- Auditoria completa de segredos no histórico Git permanece fora da verificação realizada.
