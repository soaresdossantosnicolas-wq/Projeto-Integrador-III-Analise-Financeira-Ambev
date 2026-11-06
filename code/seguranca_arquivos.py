"""Limites de recursos para arquivos CVM; não extrai membros no sistema de arquivos."""

from pathlib import Path, PurePosixPath
from zipfile import ZipFile

import config
from excecoes import ErroColetaCVM


def validar_limites_zip(caminho: Path, arquivo: ZipFile) -> None:
    """Inspeciona o diretório central antes de CRC ou descompressão."""
    membros = arquivo.infolist()
    if caminho.stat().st_size > config.CVM_MAX_DOWNLOAD_BYTES:
        raise ErroColetaCVM("ZIP excede limite de download configurado.")
    if len(membros) > config.CVM_MAX_MEMBROS_ZIP:
        raise ErroColetaCVM("ZIP excede limite de membros configurado.")
    if sum(m.file_size for m in membros) > config.CVM_MAX_DESCOMPACTADO_BYTES:
        raise ErroColetaCVM("ZIP excede limite descompactado configurado.")
    for membro in membros:
        nome = membro.filename.replace("\\", "/")
        if PurePosixPath(nome).is_absolute() or ".." in PurePosixPath(nome).parts or ":" in nome:
            raise ErroColetaCVM("ZIP contém caminho de membro inválido.")


def gravar_download_limitado(resposta, destino: Path) -> None:
    """Conta bytes efetivos; não confia apenas no Content-Length informado."""
    total = 0
    with destino.open("wb") as arquivo:
        for bloco in resposta.iter_content(chunk_size=1024 * 1024):
            total += len(bloco)
            if total > config.CVM_MAX_DOWNLOAD_BYTES:
                raise ErroColetaCVM("Download excede limite configurado.")
            arquivo.write(bloco)
