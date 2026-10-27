"""Contraprova independente dos indicadores, lendo as contas diretamente dos ZIPs da CVM."""

from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]


def contas(ano: int, tipo: str) -> dict:
    """Não importa funções de cálculo/tratamento do projeto; exige um registro por conta."""
    with zipfile.ZipFile(RAIZ / f"dados_cvm/dfp_cia_aberta_{ano}.zip") as z:
        bruto = pd.read_csv(
            z.open(f"dfp_cia_aberta_{tipo}_con_{ano}.csv"),
            sep=";",
            encoding="latin1",
            dtype={"CD_CONTA": str},
            low_memory=False,
        )
    df = bruto.loc[
        (bruto.CD_CVM == 23264)
        & (bruto.ORDEM_EXERC == "ÚLTIMO")
        & (bruto.DT_REFER == f"{ano}-12-31")
        & (bruto.DT_FIM_EXERC == f"{ano}-12-31")
    ].copy()
    df = df.loc[df.VERSAO == df.VERSAO.max()]
    if df.empty or df.CD_CONTA.duplicated().any() or not df.MOEDA.eq("REAL").all():
        raise ValueError(f"Dados ambíguos na contraprova: {ano}/{tipo}")
    fator = df.ESCALA_MOEDA.map({"MIL": 1000, "UNIDADE": 1})
    if fator.isna().any():
        raise ValueError("Escala desconhecida na contraprova")
    return dict(zip(df.CD_CONTA, df.VL_CONTA * fator))


def main() -> int:
    """Exporta diferenças numéricas por ano/indicador e falha se houver divergências."""
    publicado = pd.read_csv(RAIZ / "dados_tratados/indicadores_financeiros_ambev.csv").set_index(
        "ano_analise"
    )
    registros = []
    bases = {}
    for ano in [2022, 2023, 2024, 2025]:
        dre, ativo, passivo = (contas(ano, t) for t in ["DRE", "BPA", "BPP"])
        exigivel = passivo["2.01"] + passivo["2.02"]
        esperado = {
            "margem_bruta": dre["3.03"] / dre["3.01"] * 100,
            "margem_operacional": dre["3.05"] / dre["3.01"] * 100,
            "margem_liquida": dre["3.11"] / dre["3.01"] * 100,
            "roa": dre["3.11"] / ativo["1"] * 100,
            "roe": dre["3.11"] / passivo["2.03"] * 100,
            "liquidez_corrente": ativo["1.01"] / passivo["2.01"],
            "liquidez_seca": (ativo["1.01"] - ativo["1.01.04"]) / passivo["2.01"],
            "endividamento_geral": exigivel / ativo["1"] * 100,
            "capital_terceiros_patrimonio": exigivel / passivo["2.03"] * 100,
        }
        bases[ano] = dict(
            receita_liquida=dre["3.01"],
            lucro_bruto=dre["3.03"],
            lucro_liquido=dre["3.11"],
            ativo_total=ativo["1"],
            patrimonio_liquido=passivo["2.03"],
        )
        if ano > 2022:
            for campo, valor in bases[ano].items():
                anterior = bases[ano - 1][campo]
                esperado[f"crescimento_{campo}"] = (valor - anterior) / abs(anterior) * 100
        for indicador, valor in esperado.items():
            obtido = publicado.loc[ano, indicador]
            registros.append(
                dict(
                    ano=ano,
                    indicador=indicador,
                    esperado_zip=valor,
                    snapshot=obtido,
                    diferenca=obtido - valor,
                    status="OK" if np.isclose(obtido, valor, rtol=1e-12, atol=1e-10) else "DIVERGENTE",
                )
            )
    resultado = pd.DataFrame(registros)
    resultado.to_csv(RAIZ / "reports/validacao/contraprova_zip.csv", index=False)
    print(f"{len(resultado)} contraprovas: {resultado.status.eq('OK').sum()} OK")
    return int(resultado.status.ne("OK").any())


if __name__ == "__main__":
    raise SystemExit(main())
