"""
Executa o pipeline completo da Ambev em ordem e confere cada etapa.

Uso (na raiz do projeto, com o .venv ativo):

    python code/run_pipeline.py              # etapas 1, 2 e 3
    python code/run_pipeline.py --sem-coleta # pula a Etapa 1 (usa saida/ existente)

Antes de rodar cada etapa, confere se o arquivo realmente contém o código
daquela etapa (evita, por exemplo, colar o conteúdo da Etapa 1 dentro do
03_analise_financeira.py). Depois de rodar, confere se os arquivos de saída
foram gerados e mostra os indicadores que ficaram vazios (NaN).
"""

import subprocess
import sys
from pathlib import Path

import pandas as pd

import config

PASTA_CODE = Path(__file__).resolve().parent

# (nome, arquivo, função-marcador que TEM que existir no arquivo, saídas esperadas)
ETAPAS = [
    (
        "Etapa 1 - coleta CVM",
        "analise_ambev_cvm.py",
        "def baixar_dfp",
        [config.PASTA_SAIDA_ETAPA1 / f"ambev_{tipo}_{ano}.csv"
         for ano in config.ANOS for tipo in ("dre", "ativo", "passivo")],
    ),
    (
        "Etapa 2 - tratamento",
        "02_tratamento_ambev.py",
        "def filtrar_ultimo_exercicio",
        [config.PASTA_DADOS_TRATADOS / "ambev_financeiro_2022_2025.csv"],
    ),
    (
        "Etapa 3 - indicadores",
        "03_analise_financeira.py",
        "def calcular_liquidez",
        [config.PASTA_DADOS_TRATADOS / "indicadores_financeiros_ambev.csv"],
    ),
]

INDICADORES_CHAVE = [
    "receita_liquida", "lucro_bruto", "lucro_liquido",
    "margem_bruta", "margem_operacional", "margem_liquida",
    "roa", "roe", "liquidez_corrente", "liquidez_seca",
    "endividamento_geral",
]


def falhar(mensagem):
    print(f"\n[ERRO] {mensagem}")
    sys.exit(1)


def conferir_conteudo(nome, arquivo, marcador):
    caminho = PASTA_CODE / arquivo

    if not caminho.exists():
        falhar(f"{nome}: arquivo não encontrado em {caminho}")

    texto = caminho.read_text(encoding="utf-8", errors="ignore")

    if marcador in texto:
        return

    outras = {
        "def baixar_dfp": "Etapa 1",
        "def filtrar_ultimo_exercicio": "Etapa 2",
        "def calcular_liquidez": "Etapa 3",
    }
    achada = [e for m, e in outras.items() if m in texto]

    dica = (
        f" O arquivo contém código da {achada[0]}." if achada else ""
    )

    falhar(
        f"{nome}: o arquivo {arquivo} NÃO tem o código esperado "
        f"('{marcador}').{dica} Cole nele o conteúdo correto."
    )


def conferir_saidas(nome, saidas):
    faltando = [s for s in saidas if not s.exists()]

    if faltando:
        lista = "\n  - ".join(str(f) for f in faltando)
        falhar(f"{nome}: terminou, mas não gerou:\n  - {lista}")


def resumo_indicadores():
    caminho = config.PASTA_DADOS_TRATADOS / "indicadores_financeiros_ambev.csv"

    df = pd.read_csv(caminho, encoding="utf-8-sig")

    print("\n" + "=" * 60)
    print("INDICADORES GERADOS")
    print("=" * 60)

    existentes = [c for c in ["ano_analise"] + INDICADORES_CHAVE
                  if c in df.columns]

    print(df[existentes].round(2).to_string(index=False))

    vazios = [
        c for c in INDICADORES_CHAVE
        if c not in df.columns or df[c].isna().all()
    ]

    if vazios:
        print("\n[ATENÇÃO] Sem nenhum valor em: " + ", ".join(vazios))
        print("Veja os WARNING da Etapa 2 (conta não encontrada).")
    else:
        print("\n[OK] Todos os indicadores-chave têm valores.")


def main():
    sem_coleta = "--sem-coleta" in sys.argv

    print(f"Raiz do projeto: {config.RAIZ_PROJETO}")

    # 1) valida o conteúdo de TODOS os arquivos antes de rodar qualquer coisa
    for nome, arquivo, marcador, _ in ETAPAS:
        conferir_conteudo(nome, arquivo, marcador)

    # 2) roda em ordem, conferindo as saídas de cada etapa
    for i, (nome, arquivo, _, saidas) in enumerate(ETAPAS):

        if sem_coleta and i == 0:
            print(f"\n--- {nome}: pulada (--sem-coleta) ---")
            conferir_saidas(nome, saidas)
            continue

        print(f"\n{'=' * 60}\n{nome}  ({arquivo})\n{'=' * 60}")

        resultado = subprocess.run(
            [sys.executable, str(PASTA_CODE / arquivo)],
            cwd=config.RAIZ_PROJETO,
        )

        if resultado.returncode != 0:
            falhar(f"{nome}: o script terminou com erro "
                   f"(código {resultado.returncode}). Veja o log acima.")

        conferir_saidas(nome, saidas)

    resumo_indicadores()

    print("\nPronto. Agora rode:  streamlit run code/04_visualizacao.py")


if __name__ == "__main__":
    main()