"""Executa matriz visual com navegador opcional e dois servidores locais no mesmo processo de QA."""

import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def main() -> None:
    """Captura oito abas × dois temas × duas larguras; falhas impedem sucesso silencioso."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fase", choices=["antes", "depois"], default="depois")
    args = parser.parse_args()
    processos = []
    ambiente = {**os.environ, "QA_FASE": args.fase}
    try:
        with tempfile.TemporaryDirectory(prefix="ambev-qa-") as temporario:
            for porta, claro in [(8503, False), (8504, True)]:
                comando = [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    "code/04_visualizacao.py",
                    "--server.headless=true",
                    f"--server.port={porta}",
                    "--browser.gatherUsageStats=false",
                    "--server.address=127.0.0.1",
                ]
                if claro:
                    comando += [
                        "--theme.base=light",
                        "--theme.backgroundColor=#F4F1EA",
                        "--theme.secondaryBackgroundColor=#FFFFFF",
                        "--theme.textColor=#242C29",
                        "--theme.primaryColor=#835B20",
                    ]
                with (Path(temporario) / f"servidor-{porta}.log").open("w") as registro:
                    processo = subprocess.Popen(comando, cwd=RAIZ, stdout=registro, stderr=subprocess.STDOUT)
                processos.append(processo)
                for _ in range(300):
                    if processo.poll() is not None:
                        raise RuntimeError(f"Servidor {porta} encerrou: confira a instalação do Streamlit.")
                    try:
                        with socket.create_connection(("127.0.0.1", porta), timeout=0.1):
                            break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError(f"Servidor {porta} não iniciou no prazo.")
            subprocess.run(["node", "scripts/auditar_visual.cjs"], cwd=RAIZ, env=ambiente, check=True)
    finally:
        for processo in processos:
            processo.terminate()
            processo.wait(timeout=15)


if __name__ == "__main__":
    main()
