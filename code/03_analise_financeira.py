"""Indicadores em reais, percentuais ou razões, com diagnóstico explícito de ausências."""

import hashlib
import json
import logging

import numpy as np
import pandas as pd

import config
from excecoes import ErroValidacaoDados

log = logging.getLogger(__name__)
MONETARIOS = list(config.CONTAS_DRE) + list(config.CONTAS_ATIVO) + list(config.CONTAS_PASSIVO)


def obter_coluna(df: pd.DataFrame, nome: str) -> pd.Series:
    """Expõe ausência ao log e mantém NaN em vez de inventar zeros."""
    if nome not in df:
        log.warning("Coluna %s ausente; indicadores dependentes não disponíveis.", nome)
        return pd.Series(np.nan, index=df.index, dtype=float)
    return pd.to_numeric(df[nome], errors="coerce")


def calcular_razao(numerador: pd.Series, denominador: pd.Series) -> np.ndarray:
    """Divisão vetorizada; zero, NaN ou infinito resultam em não disponível."""
    n, d = np.broadcast_arrays(np.asarray(numerador, dtype=float), np.asarray(denominador, dtype=float))
    saida = np.full(n.shape, np.nan)
    np.divide(n, d, out=saida, where=np.isfinite(n) & np.isfinite(d) & (d != 0))
    return saida


def calcular_percentual(numerador: pd.Series, denominador: pd.Series) -> np.ndarray:
    """Retorna percentual; 40 significa 40%, não 0,40."""
    return calcular_razao(numerador, denominador) * 100


def calcular_liquidez(df: pd.DataFrame) -> pd.DataFrame:
    """Liquidez corrente e seca, em vezes, com saldo de encerramento."""
    df = df.copy()
    ac, pc, estoques = (obter_coluna(df, c) for c in ("ativo_circulante", "passivo_circulante", "estoques"))
    df["liquidez_corrente"] = calcular_razao(ac, pc)
    df["liquidez_seca"] = calcular_razao(ac - estoques, pc)
    return df


def calcular_rentabilidade(df: pd.DataFrame) -> pd.DataFrame:
    """Margens, ROA e ROE sobre saldos finais consolidados, em percentual."""
    df = df.copy()
    formulas = {
        "margem_bruta": ("lucro_bruto", "receita_liquida"),
        "margem_operacional": ("resultado_operacional", "receita_liquida"),
        "margem_liquida": ("lucro_liquido", "receita_liquida"),
        "roa": ("lucro_liquido", "ativo_total"),
        "roe": ("lucro_liquido", "patrimonio_liquido"),
    }
    for nome, (n, d) in formulas.items():
        df[nome] = calcular_percentual(obter_coluna(df, n), obter_coluna(df, d))
        if d == "patrimonio_liquido" and (obter_coluna(df, d) <= 0).any():
            log.warning("ROE/estrutura de capital: PL não positivo limita a interpretação.")
    return df


def calcular_endividamento(df: pd.DataFrame) -> pd.DataFrame:
    """Passivo exigível exclui PL; dívida financeira não se confunde com todo passivo."""
    df = df.copy()
    pc = obter_coluna(df, "passivo_circulante")
    pnc = obter_coluna(df, "passivo_nao_circulante")
    pl = obter_coluna(df, "patrimonio_liquido")
    exigivel = pc + pnc
    faltam = exigivel.isna()
    if faltam.any():
        log.warning("Passivo exigível ausente em %d linha(s); fallback = passivo CVM 2 − PL.", faltam.sum())
        exigivel = exigivel.fillna(obter_coluna(df, "passivo_total") - pl)
    df["passivo_exigivel"] = exigivel
    df["endividamento_geral"] = calcular_percentual(exigivel, obter_coluna(df, "ativo_total"))
    df["capital_terceiros_patrimonio"] = calcular_percentual(exigivel, pl)
    # Não substituir dívida financeira por passivo exigível nem EBIT por EBITDA ajustado.
    df["divida_liquida"] = obter_coluna(df, "divida_total") - obter_coluna(df, "caixa_equivalentes")
    df["divida_liquida_ebitda"] = calcular_razao(df.divida_liquida, obter_coluna(df, "ebitda_normalizado"))
    return df


def variacao_anual(serie: pd.Series, anos: pd.Series) -> np.ndarray:
    """(Atual − anterior) / |anterior| × 100; só compara anos consecutivos, sem preencher nulos."""
    resultado = calcular_percentual(serie - serie.shift(), serie.shift().abs())
    return np.where(anos.diff().eq(1), resultado, np.nan)


def calcular_crescimento(df: pd.DataFrame) -> pd.DataFrame:
    """Ordena o calendário e não transforma comparações com lacunas em crescimento anual."""
    df = df.sort_values("ano_analise").copy()
    if df.ano_analise.duplicated().any():
        raise ErroValidacaoDados("Exercício duplicado nos indicadores.")
    for coluna in ("receita_liquida", "lucro_liquido", "lucro_bruto", "ativo_total", "patrimonio_liquido"):
        if coluna in df:
            df[f"crescimento_{coluna}"] = variacao_anual(df[coluna], df.ano_analise)
    return df


def criar_analise_horizontal(df: pd.DataFrame) -> pd.DataFrame:
    """Comparação anual das contas; preserva ausências e sinais com base absoluta."""
    base = df.sort_values("ano_analise").copy()
    quadros = []
    for coluna in MONETARIOS:
        if coluna not in base:
            continue
        quadros.append(
            pd.DataFrame(
                {
                    "indicador": coluna,
                    "ano_anterior": base.ano_analise.shift(),
                    "ano_atual": base.ano_analise,
                    "valor_anterior": base[coluna].shift(),
                    "valor_atual": base[coluna],
                    "variacao_percentual": variacao_anual(base[coluna], base.ano_analise),
                }
            ).iloc[1:]
        )
    return pd.concat(quadros, ignore_index=True) if quadros else pd.DataFrame()


def criar_analise_vertical(df: pd.DataFrame) -> pd.DataFrame:
    """Cada conta da DRE / receita × 100; contas sobrepostas não devem ser somadas."""
    contas = [c for c in config.CONTAS_DRE if c in df]
    long = df.melt(id_vars="ano_analise", value_vars=contas, var_name="indicador", value_name="valor")
    long = long.merge(df[["ano_analise", "receita_liquida"]], on="ano_analise", validate="many_to_one")
    long["percentual_receita"] = calcular_percentual(long.valor, long.receita_liquida)
    return long.rename(columns={"ano_analise": "ano"})[["ano", "indicador", "valor", "percentual_receita"]]


def criar_resumo(df: pd.DataFrame) -> pd.DataFrame:
    """Compara os extremos reais do período; não troca anos com valores nulos."""
    base = df.sort_values("ano_analise")
    registros = []
    for c in list(config.FORMULAS):
        if c not in base:
            continue
        inicio, fim = base.iloc[0], base.iloc[-1]
        delta = fim[c] - inicio[c]
        registros.append(
            {
                "indicador": c,
                "primeiro_ano": inicio.ano_analise,
                "ultimo_ano": fim.ano_analise,
                "valor_inicial": inicio[c],
                "valor_final": fim[c],
                "variacao_absoluta": delta,
                "variacao_periodo_percentual": calcular_percentual(
                    pd.Series([delta]), pd.Series([abs(inicio[c])])
                )[0],
                "unidade_variacao_absoluta": "p.p."
                if c in config.PERCENTUAIS
                else "vezes"
                if c in config.RAZOES
                else "R$",
            }
        )
    return pd.DataFrame(registros)


def diagnosticar_ausencias(df: pd.DataFrame) -> pd.DataFrame:
    """Registra todo NaN exportado, inclusive primeiro ano e indicadores fora do escopo."""
    registros = []
    for coluna in df.select_dtypes(include="number"):
        for ano in df.loc[df[coluna].isna(), "ano_analise"]:
            if coluna.startswith("crescimento_"):
                motivo = "Sem par anual consecutivo válido, base zero ou valor ausente; sem preenchimento automático."
            elif coluna in {"divida_liquida", "divida_liquida_ebitda"}:
                motivo = "Dívida financeira e EBITDA normalizado não extraídos; indicador fora do escopo."
            else:
                motivo = "Entrada ausente/não finita ou denominador zero; verificar contas da base."
            registros.append({"ano": int(ano), "indicador": coluna, "motivo": motivo})
            log.info("%d/%s indisponível: %s", ano, coluna, motivo)
    return pd.DataFrame(registros, columns=["ano", "indicador", "motivo"])


def main() -> None:
    """Executa cálculos e salva indicadores, análises, resumo e diagnóstico."""
    config.preparar_pastas()
    pasta = config.PASTA_DADOS_TRATADOS
    df = pd.read_csv(pasta / f"ambev_financeiro_{config.PERIODO}.csv", encoding="utf-8-sig")
    df.columns = df.columns.str.lower()
    if df.ano_analise.duplicated().any() or set(df.ano_analise) != set(config.ANOS):
        raise ErroValidacaoDados("Base financeira com exercícios duplicados ou incompletos.")
    for funcao in (calcular_liquidez, calcular_rentabilidade, calcular_endividamento, calcular_crescimento):
        df = funcao(df)
    df.to_csv(pasta / "indicadores_financeiros_ambev.csv", index=False, encoding="utf-8-sig")
    for nome, funcao in (
        ("analise_horizontal_ambev", criar_analise_horizontal),
        ("analise_vertical_ambev", criar_analise_vertical),
        ("resumo_analise_ambev", criar_resumo),
        ("diagnostico_indicadores", diagnosticar_ausencias),
    ):
        funcao(df).to_csv(pasta / f"{nome}.csv", index=False, encoding="utf-8-sig")
    metadados = json.loads((pasta / "metadados_tratamento.json").read_text(encoding="utf-8"))
    metadados["indicadores_sha256"] = hashlib.sha256(
        (pasta / "indicadores_financeiros_ambev.csv").read_bytes()
    ).hexdigest()
    metadados["status"] = "validado"
    (pasta / "metadados.json").write_text(
        json.dumps(metadados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log.info("Indicadores e análises gravados para %s.", df.ano_analise.tolist())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    main()
