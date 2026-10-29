"""Cálculos e contratos da leitura financeira; informação oficial é curadoria, nunca geração."""

from urllib.parse import urlparse

import numpy as np
import pandas as pd

import config
from dashboard_utils import formatar_indicador, formatar_percentual, formatar_valor, numero_br
from excecoes import ErroValidacaoDados

ARQUIVOS = (
    "explicacoes_companhia.csv",
    "interpretacao_grupo.csv",
    "referencias_reconciliacao.csv",
    "documentos.csv",
)

COLUNAS_COMPANHIA = {
    "id",
    "ano",
    "tema",
    "afirmacao_parafraseada",
    "documento",
    "data_publicacao",
    "pagina",
    "url",
    "medida",
    "unidade",
    "periodo",
    "comparavel_dashboard",
    "observacao",
    "data_acesso",
    "status",
}
COLUNAS_GRUPO = {"ano", "texto", "evidencias", "limitacoes", "status", "autores"}
COLUNAS_REFERENCIAS = {
    "ano",
    "indicador_dashboard",
    "indicador_release",
    "valor_release",
    "unidade_original",
    "fator_reais",
    "ajuste_equivalencia_release",
    "medida",
    "comparavel_dashboard",
    "motivo",
    "documento",
    "data_publicacao",
    "pagina",
    "url",
    "data_acesso",
    "status",
}
COLUNAS_DOCUMENTOS = {
    "ano",
    "documento",
    "titulo_interno",
    "data_publicacao",
    "pagina_dre",
    "numero_paginas",
    "url",
    "data_acesso",
    "sha256_pdf",
    "status",
    "origem",
    "paginas_consultadas",
}
CAMPOS_CALCULADOS = [
    "receita_liquida",
    "custo_vendas",
    "despesas_receitas_operacionais",
    "lucro_liquido",
    "margem_bruta",
    "margem_operacional",
    "margem_liquida",
    "liquidez_corrente",
    "endividamento_geral",
]
HOSTS_OFICIAIS = {
    "ri.ambev.com.br",
    "api.mziq.com",
    "filemanager-cdn.mziq.com",
    "www.rad.cvm.gov.br",
    "dados.cvm.gov.br",
    "www.sec.gov",
}


def exigir_colunas(df: pd.DataFrame, colunas: set[str]) -> None:
    """Valida schema e ano sem coerção silenciosa de calendário."""
    if faltam := colunas - set(df):
        raise ErroValidacaoDados(f"Schema incompleto: {sorted(faltam)}.")
    anos = pd.to_numeric(df.ano, errors="coerce")
    if anos.isna().any() or (anos % 1 != 0).any():
        raise ErroValidacaoDados("Exercício inválido na curadoria.")


def _validar_fonte(row: pd.Series) -> None:
    """Toda linha verificada exige documento, página, medida, unidade e datas."""
    for campo in ["documento", "data_publicacao", "pagina", "url", "medida", "data_acesso"]:
        if pd.isna(row[campo]) or not str(row[campo]).strip():
            raise ErroValidacaoDados(f"Fonte incompleta: {campo} obrigatório.")
    pagina = pd.to_numeric(row.pagina, errors="coerce")
    if not np.isfinite(pagina) or pagina < 1 or pagina % 1:
        raise ErroValidacaoDados("Página deve ser um inteiro positivo.")
    url = urlparse(str(row.url))
    if url.scheme != "https" or url.hostname not in HOSTS_OFICIAIS:
        raise ErroValidacaoDados("URL fora dos domínios oficiais aceitos.")
    for campo in ["data_publicacao", "data_acesso"]:
        try:
            data = pd.to_datetime(row[campo], format="%Y-%m-%d", errors="raise")
        except (ValueError, TypeError) as exc:
            raise ErroValidacaoDados(f"Data inválida: {campo}.") from exc
        if pd.isna(data):
            raise ErroValidacaoDados(f"Data ausente: {campo}.")
    if row.data_publicacao > row.data_acesso:
        raise ErroValidacaoDados("Acesso anterior à publicação.")
    if row.comparavel_dashboard not in {"sim", "parcial", "não"}:
        raise ErroValidacaoDados("Comparabilidade deve ser sim, parcial ou não.")


def validar_companhia(df: pd.DataFrame) -> pd.DataFrame:
    """Pendências podem não ter fonte, mas jamais podem carregar afirmações oficiais."""
    exigir_colunas(df, COLUNAS_COMPANHIA)
    if not df.status.isin(["verificado", "pendente"]).all() or df.id.duplicated().any():
        raise ErroValidacaoDados("Status ou identificador inválido na camada oficial.")
    for _, row in df.iterrows():
        if row.status == "pendente":
            if pd.notna(row.afirmacao_parafraseada) and str(row.afirmacao_parafraseada).strip():
                raise ErroValidacaoDados("Entrada pendente não pode apresentar afirmação como fato.")
            if pd.isna(row.observacao) or not str(row.observacao).strip():
                raise ErroValidacaoDados("Pendência exige motivo e material a localizar.")
        else:
            _validar_fonte(row)
            for campo in ["afirmacao_parafraseada", "unidade", "periodo", "tema", "observacao"]:
                if pd.isna(row[campo]) or not str(row[campo]).strip():
                    raise ErroValidacaoDados(f"Entrada verificada sem {campo}.")
    return df.copy()


def validar_grupo(df: pd.DataFrame) -> pd.DataFrame:
    """Impede interpretação anônima, sem evidências ou com status implícito."""
    exigir_colunas(df, COLUNAS_GRUPO)
    if df.ano.duplicated().any() or not df.status.isin(["rascunho", "revisado"]).all():
        raise ErroValidacaoDados("Status ou ano inválido na interpretação.")
    for campo in COLUNAS_GRUPO - {"ano"}:
        if df[campo].isna().any() or df[campo].astype(str).str.strip().eq("").any():
            raise ErroValidacaoDados(f"Interpretação sem {campo}.")
    return df.copy()


def validar_referencias(df: pd.DataFrame) -> pd.DataFrame:
    """Confere a escala e impede tratar medidas ajustadas/orgânicas como contábeis."""
    exigir_colunas(df, COLUNAS_REFERENCIAS)
    if df.duplicated(["ano", "indicador_release"]).any():
        raise ErroValidacaoDados("Referência anual duplicada.")
    for _, row in df.iterrows():
        _validar_fonte(row)
        if row.status != "verificado" or not np.isfinite(float(row.valor_release)):
            raise ErroValidacaoDados("Referência numérica não verificada.")
        if not str(row.motivo).strip() or pd.isna(row.motivo):
            raise ErroValidacaoDados("Reconciliação exige motivo da diferença.")
        if row.comparavel_dashboard != "não":
            if row.unidade_original != "R$ milhões" or float(row.fator_reais) != 1e6:
                raise ErroValidacaoDados("Escala inválida para reconciliação monetária.")
            if row.medida != "reportada/contábil":
                raise ErroValidacaoDados("Medida diferente não pode ser conciliada como contábil.")
        if row.comparavel_dashboard == "parcial" and row.indicador_release != "resultado_operacional":
            raise ErroValidacaoDados("Ajuste de classificação não implementado para esta medida.")
    return df.copy()


def validar_catalogo(companhia: pd.DataFrame, refs: pd.DataFrame, docs: pd.DataFrame) -> None:
    """Vincula fontes verificadas ao catálogo e limita páginas ao tamanho real do PDF."""
    exigir_colunas(docs, COLUNAS_DOCUMENTOS)
    if docs.duplicated(["ano", "documento"]).any():
        raise ErroValidacaoDados("Documento duplicado no catálogo.")
    for _, row in pd.concat([companhia, refs], ignore_index=True).iterrows():
        if row.status != "verificado":
            continue
        doc = docs[(docs.ano == row.ano) & (docs.documento == row.documento)]
        if len(doc) != 1:
            raise ErroValidacaoDados("Fonte não consta do catálogo consultado.")
        fonte = doc.iloc[0]
        if row.url != fonte.url or row.data_publicacao != fonte.data_publicacao:
            raise ErroValidacaoDados("URL ou data diverge do documento catalogado.")
        if float(row.pagina) > float(fonte.numero_paginas):
            raise ErroValidacaoDados("Página fora do documento.")


def _valor(linha: pd.Series | None, campo: str) -> float:
    """Converte somente valores finitos; ausência permanece explícita."""
    if linha is None:
        return np.nan
    v = pd.to_numeric(linha.get(campo, np.nan), errors="coerce")
    return float(v) if np.isfinite(v) else np.nan


def calcular_camada1(df: pd.DataFrame, ano: int) -> pd.DataFrame:
    """Compara ano exato a ano−1; contas de custo são despesas líquidas em magnitude."""
    if "ano_analise" not in df or df.ano_analise.duplicated().any():
        raise ErroValidacaoDados("Histórico sem calendário único.")
    atual = df[df.ano_analise == ano]
    anterior = df[df.ano_analise == ano - 1]
    a = atual.iloc[0] if len(atual) else None
    p = anterior.iloc[0] if len(anterior) else None
    saida = []
    for campo in CAMPOS_CALCULADOS:
        v, ant = _valor(a, campo), _valor(p, campo)
        # A conta 3.04 é líquida: jamais chamá-la de SG&A bruto.
        if campo in {"custo_vendas", "despesas_receitas_operacionais"}:
            v, ant = -v, -ant
        motivo = ""
        if not np.isfinite(v):
            motivo = "Exercício ou conta ausente no snapshot."
        elif not np.isfinite(ant):
            motivo = "Exercício anterior ou conta ausente; comparação anual indisponível."
        delta = v - ant if np.isfinite(v) and np.isfinite(ant) else np.nan
        percentual = delta / abs(ant) * 100 if np.isfinite(delta) and ant != 0 else np.nan
        if np.isfinite(delta) and ant == 0:
            motivo = "Base anterior zero; variação percentual n/d."
        unidade = (
            "p.p."
            if campo.startswith("margem_") or campo == "endividamento_geral"
            else "vezes"
            if campo == "liquidez_corrente"
            else "R$"
        )
        rotulo = config.NOMES.get(campo, campo)
        if campo == "despesas_receitas_operacionais":
            rotulo = "Despesas operacionais líquidas (−CVM 3.04; inclui outras receitas e equivalência)"
        texto = f"{rotulo}: {formatar_indicador(campo, v)}. "
        if np.isfinite(delta):
            if unidade == "R$":
                texto += f"Variação de {formatar_valor(delta)} ({formatar_percentual(percentual)}) frente a {ano - 1}."
            else:
                texto += f"Mudança de {numero_br(delta)} {unidade} frente a {ano - 1}."
        else:
            texto += f"Variação n/d. {motivo}"
        if campo in {"custo_vendas", "despesas_receitas_operacionais"} and np.isfinite(percentual):
            r0, r1 = _valor(p, "receita_liquida"), _valor(a, "receita_liquida")
            if np.isfinite(r0) and np.isfinite(r1) and r0 > 0 and ant > 0 and v >= 0:
                cr = (r1 / r0 - 1) * 100
                rel = "superior" if percentual > cr else "inferior" if percentual < cr else "igual"
                texto += f" Variação percentual {rel} à da receita ({formatar_percentual(cr)})."
            elif v < 0 or ant <= 0:
                texto += (
                    " Saldo líquido ou mudança de sinal impede leitura como crescimento de despesa bruta."
                )
        saida.append(
            dict(
                id=f"L1-{ano}",
                ano=ano,
                indicador=campo,
                rotulo=rotulo,
                valor=v,
                anterior=ant,
                variacao=delta,
                variacao_percentual=percentual,
                unidade_variacao=unidade,
                motivo_nd=motivo,
                texto=texto,
                origem="calculado; snapshot CVM em reais",
            )
        )
    return pd.DataFrame(saida)


def ponte_margem(df: pd.DataFrame, ano: int) -> pd.DataFrame:
    """Ponte aditiva em p.p.: Δ(100+CPV/R+3.04/R), sem atribuição causal."""
    a, p = df[df.ano_analise == ano], df[df.ano_analise == ano - 1]
    colunas = ["ano", "componente", "contribuicao_pp", "tipo"]
    if a.empty or p.empty:
        return pd.DataFrame(columns=colunas)
    a, p = a.iloc[0], p.iloc[0]
    campos = [
        "receita_liquida",
        "custo_vendas",
        "despesas_receitas_operacionais",
        "resultado_operacional",
        "lucro_bruto",
    ]
    if any(not np.isfinite(_valor(row, c)) for row in [a, p] for c in campos):
        return pd.DataFrame(columns=colunas)
    if a.receita_liquida <= 0 or p.receita_liquida <= 0:
        raise ErroValidacaoDados("Ponte exige receita positiva.")
    for row in [a, p]:
        if not np.isclose(
            row.receita_liquida + row.custo_vendas, row.lucro_bruto, atol=1000, rtol=0
        ) or not np.isclose(
            row.lucro_bruto + row.despesas_receitas_operacionais, row.resultado_operacional, atol=1000, rtol=0
        ):
            raise ErroValidacaoDados("Identidade da DRE inconsistente; ponte bloqueada.")
    inicial = 100 * p.resultado_operacional / p.receita_liquida
    custo = 100 * (a.custo_vendas / a.receita_liquida - p.custo_vendas / p.receita_liquida)
    despesas = 100 * (
        a.despesas_receitas_operacionais / a.receita_liquida
        - p.despesas_receitas_operacionais / p.receita_liquida
    )
    final = 100 * a.resultado_operacional / a.receita_liquida
    return pd.DataFrame(
        [
            [ano, f"Margem {ano - 1}", inicial, "absolute"],
            [ano, "Δ CPV / receita", custo, "relative"],
            [ano, "Δ despesas líquidas / receita", despesas, "relative"],
            [ano, f"Margem {ano}", final, "absolute"],
        ],
        columns=colunas,
    )


def reconciliar(df: pd.DataFrame, referencias: pd.DataFrame) -> pd.DataFrame:
    """Converte só unidades comparáveis e documenta separadamente ajuste de classificação."""
    validar_referencias(referencias)
    saida = []
    for _, row in referencias.iterrows():
        ano = int(row.ano)
        historico = df[df.ano_analise == ano]
        v = _valor(historico.iloc[0] if len(historico) else None, row.indicador_dashboard)
        item = row.to_dict()
        item.update(
            dashboard_reais=v,
            dashboard_rs_mil=v / 1000,
            release_reais=np.nan,
            diferenca_reais=np.nan,
            release_reconciliado_reais=np.nan,
            diferenca_reconciliada_reais=np.nan,
            tolerancia_reais=np.nan,
            resultado="não comparável",
        )
        if row.comparavel_dashboard != "não":
            release = float(row.valor_release) * float(row.fator_reais)
            ajuste = float(row.ajuste_equivalencia_release) * float(row.fator_reais)
            tolerancia = config.EXPLICACOES_ARREDONDAMENTO_REAIS * (
                2 if row.comparavel_dashboard == "parcial" else 1
            )
            diferenca = v - release - ajuste
            item.update(
                release_reais=release,
                diferenca_reais=v - release,
                release_reconciliado_reais=release + ajuste,
                diferenca_reconciliada_reais=diferenca,
                tolerancia_reais=tolerancia,
                resultado="n/d"
                if not np.isfinite(v)
                else "conciliado"
                if abs(diferenca) <= tolerancia
                else "divergência",
            )
        saida.append(item)
    return pd.DataFrame(saida)


def validar_alinhamento(df: pd.DataFrame, referencias: pd.DataFrame) -> pd.DataFrame:
    """Bloqueia a seção se uma receita tiver ano ou base sem conciliação verificável."""
    if df.ano_analise.duplicated().any():
        raise ErroValidacaoDados("Calendário contábil duplicado.")
    receitas = referencias[referencias.indicador_release == "receita_liquida"]
    if set(df.ano_analise) - set(receitas.ano):
        raise ErroValidacaoDados("Receita anual sem fonte disponível; explicação bloqueada.")
    r = reconciliar(df, receitas)
    if (r.resultado != "conciliado").any():
        raise ErroValidacaoDados("Divergência no alinhamento anual da receita; corrigir antes de explicar.")
    return r


def verificar_pendencias(
    companhia: pd.DataFrame, refs: pd.DataFrame, docs: pd.DataFrame, grupo: pd.DataFrame
) -> list[str]:
    """Lista pendências editoriais sem aceitá-las como evidência oficial."""
    validar_companhia(companhia)
    validar_grupo(grupo)
    validar_referencias(refs)
    validar_catalogo(companhia, refs, docs)
    ids = set(companhia[companhia.status == "verificado"].id)
    for _, row in grupo.iterrows():
        for ref in str(row.evidencias).split(";"):
            ref = ref.strip()
            if ref not in ids and ref != f"L1-{int(row.ano)}":
                raise ErroValidacaoDados(f"Evidência desconhecida na interpretação: {ref}.")
    saida = [
        f"{r.id} | {r.tema} | documento/URL/página/medida ainda não registrados | {r.observacao}"
        for r in companhia.itertuples()
        if r.status == "pendente"
    ]
    saida += [
        f"{int(r.ano)} | interpretação rascunho: revisão dos autores pendente"
        for r in grupo.itertuples()
        if r.status == "rascunho"
    ]
    return saida
