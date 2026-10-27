"""Concilia o snapshot com referências oficiais congeladas; execução não depende de rede."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "code"))


def conciliar(indicadores: pd.DataFrame, referencia: pd.DataFrame) -> pd.DataFrame:
    """Trata arredondamento do RI e diferença conceitual do EBIT, sem sobrescrever a CVM."""
    linhas = []
    base = indicadores.set_index("ano_analise")
    for ref in referencia.itertuples(index=False):
        valor = base.loc[ref.ano, ref.indicador]
        escala = 1 if ref.unidade == "%" else 1e6
        cvm = valor / escala
        comparavel = cvm
        conceito = "Mesmo conceito; tolerância de arredondamento do RI"
        if ref.indicador == "resultado_operacional":
            comparavel = (valor - base.loc[ref.ano, "equivalencia_patrimonial"]) / escala
            conceito = "EBIT RI = CVM 3.05 − equivalência patrimonial 3.04.06"
        tolerancia = 0.05 if ref.unidade == "%" else 0.5
        diferenca = comparavel - ref.valor_publicado
        linhas.append(
            {
                "ano": ref.ano,
                "indicador": ref.indicador,
                "unidade": ref.unidade,
                "cvm": cvm,
                "oficial_ri": ref.valor_publicado,
                "comparavel": comparavel,
                "diferenca": diferenca,
                "tolerancia": tolerancia,
                "conceito": conceito,
                "status": "OK" if np.isfinite(diferenca) and abs(diferenca) <= tolerancia else "DIVERGENTE",
            }
        )
    return pd.DataFrame(linhas)


def main() -> int:
    """Gera arquivo rastreável e devolve erro se houver divergência não conciliada."""
    indicadores = pd.read_csv(RAIZ / "dados_tratados/indicadores_financeiros_ambev.csv")
    pasta = RAIZ / "reports/validacao"
    resultado = conciliar(indicadores, pd.read_csv(pasta / "referencia_ambev.csv"))
    resultado.to_csv(pasta / "conciliacao_ambev.csv", index=False)
    print(resultado[["ano", "indicador", "diferenca", "status"]].to_string(index=False))
    return int(resultado.status.ne("OK").any())


if __name__ == "__main__":
    raise SystemExit(main())
