"""Coleta DFPs, verifica ZIP/ano e preserva todas as contas da empresa para auditoria."""

import hashlib
import json
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config
from cvm import filtrar_ambev, preparar_demonstrativo
from excecoes import ErroColetaCVM

log = logging.getLogger(__name__)
PASTA_DADOS = config.PASTA_DADOS_CVM
PASTA_SAIDA = config.PASTA_SAIDA_ETAPA1


def sessao_http() -> requests.Session:
    """Repete apenas GETs transitórios, com espera crescente e timeout por tentativa."""
    sessao = requests.Session()
    retry = Retry(
        total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"]
    )
    sessao.mount("https://", HTTPAdapter(max_retries=retry))
    return sessao


def validar_zip(caminho: Path, ano: int) -> None:
    """Rejeita cache corrompido e ZIP de outro ano antes de qualquer reutilização."""
    try:
        with zipfile.ZipFile(caminho) as z:
            nomes = set(z.namelist())
            esperados = {f"dfp_cia_aberta_{tipo}_con_{ano}.csv" for tipo in config.GRUPOS_DFP}
            if not esperados <= nomes:
                raise ErroColetaCVM(f"ZIP {ano} não contém os três demonstrativos consolidados esperados.")
            corrompido = z.testzip()
            if corrompido:
                raise ErroColetaCVM(f"CRC inválido em {corrompido}.")
    except (zipfile.BadZipFile, OSError) as erro:
        raise ErroColetaCVM(f"ZIP inválido: {caminho.name}. Remova o cache e repita a coleta.") from erro


def baixar_dfp(ano: int, *, offline: bool = False) -> Path:
    """Baixa de forma atômica; um download parcial nunca substitui o cache válido."""
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    caminho = PASTA_DADOS / f"dfp_cia_aberta_{ano}.zip"
    if caminho.exists():
        validar_zip(caminho, ano)
        log.info("Cache verificado: %s", caminho.name)
        return caminho
    if offline:
        raise ErroColetaCVM(f"Modo offline: falta {caminho.name}.")
    temporario = caminho.with_suffix(".zip.part")
    try:
        with sessao_http() as sessao:
            with sessao.get(config.URL_DFP.format(ano=ano), timeout=(15, 120), stream=True) as resposta:
                resposta.raise_for_status()
                with temporario.open("wb") as arquivo:
                    for bloco in resposta.iter_content(chunk_size=1024 * 1024):
                        arquivo.write(bloco)
        validar_zip(temporario, ano)
        os.replace(temporario, caminho)
    except (requests.RequestException, OSError) as erro:
        raise ErroColetaCVM(f"Falha no download da DFP {ano}: {erro}") from erro
    finally:
        temporario.unlink(missing_ok=True)
    return caminho


def ler_csv_zip(caminho_zip: Path, nome_arquivo: str) -> pd.DataFrame:
    """Lê o membro exato em Latin-1, separado por ponto e vírgula e com códigos textuais."""
    try:
        with zipfile.ZipFile(caminho_zip) as z:
            with z.open(nome_arquivo) as arquivo:
                return pd.read_csv(
                    arquivo,
                    sep=";",
                    encoding="latin1",
                    low_memory=False,
                    dtype={"CD_CONTA": str, "CNPJ_CIA": str},
                )
    except (KeyError, zipfile.BadZipFile, OSError, pd.errors.ParserError) as erro:
        raise ErroColetaCVM(f"Não foi possível ler {nome_arquivo} em {caminho_zip.name}.") from erro


def executar_coleta(*, offline: bool = False) -> None:
    """Falha no primeiro ano inválido e só publica os CSVs após validar todos os anos."""
    config.preparar_pastas()
    preparados = []
    manifesto = {"verificado_em_utc": datetime.now(timezone.utc).isoformat(), "fontes": []}
    for ano in config.ANOS:
        caminho = baixar_dfp(ano, offline=offline)
        for tipo, nome in (("DRE", "dre"), ("BPA", "ativo"), ("BPP", "passivo")):
            membro = f"dfp_cia_aberta_{tipo}_con_{ano}.csv"
            bruto = filtrar_ambev(ler_csv_zip(caminho, membro))
            validado = preparar_demonstrativo(bruto, ano, tipo)
            preparados.append((f"ambev_{nome}_{ano}.csv", bruto))
            log.info(
                "%s/%d: %d contas atuais, versão %s, DT_REFER %s.",
                tipo,
                ano,
                len(validado),
                validado.VERSAO.iloc[0],
                validado.DT_REFER.iloc[0],
            )
        with caminho.open("rb") as arquivo_zip:
            sha256 = hashlib.file_digest(arquivo_zip, "sha256").hexdigest()
        manifesto["fontes"].append(
            {
                "ano": ano,
                "url": config.URL_DFP.format(ano=ano),
                "arquivo": caminho.name,
                "bytes": caminho.stat().st_size,
                "sha256": sha256,
            }
        )
    for nome, bruto in preparados:
        bruto.to_csv(PASTA_SAIDA / nome, index=False, encoding="utf-8-sig")
    (PASTA_SAIDA / "manifesto_coleta.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    """Ponto de entrada da coleta individual."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="exige todos os ZIPs no cache local")
    executar_coleta(offline=parser.parse_args().offline)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    main()
