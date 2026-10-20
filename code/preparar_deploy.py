"""
Prepara o repositório para o deploy do dashboard no Streamlit Cloud.

Uso (na raiz do projeto, com o .venv ativo):

    python code/preparar_deploy.py          # pergunta antes do commit/push
    python code/preparar_deploy.py --sim    # não pergunta

O que faz:
  1. confere se o CSV de indicadores existe (gerado pela Etapa 3);
  2. cria/atualiza o requirements.txt (streamlit, pandas, plotly);
  3. ajusta o .gitignore para o CSV de indicadores ir para o GitHub, mantendo
     fora do Git os ZIPs da CVM, a pasta saida/ e o restante de dados_tratados/;
  4. faz git add + commit + push da branch atual.

Não faz o deploy em si: esse passo é feito no site share.streamlit.io.
"""

import subprocess
import sys
from pathlib import Path

import config

RAIZ = config.RAIZ_PROJETO

CSV = config.PASTA_DADOS_TRATADOS / "indicadores_financeiros_ambev.csv"
CSV_REL = CSV.relative_to(RAIZ).as_posix()

PACOTES = ["streamlit", "pandas", "plotly"]

# linhas "básicas" do .gitignore: só entram se ainda não existirem
GITIGNORE_BASE = [".venv/", "__pycache__/", "saida/", "dados_cvm/"]

# regra que libera SÓ o CSV de indicadores dentro de dados_tratados/
GITIGNORE_DADOS = ["dados_tratados/*", f"!{CSV_REL}"]

# formas de ignorar a pasta inteira, que impedem liberar o CSV
IGNORA_PASTA_INTEIRA = {
    "dados_tratados", "dados_tratados/", "/dados_tratados", "/dados_tratados/"
}


def falhar(msg):
    print(f"\n[ERRO] {msg}")
    sys.exit(1)


def git(*args, check=True):
    return subprocess.run(
        ["git", *args], cwd=RAIZ, text=True, capture_output=True, check=check
    )


# ------------------------------------------------------------
# 1) CSV de indicadores
# ------------------------------------------------------------

def conferir_csv():
    if not CSV.exists():
        falhar(
            f"Não achei {CSV}.\n"
            "Rode antes:  python code/run_pipeline.py --sem-coleta"
        )

    linhas = CSV.read_text(encoding="utf-8-sig").strip().splitlines()

    if len(linhas) < 2:
        falhar("O CSV de indicadores está vazio (só cabeçalho).")

    tamanho_kb = CSV.stat().st_size / 1024
    print(f"[OK] {CSV_REL}: {len(linhas) - 1} linhas, {tamanho_kb:.1f} KB")


# ------------------------------------------------------------
# 2) requirements.txt
# ------------------------------------------------------------

def nome_pacote(linha):
    linha = linha.strip().lower()
    for sep in ("==", ">=", "<=", "~=", ">", "<", "["):
        linha = linha.split(sep)[0]
    return linha.strip()


def atualizar_requirements():
    caminho = RAIZ / "requirements.txt"

    existentes = []
    if caminho.exists():
        existentes = caminho.read_text(encoding="utf-8").splitlines()

    nomes = {nome_pacote(l) for l in existentes if l.strip()}
    faltando = [p for p in PACOTES if p not in nomes]

    if not caminho.exists():
        caminho.write_text("\n".join(PACOTES) + "\n", encoding="utf-8")
        print("[OK] requirements.txt criado.")
    elif faltando:
        novo = [l for l in existentes if l.strip()] + faltando
        caminho.write_text("\n".join(novo) + "\n", encoding="utf-8")
        print(f"[OK] requirements.txt atualizado (+ {', '.join(faltando)}).")
    else:
        print("[OK] requirements.txt já tem tudo.")


# ------------------------------------------------------------
# 3) .gitignore
# ------------------------------------------------------------

def atualizar_gitignore():
    caminho = RAIZ / ".gitignore"

    linhas = []
    if caminho.exists():
        linhas = caminho.read_text(encoding="utf-8").splitlines()

    # remove as regras que ignoram dados_tratados/ por inteiro
    removidas = [l for l in linhas if l.strip() in IGNORA_PASTA_INTEIRA]
    linhas = [l for l in linhas if l.strip() not in IGNORA_PASTA_INTEIRA]

    presentes = {l.strip().rstrip("/") for l in linhas}

    for regra in GITIGNORE_BASE:
        if regra.rstrip("/") not in presentes:
            linhas.append(regra)

    for regra in GITIGNORE_DADOS:
        if regra not in [l.strip() for l in linhas]:
            linhas.append(regra)

    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")

    if removidas:
        print(f"[OK] .gitignore: removida a regra {removidas} "
              "(impedia versionar o CSV).")
    print("[OK] .gitignore atualizado.")

    # confirma que o CSV deixou de ser ignorado.
    # (sem -v: com -v o git também "casa" regras de liberação "!" e
    # devolve sucesso mesmo quando o arquivo NÃO está ignorado)
    r = git("check-ignore", "-q", CSV_REL, check=False)

    if r.returncode == 0:
        regra = git("check-ignore", "-v", CSV_REL, check=False).stdout.strip()
        falhar(
            "O CSV de indicadores ainda está sendo ignorado pelo Git:\n"
            f"  {regra}\n"
            "Remova/ajuste essa regra no .gitignore e rode de novo."
        )

    print("[OK] O CSV de indicadores não é mais ignorado pelo Git.")


# ------------------------------------------------------------
# 4) commit + push
# ------------------------------------------------------------

def commit_e_push(sem_perguntar):
    if git("rev-parse", "--is-inside-work-tree", check=False).returncode != 0:
        falhar("Esta pasta não é um repositório Git.")

    # symbolic-ref funciona até em repositório sem nenhum commit ainda
    r = git("symbolic-ref", "--short", "-q", "HEAD", check=False)

    if r.returncode != 0:
        falhar("O Git está em 'detached HEAD'. Entre em uma branch "
               "(ex.: git switch feat) e rode de novo.")

    branch = r.stdout.strip()

    arquivos = [
        "requirements.txt",
        ".gitignore",
        CSV_REL,
        *[p.relative_to(RAIZ).as_posix() for p in sorted(
            (RAIZ / "code").glob("*.py"))],
    ]

    git("add", "--", *arquivos)

    status = git("status", "--short").stdout.strip()
    print("\nGit status:\n" + (status or "(sem mudanças)"))

    pendente = git("diff", "--cached", "--name-only").stdout.strip()

    if not pendente:
        print("\nNada novo para commitar.")
    else:
        if not sem_perguntar:
            resp = input(f"\nFazer commit e push da branch '{branch}'? [s/N] ")
            if resp.strip().lower() not in ("s", "sim", "y", "yes"):
                print("Cancelado. Nada foi commitado.")
                return

        git("commit", "-m", "Prepara deploy do dashboard no Streamlit Cloud")
        print("[OK] Commit criado.")

    r = git("push", "-u", "origin", "HEAD", check=False)

    if r.returncode != 0:
        falhar(f"git push falhou:\n{r.stderr.strip()}")

    url = git("remote", "get-url", "origin", check=False).stdout.strip()

    print(f"[OK] Push feito na branch '{branch}'.")
    print(f"Repositório: {url}")

    print(
        "\nPróximo passo (manual): em https://share.streamlit.io\n"
        "  New app -> escolha o repositório e a branch\n"
        f"  Branch: {branch}\n"
        "  Main file path: code/04_visualizacao.py\n"
        "  Advanced settings -> Python 3.12\n"
        "  Deploy"
    )


def main():
    print(f"Raiz do projeto: {RAIZ}\n")
    conferir_csv()
    atualizar_requirements()
    atualizar_gitignore()
    commit_e_push("--sim" in sys.argv)


if __name__ == "__main__":
    main()