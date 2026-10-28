"""Verifica alvos locais do README no disco e no índice Git, sem acessar serviços externos."""

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

RAIZ = Path(__file__).resolve().parents[1]


def main() -> int:
    """Falha se uma imagem ou outro link local apontar para conteúdo ausente/não versionado."""
    texto = (RAIZ / "README.md").read_text(encoding="utf-8")
    rastreados = set(subprocess.check_output(["git", "ls-files"], cwd=RAIZ, text=True).splitlines())
    falhas = []
    locais = set()
    imagens = set()
    externos = set()
    for marcador, alvo in re.findall(r"(!?)\[[^\]]*\]\(([^)]+)\)", texto):
        alvo = alvo.strip().strip("<>")
        url = urlsplit(alvo)
        if url.scheme or url.netloc:
            externos.add(alvo)
            continue
        if not url.path:
            continue
        caminho = unquote(url.path)
        locais.add(caminho)
        if marcador:
            imagens.add(caminho)
        p = RAIZ / caminho
        existe_git = caminho in rastreados or (
            p.is_dir() and any(r.startswith(caminho.rstrip("/") + "/") for r in rastreados)
        )
        if not p.exists() or not existe_git:
            falhas.append(caminho)
    print(
        f"README: {len(locais)} alvos locais verificados; {len(imagens)} imagens locais; {len(falhas)} links quebrados."
    )
    print(f"Links externos/badges: {len(externos)}; fora da verificação de arquivos locais.")
    for falha in sorted(set(falhas)):
        print(f"AUSENTE OU NÃO VERSIONADO: {falha}")
    return int(bool(falhas))


if __name__ == "__main__":
    raise SystemExit(main())
