"""Exploração e exportação de snapshots: nenhuma rotina ajusta modelos ou escreve dados históricos."""

import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from dashboard_design import estilizar_figura, insight
from dashboard_utils import calcular_variacoes, exportar_csv, formatar_indicador, numero_br
from explicacoes import ajuda_indicador


@st.cache_data(show_spinner=False)
def exportar_excel(df: pd.DataFrame) -> bytes:
    """Planilha numérica em reais, com ano inteiro e percentuais na escala original 0–100."""
    saida = io.BytesIO()
    with pd.ExcelWriter(saida, engine="openpyxl") as writer:
        df.rename(columns={"ano_analise": "Ano", **config.NOMES}).to_excel(
            writer, index=False, sheet_name="Indicadores"
        )
        folha = writer.sheets["Indicadores"]
        folha.freeze_panes = "B2"
        folha.auto_filter.ref = folha.dimensions
        for coluna in folha.columns:
            folha.column_dimensions[coluna[0].column_letter].width = min(
                45, max(16, len(str(coluna[0].value)) + 2)
            )
            for celula in coluna[1:]:
                celula.number_format = "0" if coluna[0].value == "Ano" else "#,##0.00"
    return saida.getvalue()


def acao_download() -> None:
    """Confirma a solicitação; a conclusão da gravação pertence ao navegador."""
    st.toast("Download solicitado ao navegador.", icon=":material/check_circle:")


@st.fragment
def exportacoes(df: pd.DataFrame, chave: str) -> None:
    """Exporta o recorte original, independentemente da unidade usada no gráfico."""
    with st.popover("Exportar dados", icon=":material/download:"):
        st.caption(
            "Valores monetários em reais e percentuais na escala 0–100. O filtro de anos é respeitado."
        )
        st.download_button(
            "CSV · compatível com Excel",
            exportar_csv(df),
            "ambev_indicadores.csv",
            "text/csv",
            key=f"csv_{chave}",
            on_click=acao_download,
        )
        st.download_button(
            "Excel · valores numéricos",
            exportar_excel(df),
            "ambev_indicadores.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"xlsx_{chave}",
            on_click=acao_download,
        )


@st.dialog("Detalhamento do exercício", width="large")
def detalhar_exercicio(base: pd.DataFrame, ano: int) -> None:
    """Drill-down das contas existentes, sem estimar aberturas ausentes."""
    linha = base.loc[base.ano_analise.eq(ano)].iloc[0]
    st.subheader(f"{ano} · da receita ao balanço")
    campos = [
        "receita_liquida",
        "custo_vendas",
        "lucro_bruto",
        "resultado_operacional",
        "lucro_liquido",
        "ativo_total",
        "passivo_exigivel",
        "patrimonio_liquido",
    ]
    st.dataframe(
        pd.DataFrame(
            {
                "Conta": [config.NOMES[c] for c in campos],
                "Valor realizado": [formatar_indicador(c, linha[c]) for c in campos],
                "Código CVM": ["3.01", "3.02", "3.03", "3.05", "3.11", "1", "2.01 + 2.02", "2.03"],
            }
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption("Demonstração consolidada. Passivo exigível é PC + PNC; EBIT inclui equivalência patrimonial.")


def figura_exploracao(
    base: pd.DataFrame,
    recorte: pd.DataFrame,
    campo: str,
    tema: str,
    unidade: str,
    modo: str,
    forma: str,
    ano: int,
) -> go.Figure:
    """Usa o calendário completo nos deltas; só a cópia exibida recebe conversão de unidade."""
    percentual = campo in config.PERCENTUAIS
    razao = campo in config.RAZOES
    divisor, eixo = config.UNIDADES_VISUAIS[unidade]
    y = recorte[campo].to_numpy(copy=True)
    valores = [formatar_indicador(campo, v) for v in y]
    if percentual or razao:
        eixo = "%" if percentual else "Vezes"
    elif modo == "% da receita":
        y = y / recorte.receita_liquida.to_numpy() * 100
        eixo = "% da receita líquida"
        valores = [numero_br(v) + "% da receita" for v in y]
    else:
        y = y / divisor
    deltas = []
    for a in recorte.ano_analise:
        atual, anterior, relativo = calcular_variacoes(base, campo, int(a))
        valor = atual - anterior if percentual else relativo
        deltas.append(
            "n/d" if not np.isfinite(valor) else numero_br(valor) + (" p.p." if percentual else "%")
        )
    dados = list(zip(valores, deltas, recorte.ano_analise.astype(int)))
    cor = config.PALETA.get(campo, config.PALETA["primaria"])
    tooltip = "<b>%{x}</b><br>%{customdata[0]}<br>Vs. ano anterior: %{customdata[1]}<extra></extra>"
    fig = go.Figure()
    if forma == "Barras":
        fig.add_bar(
            x=recorte.ano_analise,
            y=y,
            marker=dict(color=cor, opacity=[1 if a == ano else 0.55 for a in recorte.ano_analise]),
            customdata=dados,
            hovertemplate=tooltip,
            name=config.NOMES[campo],
        )
    else:
        fig.add_scatter(
            x=recorte.ano_analise,
            y=y,
            mode="lines+markers",
            line=dict(color=cor, width=3),
            marker=dict(size=[11 if a == ano else 6 for a in recorte.ano_analise], color=cor),
            customdata=dados,
            hovertemplate=tooltip,
            name=config.NOMES[campo],
        )
    estilizar_figura(fig, config.NOMES[campo], eixo, tema)
    fig.update_layout(showlegend=False, clickmode="event+select", height=380)
    fig.update_xaxes(type="category")
    if razao and campo.startswith("liquidez"):
        fig.add_hline(
            y=1, line_dash="dot", line_color=config.PALETA["neutro"], annotation_text="Referência: 1,0 ×"
        )
    return fig


@st.cache_data(show_spinner=False)
def exportar_html(figura_json: str) -> bytes:
    """HTML independente, com Plotly incorporado; nenhum renderizador de sistema é necessário."""
    import plotly.io as pio

    return pio.from_json(figura_json).to_html(include_plotlyjs=True, full_html=True).encode("utf-8")


def solicitar_detalhe_grafico() -> None:
    """Consome apenas eventos novos de seleção, sem reabrir o diálogo em outros controles."""
    estado = st.session_state.get("exploracao", {})
    pontos = estado.get("selection", {}).get("points", [])
    if pontos:
        dado = pontos[0].get("customdata")
        st.session_state["_detalhe_solicitado"] = int(dado[2] if dado else pontos[0]["x"])


@st.fragment
def explorar(base: pd.DataFrame, filtrado: pd.DataFrame, tema: str, unidade: str, explicar: bool) -> None:
    """Indicador, foco, insight e figura atualizam juntos em um único fragment."""
    a, b, c = st.columns([2, 1.3, 1])
    campo = a.selectbox(
        "Indicador em foco",
        config.PREDITIVA_ALVOS + ["margem_liquida", "roe", "liquidez_corrente", "endividamento_geral"],
        format_func=lambda v: config.NOMES[v],
        key="indicador",
        bind="query-params",
    )
    modo = b.segmented_control(
        "Leitura",
        ["Valores", "% da receita"],
        default="Valores",
        required=True,
        key="leitura",
        bind="query-params",
        disabled=campo in config.PERCENTUAIS or campo in config.RAZOES,
    )
    forma = c.segmented_control(
        "Visual", ["Linha", "Barras"], default="Linha", required=True, key="forma", bind="query-params"
    )
    anos = filtrado.ano_analise.astype(int).tolist()
    if "ano_foco" in st.session_state and st.session_state.ano_foco not in anos:
        st.session_state.ano_foco = anos[-1]
    grafico, resumo = st.columns([2.5, 1], gap="large")
    with resumo:
        ano = st.selectbox(
            "Exercício em foco", anos, index=len(anos) - 1, key="ano_foco", bind="query-params"
        )
        atual, anterior, relativo = calcular_variacoes(base, campo, ano)
        delta = atual - anterior if campo in config.PERCENTUAIS else relativo
        unidade_delta = "p.p." if campo in config.PERCENTUAIS else "%"
        variacao = (
            f"{numero_br(delta)} {unidade_delta} frente a {ano - 1}."
            if np.isfinite(delta)
            else "Sem ano anterior comparável."
        )
        insight(f"{ano} · {config.NOMES[campo]}", formatar_indicador(campo, atual), variacao)
        with st.popover("Entender o indicador", icon=":material/info:"):
            st.write(ajuda_indicador(campo))
            st.caption(config.FORMULAS.get(campo, "Valor consolidado informado na DFP."))
        if st.button(f"Ver contas de {ano}", key="abrir_contas", width="stretch"):
            detalhar_exercicio(base, ano)
    with grafico:
        fig = figura_exploracao(base, filtrado, campo, tema, unidade, modo, forma, ano)
        st.plotly_chart(
            fig,
            theme=None,
            width="stretch",
            key="exploracao",
            on_select=solicitar_detalhe_grafico,
            selection_mode="points",
            config={"displaylogo": False, "scrollZoom": False},
            alt=f"Histórico de {config.NOMES[campo]} nos exercícios selecionados.",
        )
        ano_clicado = st.session_state.pop("_detalhe_solicitado", None)
        if ano_clicado in anos:
            detalhar_exercicio(base, ano_clicado)
        if explicar:
            st.caption(
                "Como ler: selecione um ponto ou uma barra para abrir as contas do exercício. A mudança anual usa o calendário completo, inclusive anos ocultos."
            )
        st.download_button(
            "↓ Gráfico interativo · HTML",
            exportar_html(fig.to_json()),
            "ambev_grafico.html",
            "text/html",
            key="html_exploracao",
            on_click="ignore",
        )


def tabela_executiva(df: pd.DataFrame, unidade: str, tema: str = "Escuro") -> None:
    """Números ordenáveis com formatação pt-BR e sparklines, sem modificar o snapshot."""
    campos = [
        "receita_liquida",
        "lucro_liquido",
        "margem_liquida",
        "roe",
        "liquidez_corrente",
        "endividamento_geral",
    ]
    divisor, rotulo = config.UNIDADES_VISUAIS[unidade]
    linhas = []
    for campo in campos:
        escala = 1 if campo in config.PERCENTUAIS or campo in config.RAZOES else divisor
        sufixo = "%" if campo in config.PERCENTUAIS else "×" if campo in config.RAZOES else rotulo
        valores = (df[campo] / escala).tolist()
        linha = {
            "Indicador": config.NOMES[campo] + f" ({sufixo})",
            **dict(zip(df.ano_analise.astype(str), valores)),
            "Evolução": valores,
            "Último / maior": valores[-1] / max(valores) * 100 if max(valores) > 0 else np.nan,
        }
        linhas.append(linha)
    tabela = pd.DataFrame(linhas)
    numericas = df.ano_analise.astype(str).tolist()
    estilo = tabela.style.format(precision=2, decimal=",", thousands=".", na_rep="n/d", subset=numericas)
    estilo = estilo.highlight_max(
        axis=1, subset=numericas, props=f"color: {config.TEMAS_DASHBOARD[tema]['acento']}; font-weight: 700;"
    )
    st.dataframe(
        estilo,
        hide_index=True,
        width="stretch",
        row_height=44,
        column_config={
            "Indicador": st.column_config.TextColumn(pinned=True, width="medium"),
            "Último / maior": st.column_config.ProgressColumn(
                "Último / maior (%)",
                min_value=0,
                max_value=100,
                format="%.0f%%",
                help="Último valor dividido pelo maior valor no recorte. Não é meta nem avaliação de desempenho.",
                color=config.PALETA["primaria"],
            ),
            "Evolução": st.column_config.LineChartColumn(
                "Trajetória",
                width="medium",
                help="Mesmos exercícios selecionados; cada linha tem escala própria.",
                color=config.PALETA["primaria"],
            ),
        },
    )
    st.caption(
        "Maior valor de cada linha em destaque, sem julgamento de desempenho. Barra: último / maior valor do recorte. Sparklines têm escalas próprias. Exportações em reais; ordenação e busca disponíveis na tabela."
    )
    exportacoes(df, "executiva")


@st.fragment
def comparar(base: pd.DataFrame, filtrado: pd.DataFrame, tema: str) -> None:
    """Dois exercícios explícitos, com deltas absolutos e relativos separados."""
    anos = filtrado.ano_analise.astype(int).tolist()
    if len(anos) < 2:
        st.info("Selecione pelo menos dois exercícios para comparar períodos.")
        return
    a, b = st.columns(2)
    for chave, padrao in [("comparar_inicio", anos[0]), ("comparar_fim", anos[-1])]:
        if chave in st.session_state and st.session_state[chave] not in anos:
            st.session_state[chave] = padrao
    inicio = a.selectbox("Exercício de referência", anos, index=0, key="comparar_inicio", bind="query-params")
    fim = b.selectbox(
        "Exercício de comparação", anos, index=len(anos) - 1, key="comparar_fim", bind="query-params"
    )
    if inicio == fim:
        st.info("Escolha dois exercícios diferentes para comparar.")
        return
    dados = base.set_index("ano_analise")
    linhas = []
    for campo in [
        "receita_liquida",
        "resultado_operacional",
        "lucro_liquido",
        "roe",
        "liquidez_corrente",
        "endividamento_geral",
    ]:
        v0, v1 = float(dados.loc[inicio, campo]), float(dados.loc[fim, campo])
        absoluta = v1 - v0
        relativo = (v1 - v0) / abs(v0) * 100 if v0 else np.nan
        unidade = "p.p." if campo in config.PERCENTUAIS else "×" if campo in config.RAZOES else "R$"
        linhas.append(
            {
                "Indicador": config.NOMES[campo],
                str(inicio): formatar_indicador(campo, v0),
                str(fim): formatar_indicador(campo, v1),
                "Variação absoluta": numero_br(absoluta) + f" {unidade}"
                if unidade != "R$"
                else formatar_indicador(campo, absoluta),
                "Variação relativa": numero_br(relativo) + "%" if np.isfinite(relativo) else "n/d",
            }
        )
    st.dataframe(
        pd.DataFrame(linhas),
        hide_index=True,
        width="stretch",
        column_config={"Indicador": st.column_config.TextColumn(pinned=True, width="medium")},
    )
    campos = ["receita_liquida", "resultado_operacional", "lucro_liquido"]
    variacoes = [
        (dados.loc[fim, c] / dados.loc[inicio, c] - 1) * 100 if dados.loc[inicio, c] else np.nan
        for c in campos
    ]
    fig = go.Figure(
        go.Bar(
            x=variacoes,
            y=[config.NOMES[c] for c in campos],
            orientation="h",
            marker_color=[
                config.PALETA["positivo"] if v >= 0 else config.PALETA["negativo"] for v in variacoes
            ],
            customdata=[numero_br(v) + "%" for v in variacoes],
            hovertemplate="%{y}: %{customdata}<extra></extra>",
        )
    )
    estilizar_figura(fig, f"O que mudou · {inicio} → {fim}", "Indicador", tema)
    fig.update_layout(height=280, showlegend=False, margin=dict(t=65, l=15, b=20, r=15))
    fig.update_xaxes(title="Variação relativa (%)")
    st.plotly_chart(fig, theme=None, width="stretch", key="comparacao_barras")
    st.caption(
        "Comparação entre os dois anos escolhidos, sem anualização. Cores indicam aumento/redução, não um julgamento econômico automático."
    )


def composicao_balanco(linha: pd.Series, tema: str) -> None:
    """Composições mutuamente exclusivas, sempre calculadas a partir das contas existentes."""
    for coluna, titulo, campos in zip(
        st.columns(2),
        ["Onde estão os recursos", "Como são financiados"],
        [
            ("ativo_circulante", "ativo_nao_circulante"),
            ("passivo_circulante", "passivo_nao_circulante", "patrimonio_liquido"),
        ],
    ):
        with coluna:
            fig = go.Figure(
                go.Pie(
                    labels=[config.NOMES[c] for c in campos],
                    values=[linha[c] for c in campos],
                    hole=0.72,
                    marker_colors=[config.PALETA.get(c, config.PALETA["primaria"]) for c in campos],
                    customdata=[
                        [
                            formatar_indicador(c, linha[c]),
                            numero_br(linha[c] / sum(linha[k] for k in campos) * 100) + "%",
                        ]
                        for c in campos
                    ],
                    hovertemplate="%{label}<br>%{customdata[0]}<br>%{customdata[1]}<extra></extra>",
                    textinfo="none",
                    sort=False,
                )
            )
            estilizar_figura(fig, titulo, "", tema)
            fig.update_layout(
                height=310,
                margin=dict(t=100, b=5, l=10, r=10),
                annotations=[
                    dict(text=str(int(linha.ano_analise)), x=0.5, y=0.5, showarrow=False, font=dict(size=24))
                ],
                legend=dict(font=dict(size=10)),
            )
            st.plotly_chart(fig, theme=None, width="stretch", key=f"composicao_{campos[0]}")


@st.fragment
def analise_vertical(df: pd.DataFrame, tema: str, explicar: bool) -> None:
    """Compara contas/receita sem tratar subtotais sobrepostos como partes de um total."""
    campo = st.segmented_control(
        "Leitura da análise vertical",
        ["Mapa de calor", "Barras"],
        default="Mapa de calor",
        required=True,
        key="vertical",
        bind="query-params",
    )
    contas = ["custo_vendas", "lucro_bruto", "resultado_operacional", "lucro_liquido"]
    valores = df[contas].div(df.receita_liquida, axis=0).T * 100
    textos = [[numero_br(v) + "%" for v in linha] for linha in valores.to_numpy()]
    fig = go.Figure()
    if campo == "Mapa de calor":
        limite = float(np.abs(valores.to_numpy()).max())
        fig.add_trace(
            go.Heatmap(
                z=valores.to_numpy(),
                x=df.ano_analise.astype(str),
                y=["Custos", "Lucro bruto", "EBIT CVM", "Lucro líquido"],
                zmin=-limite,
                zmax=limite,
                zmid=0,
                colorscale=[
                    [0, config.PALETA["negativo"]],
                    [0.5, config.TEMAS_DASHBOARD[tema]["superficie"]],
                    [1, config.PALETA["secundaria"]],
                ],
                text=textos,
                texttemplate="%{text}",
                customdata=textos,
                hovertemplate="%{y} · %{x}<br>%{customdata} da receita<extra></extra>",
                showscale=False,
                xgap=5,
                ygap=5,
            )
        )
    else:
        for i, c in enumerate(contas):
            fig.add_bar(
                x=df.ano_analise.astype(str),
                y=valores.loc[c],
                name=config.NOMES[c],
                marker_color=config.PALETA.get(c, config.PALETA["neutro"]),
                customdata=textos[i],
                hovertemplate="%{x}: %{customdata} da receita<extra></extra>",
            )
    estilizar_figura(
        fig, "Quanto cada conta representa da receita", "% da receita" if campo == "Barras" else "", tema
    )
    fig.update_layout(
        barmode="group",
        height=380,
        margin=dict(t=90, b=25, l=105 if campo == "Mapa de calor" else 15, r=15),
    )
    fig.update_xaxes(type="category")
    st.plotly_chart(fig, theme=None, width="stretch", key="vertical_figura")
    if explicar:
        st.caption(
            "Como ler: cada célula ou barra divide a conta pela receita do mesmo exercício. Custos mantêm o sinal negativo da DFP."
        )
    st.caption("As contas se sobrepõem: lucro bruto, EBIT e lucro líquido não formam uma composição de 100%.")
