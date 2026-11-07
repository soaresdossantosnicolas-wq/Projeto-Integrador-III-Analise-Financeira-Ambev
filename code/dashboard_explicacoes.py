"""Aba de leitura financeira: cálculo, fonte oficial e interpretação com status explícito."""

import io
import logging

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from analise_explicacoes import (
    ARQUIVOS,
    calcular_camada1,
    ponte_margem,
    reconciliar,
    validar_alinhamento,
    validar_catalogo,
    validar_companhia,
    validar_grupo,
    validar_referencias,
    verificar_pendencias,
)
from dashboard_renderizacao import mostrar_figura
from dashboard_design import estilizar_figura
from dashboard_utils import numero_br
from excecoes import ErroValidacaoDados

log = logging.getLogger(__name__)
AVISO = (
    "Distinguimos o que é cálculo, o que a companhia informa e o que é interpretação do grupo. "
    "Os números do dashboard seguem a base contábil (CVM); releases podem usar medidas orgânicas ou ajustadas."
)


@st.cache_data(show_spinner=False)
def carregar_curadoria(conteudos: tuple[bytes, ...]) -> tuple[pd.DataFrame, ...]:
    """Cache pelo conteúdo; alterações editoriais invalidam a leitura sem reiniciar o servidor."""
    if len(conteudos) != len(ARQUIVOS):
        raise ErroValidacaoDados("Conjunto de arquivos de explicações incompleto.")
    companhia, grupo, refs, docs = [
        pd.read_csv(io.BytesIO(b), encoding="utf-8-sig").fillna("") for b in conteudos
    ]
    validar_companhia(companhia)
    validar_grupo(grupo)
    validar_referencias(refs)
    validar_catalogo(companhia, refs, docs)
    verificar_pendencias(companhia, refs, docs, grupo)
    return companhia, grupo, refs, docs


def preparar_exportacoes(
    df: pd.DataFrame,
    anos: list[int],
    companhia: pd.DataFrame,
    grupo: pd.DataFrame,
    refs: pd.DataFrame,
    docs: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Exporta os três níveis, fontes e fórmulas da ponte sem misturar autoria."""
    pontes = [ponte_margem(df, ano) for ano in anos]
    pontes_validas = [p for p in pontes if not p.empty]
    ponte = pd.concat(pontes_validas, ignore_index=True) if pontes_validas else pontes[0]
    return {
        "calculos": pd.concat([calcular_camada1(df, ano) for ano in anos], ignore_index=True),
        "companhia": companhia[companhia.ano.isin(anos)].copy(),
        "grupo": grupo[grupo.ano.isin(anos)].copy(),
        "reconciliacao": reconciliar(df, refs[refs.ano.isin(anos)]),
        "ponte_margem": ponte,
        "fontes": docs[docs.ano.isin(anos)].copy(),
    }


@st.cache_data(show_spinner=False)
def exportar_camadas(tabelas: dict[str, pd.DataFrame]) -> tuple[bytes, bytes]:
    """CSV longo com coluna de camada e Excel com abas separadas, ambos incluindo referências."""
    unificado = pd.concat([t.assign(camada=nome) for nome, t in tabelas.items()], ignore_index=True)
    csv = unificado.to_csv(index=False, sep=";", decimal=",", lineterminator="\n").encode("utf-8-sig")
    excel = io.BytesIO()
    with pd.ExcelWriter(excel, engine="openpyxl") as writer:
        for nome, tabela in tabelas.items():
            tabela.to_excel(writer, sheet_name=nome, index=False)
    return csv, excel.getvalue()


def _cartoes(df: pd.DataFrame, ano: int, companhia: pd.DataFrame, grupo: pd.DataFrame) -> None:
    """Três cartões responsivos: as afirmações oficiais vêm exclusivamente do CSV curado."""
    st.subheader(f"Exercício {ano}")
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1, st.container(border=True):
        st.caption("01 · CALCULADO · BASE CVM")
        st.markdown("#### O que os dados mostram")
        for row in calcular_camada1(df, ano).itertuples():
            st.markdown(row.texto)
        st.caption(
            "Leitura contábil, sem atribuição causal. Despesas líquidas = −conta 3.04; "
            "incluem outras receitas e equivalência patrimonial, não apenas SG&A. "
            "Variações usam exclusivamente o ano anterior do calendário."
        )
    with c2, st.container(border=True):
        st.caption("02 · FONTE OFICIAL · PARÁFRASE")
        st.markdown("#### O que a companhia diz")
        registros = companhia[(companhia.ano == ano) & (companhia.status == "verificado")]
        if registros.empty:
            st.info("Explicação oficial ainda não registrada.")
        for row in registros.itertuples():
            st.markdown(f"**{row.tema.capitalize()} · {row.id}**")
            st.write(row.afirmacao_parafraseada)
            if row.comparavel_dashboard != "sim":
                st.caption(
                    "⚠ Medida diferente da do dashboard · comparabilidade: " + row.comparavel_dashboard
                )
            st.caption(
                f"{row.documento} · p. {int(row.pagina)} · {row.periodo} · {row.medida} · {row.unidade}"
            )
            st.markdown(f"[Consultar fonte oficial ↗]({row.url}#page={int(row.pagina)})")
            st.caption(f"Publicado em {row.data_publicacao} · acesso em {row.data_acesso}. {row.observacao}")
        pendentes = companhia[(companhia.ano == ano) & (companhia.status == "pendente")]
        if not pendentes.empty:
            with st.expander(f"{len(pendentes)} temas com explicação oficial ainda não registrada"):
                for row in pendentes.itertuples():
                    st.write(f"**{row.tema}** — {row.observacao}")
    with c3, st.container(border=True):
        st.caption("03 · LEITURA DOS AUTORES")
        st.markdown("#### Interpretação do grupo")
        registro = grupo[grupo.ano == ano]
        if registro.empty:
            st.info("Interpretação ainda não registrada; aguarda os autores.")
        else:
            row = registro.iloc[0]
            if row.status == "rascunho":
                st.warning("Rascunho (a revisar pelo grupo)")
            else:
                st.success("Revisado pelos autores")
            st.write(row.texto)
            st.markdown("**Evidências**")
            st.write(row.evidencias)
            st.markdown("**Limitações e o que não se pode concluir**")
            st.write(row.limitacoes)
            st.caption("Responsabilidade editorial: " + row.autores)


def _mostrar_ponte(df: pd.DataFrame, ano: int, tema: str) -> None:
    """Mostra contribuições aritméticas à margem operacional, sem simular causas econômicas."""
    ponte = ponte_margem(df, ano)
    if ponte.empty:
        st.info(f"Ponte de margem {ano}: n/d — exige receita e DRE completas de {ano - 1} e {ano}.")
        return
    fig = go.Figure(
        go.Waterfall(
            x=ponte.componente,
            y=ponte.contribuicao_pp,
            measure=ponte.tipo,
            text=[numero_br(v) + " p.p." for v in ponte.contribuicao_pp],
            textposition="outside",
            customdata=[[numero_br(v)] for v in ponte.contribuicao_pp],
            hovertemplate="%{x}: %{customdata[0]} p.p.<extra></extra>",
            increasing={"marker": {"color": config.PALETA["positivo"]}},
            decreasing={"marker": {"color": config.PALETA["negativo"]}},
            totals={"marker": {"color": config.PALETA["primaria"]}},
            connector={"line": {"color": config.PALETA["neutro"], "width": 1}},
        )
    )
    estilizar_figura(fig, f"Ponte da margem operacional · {ano - 1} → {ano}", "Pontos percentuais", tema)
    fig.update_yaxes(rangemode="normal", ticksuffix=" p.p.")
    mostrar_figura(fig, theme=None, width="stretch", key=f"ponte_explicacoes_{ano}")
    st.caption(
        "Margem operacional = 100 + CPV/receita × 100 + conta 3.04/receita × 100. "
        "A primeira contribuição é a mudança da margem bruta; a segunda é a mudança da razão "
        "de despesas líquidas. São identidades aritméticas; não isolam preço, volume, câmbio ou eficiência."
    )


def _tabela_reconciliacao(tabela: pd.DataFrame) -> None:
    """Exibe escala original, escala CVM e as duas diferenças, sem erro numérico entre bases distintas."""
    st.subheader("Reconciliação · dashboard e release")
    st.caption(
        "CSV interno em reais; coluna CVM convertida para R$ mil apenas na apresentação. "
        "Release em R$ milhões, salvo variações orgânicas em %. "
        "Diferença = dashboard − release; após classificação, soma-se a equivalência ao lucro operacional."
    )
    if (tabela.resultado == "divergência").any():
        st.error("Há divergência não conciliada. Confira a linha e sua fonte; não atribua uma causa.")
    visual = pd.DataFrame(
        {
            "Ano": tabela.ano,
            "Indicador do release": tabela.indicador_release,
            "Dashboard · R$ mil": tabela.dashboard_rs_mil.map(lambda v: numero_br(v, 3)),
            "Release · valor original": tabela.valor_release.map(lambda v: numero_br(v, 1)),
            "Unidade original": tabela.unidade_original,
            "Medida": tabela.medida,
            "Diferença · R$ mil": (tabela.diferenca_reais / 1000).map(lambda v: numero_br(v, 3)),
            "Ajuste equivalência · R$ milhões": tabela.ajuste_equivalencia_release.map(numero_br),
            "Diferença após classificação · R$ mil": (tabela.diferenca_reconciliada_reais / 1000).map(
                lambda v: numero_br(v, 3)
            ),
            "Resultado": tabela.resultado,
            "Motivo": tabela.motivo,
            "Documento": tabela.documento,
            "Página": tabela.pagina,
            "Fonte": tabela.url,
        }
    )
    st.dataframe(
        visual,
        hide_index=True,
        width="stretch",
        column_config={"Fonte": st.column_config.LinkColumn("Fonte oficial", display_text="Abrir ↗")},
    )
    st.caption(
        "n/d nas diferenças de medidas não comparáveis é intencional. Não se subtrai crescimento orgânico de um montante contábil."
    )


@st.fragment
def renderizar_explicacoes(df: pd.DataFrame, tema: str) -> None:
    """Renderiza a aba com atualização parcial e estados vazios seguros."""
    st.subheader("O que explica os resultados?")
    st.info(AVISO)
    if df.empty or "ano_analise" not in df:
        st.info("Sem dados contábeis disponíveis para esta seção.")
        return
    try:
        conteudos = tuple((config.PASTA_EXPLICACOES / nome).read_bytes() for nome in ARQUIVOS)
        companhia, grupo, refs, docs = carregar_curadoria(conteudos)
        validar_alinhamento(df, refs)
    except (OSError, ValueError, ErroValidacaoDados) as exc:
        log.exception("Explicações indisponíveis ou fonte inconsistente.")
        st.error("A seção foi bloqueada: falta fonte válida ou há divergência no alinhamento dos anos.")
        st.caption(str(exc))
        return
    anos = sorted(df.ano_analise.astype(int).unique().tolist())
    ano = st.selectbox(
        "Exercício explicado", anos, index=len(anos) - 1, key="exercicio_explicado", bind="query-params"
    )
    comparar = st.toggle("Comparar dois exercícios", key="comparar_explicacoes", bind="query-params")
    selecionados = [int(ano)]
    if comparar and len(anos) > 1:
        outro = st.selectbox(
            "Segundo exercício explicado",
            [y for y in anos if y != ano],
            key="segundo_exercicio_explicado",
            bind="query-params",
        )
        selecionados = sorted([int(ano), int(outro)])
    st.caption(
        "Esta aba usa o histórico completo: os filtros de séries e escala de outras abas não alteram as fontes nem a base da variação anual."
    )
    tabelas = preparar_exportacoes(df, selecionados, companhia, grupo, refs, docs)
    if len(selecionados) == 2:
        st.markdown("#### Comparação dos níveis contábeis")
        comp = tabelas["calculos"].pivot(index="rotulo", columns="ano", values="valor")
        st.dataframe(comp.map(lambda v: numero_br(v, 2)), width="stretch")
        st.caption(
            "Contas monetárias em R$; margens e endividamento em %; liquidez em vezes. Variações detalhadas nos cartões abaixo."
        )
    for y in selecionados:
        _cartoes(df, y, companhia, grupo)
        _mostrar_ponte(df, y, tema)
    _tabela_reconciliacao(tabelas["reconciliacao"])
    csv, excel = exportar_camadas(tabelas)
    st.download_button(
        "Baixar três camadas e fontes · CSV",
        csv,
        file_name="explicacoes_" + "_".join(map(str, selecionados)) + ".csv",
        mime="text/csv",
        key="exportar_explicacoes_csv",
        on_click="ignore",
    )
    st.download_button(
        "Baixar três camadas e fontes · Excel",
        excel,
        file_name="explicacoes_" + "_".join(map(str, selecionados)) + ".xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="exportar_explicacoes_excel",
        on_click="ignore",
    )
