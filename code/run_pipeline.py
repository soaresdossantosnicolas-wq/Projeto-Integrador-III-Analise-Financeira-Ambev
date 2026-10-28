"""Executa coleta, tratamento e indicadores com o mesmo interpretador e falha imediata."""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

import config

log = logging.getLogger(__name__)


def main() -> int:
    """Orquestra subprocessos, preservando erros e permitindo execução inteiramente offline."""
    parser = argparse.ArgumentParser(description=__doc__)
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--sem-coleta", action="store_true", help="reutiliza CSVs já extraídos em saida/")
    grupo.add_argument("--offline", action="store_true", help="executa coleta com ZIPs em cache, sem rede")
    args = parser.parse_args()
    etapas = [] if args.sem_coleta else [("analise_ambev_cvm.py", ["--offline"] if args.offline else [])]
    etapas += [("02_tratamento_ambev.py", []), ("03_analise_financeira.py", [])]
    for nome, opcoes in etapas:
        log.info("Executando %s", nome)
        resultado = subprocess.run(
            [sys.executable, str(Path(__file__).parent / nome), *opcoes], cwd=config.RAIZ_PROJETO
        )
        if resultado.returncode:
            log.error("Etapa %s falhou; saídas antigas não comprovam sucesso desta execução.", nome)
            return resultado.returncode
    log.info("Pipeline concluído. Dashboard: python -m streamlit run code/04_visualizacao.py")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    raise SystemExit(main())
