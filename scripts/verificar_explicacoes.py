"""Audita fontes, páginas, reconciliação e integridade dos históricos, sem internet."""

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "code"))
from analise_explicacoes import (  # noqa: E402
    ARQUIVOS,
    reconciliar,
    validar_alinhamento,
    verificar_pendencias,
)
from excecoes import ErroValidacaoDados  # noqa: E402

log = logging.getLogger(__name__)


def main() -> int:
    """Pendência editorial gera aviso; fonte inválida, divergência ou hash diferente falha."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hashes-inicio", type=Path)
    parser.add_argument("--exigir-revisao", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        companhia, grupo, refs, docs = (
            pd.read_csv(RAIZ / "dados/explicacoes" / nome).fillna("") for nome in ARQUIVOS
        )
        df = pd.read_csv(RAIZ / "dados_tratados/indicadores_financeiros_ambev.csv")
        pendencias = verificar_pendencias(companhia, refs, docs, grupo)
        validar_alinhamento(df, refs)
        tabela = reconciliar(df, refs)
        if (tabela.resultado == "divergência").any():
            raise ErroValidacaoDados("Referências com divergência monetária não explicada.")
        for p in pendencias:
            log.warning(p)
        if args.hashes_inicio:
            hashes = json.loads(args.hashes_inicio.read_text())
            for nome, esperado in hashes.items():
                if hashlib.sha256((RAIZ / nome).read_bytes()).hexdigest() != esperado:
                    raise ErroValidacaoDados(f"Histórico alterado: {nome}")
            log.info("SHA-256: %d/%d históricos/preditivos preservados.", len(hashes), len(hashes))
        log.info("Anos alinhados: %s.", sorted(df.ano_analise.tolist()))
        log.info(
            "%d afirmações verificadas; %d pendências oficiais; %d rascunhos.",
            int((companhia.status == "verificado").sum()),
            int((companhia.status == "pendente").sum()),
            int((grupo.status == "rascunho").sum()),
        )
        log.info(
            "Reconciliação: %d conciliadas; %d não comparáveis; zero divergências.",
            int((tabela.resultado == "conciliado").sum()),
            int((tabela.resultado == "não comparável").sum()),
        )
        if args.exigir_revisao and pendencias:
            log.error("Publicação editorial final depende da revisão das pendências.")
            return 1
    except (OSError, ValueError, ErroValidacaoDados) as exc:
        log.error("Auditoria falhou: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
