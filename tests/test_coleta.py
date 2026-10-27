"""Rede substituída por mocks; ZIPs criados em diretório temporário."""

import zipfile

import pytest

from excecoes import ErroColetaCVM


def criar_zip(caminho, ano):
    with zipfile.ZipFile(caminho, "w") as z:
        for tipo in ("DRE", "BPA", "BPP"):
            z.writestr(f"dfp_cia_aberta_{tipo}_con_{ano}.csv", "CD_CONTA;VL_CONTA\n3.10;0\n")


def test_zip_outro_ano_e_corrupcao(coleta, tmp_path):
    arquivo = tmp_path / "cache.zip"
    criar_zip(arquivo, 2024)
    with pytest.raises(ErroColetaCVM):
        coleta.validar_zip(arquivo, 2025)
    arquivo.write_bytes(b"download interrompido")
    with pytest.raises(ErroColetaCVM):
        coleta.validar_zip(arquivo, 2025)


def test_cache_idempotente_sem_rede(coleta, tmp_path, monkeypatch):
    arquivo = tmp_path / "dfp_cia_aberta_2025.zip"
    criar_zip(arquivo, 2025)
    monkeypatch.setattr(coleta, "PASTA_DADOS", tmp_path)
    monkeypatch.setattr(coleta, "sessao_http", lambda: pytest.fail("cache não deve acessar rede"))
    antes = arquivo.read_bytes()
    assert coleta.baixar_dfp(2025) == arquivo
    assert coleta.baixar_dfp(2025, offline=True) == arquivo
    assert arquivo.read_bytes() == antes


def test_offline_exige_cache(coleta, tmp_path, monkeypatch):
    monkeypatch.setattr(coleta, "PASTA_DADOS", tmp_path)
    with pytest.raises(ErroColetaCVM, match="offline"):
        coleta.baixar_dfp(2025, offline=True)


def test_codigo_textual_na_leitura(coleta, tmp_path):
    arquivo = tmp_path / "cache.zip"
    criar_zip(arquivo, 2025)
    df = coleta.ler_csv_zip(arquivo, "dfp_cia_aberta_DRE_con_2025.csv")
    assert df.CD_CONTA.tolist() == ["3.10"]
    with pytest.raises(ErroColetaCVM):
        coleta.ler_csv_zip(arquivo, "dfp_cia_aberta_DRE_con_2024.csv")


def test_retries_configurados(coleta):
    with coleta.sessao_http() as sessao:
        retry = sessao.get_adapter("https://").max_retries
        assert retry.total == 3
        assert 429 in retry.status_forcelist
        assert retry.allowed_methods == ["GET"]
