"""Aba preditiva: lê saídas validadas e nunca ajusta modelos durante interações."""

import hashlib
import io
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from dashboard_utils import formatar_indicador, numero_br
from dashboard_design import estilizar_figura


@st.cache_data(show_spinner=False)
def carregar_saidas(arquivos: tuple) -> dict:
    """Cache por conteúdo e verificação de hashes do lote salvo pelo estágio 5."""
    conteudos = dict(arquivos)
    metadados = json.loads(conteudos["metadados.json"].decode("utf-8"))
    for nome, sha in metadados.get("sha256_arquivos", {}).items():
        if nome in conteudos and hashlib.sha256(conteudos[nome]).hexdigest() != sha:
            raise ValueError("Arquivo incompatível com os metadados preditivos.")
    dados = {nome[:-4]: pd.read_csv(io.BytesIO(b)) for nome, b in arquivos if nome.endswith(".csv")}
    dados["metadados"] = metadados
    return dados


def grafico_projecao(
    historico: pd.DataFrame, previsto: pd.DataFrame, variavel: str, tema: str, unidade_visual: str = "Bilhões"
) -> go.Figure:
    """Dados realizados sólidos, futuro tracejado e faixa exploratória; apenas muda a unidade de exibição."""
    divisor = (
        1
        if variavel in config.PERCENTUAIS or variavel in config.RAZOES
        else config.UNIDADES_VISUAIS[unidade_visual][0]
    )
    unidade = (
        "%"
        if variavel in config.PERCENTUAIS
        else "Vezes"
        if variavel in config.RAZOES
        else config.UNIDADES_VISUAIS[unidade_visual][1]
    )
    hist = historico.dropna(subset=[variavel]).sort_values("data")
    if previsto.frequencia.iloc[0] == "trimestral":
        hist = hist.tail(12)
    futuro = previsto.sort_values("data")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=futuro.data,
            y=futuro.superior / divisor,
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=futuro.data,
            y=futuro.inferior / divisor,
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(149,116,181,.20)",
            name="Faixa exploratória",
            customdata=[
                [formatar_indicador(variavel, a), formatar_indicador(variavel, b)]
                for a, b in zip(futuro.inferior, futuro.superior)
            ],
            hovertemplate="Faixa: %{customdata[0]} a %{customdata[1]}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=hist.data,
            y=hist[variavel] / divisor,
            mode="lines+markers",
            name="Realizado — CVM",
            line=dict(color=config.PALETA["primaria"]),
            customdata=hist[variavel].map(lambda v: formatar_indicador(variavel, v)),
            hovertemplate="Realizado: %{customdata}<extra></extra>",
        )
    )
    valores = [hist[variavel].iloc[-1], *futuro.valor]
    fig.add_trace(
        go.Scatter(
            x=[hist.data.iloc[-1], *futuro.data],
            y=np.asarray(valores) / divisor,
            mode="lines+markers",
            name="Projetado — cenário",
            line=dict(color=config.PALETA["destaque"], dash="dash"),
            customdata=[formatar_indicador(variavel, v) for v in valores],
            hovertemplate="Projetado: %{customdata}<extra></extra>",
        )
    )
    estilizar_figura(fig, config.NOMES[variavel] + "<br><sup>Histórico e projeção</sup>", unidade, tema)
    fig.update_layout(height=440, margin=dict(t=115, b=40, l=15, r=15))
    periodos = pd.to_datetime(pd.concat([hist.data, futuro.data], ignore_index=True))
    trimestral = previsto.frequencia.iloc[0] == "trimestral"
    rotulos = [f"{d.year}T{d.quarter}" if trimestral else str(d.year) for d in periodos]
    fig.update_xaxes(
        tickmode="array",
        tickvals=periodos.tolist(),
        ticktext=rotulos,
        tickangle=-45 if trimestral else 0,
        title="Trimestre" if trimestral else "Exercício",
    )
    fig.update_yaxes(rangemode="tozero", gridcolor=config.TEMAS_DASHBOARD[tema]["grade"])
    fig.add_vline(
        x=pd.Timestamp(hist.data.iloc[-1]).timestamp() * 1000,
        line_dash="dot",
        line_color=config.PALETA["neutro"],
    )
    return fig


def mostrar_metricas(dados: dict, freq: str, variavel: str) -> None:
    """Tabelas por alvo/horizonte e conjunto, sem reescolher pelo teste final."""
    with st.expander("Comparar modelos e entender as métricas"):
        conjunto = st.selectbox(
            "Conjunto de avaliação",
            key="avaliacao",
            bind="query-params",
            options=["desenvolvimento", "teste_final"],
            format_func=lambda c: (
                "Desenvolvimento — usado na seleção"
                if c == "desenvolvimento"
                else "Teste final reservado — não usado na seleção"
            ),
        )
        m = dados["metricas"].loc[
            lambda d: d.frequencia.eq(freq) & d.variavel.eq(variavel) & d.conjunto.eq(conjunto)
        ]
        linhas = []
        for r in m.itertuples():
            linhas.append(
                {
                    "Modelo": config.PREDITIVA_ROTULOS_MODELOS[r.modelo],
                    "Horizonte": r.horizonte,
                    "Nº de erros": r.n,
                    "MAE": formatar_indicador(variavel, r.mae),
                    "RMSE": formatar_indicador(variavel, r.rmse),
                    "sMAPE (%)": numero_br(r.smape),
                    "MAPE (%)": numero_br(r.mape),
                    "MASE (×)": numero_br(r.mase),
                    "Supera ingênuo (MAE)": "Sim" if r.supera_ingenuo else "Não",
                    "Supera sazonal (MAE)": ("Sim" if r.supera_ingenuo_sazonal else "Não")
                    if freq == "trimestral"
                    else "Não se aplica",
                }
            )
        st.dataframe(pd.DataFrame(linhas), hide_index=True, width="stretch")
        st.caption(
            "MAE/RMSE: erro na unidade do alvo. sMAPE/MAPE: erro relativo; MAPE pode distorcer com valores perto de zero. MASE usa variação ingênua SOMENTE do treino (sazonal nos trimestres); MASE < 1 não prova vitória sobre o baseline no teste. Comparações usam as mesmas origens. N=1 não permite inferir confiabilidade."
        )


def mostrar_premissas(dados: dict, freq: str, modelo: str, cenario: str, variavel: str) -> None:
    """Distingue quantis históricos de crescimento/margens efetivos e sensibilidade de um parâmetro."""
    with st.expander("Premissas e sensibilidade dos cenários"):
        p = (
            dados["premissas_cenarios"]
            .loc[lambda d: d.frequencia.eq(freq) & d.modelo.eq(modelo) & d.cenario.eq(cenario)]
            .copy()
        )
        for c in ["valor", "referencia_base"]:
            p[c] = p[c].map(lambda v: numero_br(v * 100) + "%")
        p["parametro"] = p.parametro.map(
            {
                "crescimento": "Referência histórica de crescimento (choque relativo)",
                "margem_operacional": "Referência histórica de margem operacional",
                "margem_liquida": "Referência histórica de margem líquida",
                "crescimento_receita_efetivo": "Crescimento efetivo da receita projetada",
                "margem_operacional_efetiva": "Margem operacional efetiva",
                "margem_liquida_efetiva": "Margem líquida efetiva",
            }
        )
        p = p.drop(columns=["modelo", "frequencia", "cenario"]).rename(
            columns={
                "parametro": "Premissa",
                "valor": "Valor do cenário",
                "referencia_base": "Referência sem choque",
                "quantil": "Quantil",
                "origem": "Origem",
                "treino_fim": "Último período do treino",
                "n_observacoes": "Observações históricas",
                "trimestre": "Trimestre (0 = anual)",
                "horizonte": "Horizonte",
            }
        )
        st.dataframe(p, hide_index=True, width="stretch")
        st.caption(
            "Pessimista/base/otimista usam quantis históricos 25/50/75; margens trimestrais usam o mesmo trimestre do calendário. São referências de choque relativo, não taxas aplicadas diretamente a todos os modelos: veja as linhas efetivas. Não representam probabilidades dos cenários. Overrides exigem fonte/justificativa; o PL residual fecha o balanço."
        )
        st.caption(
            "Sensibilidade do modelo de direcionadores: muda uma premissa por vez entre quartis históricos, independentemente do modelo escolhido no gráfico."
        )
        sens = (
            dados["sensibilidade"]
            .loc[lambda d: d.frequencia.eq(freq) & d.variavel.eq(variavel)]
            .drop(columns=["frequencia", "modelo", "variavel"])
            .copy()
        )
        sens["premissa"] = sens.premissa.map(
            {
                "crescimento": "Crescimento anual da receita",
                "margem_operacional": "Margem operacional",
                "margem_liquida": "Margem líquida",
            }
        )
        for c in ["valor_base", "valor_sensibilidade", "diferenca"]:
            sens[c] = sens[c].map(lambda v: formatar_indicador(variavel, v))
        st.dataframe(
            sens.rename(
                columns={
                    "premissa": "Premissa alterada",
                    "choque": "Quantil",
                    "data": "Período",
                    "valor_base": "Base",
                    "valor_sensibilidade": "Após mudança",
                    "diferenca": "Diferença",
                }
            ),
            hide_index=True,
            width="stretch",
        )


@st.fragment
def renderizar_projecoes(tema: str, unidade_visual: str = "Bilhões") -> None:
    """Interface de leitura; previsões são geradas separadamente no estágio 5."""
    st.subheader("Projeções exploratórias, com limites explícitos")
    st.warning(
        "Projeções baseadas em dados históricos e premissas simplificadas; não constituem recomendação de investimento."
    )
    st.info(
        "Corte contábil em 31/12/2025. Este é um exercício retrospectivo para 2026–2027, não uma previsão em tempo real de outubro de 2026. As faixas não têm cobertura estatística futura demonstrada."
    )
    nomes = [
        "projecoes.csv",
        "metricas.csv",
        "selecao.csv",
        "premissas_cenarios.csv",
        "historico_anual.csv",
        "historico_trimestral.csv",
        "modelos_descartados.csv",
        "diagnostico_residuos.csv",
        "sensibilidade.csv",
        "metadados.json",
    ]
    try:
        dados = carregar_saidas(tuple((n, (config.PASTA_PREDITIVA / n).read_bytes()) for n in nomes))
    except (OSError, ValueError, KeyError):
        st.error(
            "Saídas preditivas indisponíveis ou inconsistentes. Execute o estágio 5 e publique seus CSVs e metadados juntos."
        )
        return
    a, b = st.columns(2)
    freq = a.selectbox(
        "Frequência das projeções",
        key="frequencia",
        bind="query-params",
        options=["anual", "trimestral"],
        format_func=lambda f: "Anual · 2026–2027" if f == "anual" else "Trimestral · 2026T1–T4",
    )
    variavel = b.selectbox(
        "Variável projetada",
        key="variavel_projetada",
        bind="query-params",
        options=config.PREDITIVA_ALVOS + config.PREDITIVA_INDICADORES,
        format_func=lambda c: config.NOMES[c],
    )
    selecionado = dados["selecao"].loc[lambda d: d.frequencia.eq(freq)].iloc[0]
    modelos = sorted(dados["projecoes"].loc[lambda d: d.frequencia.eq(freq), "modelo"].unique())
    a, b = st.columns(2)
    modelo = a.selectbox(
        "Modelo para projeção",
        key=f"modelo_projecao_{freq}",
        bind="query-params",
        options=modelos,
        index=modelos.index(selecionado.modelo),
        format_func=lambda m: config.PREDITIVA_ROTULOS_MODELOS[m],
    )
    cenario = b.selectbox(
        "Cenário",
        ["base", "pessimista", "otimista"],
        format_func=str.capitalize,
        key="cenario",
        bind="query-params",
    )
    st.caption(
        "O padrão foi definido no desenvolvimento, sem usar o teste final. A escolha manual explora alternativas. Os filtros descritivos de anos não alteram o treino desta aba."
    )
    st.caption(selecionado.regra + " " + selecionado.conclusao_final)
    if freq == "anual":
        st.warning(
            "Apenas 7 observações anuais comparáveis e 1 erro por horizonte no teste final. Evidência insuficiente para precisão robusta, especialmente em 2027."
        )
    else:
        st.caption(
            "28 trimestres comparáveis; teste final de apenas 4 trimestres. ROE trimestral usa lucro dos últimos 12 meses. O gráfico mostra os últimos 12 trimestres históricos."
        )
    hist = dados[f"historico_{freq}"].copy()
    hist["data"] = pd.to_datetime(hist.data)
    previsto = (
        dados["projecoes"]
        .loc[
            lambda d: (
                d.frequencia.eq(freq) & d.modelo.eq(modelo) & d.cenario.eq(cenario) & d.variavel.eq(variavel)
            )
        ]
        .copy()
    )
    if previsto.empty:
        st.info("Sem projeção disponível; nenhuma linha sem faixa será exibida.")
        return
    previsto["data"] = pd.to_datetime(previsto.data)
    st.plotly_chart(
        grafico_projecao(hist, previsto, variavel, tema, unidade_visual),
        theme=None,
        width="stretch",
        key="grafico_projecoes",
    )
    st.caption(
        "Faixas: quantis 10º–90º de simulações com resíduos centrados e estados históricos de crescimento, margens e razões patrimoniais. Não são intervalos calibrados nem probabilidades dos cenários. Mil simulações não equivalem a mil observações. Limites econômicos podem truncar os extremos."
    )
    tabela = pd.DataFrame(
        {
            "Período": previsto.data.dt.strftime("%Y")
            if freq == "anual"
            else [f"{d.year}T{d.quarter}" for d in previsto.data],
            "Projeção central": previsto.valor.map(lambda v: formatar_indicador(variavel, v)),
            "Faixa inferior": previsto.inferior.map(lambda v: formatar_indicador(variavel, v)),
            "Faixa superior": previsto.superior.map(lambda v: formatar_indicador(variavel, v)),
            "Erros históricos no horizonte": previsto.n_residuos_horizonte,
        }
    )
    st.dataframe(tabela, hide_index=True, width="stretch")
    st.download_button(
        "Baixar projeções selecionadas",
        previsto.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name="ambev_projecoes.csv",
        mime="text/csv",
    )
    mostrar_metricas(dados, freq, variavel)
    mostrar_premissas(dados, freq, modelo, cenario, variavel)
    with st.expander("Resíduos, plausibilidade e modelos descartados"):
        d = (
            dados["diagnostico_residuos"]
            .loc[lambda x: x.frequencia.eq(freq) & x.modelo.eq(modelo) & x.variavel.eq(variavel)]
            .drop(columns=["frequencia", "modelo", "variavel"])
            .copy()
        )
        d["vies_observado_menos_previsto"] = d.vies_observado_menos_previsto.map(
            lambda v: formatar_indicador(variavel, v)
        )
        for c in ["autocorrelacao_lag1", "ljung_box_p_exploratorio"]:
            d[c] = d[c].map(lambda v: numero_br(v, 4))
        st.dataframe(
            d.rename(
                columns={
                    "horizonte": "Horizonte",
                    "conjunto": "Conjunto",
                    "n": "Nº de erros",
                    "vies_observado_menos_previsto": "Viés (observado − previsto)",
                    "autocorrelacao_lag1": "Autocorrelação lag 1",
                    "ljung_box_p_exploratorio": "Ljung–Box: p exploratório",
                    "limite": "Limite de interpretação",
                }
            ),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Viés positivo: subestimação. Autocorrelação e Ljung–Box são exploratórios, com poucos erros e horizontes sobrepostos. Receita não positiva recebe fallback explícito e margens ficam nos limites do treino. Liquidez por razões não é previsão de caixa. Alternativas anuais e trimestrais são modeladas separadamente; não há reconciliação automática entre cenários/modelos distintos."
        )
        st.dataframe(dados["modelos_descartados"], hide_index=True, width="stretch")
    st.caption(
        "Fontes atuais podem incorporar revisões posteriores; não se reconstroem vintages nem atraso de divulgação. Consulte a metodologia e os riscos antes de interpretar cada número."
    )
    st.markdown(f"[Método, resultados e limites]({config.REPOSITORIO}/blob/feat/docs/analise-preditiva.md)")
