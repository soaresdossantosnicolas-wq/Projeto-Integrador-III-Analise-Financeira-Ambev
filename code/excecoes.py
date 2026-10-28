"""Erros de domínio exibidos ao usuário sem mascarar falhas de programação."""


class ErroColetaCVM(RuntimeError):
    """Falha de download, integridade do ZIP ou localização do demonstrativo."""


class ErroValidacaoDados(ValueError):
    """Entrada incompatível com o contrato financeiro e temporal do pipeline."""
