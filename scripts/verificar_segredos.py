"""Busca heurística de segredos em blobs de todas as refs locais, sem exibir o conteúdo."""

import json
import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PADROES = {
    "chave_privada": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "token_github": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{70,})"),
    "chave_aws": re.compile(rb"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    "token_openai": re.compile(rb"sk-(?:proj-|svcacct-)[A-Za-z0-9_-]{40,}"),
}


def detectar(conteudo: bytes) -> list[str]:
    """Retorna somente os tipos de achados; nunca imprime credenciais."""
    return [nome for nome, padrao in PADROES.items() if padrao.search(conteudo)]


def main() -> int:
    """Varre objetos únicos do histórico Git acessível e registra o alcance da verificação."""
    objetos = (
        subprocess.check_output(["git", "rev-list", "--objects", "--all"], cwd=RAIZ).decode().splitlines()
    )
    achados = []
    total = 0
    processo = subprocess.Popen(
        ["git", "cat-file", "--batch"], cwd=RAIZ, stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )
    for linha in objetos:
        sha, _, caminho = linha.partition(" ")
        processo.stdin.write((sha + "\n").encode())
        processo.stdin.flush()
        cabecalho = processo.stdout.readline().decode().split()
        if len(cabecalho) != 3:
            raise RuntimeError("Objeto Git indisponível; varredura incompleta.")
        tamanho = int(cabecalho[2])
        conteudo = processo.stdout.read(tamanho)
        processo.stdout.read(1)
        if cabecalho[1] != "blob":
            continue
        total += 1
        for tipo in detectar(conteudo):
            achados.append({"objeto": sha, "caminho": caminho, "tipo": tipo})
        nome = Path(caminho).name
        if nome in {".env", "id_rsa", "id_ed25519", "secrets.toml"}:
            achados.append({"objeto": sha, "caminho": caminho, "tipo": "arquivo_sensivel"})
    processo.stdin.close()
    processo.wait()
    resultado = {
        "commits": int(subprocess.check_output(["git", "rev-list", "--count", "--all"], cwd=RAIZ)),
        "blobs_verificados": total,
        "achados": achados,
        "limite": "Heurística para formatos conhecidos; não prova ausência universal de segredos ou dados pessoais. Metadados de autores Git não são classificados como segredos.",
    }
    (RAIZ / "reports/validacao/seguranca.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return int(bool(achados))


if __name__ == "__main__":
    raise SystemExit(main())
