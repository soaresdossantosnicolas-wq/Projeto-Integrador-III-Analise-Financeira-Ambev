"""Dashboard acadêmico: demonstrações consolidadas, unidades explícitas e comparações honestas."""

import hashlib
import io
import json
import logging

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import config
from dashboard_utils import (
    calcular_variacoes,
    exportar_csv,
    formatar_indicador,
    formatar_percentual,
    formatar_valor,
    numero_br,
    preparar_series,
    validar_snapshot,
)
from excecoes import ErroValidacaoDados

log = logging.getLogger(__name__)
st.set_page_config(page_title="Ambev | Análise financeira", page_icon="📊", layout="wide")


@st.cache_data(show_spinner=False)
def carregar_dados(conteudo: bytes) -> pd.DataFrame:
    """Cache por conteúdo: atualizar o CSV invalida a leitura, mesmo sem mudar o caminho."""
    return validar_snapshot(pd.read_csv(io.BytesIO(conteudo), encoding="utf-8-sig"))


@st.cache_data(show_spinner=False)
def dados_grafico(df: pd.DataFrame, colunas: tuple[str, ...], percentual: bool = False) -> pd.DataFrame:
    """Preparação leve e cacheada; o dashboard não reexecuta o ETL."""
    return preparar_series(df, list(colunas), percentual=percentual)


def estilizar(fig: go.Figure, titulo: str, eixo: str, tema: str) -> go.Figure:
    """Template único, cores centralizadas e contraste dos eixos em claro/escuro."""
    escuro = tema == "Escuro"
    fig.update_layout(
        template="plotly_dark" if escuro else "plotly_white",
        title=dict(text=titulo, font=dict(size=19)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", size=13, color="#E5EDF8" if escuro else "#17253C"),
        margin=dict(l=10, r=10, t=65, b=20),
        height=370,
        separators=",.",
        legend=dict(orientation="h", y=-0.23, x=0),
        legend_title_text="",
        hovermode="x unified",
        dragmode=False,
    )
    fig.update_xaxes(title=None, type="category", showgrid=False)
    fig.update_yaxes(title=eixo, gridcolor="rgba(133,147,169,0.18)", zeroline=True, rangemode="tozero")
    return fig


def mostrar(fig: go.Figure, chave: str) -> None:
    """Renderiza responsivamente com ferramentas discretas."""
    st.plotly_chart(
        fig,
        use_container_width=True,
        key=chave,
        config={"displaylogo": False, "scrollZoom": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
    )


def grafico_series(
    df: pd.DataFrame,
    colunas: tuple[str, ...],
    titulo: str,
    tema: str,
    *,
    percentual: bool = False,
    linha: bool = False,
    razao: bool = False,
) -> go.Figure:
    """Gráfico sem transformação monetária oculta; os eixos declaram R$ bilhões, % ou vezes."""
    dados = dados_grafico(df, colunas, percentual).copy()
    dados["y"] = dados.valor if percentual or razao else dados.valor / 1e9
    cores = {
        config.NOMES.get(c, c): config.PALETA.get(c, list(config.PALETA.values())[i % 6])
        for i, c in enumerate(colunas)
    }
    parametros = dict(
        data_frame=dados,
        x="ano_analise",
        y="y",
        color="rotulo",
        color_discrete_map=cores,
        custom_data=["exibicao", "rotulo"],
    )
    if linha:
        fig = px.line(**parametros, markers=True, line_shape="linear")
        fig.update_traces(
            mode="lines+markers+text",
            text=dados.exibicao if len(colunas) == 1 else None,
            textposition="top center",
        )
    else:
        fig = px.bar(**parametros, barmode="group")
    fig.update_traces(hovertemplate="%{customdata[1]}: %{customdata[0]}<extra></extra>")
    return estilizar(fig, titulo, "%" if percentual else "Vezes" if razao else "R$ bilhões", tema)


def criar_kpis(base: pd.DataFrame, ano: int) -> None:
    """Quatro cards; percentuais variam em p.p., dinheiro em %, sempre contra ano−1."""
    colunas = st.columns(4)
    for container, nome in zip(colunas, ("receita_liquida", "lucro_liquido", "roe", "endividamento_geral")):
        atual, anterior, relativo = calcular_variacoes(base, nome, ano)
        delta = None
        if np.isfinite(atual) and np.isfinite(anterior):
            mudanca = atual - anterior if nome in config.PERCENTUAIS else relativo
            if np.isfinite(mudanca):
                unidade = "p.p." if nome in config.PERCENTUAIS else "%"
                seta = "▲" if mudanca > 0 else "▼" if mudanca < 0 else "="
                delta = f"{numero_br(mudanca)} {unidade} {seta} vs. {ano - 1}"
        container.metric(
            config.NOMES[nome],
            formatar_indicador(nome, atual),
            delta=delta,
            delta_color="inverse" if nome == "endividamento_geral" else "normal",
            help=config.FORMULAS[nome] + " Delta usa o ano calendário anterior, mesmo fora do filtro.",
        )


def tabela_dados(df: pd.DataFrame) -> None:
    """Tabela formatada como texto pt-BR e exportação numérica independente."""
    colunas = [
        "ano_analise",
        "receita_liquida",
        "lucro_liquido",
        "margem_bruta",
        "margem_liquida",
        "roe",
        "liquidez_corrente",
        "liquidez_seca",
        "endividamento_geral",
    ]
    exibicao = pd.DataFrame({"Ano": df.ano_analise.astype(str)})
    for nome in colunas[1:]:
        exibicao[config.NOMES[nome]] = df[nome].map(lambda v, c=nome: formatar_indicador(c, v))
    st.dataframe(
        exibicao,
        hide_index=True,
        use_container_width=True,
        column_config={"Ano": st.column_config.TextColumn("Exercício", width="small")},
    )
    st.download_button(
        "↓ Baixar dados selecionados",
        data=exportar_csv(df),
        file_name="ambev_indicadores.csv",
        mime="text/csv",
        help="Valores monetários em reais; percentuais na escala 0–100. CSV pt-BR.",
    )


def cascata_dre(linha: pd.Series, tema: str) -> go.Figure:
    """Ponte reconciliada até o lucro: despesas/receitas operacionais são agregadas, sem inventar aberturas."""
    nomes = [
        "Receita",
        "Custos",
        "Bruto",
        "Operacionais",
        "EBIT CVM",
        "Financeiro",
        "Tributos",
        "Descontinuadas",
        "Líquido",
    ]
    valores = [
        linha.receita_liquida,
        linha.custo_vendas,
        linha.lucro_bruto,
        linha.despesas_receitas_operacionais,
        linha.resultado_operacional,
        linha.resultado_financeiro,
        linha.tributos_lucro,
        linha.resultado_descontinuado,
        linha.lucro_liquido,
    ]
    fig = go.Figure(
        go.Waterfall(
            x=nomes,
            y=np.array(valores) / 1e9,
            measure=[
                "absolute",
                "relative",
                "total",
                "relative",
                "total",
                "relative",
                "relative",
                "relative",
                "total",
            ],
            customdata=[formatar_valor(v) for v in valores],
            hovertemplate="%{x}: %{customdata}<extra></extra>",
            increasing=dict(marker=dict(color=config.PALETA["positivo"])),
            decreasing=dict(marker=dict(color=config.PALETA["negativo"])),
            totals=dict(marker=dict(color=config.PALETA["primaria"])),
        )
    )
    return estilizar(fig, f"Da receita ao lucro · {int(linha.ano_analise)}", "R$ bilhões", tema)


def sobre(metadados: dict) -> None:
    """Metodologia e atribuição disponíveis dentro da aplicação publicada."""
    st.subheader("Uma leitura dos números, com origem verificável")
    st.write(
        "Projeto Integrador III · Ciência de Dados · Fatec Cotia. Análise descritiva das DFPs consolidadas da Ambev, de 2022 a 2025."
    )
    st.markdown(
        f"**Autores:** {', '.join(config.AUTORES)}.  \n**Licença do código:** {config.LICENCA}.  \n[Fonte CVM]({config.FONTE_CVM}) · [Código e documentação]({config.REPOSITORIO})"
    )
    st.markdown(
        "**Método:** empresa por código CVM/CNPJ; demonstração consolidada; exercício ÚLTIMO; datas anuais e última versão da DFP; contas exatas; conversão de R$ mil para reais; validações contábeis antes da publicação."
    )
    st.dataframe(
        pd.DataFrame(
            [{"Indicador": config.NOMES.get(k, k), "Definição": v} for k, v in config.FORMULAS.items()]
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.info(
        "EBIT CVM (3.05) inclui equivalência patrimonial. O EBIT do RI exclui esse resultado; diferenças de conceito e arredondamento estão reconciliadas em reports/validacao/conciliacao_ambev.csv."
    )
    st.markdown(
        "**Limitações:** quatro observações anuais; valores nominais; ROA/ROE com saldos finais; sem previsão ou inferência causal. Dívida financeira e EBITDA normalizado não são extraídos, portanto dívida líquida/EBITDA é n/d. A liquidez seca desconta apenas estoques. Menor endividamento não significa, isoladamente, melhor desempenho."
    )
    st.caption(
        "Finalidade educacional. Não constitui recomendação de investimento. Nenhuma marca ou logotipo da companhia é utilizado."
    )
    with st.expander("Rastreabilidade e atualização"):
        st.json(metadados)


def main() -> None:
    """Carrega somente snapshots locais; erros esperados têm explicação sem traceback."""
    st.markdown(
        "<style>.block-container{padding-top:4.2rem;max-width:1500px} [data-testid='stMetricValue']{font-size:1.65rem} h1{letter-spacing:-.045em} [data-testid='stCaptionContainer']{line-height:1.5}</style>",
        unsafe_allow_html=True,
    )
    try:
        with st.spinner("Carregando demonstrações financeiras…"):
            conteudo = (config.PASTA_DADOS_TRATADOS / "indicadores_financeiros_ambev.csv").read_bytes()
            df = carregar_dados(conteudo)
            metadados = json.loads(
                (config.PASTA_DADOS_TRATADOS / "metadados.json").read_text(encoding="utf-8")
            )
            if (
                hashlib.sha256(conteudo).hexdigest() != metadados.get("indicadores_sha256")
                or metadados.get("status") != "validado"
            ):
                raise ErroValidacaoDados("Snapshot diverge dos metadados da última execução válida.")
    except (OSError, ValueError, ErroValidacaoDados, pd.errors.ParserError):
        log.exception("Snapshot indisponível ou inválido.")
        st.error("Não foi possível abrir os dados validados do projeto.")
        st.info(
            "Confira os arquivos de indicadores e metadados. Para regenerá-los: python code/run_pipeline.py"
        )
        return
    st.caption("PROJETO INTEGRADOR III  /  CIÊNCIA DE DADOS")
    st.title("Ambev, em perspectiva.")
    st.markdown("Demonstrações consolidadas · **2022–2025** · Dados abertos da CVM")
    atualizado = pd.to_datetime(metadados.get("gerado_em_utc"), utc=True, errors="coerce")
    st.caption(
        f"Último exercício: 2025 · Snapshot gerado em {atualizado.strftime('%d/%m/%Y %H:%M UTC') if not pd.isna(atualizado) else 'data não disponível'} · Valores nominais em reais"
    )
    with st.sidebar:
        st.subheader("Explorar a análise")
        st.caption("AMBEV S.A. · CVM 23264")
        if st.button("Limpar filtros", use_container_width=True):
            st.session_state["anos"] = list(config.ANOS)
            st.session_state["series"] = ["receita_liquida", "lucro_liquido", "resultado_operacional"]
        anos = st.multiselect("Exercícios", config.ANOS, default=config.ANOS, key="anos")
        st.caption("Demonstração: consolidada. O pipeline não mistura dados individuais.")
        series = st.multiselect(
            "Séries da DRE",
            ["receita_liquida", "lucro_bruto", "resultado_operacional", "lucro_liquido"],
            default=["receita_liquida", "lucro_liquido", "resultado_operacional"],
            format_func=lambda c: config.NOMES[c],
            key="series",
        )
        tema = st.selectbox(
            "Contraste dos gráficos",
            ["Escuro", "Claro"],
            index=1 if st.get_option("theme.base") == "light" else 0,
        )
        st.divider()
        st.caption(
            "Filtro de anos afeta gráficos e exportação. O delta dos cards compara o último ano selecionado com o ano calendário anterior da base completa."
        )
        st.markdown(f"[Abrir repositório ↗]({config.REPOSITORIO})")
    filtrado = df.loc[df.ano_analise.isin(anos)].copy()
    if filtrado.empty:
        st.info("Selecione ao menos um exercício na barra lateral.")
        return
    ultimo = int(filtrado.ano_analise.max())
    criar_kpis(df, ultimo)
    st.caption(
        f"Cards referentes a {ultimo}. ▲/▼ indicam direção; interpretação exige contexto. Percentuais variam em pontos percentuais."
    )
    st.divider()
    abas = st.tabs(
        [
            "Visão Geral",
            "DRE",
            "Rentabilidade",
            "Liquidez e Endividamento",
            "Balanço",
            "Comparação de Períodos",
            "Sobre",
        ]
    )
    with abas[0]:
        st.subheader("O desempenho ao longo do tempo")
        if series:
            mostrar(
                grafico_series(filtrado, tuple(series), "Receita e resultados consolidados", tema), "geral"
            )
        else:
            st.info("Selecione uma série da DRE na barra lateral.")
        a, b = st.columns(2)
        with a:
            melhor = filtrado.loc[filtrado.margem_liquida.idxmax()]
            st.markdown(
                f"**Maior margem líquida no recorte**  \n{int(melhor.ano_analise)} · {formatar_percentual(melhor.margem_liquida)}"
            )
        with b:
            atual, anterior, delta = calcular_variacoes(df, "receita_liquida", ultimo)
            st.markdown(
                f"**Receita de {ultimo}**  \n{formatar_valor(atual)} · {formatar_percentual(delta)} contra {ultimo - 1}"
                if np.isfinite(delta)
                else f"**Receita de {ultimo}**  \n{formatar_valor(atual)} · sem comparação anual disponível"
            )
        tabela_dados(filtrado)
    with abas[1]:
        mostrar(cascata_dre(filtrado.iloc[-1], tema), "cascata")
        st.caption(
            "Custos e despesas mantêm o sinal da DFP. Operacionais incluem equivalência patrimonial; subtotais não são somados duas vezes."
        )
        contas = ("custo_vendas", "lucro_bruto", "resultado_operacional", "lucro_liquido")
        vertical = dados_grafico(filtrado, contas).copy()
        receitas = filtrado.set_index("ano_analise").receita_liquida
        vertical["percentual"] = vertical.valor / vertical.ano_analise.map(receitas) * 100
        vertical["texto"] = vertical.percentual.map(formatar_percentual)
        fig = px.bar(
            vertical,
            x="ano_analise",
            y="percentual",
            color="rotulo",
            barmode="group",
            color_discrete_sequence=[
                config.PALETA[k] for k in ("neutro", "secundaria", "destaque", "positivo")
            ],
            custom_data=["texto", "rotulo"],
        )
        fig.update_traces(hovertemplate="%{customdata[1]}: %{customdata[0]}<extra></extra>")
        mostrar(
            estilizar(fig, "Análise vertical · contas em relação à receita", "% da receita líquida", tema),
            "vertical",
        )
        st.caption(
            "As contas se sobrepõem: lucro bruto, EBIT e lucro líquido não formam uma composição de 100%."
        )
    with abas[2]:
        mostrar(
            grafico_series(
                filtrado,
                ("margem_bruta", "margem_operacional", "margem_liquida"),
                "Margens sobre a receita",
                tema,
                percentual=True,
                linha=True,
            ),
            "margens",
        )
        mostrar(
            grafico_series(
                filtrado,
                ("roa", "roe"),
                "Retornos sobre saldos de encerramento",
                tema,
                percentual=True,
                linha=True,
            ),
            "retornos",
        )
    with abas[3]:
        fig = grafico_series(
            filtrado,
            ("liquidez_corrente", "liquidez_seca"),
            "Cobertura do passivo circulante",
            tema,
            razao=True,
        )
        fig.add_hline(
            y=1, line_dash="dot", line_color=config.PALETA["neutro"], annotation_text="Referência: 1,0 ×"
        )
        mostrar(fig, "liquidez")
        mostrar(
            grafico_series(
                filtrado,
                ("endividamento_geral", "capital_terceiros_patrimonio"),
                "Estrutura de financiamento",
                tema,
                percentual=True,
                linha=True,
            ),
            "endividamento",
        )
        st.info(
            "Dívida líquida / EBITDA: n/d. O pipeline não extrai dívida financeira nem EBITDA normalizado; passivo exigível não é uma medida equivalente de dívida financeira."
        )
    with abas[4]:
        dados = dados_grafico(
            filtrado, ("passivo_circulante", "passivo_nao_circulante", "patrimonio_liquido")
        ).copy()
        dados["bilhoes"] = dados.valor / 1e9
        fig = px.bar(
            dados,
            x="ano_analise",
            y="bilhoes",
            color="rotulo",
            barmode="stack",
            color_discrete_map={
                config.NOMES[c]: config.PALETA[c]
                for c in ("passivo_circulante", "passivo_nao_circulante", "patrimonio_liquido")
            },
            custom_data=["exibicao", "rotulo"],
        )
        fig.update_traces(hovertemplate="%{customdata[1]}: %{customdata[0]}<extra></extra>")
        mostrar(estilizar(fig, "Como os ativos são financiados", "R$ bilhões", tema), "balanco")
        st.caption(
            "Passivo circulante + passivo não circulante + patrimônio líquido = ativo total. Identidade validada antes da geração do snapshot."
        )
    with abas[5]:
        st.subheader("Variações e comparação entre extremos")
        if len(filtrado) < 2:
            st.info("Selecione pelo menos dois exercícios para comparar períodos.")
        else:
            inicio, fim = filtrado.iloc[0], filtrado.iloc[-1]
            linhas = []
            for c in ("receita_liquida", "lucro_liquido", "roe", "liquidez_corrente", "endividamento_geral"):
                diferenca = fim[c] - inicio[c]
                unidade = "p.p." if c in config.PERCENTUAIS else "×" if c in config.RAZOES else "R$"
                linhas.append(
                    {
                        "Indicador": config.NOMES[c],
                        str(int(inicio.ano_analise)): formatar_indicador(c, inicio[c]),
                        str(int(fim.ano_analise)): formatar_indicador(c, fim[c]),
                        "Variação absoluta": f"{numero_br(diferenca)} {unidade}"
                        if unidade != "R$"
                        else formatar_valor(diferenca),
                    }
                )
            st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
            st.caption("Comparação entre extremos selecionados; não é crescimento anualizado.")
        campo = st.selectbox(
            "Conta para análise horizontal anual",
            ["receita_liquida", "lucro_liquido", "lucro_bruto"],
            format_func=lambda c: config.NOMES[c],
        )
        crescimento = f"crescimento_{campo}"
        horizontal = filtrado[["ano_analise", crescimento]].dropna().copy()
        if horizontal.empty:
            st.info("Não há variação anual disponível para os anos selecionados.")
        else:
            horizontal["direcao"] = np.where(horizontal[crescimento] >= 0, "▲ Aumento", "▼ Redução")
            horizontal["texto"] = horizontal[crescimento].map(formatar_percentual)
            fig = px.bar(
                horizontal,
                x="ano_analise",
                y=crescimento,
                color="direcao",
                text="texto",
                custom_data=["texto"],
                color_discrete_map={
                    "▲ Aumento": config.PALETA["positivo"],
                    "▼ Redução": config.PALETA["negativo"],
                },
            )
            fig.update_traces(hovertemplate="Variação anual: %{customdata[0]}<extra></extra>")
            mostrar(
                estilizar(fig, config.NOMES[campo] + " · variação contra o ano anterior", "%", tema),
                "horizontal",
            )
            st.caption(
                "Base completa do calendário: ocultar um ano não altera a variação do seguinte. Base zero, ausente ou sem ano anterior gera n/d."
            )
    with abas[6]:
        sobre(metadados)
    st.divider()
    st.caption(f"{' · '.join(config.AUTORES)} · 2026 · Licença MIT · Projeto Integrador III")
    st.markdown(f"[Código-fonte e metodologia ↗]({config.REPOSITORIO})")


if __name__ == "__main__":
    main()
