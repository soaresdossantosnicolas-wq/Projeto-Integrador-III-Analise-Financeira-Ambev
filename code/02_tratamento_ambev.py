"""Seleciona contas CVM exatas, rejeita ambiguidade e valida identidades financeiras."""

import json
import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import config
from cvm import (  # noqa: F401 — pontos públicos mantidos para testes e uso isolado
    converter_numerico,
    filtrar_ambev,
    filtrar_ultimo_exercicio,
    preparar_demonstrativo,
)
from excecoes import ErroValidacaoDados

log = logging.getLogger(__name__)
PASTA_ENTRADA = config.PASTA_SAIDA_ETAPA1
PASTA_SAIDA = config.PASTA_DADOS_TRATADOS


def localizar_conta_por_codigo(df: pd.DataFrame, codigo: str) -> pd.DataFrame:
    """Código exato; uma subconta nunca substitui sua conta-resumo."""
    if "CD_CONTA" not in df:
        raise ErroValidacaoDados("CD_CONTA ausente.")
    encontrados = df.loc[df.CD_CONTA.astype(str).str.strip().eq(codigo)].copy()
    if encontrados.empty:
        log.warning("Conta %s não encontrada.", codigo)
    return encontrados


def carregar_demonstrativo(tipo: str, nome: str) -> pd.DataFrame:
    """Exige arquivo e exercício válidos para cada ano configurado."""
    quadros = []
    for ano in config.ANOS:
        caminho = PASTA_ENTRADA / f"ambev_{nome}_{ano}.csv"
        if not caminho.exists():
            raise ErroValidacaoDados(f"Falta {caminho.name}; execute a coleta.")
        bruto = pd.read_csv(caminho, encoding="utf-8-sig", dtype={"CD_CONTA": str})
        quadros.append(preparar_demonstrativo(bruto, ano, tipo))
    return pd.concat(quadros, ignore_index=True)


def criar_tabela_financeira(base: pd.DataFrame) -> pd.DataFrame:
    """Não agrega valores conflitantes: (ano, indicador) deve ser uma chave única."""
    if base.duplicated(["ANO_ANALISE", "INDICADOR"]).any():
        raise ErroValidacaoDados("Mais de um valor por ano/indicador; média ou first mascarariam o erro.")
    tabela = base.pivot(index="ANO_ANALISE", columns="INDICADOR", values="VL_CONTA").reset_index()
    tabela.columns.name = None
    return derivar_lucro_bruto(tabela)


def derivar_lucro_bruto(tabela: pd.DataFrame) -> pd.DataFrame:
    """Fallback contábil explícito: receita + custo negativo; nunca busca DS_CONTA."""
    tabela = tabela.copy()
    if "lucro_bruto" not in tabela:
        tabela["lucro_bruto"] = np.nan
    faltam = tabela.lucro_bruto.isna()
    if faltam.any():
        if not {"receita_liquida", "custo_vendas"} <= set(tabela):
            raise ErroValidacaoDados("Lucro bruto ausente e sem entradas para derivá-lo.")
        log.warning(
            "Conta 3.03 ausente em %s; derivando receita + custo.", tabela.loc[faltam, "ANO_ANALISE"].tolist()
        )
        tabela.loc[faltam, "lucro_bruto"] = (
            tabela.loc[faltam, "receita_liquida"] + tabela.loc[faltam, "custo_vendas"]
        )
    return tabela


def validar_igualdade(tabela: pd.DataFrame, esquerda: str, direita: pd.Series, nome: str) -> pd.DataFrame:
    """Produz evidência por ano; divergência acima do arredondamento interrompe a etapa."""
    valor = tabela[esquerda]
    diferenca = (valor - direita).abs()
    tolerancia = np.maximum(config.TOLERANCIA_ABSOLUTA, valor.abs() * config.TOLERANCIA_IDENTIDADE_CONTABIL)
    if valor.isna().any() or direita.isna().any() or (diferenca > tolerancia).any():
        raise ErroValidacaoDados(f"Identidade contábil inválida: {nome}.")
    return pd.DataFrame(
        {
            "ano": tabela.ANO_ANALISE,
            "validacao": nome,
            "diferenca_reais": diferenca,
            "tolerancia_reais": tolerancia,
            "status": "OK",
        }
    )


def validar_tabela(tabela: pd.DataFrame) -> pd.DataFrame:
    """Confere presença, finitude, calendário, balanço e encadeamento da DRE."""
    obrigatorias = set(config.CONTAS_DRE) | set(config.CONTAS_ATIVO) | set(config.CONTAS_PASSIVO)
    faltam = obrigatorias - set(tabela)
    if faltam:
        raise ErroValidacaoDados(f"Contas obrigatórias ausentes: {sorted(faltam)}.")
    if not np.isfinite(tabela[list(obrigatorias)].to_numpy()).all():
        raise ErroValidacaoDados("Contas obrigatórias com valores ausentes ou infinitos.")
    if tabela.ANO_ANALISE.duplicated().any() or set(tabela.ANO_ANALISE) != set(config.ANOS):
        raise ErroValidacaoDados("Exercícios duplicados ou incompletos.")
    if (tabela.custo_vendas > 0).any() or (tabela.receita_liquida <= 0).any():
        raise ErroValidacaoDados("Sinal inesperado: custo positivo ou receita não positiva.")
    testes = [
        ("ativo_total", tabela.passivo_total, "Ativo = Passivo + PL"),
        (
            "passivo_total",
            tabela.passivo_circulante + tabela.passivo_nao_circulante + tabela.patrimonio_liquido,
            "Passivo CVM 2 = PC + PNC + PL",
        ),
        ("ativo_total", tabela.ativo_circulante + tabela.ativo_nao_circulante, "Ativo = AC + ANC"),
        ("lucro_bruto", tabela.receita_liquida + tabela.custo_vendas, "Lucro bruto = Receita + Custo"),
        (
            "resultado_operacional",
            tabela.lucro_bruto + tabela.despesas_receitas_operacionais,
            "EBIT = Bruto + Operacionais",
        ),
        (
            "resultado_antes_tributos",
            tabela.resultado_operacional + tabela.resultado_financeiro,
            "LAIR = EBIT + Financeiro",
        ),
        (
            "resultado_continuado",
            tabela.resultado_antes_tributos + tabela.tributos_lucro,
            "Continuado = LAIR + Tributos",
        ),
        (
            "lucro_liquido",
            tabela.resultado_continuado + tabela.resultado_descontinuado,
            "Líquido = Continuado + Descontinuado",
        ),
    ]
    return pd.concat([validar_igualdade(tabela, a, b, n) for a, b, n in testes], ignore_index=True)


def validar_subtotais(df: pd.DataFrame, tipo: str) -> list[dict]:
    """Confere pais contábeis contra filhos imediatos no balanço e na conta 3.04."""
    registros = []
    for ano, dados in df.groupby("ANO_ANALISE"):
        valores = dados.set_index("CD_CONTA").VL_CONTA
        for pai in valores.index:
            if tipo == "DRE" and pai != "3.04":
                continue
            filhos = [
                c for c in valores.index if c.startswith(pai + ".") and c.count(".") == pai.count(".") + 1
            ]
            if len(filhos) < 2:
                continue
            diferenca = abs(valores[pai] - valores[filhos].sum())
            tolerancia = max(
                config.TOLERANCIA_ABSOLUTA, abs(valores[pai]) * config.TOLERANCIA_IDENTIDADE_CONTABIL
            )
            if diferenca > tolerancia:
                raise ErroValidacaoDados(
                    f"{tipo}/{ano}: subtotal {pai} não corresponde aos filhos imediatos."
                )
            registros.append(
                {
                    "ano": ano,
                    "validacao": f"{tipo} subtotal {pai}",
                    "diferenca_reais": diferenca,
                    "tolerancia_reais": tolerancia,
                    "status": "OK",
                }
            )
    return registros


def main() -> None:
    """Calcula tudo em memória e só grava as saídas após concluir as validações."""
    config.preparar_pastas()
    demonstrativos = {
        "DRE": carregar_demonstrativo("DRE", "dre"),
        "BPA": carregar_demonstrativo("BPA", "ativo"),
        "BPP": carregar_demonstrativo("BPP", "passivo"),
    }
    registros = []
    validacoes = []
    for tipo, mapa in (
        ("DRE", config.CONTAS_DRE),
        ("BPA", config.CONTAS_ATIVO),
        ("BPP", config.CONTAS_PASSIVO),
    ):
        df = demonstrativos[tipo]
        validacoes.extend(validar_subtotais(df, tipo))
        for nome, codigo in mapa.items():
            conta = localizar_conta_por_codigo(df, codigo)
            if conta.empty and nome != "lucro_bruto":
                raise ErroValidacaoDados(f"{tipo}: conta obrigatória {codigo} ({nome}) ausente.")
            registros.append(conta.assign(INDICADOR=nome))
    base = pd.concat(registros, ignore_index=True)
    tabela = criar_tabela_financeira(base)
    qualidade = pd.concat([validar_tabela(tabela), pd.DataFrame(validacoes)], ignore_index=True)
    proveniencia = base[
        ["ANO_ANALISE", "INDICADOR", "CD_CONTA", "DT_REFER", "DT_FIM_EXERC", "VERSAO", "VL_CONTA"]
    ]
    proveniencia.to_csv(PASTA_SAIDA / "proveniencia_contas.csv", index=False, encoding="utf-8-sig")
    tabela.to_csv(PASTA_SAIDA / f"ambev_financeiro_{config.PERIODO}.csv", index=False, encoding="utf-8-sig")
    qualidade.to_csv(PASTA_SAIDA / "relatorio_qualidade.csv", index=False, encoding="utf-8-sig")
    manifesto = PASTA_ENTRADA / "manifesto_coleta.json"
    metadados = {
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "anos": config.ANOS,
        "moeda": "BRL",
        "escala": "UNIDADE",
        "demonstracao": "Consolidado",
        "validacoes": len(qualidade),
        "fontes": json.loads(manifesto.read_text())["fontes"] if manifesto.exists() else [],
    }
    (PASTA_SAIDA / "metadados_tratamento.json").write_text(
        json.dumps(metadados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log.info("Tratamento concluído: %d exercícios; %d validações OK.", len(tabela), len(qualidade))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    main()
