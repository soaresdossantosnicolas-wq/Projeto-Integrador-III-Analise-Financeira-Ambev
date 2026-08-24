from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Análise Financeira - Ambev",
    page_icon="📊",
    layout="wide"
)


# ============================================================
# CAMINHOS
# ============================================================

RAIZ_PROJETO = Path(__file__).resolve().parent.parent

PASTA_DATA = RAIZ_PROJETO / "data"

ARQUIVOS_POSSIVEIS = [
    PASTA_DATA / "indicadores_financeiros_ambev.csv",
    PASTA_DATA / "processed" / "indicadores_financeiros_ambev.csv",
    RAIZ_PROJETO / "dados_tratados" / "indicadores_financeiros_ambev.csv",
]


# ============================================================
# LOCALIZAR ARQUIVO
# ============================================================

def localizar_base():

    for arquivo in ARQUIVOS_POSSIVEIS:

        if arquivo.exists():
            return arquivo

    return None


# ============================================================
# CARREGAR DADOS
# ============================================================

@st.cache_data
def carregar_dados():

    arquivo = localizar_base()

    if arquivo is None:

        return None

    df = pd.read_csv(
        arquivo,
        encoding="utf-8-sig"
    )

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )

    if "ano_analise" in df.columns:

        df["ano_analise"] = pd.to_numeric(
            df["ano_analise"],
            errors="coerce"
        )

    return df.sort_values(
        "ano_analise"
    )


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def formatar_valor(valor):

    if pd.isna(valor):
        return "N/D"

    valor = float(valor)

    valor_abs = abs(valor)

    if valor_abs >= 1_000_000_000:

        return f"R$ {valor / 1_000_000_000:.2f} bi"

    if valor_abs >= 1_000_000:

        return f"R$ {valor / 1_000_000:.2f} mi"

    if valor_abs >= 1_000:

        return f"R$ {valor / 1_000:.2f} mil"

    return f"R$ {valor:,.2f}"


def formatar_percentual(valor):

    if pd.isna(valor):
        return "N/D"

    return f"{valor:.2f}%"


def obter_ultimo_valor(df, coluna):

    if coluna not in df.columns:
        return None

    dados = df[
        ["ano_analise", coluna]
    ].dropna()

    if dados.empty:
        return None

    return dados.iloc[-1][coluna]


# ============================================================
# CARREGAMENTO
# ============================================================

df = carregar_dados()


# ============================================================
# VERIFICAÇÃO
# ============================================================

if df is None:

    st.error(
        "A base de indicadores não foi encontrada."
    )

    st.info(
        "Execute primeiro a Etapa 3:"
    )

    st.code(
        "python code/03_analise_financeira.py"
    )

    st.stop()


# ============================================================
# CABEÇALHO
# ============================================================

st.title(
    "📊 Análise Financeira da Ambev"
)

st.markdown(
    """
    **Análise dos principais indicadores financeiros da Ambev S.A.**

    Período analisado: **2022–2025**
    """
)


st.divider()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header(
    "⚙️ Filtros"
)

anos_disponiveis = sorted(
    df["ano_analise"]
    .dropna()
    .astype(int)
    .unique()
)

anos_selecionados = st.sidebar.multiselect(
    "Selecione os anos",
    anos_disponiveis,
    default=anos_disponiveis
)

if not anos_selecionados:

    st.warning(
        "Selecione pelo menos um ano."
    )

    st.stop()


df_filtrado = df[
    df["ano_analise"].isin(
        anos_selecionados
    )
].copy()


# ============================================================
# INDICADORES PRINCIPAIS
# ============================================================

st.subheader(
    "📌 Principais Indicadores"
)

col1, col2, col3, col4 = st.columns(4)


receita = obter_ultimo_valor(
    df_filtrado,
    "receita_liquida"
)

lucro = obter_ultimo_valor(
    df_filtrado,
    "lucro_liquido"
)

roe = obter_ultimo_valor(
    df_filtrado,
    "roe"
)

liquidez = obter_ultimo_valor(
    df_filtrado,
    "liquidez_corrente"
)


with col1:

    st.metric(
        "Receita Líquida",
        formatar_valor(receita)
    )


with col2:

    st.metric(
        "Lucro Líquido",
        formatar_valor(lucro)
    )


with col3:

    st.metric(
        "ROE",
        formatar_percentual(roe)
    )


with col4:

    if liquidez is not None:

        st.metric(
            "Liquidez Corrente",
            f"{liquidez:.2f}"
        )

    else:

        st.metric(
            "Liquidez Corrente",
            "N/D"
        )


st.divider()


# ============================================================
# ABAS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📈 Resultados",
        "💰 Rentabilidade",
        "🏦 Liquidez e Endividamento",
        "📋 Dados"
    ]
)


# ============================================================
# ABA 1 — RESULTADOS
# ============================================================

with tab1:

    st.subheader(
        "Receita e Lucro"
    )

    colunas = [
        "ano_analise",
        "receita_liquida",
        "lucro_liquido"
    ]

    existentes = [
        c
        for c in colunas
        if c in df_filtrado.columns
    ]

    if len(existentes) == 3:

        dados = df_filtrado[
            existentes
        ].melt(
            id_vars="ano_analise",
            var_name="Indicador",
            value_name="Valor"
        )

        nomes = {
            "receita_liquida": "Receita Líquida",
            "lucro_liquido": "Lucro Líquido"
        }

        dados["Indicador"] = (
            dados["Indicador"]
            .map(nomes)
        )

        fig = px.bar(
            dados,
            x="ano_analise",
            y="Valor",
            color="Indicador",
            barmode="group",
            title="Evolução da Receita e do Lucro"
        )

        fig.update_layout(
            template="plotly_white",
            xaxis_title="Ano",
            yaxis_title="Valor"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


    st.subheader(
        "Crescimento"
    )

    indicadores = [
        "crescimento_receita_liquida",
        "crescimento_lucro_liquido"
    ]

    existentes = [
        c
        for c in indicadores
        if c in df_filtrado.columns
    ]

    if existentes:

        dados = df_filtrado[
            ["ano_analise"] + existentes
        ].melt(
            id_vars="ano_analise",
            var_name="Indicador",
            value_name="Crescimento"
        )

        nomes = {
            "crescimento_receita_liquida":
                "Crescimento da Receita",

            "crescimento_lucro_liquido":
                "Crescimento do Lucro"
        }

        dados["Indicador"] = (
            dados["Indicador"]
            .map(nomes)
        )

        fig = px.bar(
            dados,
            x="ano_analise",
            y="Crescimento",
            color="Indicador",
            barmode="group",
            title="Crescimento Anual"
        )

        fig.add_hline(
            y=0,
            line_dash="dash"
        )

        fig.update_layout(
            template="plotly_white",
            yaxis_ticksuffix="%"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# ============================================================
# ABA 2 — RENTABILIDADE
# ============================================================

with tab2:

    st.subheader(
        "Margens"
    )

    indicadores = [
        "margem_bruta",
        "margem_operacional",
        "margem_liquida"
    ]

    existentes = [
        c
        for c in indicadores
        if c in df_filtrado.columns
    ]

    if existentes:

        dados = df_filtrado[
            ["ano_analise"] + existentes
        ].melt(
            id_vars="ano_analise",
            var_name="Indicador",
            value_name="Percentual"
        )

        nomes = {
            "margem_bruta": "Margem Bruta",
            "margem_operacional":
                "Margem Operacional",
            "margem_liquida":
                "Margem Líquida"
        }

        dados["Indicador"] = (
            dados["Indicador"]
            .map(nomes)
        )

        fig = px.line(
            dados,
            x="ano_analise",
            y="Percentual",
            color="Indicador",
            markers=True,
            title="Evolução das Margens"
        )

        fig.update_layout(
            template="plotly_white",
            yaxis_ticksuffix="%",
            xaxis_title="Ano",
            yaxis_title="Percentual"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


    st.subheader(
        "ROA × ROE"
    )

    indicadores = [
        "roa",
        "roe"
    ]

    existentes = [
        c
        for c in indicadores
        if c in df_filtrado.columns
    ]

    if existentes:

        dados = df_filtrado[
            ["ano_analise"] + existentes
        ].melt(
            id_vars="ano_analise",
            var_name="Indicador",
            value_name="Percentual"
        )

        nomes = {
            "roa": "ROA",
            "roe": "ROE"
        }

        dados["Indicador"] = (
            dados["Indicador"]
            .map(nomes)
        )

        fig = px.line(
            dados,
            x="ano_analise",
            y="Percentual",
            color="Indicador",
            markers=True,
            title="Retorno sobre Ativos e Patrimônio"
        )

        fig.update_layout(
            template="plotly_white",
            yaxis_ticksuffix="%"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# ============================================================
# ABA 3 — LIQUIDEZ E ENDIVIDAMENTO
# ============================================================

with tab3:

    st.subheader(
        "Liquidez"
    )

    indicadores = [
        "liquidez_corrente",
        "liquidez_seca"
    ]

    existentes = [
        c
        for c in indicadores
        if c in df_filtrado.columns
    ]

    if existentes:

        dados = df_filtrado[
            ["ano_analise"] + existentes
        ].melt(
            id_vars="ano_analise",
            var_name="Indicador",
            value_name="Índice"
        )

        nomes = {
            "liquidez_corrente":
                "Liquidez Corrente",

            "liquidez_seca":
                "Liquidez Seca"
        }

        dados["Indicador"] = (
            dados["Indicador"]
            .map(nomes)
        )

        fig = px.line(
            dados,
            x="ano_analise",
            y="Índice",
            color="Indicador",
            markers=True,
            title="Indicadores de Liquidez"
        )

        fig.add_hline(
            y=1,
            line_dash="dash",
            annotation_text="Referência = 1"
        )

        fig.update_layout(
            template="plotly_white"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


    st.subheader(
        "Endividamento"
    )

    if "endividamento_geral" in df_filtrado.columns:

        fig = px.line(
            df_filtrado,
            x="ano_analise",
            y="endividamento_geral",
            markers=True,
            title="Endividamento Geral"
        )

        fig.update_layout(
            template="plotly_white",
            yaxis_ticksuffix="%"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


    if "capital_terceiros_patrimonio" in df_filtrado.columns:

        fig = px.line(
            df_filtrado,
            x="ano_analise",
            y="capital_terceiros_patrimonio",
            markers=True,
            title="Capital de Terceiros / Patrimônio Líquido"
        )

        fig.update_layout(
            template="plotly_white",
            yaxis_ticksuffix="%"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# ============================================================
# ABA 4 — DADOS
# ============================================================

with tab4:

    st.subheader(
        "Base de Indicadores"
    )

    st.dataframe(
        df_filtrado,
        use_container_width=True,
        hide_index=True
    )


    st.subheader(
        "Download"
    )

    csv = df_filtrado.to_csv(
        index=False
    ).encode(
        "utf-8-sig"
    )

    st.download_button(
        label="⬇️ Baixar dados filtrados",
        data=csv,
        file_name="indicadores_ambev_filtrados.csv",
        mime="text/csv"
    )


# ============================================================
# RODAPÉ
# ============================================================

st.divider()

st.caption(
    "Projeto Integrador III — Análise Financeira da Ambev | "
    "Dados financeiros processados a partir das demonstrações "
    "financeiras."
)