"""
Etapa 4 — Visualização e Dashboard Interativo
Projeto Integrador III — Análise Financeira da Ambev S.A.

Consome a base de indicadores gerada pela Etapa 3
(dados_tratados/indicadores_financeiros_ambev.csv) e apresenta
um dashboard interativo em Streamlit + Plotly.

Execução:
    python -m streamlit run code/04_visualizacao.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
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

ARQUIVOS_POSSIVEIS = [
    RAIZ_PROJETO / "dados_tratados" / "indicadores_financeiros_ambev.csv",
    RAIZ_PROJETO / "data" / "indicadores_financeiros_ambev.csv",
    RAIZ_PROJETO / "data" / "processed" / "indicadores_financeiros_ambev.csv",
]

# Rótulos legíveis para os indicadores (usados em gráficos, KPIs e tabela)
NOMES_INDICADORES = {
    "receita_liquida": "Receita Líquida",
    "lucro_bruto": "Lucro Bruto",
    "resultado_operacional": "Resultado Operacional (EBIT)",
    "lucro_liquido": "Lucro Líquido",
    "ativo_total": "Ativo Total",
    "ativo_circulante": "Ativo Circulante",
    "caixa_equivalentes": "Caixa e Equivalentes",
    "passivo_circulante": "Passivo Circulante",
    "passivo_total": "Passivo Total",
    "patrimonio_liquido": "Patrimônio Líquido",
    "liquidez_corrente": "Liquidez Corrente",
    "liquidez_seca": "Liquidez Seca",
    "margem_bruta": "Margem Bruta",
    "margem_operacional": "Margem Operacional",
    "margem_liquida": "Margem Líquida",
    "roa": "ROA",
    "roe": "ROE",
    "endividamento_geral": "Endividamento Geral",
    "capital_terceiros_patrimonio": "Capital de Terceiros / PL",
    "divida_liquida": "Dívida Líquida",
    "divida_liquida_ebitda": "Dívida Líquida / EBITDA",
}

# Indicadores expressos em percentual (para formatação e eixos)
INDICADORES_PERCENTUAIS = {
    "margem_bruta", "margem_operacional", "margem_liquida",
    "roa", "roe", "endividamento_geral", "capital_terceiros_patrimonio",
}

# Indicadores expressos como índice/razão (não moeda, não percentual)
INDICADORES_RAZAO = {
    "liquidez_corrente", "liquidez_seca", "divida_liquida_ebitda",
}

COLUNA_ANO = "ano_analise"


# ============================================================
# CARREGAMENTO
# ============================================================

def localizar_base():
    """Retorna o primeiro caminho existente entre os candidatos conhecidos."""

    for arquivo in ARQUIVOS_POSSIVEIS:

        if arquivo.exists():
            return arquivo

    return None


@st.cache_data
def carregar_dados(caminho_str):
    """
    Carrega a base de indicadores gerada pela Etapa 3.
    Recebe o caminho como string para ser compatível com o
    cache do Streamlit (Path nem sempre é hashable de forma estável).
    """

    df = pd.read_csv(
        caminho_str,
        encoding="utf-8-sig"
    )

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )

    if COLUNA_ANO in df.columns:

        df[COLUNA_ANO] = pd.to_numeric(
            df[COLUNA_ANO],
            errors="coerce"
        )

        df = df.dropna(subset=[COLUNA_ANO])
        df[COLUNA_ANO] = df[COLUNA_ANO].astype(int)

        df = df.sort_values(COLUNA_ANO).reset_index(drop=True)

    return df


# ============================================================
# VALIDAÇÃO
# ============================================================

def validar_dados(df):
    """
    Verifica a integridade básica da base carregada e devolve
    um dicionário com o diagnóstico, sem interromper a execução.
    """

    diagnostico = {
        "colunas_nulas": {},
        "duplicadas": 0,
        "anos_presentes": [],
        "anos_ausentes": [],
        "indicadores_ausentes": [],
    }

    if COLUNA_ANO not in df.columns:
        diagnostico["erro_critico"] = (
            f"Coluna obrigatória '{COLUNA_ANO}' não encontrada na base."
        )
        return diagnostico

    diagnostico["duplicadas"] = int(
        df.drop(columns=[COLUNA_ANO]).duplicated().sum()
    )

    for coluna in df.columns:

        nulos = int(df[coluna].isna().sum())

        if nulos > 0:
            diagnostico["colunas_nulas"][coluna] = nulos

    anos_esperados = [2022, 2023, 2024, 2025]
    anos_presentes = sorted(df[COLUNA_ANO].dropna().unique().tolist())

    diagnostico["anos_presentes"] = anos_presentes
    diagnostico["anos_ausentes"] = [
        ano for ano in anos_esperados if ano not in anos_presentes
    ]

    diagnostico["indicadores_ausentes"] = [
        nome for nome in NOMES_INDICADORES
        if nome not in df.columns
    ]

    return diagnostico


# ============================================================
# FORMATAÇÃO
# ============================================================

def formatar_valor(valor):
    """Formata valores monetários em R$, com sufixo bi/mi/mil."""

    if valor is None or pd.isna(valor):
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


def formatar_percentual(valor, casas=2):

    if valor is None or pd.isna(valor):
        return "N/D"

    return f"{valor:.{casas}f}%"


def formatar_razao(valor, casas=2):

    if valor is None or pd.isna(valor):
        return "N/D"

    return f"{valor:.{casas}f}"


def formatar_indicador(nome, valor):
    """Escolhe a formatação adequada conforme o tipo do indicador."""

    if nome in INDICADORES_PERCENTUAIS:
        return formatar_percentual(valor)

    if nome in INDICADORES_RAZAO:
        return formatar_razao(valor)

    return formatar_valor(valor)


# ============================================================
# VARIAÇÕES ANO A ANO (para os cards de KPI)
# ============================================================

def calcular_variacoes(df, coluna):
    """
    Retorna (valor_atual, valor_anterior, variacao_percentual)
    considerando o último ano disponível (não-nulo) e o ano
    imediatamente anterior presente na base filtrada.
    """

    if coluna not in df.columns:
        return None, None, None

    dados = df[[COLUNA_ANO, coluna]].dropna().sort_values(COLUNA_ANO)

    if dados.empty:
        return None, None, None

    valor_atual = dados.iloc[-1][coluna]

    if len(dados) < 2:
        return valor_atual, None, None

    valor_anterior = dados.iloc[-2][coluna]

    if valor_anterior == 0 or pd.isna(valor_anterior):
        variacao = None
    else:
        variacao = ((valor_atual - valor_anterior) / abs(valor_anterior)) * 100

    return valor_atual, valor_anterior, variacao


# ============================================================
# KPIs
# ============================================================

def criar_kpis(df):
    """Renderiza os cards de KPI com valor atual e variação vs. ano anterior."""

    indicadores_kpi = [
        ("receita_liquida", "Receita Líquida"),
        ("lucro_liquido", "Lucro Líquido"),
        ("margem_liquida", "Margem Líquida"),
        ("roe", "ROE"),
        ("roa", "ROA"),
        ("liquidez_corrente", "Liquidez Corrente"),
        ("endividamento_geral", "Endividamento Geral"),
    ]

    disponiveis = [
        (col, rotulo) for col, rotulo in indicadores_kpi
        if col in df.columns
    ]

    if not disponiveis:
        st.info("Nenhum dos indicadores principais está disponível na base.")
        return

    colunas_layout = st.columns(len(disponiveis))

    for coluna_layout, (coluna, rotulo) in zip(colunas_layout, disponiveis):

        valor_atual, valor_anterior, variacao = calcular_variacoes(df, coluna)

        texto_valor = formatar_indicador(coluna, valor_atual)

        if variacao is None:
            texto_delta = None
        else:
            texto_delta = f"{variacao:+.2f}% vs. ano anterior"

        with coluna_layout:

            st.metric(
                label=rotulo,
                value=texto_valor,
                delta=texto_delta,
                delta_color="normal"
            )


# ============================================================
# GRÁFICO — DRE
# ============================================================

def criar_grafico_dre(df):

    colunas = [
        "receita_liquida",
        "lucro_bruto",
        "resultado_operacional",
        "lucro_liquido",
    ]

    existentes = [c for c in colunas if c in df.columns]

    if not existentes:
        st.info("Nenhuma conta da DRE disponível para exibição.")
        return

    dados = df[[COLUNA_ANO] + existentes].melt(
        id_vars=COLUNA_ANO,
        var_name="Indicador",
        value_name="Valor"
    )

    dados["Indicador"] = dados["Indicador"].map(NOMES_INDICADORES)

    fig = px.bar(
        dados,
        x=COLUNA_ANO,
        y="Valor",
        color="Indicador",
        barmode="group",
        title="Evolução das Principais Contas da DRE"
    )

    fig.update_layout(
        template="plotly_white",
        xaxis_title="Ano",
        yaxis_title="Valor (R$)",
        xaxis=dict(dtick=1)
    )

    st.plotly_chart(fig, width='stretch')


def criar_grafico_crescimento(df):

    colunas = [
        "crescimento_receita_liquida",
        "crescimento_lucro_liquido",
    ]

    existentes = [c for c in colunas if c in df.columns]

    if not existentes:
        st.info("Indicadores de crescimento não disponíveis na base.")
        return

    dados = df[[COLUNA_ANO] + existentes].melt(
        id_vars=COLUNA_ANO,
        var_name="Indicador",
        value_name="Crescimento"
    )

    nomes = {
        "crescimento_receita_liquida": "Crescimento da Receita",
        "crescimento_lucro_liquido": "Crescimento do Lucro",
    }

    dados["Indicador"] = dados["Indicador"].map(nomes)

    fig = px.bar(
        dados,
        x=COLUNA_ANO,
        y="Crescimento",
        color="Indicador",
        barmode="group",
        title="Crescimento Anual (%)"
    )

    fig.add_hline(y=0, line_dash="dash", line_color="gray")

    fig.update_layout(
        template="plotly_white",
        yaxis_ticksuffix="%",
        xaxis_title="Ano",
        yaxis_title="Variação (%)",
        xaxis=dict(dtick=1)
    )

    st.plotly_chart(fig, width='stretch')


# ============================================================
# GRÁFICO — MARGENS
# ============================================================

def criar_grafico_margens(df):

    colunas = ["margem_bruta", "margem_operacional", "margem_liquida"]
    existentes = [c for c in colunas if c in df.columns]

    if not existentes:
        st.info("Indicadores de margem não disponíveis na base.")
        return

    dados = df[[COLUNA_ANO] + existentes].melt(
        id_vars=COLUNA_ANO,
        var_name="Indicador",
        value_name="Percentual"
    )

    dados["Indicador"] = dados["Indicador"].map(NOMES_INDICADORES)

    fig = px.line(
        dados,
        x=COLUNA_ANO,
        y="Percentual",
        color="Indicador",
        markers=True,
        title="Evolução das Margens"
    )

    fig.update_layout(
        template="plotly_white",
        yaxis_ticksuffix="%",
        xaxis_title="Ano",
        yaxis_title="Percentual",
        xaxis=dict(dtick=1)
    )

    st.plotly_chart(fig, width='stretch')


# ============================================================
# GRÁFICO — RENTABILIDADE
# ============================================================

def criar_grafico_rentabilidade(df):

    colunas = ["roa", "roe"]
    existentes = [c for c in colunas if c in df.columns]

    if not existentes:
        st.info("Indicadores de rentabilidade (ROA/ROE) não disponíveis.")
        return

    dados = df[[COLUNA_ANO] + existentes].melt(
        id_vars=COLUNA_ANO,
        var_name="Indicador",
        value_name="Percentual"
    )

    dados["Indicador"] = dados["Indicador"].map(NOMES_INDICADORES)

    fig = px.line(
        dados,
        x=COLUNA_ANO,
        y="Percentual",
        color="Indicador",
        markers=True,
        title="Retorno sobre Ativos (ROA) e sobre Patrimônio Líquido (ROE)"
    )

    fig.update_layout(
        template="plotly_white",
        yaxis_ticksuffix="%",
        xaxis_title="Ano",
        yaxis_title="Percentual",
        xaxis=dict(dtick=1)
    )

    st.plotly_chart(fig, width='stretch')


# ============================================================
# GRÁFICO — LIQUIDEZ
# ============================================================

def criar_grafico_liquidez(df):

    colunas = ["liquidez_corrente", "liquidez_seca"]
    existentes = [c for c in colunas if c in df.columns and df[c].notna().any()]

    if not existentes:
        st.info("Indicadores de liquidez não disponíveis (ou totalmente vazios) na base.")
        return

    dados = df[[COLUNA_ANO] + existentes].melt(
        id_vars=COLUNA_ANO,
        var_name="Indicador",
        value_name="Índice"
    )

    dados["Indicador"] = dados["Indicador"].map(NOMES_INDICADORES)

    fig = px.line(
        dados,
        x=COLUNA_ANO,
        y="Índice",
        color="Indicador",
        markers=True,
        title="Indicadores de Liquidez"
    )

    fig.add_hline(
        y=1,
        line_dash="dash",
        line_color="gray",
        annotation_text="Referência = 1,0"
    )

    fig.update_layout(
        template="plotly_white",
        xaxis_title="Ano",
        yaxis_title="Índice",
        xaxis=dict(dtick=1)
    )

    st.plotly_chart(fig, width='stretch')


# ============================================================
# GRÁFICO — ENDIVIDAMENTO
# ============================================================

def criar_grafico_endividamento(df):

    colunas = ["endividamento_geral", "capital_terceiros_patrimonio"]
    existentes = [c for c in colunas if c in df.columns and df[c].notna().any()]

    if not existentes:
        st.info("Indicadores de endividamento não disponíveis na base.")
        return

    dados = df[[COLUNA_ANO] + existentes].melt(
        id_vars=COLUNA_ANO,
        var_name="Indicador",
        value_name="Percentual"
    )

    dados["Indicador"] = dados["Indicador"].map(NOMES_INDICADORES)

    fig = px.line(
        dados,
        x=COLUNA_ANO,
        y="Percentual",
        color="Indicador",
        markers=True,
        title="Indicadores de Endividamento"
    )

    fig.update_layout(
        template="plotly_white",
        yaxis_ticksuffix="%",
        xaxis_title="Ano",
        yaxis_title="Percentual",
        xaxis=dict(dtick=1)
    )

    st.plotly_chart(fig, width='stretch')

    if "divida_liquida" in df.columns and df["divida_liquida"].notna().any():

        fig_divida = px.bar(
            df,
            x=COLUNA_ANO,
            y="divida_liquida",
            title="Dívida Líquida"
        )

        fig_divida.update_layout(
            template="plotly_white",
            xaxis_title="Ano",
            yaxis_title="Valor (R$)",
            xaxis=dict(dtick=1)
        )

        st.plotly_chart(fig_divida, width='stretch')


# ============================================================
# GRÁFICO — BALANÇO PATRIMONIAL
# ============================================================

def criar_grafico_balanco(df):

    colunas = ["ativo_total", "passivo_total", "patrimonio_liquido"]
    existentes = [c for c in colunas if c in df.columns and df[c].notna().any()]

    if not existentes:
        st.info("Contas patrimoniais não disponíveis na base.")
        return

    dados = df[[COLUNA_ANO] + existentes].melt(
        id_vars=COLUNA_ANO,
        var_name="Indicador",
        value_name="Valor"
    )

    dados["Indicador"] = dados["Indicador"].map(NOMES_INDICADORES)

    fig = px.bar(
        dados,
        x=COLUNA_ANO,
        y="Valor",
        color="Indicador",
        barmode="group",
        title="Evolução da Estrutura Patrimonial"
    )

    fig.update_layout(
        template="plotly_white",
        xaxis_title="Ano",
        yaxis_title="Valor (R$)",
        xaxis=dict(dtick=1)
    )

    st.plotly_chart(fig, width='stretch')

    outras = ["ativo_circulante", "caixa_equivalentes", "passivo_circulante"]
    outras_existentes = [c for c in outras if c in df.columns and df[c].notna().any()]

    if outras_existentes:

        dados2 = df[[COLUNA_ANO] + outras_existentes].melt(
            id_vars=COLUNA_ANO,
            var_name="Indicador",
            value_name="Valor"
        )

        dados2["Indicador"] = dados2["Indicador"].map(NOMES_INDICADORES)

        fig2 = px.line(
            dados2,
            x=COLUNA_ANO,
            y="Valor",
            color="Indicador",
            markers=True,
            title="Contas Complementares do Balanço"
        )

        fig2.update_layout(
            template="plotly_white",
            xaxis_title="Ano",
            yaxis_title="Valor (R$)",
            xaxis=dict(dtick=1)
        )

        st.plotly_chart(fig2, width='stretch')


# ============================================================
# TABELA FINANCEIRA
# ============================================================

def criar_tabela_financeira(df):

    colunas_tabela = [
        c for c in NOMES_INDICADORES
        if c in df.columns and c not in (
            "ativo_circulante", "caixa_equivalentes", "passivo_circulante",
            "ativo_total", "passivo_total", "patrimonio_liquido",
            "lucro_bruto", "resultado_operacional",
            "divida_liquida", "divida_liquida_ebitda",
        )
    ]

    if not colunas_tabela:
        st.info("Não há indicadores suficientes para montar a tabela.")
        return

    tabela = df[[COLUNA_ANO] + colunas_tabela].copy()

    tabela_formatada = tabela.copy()

    for coluna in colunas_tabela:

        tabela_formatada[coluna] = tabela[coluna].apply(
            lambda v, c=coluna: formatar_indicador(c, v)
        )

    tabela_formatada = tabela_formatada.rename(
        columns={COLUNA_ANO: "Ano", **NOMES_INDICADORES}
    )

    st.dataframe(
        tabela_formatada,
        width='stretch',
        hide_index=True
    )

    csv = tabela.rename(
        columns={COLUNA_ANO: "ano", **NOMES_INDICADORES}
    ).to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="⬇️ Baixar tabela de indicadores (CSV)",
        data=csv,
        file_name="tabela_indicadores_ambev.csv",
        mime="text/csv"
    )


# ============================================================
# INSIGHTS AUTOMÁTICOS
# ============================================================

def gerar_insights(df):
    """
    Gera interpretações descritivas simples, sem inferir causas.
    Baseia-se apenas em comparações numéricas presentes na base.
    """

    insights = []

    def maior_e_menor(coluna, rotulo, sufixo="%", inverte_melhor=False):

        if coluna not in df.columns:
            return

        serie = df[[COLUNA_ANO, coluna]].dropna()

        if serie.empty:
            return

        linha_max = serie.loc[serie[coluna].idxmax()]
        linha_min = serie.loc[serie[coluna].idxmin()]

        insights.append(
            f"**Maior {rotulo}**: {int(linha_max[COLUNA_ANO])} "
            f"({linha_max[coluna]:.2f}{sufixo})"
        )

        insights.append(
            f"**Menor {rotulo}**: {int(linha_min[COLUNA_ANO])} "
            f"({linha_min[coluna]:.2f}{sufixo})"
        )

    def maior_crescimento(coluna, rotulo):

        if coluna not in df.columns:
            return

        serie = df[[COLUNA_ANO, coluna]].dropna()

        if serie.empty:
            return

        linha = serie.loc[serie[coluna].idxmax()]

        insights.append(
            f"**Maior crescimento de {rotulo}**: {int(linha[COLUNA_ANO])} "
            f"({linha[coluna]:+.2f}% em relação ao ano anterior)"
        )

    maior_crescimento("crescimento_receita_liquida", "receita")
    maior_crescimento("crescimento_lucro_liquido", "lucro")

    maior_e_menor("margem_liquida", "margem líquida")
    maior_e_menor("roe", "ROE")
    maior_e_menor("liquidez_corrente", "liquidez corrente", sufixo="")
    maior_e_menor("endividamento_geral", "endividamento geral")

    if not insights:
        st.info(
            "Não há dados suficientes na base para gerar insights automáticos."
        )
        return

    for texto in insights:
        st.markdown(f"- {texto}")


# ============================================================
# COMPARAÇÃO 2022 × 2025 (ou primeiro vs. último ano disponível)
# ============================================================

def criar_comparacao_periodo(df):

    if df.empty or COLUNA_ANO not in df.columns:
        st.info("Não há dados suficientes para a comparação entre períodos.")
        return

    anos_disponiveis = sorted(df[COLUNA_ANO].dropna().unique())

    if len(anos_disponiveis) < 2:
        st.info(
            "É necessário ao menos dois anos selecionados para "
            "comparar o início e o fim do período."
        )
        return

    ano_inicial = anos_disponiveis[0]
    ano_final = anos_disponiveis[-1]

    st.caption(f"Comparação entre {int(ano_inicial)} e {int(ano_final)}")

    colunas = [
        "receita_liquida", "lucro_liquido", "margem_liquida",
        "roe", "roa", "liquidez_corrente", "endividamento_geral",
    ]

    linha_inicial = df[df[COLUNA_ANO] == ano_inicial].iloc[0]
    linha_final = df[df[COLUNA_ANO] == ano_final].iloc[0]

    registros = []

    for coluna in colunas:

        if coluna not in df.columns:
            continue

        valor_inicial = linha_inicial.get(coluna, np.nan)
        valor_final = linha_final.get(coluna, np.nan)

        if pd.isna(valor_inicial) or pd.isna(valor_final):
            variacao_pct = np.nan
        elif valor_inicial == 0:
            variacao_pct = np.nan
        else:
            variacao_pct = (
                (valor_final - valor_inicial) / abs(valor_inicial)
            ) * 100

        variacao_absoluta = (
            valor_final - valor_inicial
            if not (pd.isna(valor_inicial) or pd.isna(valor_final))
            else np.nan
        )

        registros.append({
            "Indicador": NOMES_INDICADORES.get(coluna, coluna),
            f"{int(ano_inicial)}": formatar_indicador(coluna, valor_inicial),
            f"{int(ano_final)}": formatar_indicador(coluna, valor_final),
            "Variação absoluta": formatar_indicador(coluna, variacao_absoluta),
            "Variação (%)": formatar_percentual(variacao_pct),
        })

    if not registros:
        st.info("Nenhum dos indicadores comparáveis está disponível na base.")
        return

    tabela_comparativa = pd.DataFrame(registros)

    st.dataframe(
        tabela_comparativa,
        width='stretch',
        hide_index=True
    )


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

def main():

    st.title("📊 Análise Financeira da Ambev")
    st.markdown(
        "**Análise dos principais indicadores financeiros — 2022 a 2025**"
    )

    caminho = localizar_base()

    if caminho is None:

        st.error(
            "A base de indicadores não foi encontrada em nenhum dos "
            "caminhos esperados."
        )

        st.info(
            "Execute primeiro as etapas anteriores do pipeline, na ordem:"
        )

        st.code(
            "python code/02_tratamento_ambev.py\n"
            "python code/03_analise_financeira.py"
        )

        st.caption(
            "Caminhos verificados:\n" +
            "\n".join(str(p) for p in ARQUIVOS_POSSIVEIS)
        )

        st.stop()

    try:
        df = carregar_dados(str(caminho))
    except Exception as erro:
        st.error(f"Não foi possível carregar a base de dados: {erro}")
        st.stop()

    if df.empty:
        st.warning("A base de indicadores foi encontrada, mas está vazia.")
        st.stop()

    diagnostico = validar_dados(df)

    if diagnostico.get("erro_critico"):
        st.error(diagnostico["erro_critico"])
        st.stop()

    st.divider()

    # --------------------------------------------------------
    # SIDEBAR — FILTROS
    # --------------------------------------------------------

    st.sidebar.header("⚙️ Filtros")

    anos_disponiveis = sorted(df[COLUNA_ANO].dropna().unique().tolist())

    marcar_todos = st.sidebar.checkbox("Selecionar todos os anos", value=True)

    if marcar_todos:
        anos_selecionados = anos_disponiveis
        st.sidebar.multiselect(
            "Anos selecionados",
            anos_disponiveis,
            default=anos_disponiveis,
            disabled=True
        )
    else:
        anos_selecionados = st.sidebar.multiselect(
            "Selecione os anos",
            anos_disponiveis,
            default=anos_disponiveis
        )

    if not anos_selecionados:
        st.warning("Selecione pelo menos um ano na barra lateral.")
        st.stop()

    indicadores_disponiveis = [
        c for c in NOMES_INDICADORES if c in df.columns
    ]

    indicadores_selecionados = st.sidebar.multiselect(
        "Indicadores em destaque na tabela e nos insights",
        options=indicadores_disponiveis,
        default=indicadores_disponiveis,
        format_func=lambda c: NOMES_INDICADORES.get(c, c)
    )

    if diagnostico["anos_ausentes"]:

        st.sidebar.warning(
            "Anos ausentes na base: "
            + ", ".join(str(a) for a in diagnostico["anos_ausentes"])
        )

    if diagnostico["indicadores_ausentes"]:

        with st.sidebar.expander("Indicadores ausentes na base"):

            for nome in diagnostico["indicadores_ausentes"]:
                st.caption(f"- {NOMES_INDICADORES.get(nome, nome)}")

    df_filtrado = df[df[COLUNA_ANO].isin(anos_selecionados)].copy()

    colunas_manter = [COLUNA_ANO] + [
        c for c in df_filtrado.columns
        if c != COLUNA_ANO
        and (c not in NOMES_INDICADORES or c in indicadores_selecionados)
    ]

    df_filtrado_indicadores = df_filtrado[colunas_manter].copy()

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------

    st.subheader("📌 Principais Indicadores")
    criar_kpis(df_filtrado)

    st.divider()

    # --------------------------------------------------------
    # ABAS
    # --------------------------------------------------------

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Resultados (DRE)",
        "💰 Rentabilidade",
        "🏦 Liquidez e Endividamento",
        "🏛️ Balanço Patrimonial",
        "📋 Tabela e Insights",
        "🔁 2022 × 2025",
    ])

    with tab1:
        st.subheader("Demonstração do Resultado (DRE)")
        criar_grafico_dre(df_filtrado)

        st.subheader("Crescimento Anual")
        criar_grafico_crescimento(df_filtrado)

    with tab2:
        st.subheader("Margens")
        criar_grafico_margens(df_filtrado)

        st.subheader("Rentabilidade (ROA e ROE)")
        criar_grafico_rentabilidade(df_filtrado)

    with tab3:
        st.subheader("Liquidez")
        criar_grafico_liquidez(df_filtrado)

        st.subheader("Endividamento")
        criar_grafico_endividamento(df_filtrado)

    with tab4:
        st.subheader("Estrutura Patrimonial")
        criar_grafico_balanco(df_filtrado)

    with tab5:
        col_tabela, col_insights = st.columns([2, 1])

        with col_tabela:
            st.subheader("Tabela de Indicadores por Ano")
            criar_tabela_financeira(df_filtrado_indicadores)

        with col_insights:
            st.subheader("Principais Insights")
            gerar_insights(df_filtrado)

    with tab6:
        st.subheader("Comparação entre Início e Fim do Período")
        criar_comparacao_periodo(df_filtrado)

    # --------------------------------------------------------
    # RODAPÉ
    # --------------------------------------------------------

    st.divider()

    st.caption(
        "Projeto Integrador III — Análise Financeira da Ambev | "
        "Dados extraídos das Demonstrações Financeiras Padronizadas (DFP) "
        "disponibilizadas pela CVM. Base consumida: "
        f"`{caminho.relative_to(RAIZ_PROJETO)}`."
    )


if __name__ == "__main__":
    main()