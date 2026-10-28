"""Ampliação CVM isolada do estágio 3: DFP anual, ITR acumulado e balanço trimestral."""

import hashlib
import json
import logging
import os
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import config
from analise_ambev_cvm import sessao_http
from cvm import converter_numerico, filtrar_ambev, filtrar_ultimo_exercicio, preparar_demonstrativo
from excecoes import ErroColetaCVM, ErroValidacaoDados

log = logging.getLogger(__name__)
MAPAS = {"DRE": config.CONTAS_DRE, "BPA": config.CONTAS_ATIVO, "BPP": config.CONTAS_PASSIVO}
FLUXOS = list(config.CONTAS_DRE)


def baixar_documento(documento: str, ano: int, *, offline: bool = False) -> Path:
    """Baixa ZIP com retries, valida CRC e membros; cache nunca entra no Git."""
    pasta = config.PASTA_DADOS_MODELAGEM
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"{documento.lower()}_cia_aberta_{ano}.zip"
    caminho = pasta / nome
    temporario = caminho.with_suffix(".part")
    if not caminho.exists():
        if offline:
            raise ErroColetaCVM(f"Cache preditivo ausente: {nome}.")
        try:
            with sessao_http() as sessao:
                with sessao.get(
                    f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/{documento}/DADOS/{nome}",
                    timeout=(15, 120),
                    stream=True,
                ) as resposta:
                    resposta.raise_for_status()
                    with temporario.open("wb") as arquivo:
                        for bloco in resposta.iter_content(1024 * 1024):
                            arquivo.write(bloco)
            validar_arquivo(temporario, documento, ano)
            os.replace(temporario, caminho)
        except (requests.RequestException, OSError, zipfile.BadZipFile) as erro:
            raise ErroColetaCVM(f"Falha na ampliação {documento}/{ano}: {erro}") from erro
        finally:
            temporario.unlink(missing_ok=True)
    validar_arquivo(caminho, documento, ano)
    return caminho


def validar_arquivo(caminho: Path, documento: str, ano: int) -> None:
    """Exige os três membros do ano indicado e CRC íntegro."""
    with zipfile.ZipFile(caminho) as z:
        for tipo in MAPAS:
            if f"{documento.lower()}_cia_aberta_{tipo}_con_{ano}.csv" not in z.namelist():
                raise ErroColetaCVM(f"Membro {tipo}/{ano} ausente em {caminho.name}.")
        if z.testzip():
            raise ErroColetaCVM(f"CRC inválido em {caminho.name}.")


def ler_membro(caminho: Path, documento: str, tipo: str, ano: int) -> pd.DataFrame:
    """Filtra somente a mesma empresa e preserva códigos com zeros e datas originais."""
    with zipfile.ZipFile(caminho) as z:
        with z.open(f"{documento.lower()}_cia_aberta_{tipo}_con_{ano}.csv") as arquivo:
            df = pd.read_csv(arquivo, sep=";", encoding="latin1", low_memory=False, dtype={"CD_CONTA": str})
    return filtrar_ambev(df)


def extrair_contas(df: pd.DataFrame, tipo: str) -> dict:
    """Contas-resumo exatas e únicas; ausência material não vira zero ou média."""
    if df.CD_CONTA.duplicated().any():
        raise ErroValidacaoDados("Conta repetida na mesma demonstração/período.")
    valores = df.set_index("CD_CONTA").VL_CONTA
    saida = {}
    for nome, codigo in MAPAS[tipo].items():
        if codigo not in valores:
            if nome == "lucro_bruto" and {"3.01", "3.02"} <= set(valores.index):
                log.warning("Derivando 3.03 de 3.01 + 3.02.")
                saida[nome] = valores["3.01"] + valores["3.02"]
            else:
                raise ErroValidacaoDados(f"Conta {codigo} ausente ({nome}).")
        else:
            saida[nome] = float(valores[codigo])
    return saida


def preparar_itr(
    df: pd.DataFrame, ano: int, trimestre: int, tipo: str, *, acumulado: bool = True
) -> pd.DataFrame:
    """Seleciona DT_REFER e intervalo exatos; não confunde DRE trimestral com acumulada."""
    obrigatorias = {"DT_REFER", "DT_FIM_EXERC", "VERSAO", "GRUPO_DFP", "CD_CONTA", "MOEDA"}
    if tipo == "DRE":
        obrigatorias.add("DT_INI_EXERC")
    if not obrigatorias <= set(df):
        raise ErroValidacaoDados(f"Schema ITR incompleto: {sorted(obrigatorias - set(df))}.")
    fim = pd.Period(f"{ano}Q{trimestre}", freq="Q").end_time.normalize()
    referencia = pd.to_datetime(df.DT_REFER, errors="coerce")
    grupo = df.GRUPO_DFP.astype(str).str.strip().eq(config.GRUPOS_DFP[tipo])
    atual = filtrar_ultimo_exercicio(df.loc[referencia.eq(fim) & grupo])
    atual = atual.loc[
        pd.to_numeric(atual.VERSAO, errors="raise").eq(pd.to_numeric(atual.VERSAO).max())
    ].copy()
    if not pd.to_datetime(atual.DT_FIM_EXERC, errors="coerce").eq(fim).all():
        raise ErroValidacaoDados("Fim do exercício ITR não corresponde a DT_REFER.")
    if tipo == "DRE":
        inicio = pd.Timestamp(ano, 1 if acumulado else (trimestre - 1) * 3 + 1, 1)
        atual = atual.loc[pd.to_datetime(atual.DT_INI_EXERC, errors="coerce").eq(inicio)].copy()
    if atual.empty:
        raise ErroValidacaoDados(f"ITR {ano}/T{trimestre}/{tipo}: intervalo solicitado ausente.")
    atual = converter_numerico(atual).drop_duplicates()
    if atual.CD_CONTA.duplicated().any():
        raise ErroValidacaoDados("ITR com conta ambígua no intervalo e versão selecionados.")
    return atual


def desagregar_trimestres(acumulados: pd.DataFrame, anual: pd.Series, colunas: list[str]) -> pd.DataFrame:
    """Q1=3m; Q2=6m−3m; Q3=9m−6m; Q4=DFP−9m. Balanços nunca são somados."""
    if acumulados.trimestre.duplicated().any() or set(acumulados.trimestre) != {1, 2, 3}:
        raise ErroValidacaoDados("Esperados exatamente os acumulados de 3, 6 e 9 meses.")
    dados = acumulados.set_index("trimestre").sort_index()[colunas]
    if not np.isfinite(dados.to_numpy()).all() or not np.isfinite(anual[colunas].to_numpy(dtype=float)).all():
        raise ErroValidacaoDados("DRE com valor não finito na desagregação.")
    quatro = pd.concat([dados, pd.DataFrame([anual[colunas].to_dict()], index=[4])])
    resultado = quatro.diff().fillna(quatro.iloc[0])
    if not np.allclose(resultado.sum(), anual[colunas].to_numpy(dtype=float), rtol=1e-12, atol=0.01):
        raise ErroValidacaoDados("Soma dos trimestres diverge da DFP.")
    return resultado.rename_axis("trimestre").reset_index()


def conferir_identidades(linha: dict | pd.Series) -> None:
    """Valida balanço e principais subtotalizações da DRE de cada período."""
    testes = [
        (
            linha["ativo_total"],
            linha["passivo_circulante"] + linha["passivo_nao_circulante"] + linha["patrimonio_liquido"],
        ),
        (linha["ativo_total"], linha["ativo_circulante"] + linha["ativo_nao_circulante"]),
        (linha["lucro_bruto"], linha["receita_liquida"] + linha["custo_vendas"]),
        (linha["resultado_operacional"], linha["lucro_bruto"] + linha["despesas_receitas_operacionais"]),
        (linha["lucro_liquido"], linha["resultado_continuado"] + linha["resultado_descontinuado"]),
    ]
    for esquerda, direita in testes:
        if not np.isfinite([esquerda, direita]).all() or abs(esquerda - direita) > max(
            4000, abs(esquerda) * 1e-6
        ):
            raise ErroValidacaoDados("Identidade financeira inválida na ampliação da série.")


def derivar_indicadores(df: pd.DataFrame, frequencia: str) -> pd.DataFrame:
    """Mesmas definições anuais; ROE trimestral usa lucro de 12 meses, não um trimestre."""
    df = df.sort_values("data").copy()
    df["margem_operacional"] = df.resultado_operacional / df.receita_liquida * 100
    df["margem_liquida"] = df.lucro_liquido / df.receita_liquida * 100
    df["liquidez_corrente"] = df.ativo_circulante / df.passivo_circulante
    df["passivo_exigivel"] = df.passivo_circulante + df.passivo_nao_circulante
    df["endividamento_geral"] = df.passivo_exigivel / df.ativo_total * 100
    lucro = df.lucro_liquido if frequencia == "anual" else df.lucro_liquido.rolling(4).sum()
    df["roe"] = lucro / df.patrimonio_liquido * 100
    return df


def preparar_series(*, offline: bool = False) -> dict:
    """Audita todo o histórico baixado; modelagem principal começa em 2019 por comparabilidade."""
    pasta = config.PASTA_PREDITIVA
    pasta.mkdir(parents=True, exist_ok=True)
    anuais, trimestrais, fontes, conciliacoes, versoes = [], [], [], [], []
    for ano in config.PREDITIVA_ANOS_COLETA:
        caminhos = {doc: baixar_documento(doc, ano, offline=offline) for doc in ("DFP", "ITR")}
        anual = {"data": f"{ano}-12-31", "ano": ano}
        brutos_itr = {}
        for tipo in MAPAS:
            df = preparar_demonstrativo(ler_membro(caminhos["DFP"], "DFP", tipo, ano), ano, tipo)
            anual.update(extrair_contas(df, tipo))
            brutos_itr[tipo] = ler_membro(caminhos["ITR"], "ITR", tipo, ano)
            versoes.append(
                {
                    "ano": ano,
                    "documento": "DFP",
                    "tipo": tipo,
                    "referencia": f"{ano}-12-31",
                    "versao": df.VERSAO.iloc[0],
                }
            )
        conferir_identidades(anual)
        anuais.append(anual)
        acumulados, balancos = [], {}
        diretos = {}
        for tri in (1, 2, 3):
            dre = preparar_itr(brutos_itr["DRE"], ano, tri, "DRE")
            acumulados.append({"trimestre": tri, **extrair_contas(dre, "DRE")})
            diretos[tri] = extrair_contas(
                preparar_itr(brutos_itr["DRE"], ano, tri, "DRE", acumulado=False), "DRE"
            )
            saldo = {}
            for tipo in ("BPA", "BPP"):
                df = preparar_itr(brutos_itr[tipo], ano, tri, tipo)
                saldo.update(extrair_contas(df, tipo))
            balancos[tri] = saldo
            versoes.append(
                {
                    "ano": ano,
                    "documento": "ITR",
                    "tipo": "DRE",
                    "referencia": dre.DT_REFER.iloc[0],
                    "versao": dre.VERSAO.iloc[0],
                }
            )
        balancos[4] = {k: anual[k] for tipo in ("BPA", "BPP") for k in MAPAS[tipo]}
        quadros = desagregar_trimestres(pd.DataFrame(acumulados), pd.Series(anual), FLUXOS)
        for linha in quadros.to_dict("records"):
            tri = int(linha.pop("trimestre"))
            for campo in FLUXOS:
                if tri < 4:
                    diferenca = linha[campo] - diretos[tri][campo]
                    tolerancia = max(4000, abs(linha[campo]) * 1e-6)
                    conciliacoes.append(
                        {
                            "ano": ano,
                            "trimestre": tri,
                            "conta": campo,
                            "diferenca": diferenca,
                            "verificacao": "incremento vs trimestre direto",
                            "status": "OK" if abs(diferenca) <= tolerancia else "REAPRESENTACAO",
                        }
                    )
            linha.update(balancos[tri])
            conferir_identidades(linha)
            linha.update(
                data=str(pd.Period(f"{ano}Q{tri}", freq="Q").end_time.date()), ano=ano, trimestre=tri
            )
            trimestrais.append(linha)
        for campo in FLUXOS:
            conciliacoes.append(
                {
                    "ano": ano,
                    "trimestre": 0,
                    "conta": campo,
                    "diferenca": quadros[campo].sum() - anual[campo],
                    "verificacao": "soma Q1..Q4 vs DFP",
                    "status": "OK",
                }
            )
        for doc, caminho in caminhos.items():
            with caminho.open("rb") as f:
                sha = hashlib.file_digest(f, "sha256").hexdigest()
            fontes.append(
                {
                    "ano": ano,
                    "documento": doc,
                    "arquivo": caminho.name,
                    "sha256": sha,
                    "url": f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/{doc}/DADOS/{caminho.name}",
                }
            )
    anual = derivar_indicadores(pd.DataFrame(anuais), "anual")
    tri = derivar_indicadores(pd.DataFrame(trimestrais), "trimestral")
    anual.to_csv(pasta / "serie_anual_ampliada.csv", index=False)
    tri.to_csv(pasta / "serie_trimestral_ampliada.csv", index=False)
    pd.DataFrame(conciliacoes).to_csv(pasta / "conciliacao_trimestres.csv", index=False)
    pd.DataFrame(versoes).to_csv(pasta / "versoes_contas.csv", index=False)
    # A camada nova deve preservar exatamente os históricos previamente validados.
    antigo = pd.read_csv(config.PASTA_DADOS_TRATADOS / "indicadores_financeiros_ambev.csv").set_index(
        "ano_analise"
    )
    comparavel = anual.set_index("ano").loc[antigo.index]
    for campo in config.PREDITIVA_ALVOS + config.PREDITIVA_INDICADORES:
        np.testing.assert_allclose(comparavel[campo], antigo[campo], rtol=1e-12, atol=0.01)
    main_anual = anual.loc[anual.ano >= config.PREDITIVA_ANO_INICIAL].copy()
    main_tri = derivar_indicadores(tri.loc[tri.ano >= config.PREDITIVA_ANO_INICIAL].copy(), "trimestral")
    main_anual.to_csv(pasta / "historico_anual.csv", index=False)
    main_tri.to_csv(pasta / "historico_trimestral.csv", index=False)
    diagnostico = {
        "corte_informacao": config.PREDITIVA_DATA_CORTE,
        "coleta_anos": config.PREDITIVA_ANOS_COLETA,
        "anos_modelagem": [int(main_anual.ano.min()), int(main_anual.ano.max())],
        "n_anual": len(main_anual),
        "n_trimestral": len(main_tri),
        "estrategia": "ITR trimestral ampliado e DFP anual; corte conservador em 2019",
        "comparabilidade": "Não misturar DFPs originais pré-2019 com comparativos posteriormente reapresentados por IFRS 16; período pós-IAS 29. Sem garantia de ausência de novas quebras ou efeitos macroeconômicos.",
        "reapresentacoes_trimestrais": sum(r["status"] != "OK" for r in conciliacoes),
        "aviso_vintage": "Arquivos são as versões disponíveis na coleta atual, não um arquivo de vintages em tempo real. Backtest retrospectivo pode incorporar revisões contábeis posteriores.",
        "fontes": fontes,
    }
    (pasta / "diagnostico_dados.json").write_text(
        json.dumps(diagnostico, ensure_ascii=False, indent=2) + "\n"
    )
    return diagnostico
