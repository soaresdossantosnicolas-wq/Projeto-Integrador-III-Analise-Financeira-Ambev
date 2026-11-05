"""Rejeição de entradas sintéticas sem rede nem arquivos grandes."""

import zipfile

import pytest

import config
from excecoes import ErroColetaCVM
from seguranca_arquivos import gravar_download_limitado, validar_limites_zip


@pytest.mark.parametrize(
    "limite,valor",
    [("CVM_MAX_MEMBROS_ZIP", 0), ("CVM_MAX_DESCOMPACTADO_BYTES", 2), ("CVM_MAX_DOWNLOAD_BYTES", 1)],
)
def test_limites_zip(tmp_path, monkeypatch, limite, valor):
    caminho = tmp_path / "teste.zip"
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("dados.csv", "abc")
    monkeypatch.setattr(config, limite, valor)
    with zipfile.ZipFile(caminho) as z, pytest.raises(ErroColetaCVM, match="limite"):
        validar_limites_zip(caminho, z)


def test_caminho_malicioso(tmp_path):
    caminho = tmp_path / "teste.zip"
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("../fora.csv", "abc")
    with zipfile.ZipFile(caminho) as z, pytest.raises(ErroColetaCVM, match="caminho"):
        validar_limites_zip(caminho, z)


def test_download_conta_bytes(tmp_path, monkeypatch):
    class Resposta:
        def iter_content(self, chunk_size):
            yield b"abc"
            yield b"def"

    monkeypatch.setattr(config, "CVM_MAX_DOWNLOAD_BYTES", 4)
    with pytest.raises(ErroColetaCVM, match="Download"):
        gravar_download_limitado(Resposta(), tmp_path / "arquivo.part")
    assert (tmp_path / "arquivo.part").read_bytes() == b"abc"
