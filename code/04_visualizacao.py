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
from dashboard_projecoes import renderizar_projecoes
from dashboard_design import aplicar_tema, estilizar_figura
from dashboard_interacoes import explorar, comparar, tabela_executiva, composicao_balanco, analise_vertical
from excecoes import ErroValidacaoDados
from explicacoes import EXPLICACOES_GRAFICOS, GLOSSARIO, ajuda_indicador

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
    estilizar_figura(fig, titulo, eixo, tema)
    fig.update_xaxes(type="category")
    return fig


def mostrar(fig: go.Figure, chave: str) -> None:
    """Renderiza responsivamente com ferramentas discretas."""
    st.plotly_chart(
        fig,
        theme=None,
        width="stretch",
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
    unidade: str = "Bilhões",
) -> go.Figure:
    """Gráfico sem transformação monetária oculta; os eixos declaram R$ bilhões, % ou vezes."""
    dados = dados_grafico(df, colunas, percentual).copy()
    divisor, eixo = config.UNIDADES_VISUAIS[unidade]
    dados["y"] = dados.valor if percentual or razao else dados.valor / divisor
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
        for i, traco in enumerate(fig.data):
            traco.update(
                line_dash=["solid", "dash", "dot"][i % 3],
                marker_symbol=["circle", "square", "diamond"][i % 3],
            )
    else:
        fig = px.bar(**parametros, barmode="group")
    fig.update_traces(hovertemplate="%{customdata[1]}: %{customdata[0]}<extra></extra>")
    return estilizar(fig, titulo, "%" if percentual else "Vezes" if razao else eixo, tema)


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
            {"lucro_liquido": "Lucro líquido", "endividamento_geral": "Endividamento"}.get(
                nome, config.NOMES[nome]
            ),
            formatar_indicador(nome, atual),
            delta=delta,
            delta_color="inverse" if nome == "endividamento_geral" else "normal",
            border=True,
            chart_data=base.loc[base.ano_analise.le(ano), nome].tolist(),
            chart_type="area",
            delta_arrow="off",
            help=ajuda_indicador(nome) + " Delta usa o ano calendário anterior, mesmo fora do filtro.",
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
        width="stretch",
        column_config={"Ano": st.column_config.TextColumn("Exercício", width="small")},
    )
    st.download_button(
        "↓ Baixar dados selecionados",
        data=exportar_csv(df),
        file_name="ambev_indicadores.csv",
        mime="text/csv",
        help="Valores monetários em reais; percentuais na escala 0–100. CSV pt-BR.",
    )


def cascata_dre(linha: pd.Series, tema: str, unidade: str = "Bilhões") -> go.Figure:
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
    divisor, eixo = config.UNIDADES_VISUAIS[unidade]
    fig = go.Figure(
        go.Waterfall(
            x=nomes,
            y=np.array(valores) / divisor,
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
    return estilizar(fig, f"Da receita ao lucro · {int(linha.ano_analise)}", eixo, tema)


def explicar_grafico(chave: str, mostrar_explicacoes: bool) -> None:
    """Mostra uma frase de leitura sem ocultar avisos essenciais de integridade."""
    if mostrar_explicacoes:
        st.caption("Como ler: " + EXPLICACOES_GRAFICOS[chave])


def sobre(metadados: dict) -> None:
    """Metodologia e atribuição disponíveis dentro da aplicação publicada."""
    st.subheader("Uma leitura dos números, com origem verificável")
    st.write(
        "Projeto Integrador III · Ciência de Dados · Fatec Cotia. Análise descritiva das DFPs consolidadas da Ambev, de 2022 a 2025."
    )
    st.markdown(
        f"**Autores:** {', '.join(config.AUTORES)}.  \n**Licença do código:** {config.LICENCA}.  \n[Fonte CVM]({config.FONTE_CVM}) · [Código e documentação]({config.REPOSITORIO})"
    )
    st.subheader("Glossário para quem está começando")
    st.caption(
        "Exemplos hipotéticos para explicar os conceitos; não são resultados adicionais da Ambev. O glossário permanece disponível mesmo quando as explicações dos gráficos estão ocultas."
    )
    for nome, (titulo, significado, cuidado, exemplo) in GLOSSARIO.items():
        with st.expander(titulo):
            st.write(significado)
            st.markdown(f"**Como interpretar:** {cuidado}")
            st.markdown(f"**Exemplo hipotético:** {exemplo}")
            if nome in config.FORMULAS:
                st.caption("Fórmula no projeto: " + config.FORMULAS[nome])
    st.subheader("Metodologia e fórmulas")
    st.markdown(
        "**Método:** empresa por código CVM/CNPJ; demonstração consolidada; exercício ÚLTIMO; datas anuais e última versão da DFP; contas exatas; conversão de R$ mil para reais; validações contábeis antes da publicação."
    )
    st.dataframe(
        pd.DataFrame(
            [{"Indicador": config.NOMES.get(k, k), "Definição": v} for k, v in config.FORMULAS.items()]
        ),
        hide_index=True,
        width="stretch",
    )
    st.info(
        "EBIT CVM (3.05) inclui equivalência patrimonial. O EBIT do RI exclui esse resultado; diferenças de conceito e arredondamento estão reconciliadas em reports/validacao/conciliacao_ambev.csv."
    )
    st.markdown(
        "**Limitações:** quatro observações anuais; valores nominais; ROA/ROE com saldos finais; análise histórica descritiva e projeções exploratórias separadas, sem inferência causal. Dívida financeira e EBITDA normalizado não são extraídos, portanto dívida líquida/EBITDA é n/d. A liquidez seca desconta apenas estoques. Menor endividamento não significa, isoladamente, melhor desempenho."
    )
    st.caption(
        "Finalidade educacional. Não constitui recomendação de investimento. Nenhuma marca ou logotipo da companhia é utilizado."
    )
    with st.expander("Rastreabilidade e atualização"):
        st.json(metadados)


def main() -> None:
    """Apresenta snapshots locais, com estado compartilhável e interação sem reexecutar o pipeline."""
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
    with st.sidebar:
        st.markdown('<div class="eyebrow">Observatório financeiro</div>', unsafe_allow_html=True)
        st.subheader("Explorar a análise")
        st.caption("AMBEV S.A. · CVM 23264")
        if st.button("Limpar filtros", width="stretch"):
            padroes = {
                "anos": list(config.ANOS),
                "series": ["receita_liquida", "lucro_liquido", "resultado_operacional"],
                "indicador": "receita_liquida",
                "ano_foco": max(config.ANOS),
                "unidade": "Bilhões",
                "leitura": "Valores",
                "forma": "Linha",
                "aba": "Visão Geral",
                "cenario": "base",
                "frequencia": "anual",
                "variavel_projetada": "receita_liquida",
                "comparar_inicio": min(config.ANOS),
                "comparar_fim": max(config.ANOS),
            }
            for chave, valor in padroes.items():
                st.session_state[chave] = valor
            for chave in list(st.session_state):
                if chave.startswith("modelo_projecao_"):
                    del st.session_state[chave]
        st.caption("01 / RECORTE HISTÓRICO")
        anos = st.multiselect("Exercícios", config.ANOS, default=config.ANOS, key="anos", bind="query-params")
        with st.expander("Séries da visão conjunta"):
            series = st.multiselect(
                "Séries da DRE",
                ["receita_liquida", "lucro_bruto", "resultado_operacional", "lucro_liquido"],
                default=["receita_liquida", "lucro_liquido", "resultado_operacional"],
                format_func=lambda c: config.NOMES[c],
                key="series",
                bind="query-params",
            )
        st.caption(f"{len(anos)} de {len(config.ANOS)} exercícios · {len(series)} séries na visão conjunta")
        st.caption("02 / APRESENTAÇÃO")
        tema = st.selectbox(
            "Aparência",
            ["Escuro", "Claro"],
            index=1 if st.get_option("theme.base") == "light" else 0,
            key="tema",
            bind="query-params",
        )
        unidade = st.selectbox(
            "Unidade monetária",
            list(config.UNIDADES_VISUAIS),
            key="unidade",
            bind="query-params",
            help="Altera apenas a exibição monetária. Exportações mantêm os valores em reais.",
        )
        mostrar_explicacoes = st.checkbox(
            "Mostrar explicações",
            value=True,
            key="mostrar_explicacoes",
            bind="query-params",
            help="Guias de leitura junto aos gráficos. Fórmulas e avisos essenciais permanecem visíveis.",
        )
        st.divider()
        st.caption(
            "Deltas dos cards usam o ano calendário anterior da base completa. Selecionar anos não altera os dados nem o treino das projeções."
        )
        st.markdown(f"[Código e metodologia ↗]({config.REPOSITORIO})")
    apresentacao = st.toggle(
        "Modo apresentação",
        value=False,
        key="apresentacao",
        bind="query-params",
        help="Amplia a área de leitura e oculta os filtros laterais. Desative aqui para voltar.",
    )
    aplicar_tema(tema, apresentacao)
    filtrado = df.loc[df.ano_analise.isin(anos)].copy()
    if filtrado.empty:
        st.title("Ambev, em perspectiva.")
        st.info("Selecione ao menos um exercício na barra lateral.")
        return
    ultimo = int(filtrado.ano_analise.max())
    atual = filtrado.iloc[-1]
    _, _, delta_receita = calcular_variacoes(df, "receita_liquida", ultimo)
    atualizado = pd.to_datetime(metadados.get("gerado_em_utc"), utc=True, errors="coerce")
    data_snapshot = (
        atualizado.tz_convert("America/Sao_Paulo").strftime("%d/%m/%Y · %H:%M BRT")
        if not pd.isna(atualizado)
        else "data não disponível"
    )
    with st.container(key="hero"):
        st.markdown(
            '<div class="eyebrow">Projeto Integrador III / Ciência de Dados</div>', unsafe_allow_html=True
        )
        st.title("Ambev, em perspectiva.")
        st.markdown(
            f'<span class="snapshot-badge">DFP CONSOLIDADA · CVM · 2022–2025</span> <span class="snapshot-badge">Snapshot: {data_snapshot}</span>',
            unsafe_allow_html=True,
        )
        variacao = (
            f"variação de <strong>{formatar_percentual(delta_receita)}</strong> frente a {ultimo - 1}"
            if np.isfinite(delta_receita)
            else "sem comparação anual disponível"
        )
        st.markdown(
            f'<div class="hero-resumo">Em {ultimo}, a receita foi de <strong>{formatar_valor(atual.receita_liquida)}</strong>, com {variacao}. A margem líquida fechou em <strong>{formatar_percentual(atual.margem_liquida)}</strong>.</div>',
            unsafe_allow_html=True,
        )
    criar_kpis(df, ultimo)
    st.caption(
        f"Realizado · {ultimo} · Sparklines: histórico até {ultimo}. Deltas em % para moeda e em p.p. para percentuais. Sem atualização em tempo real."
    )
    abas = st.tabs(config.ABAS_DASHBOARD, key="aba", bind="query-params")
    with abas[0]:
        st.markdown('<div class="secao-numero">01 / A HISTÓRIA DOS RESULTADOS</div>', unsafe_allow_html=True)
        st.subheader("O que move os resultados")
        with st.container(border=True):
            explorar(df, filtrado, tema, unidade, mostrar_explicacoes)
        with st.expander("Receita e resultados · visão conjunta", expanded=False):
            explicar_grafico("geral", mostrar_explicacoes)
            if series:
                mostrar(
                    grafico_series(filtrado, tuple(series), "Resultados consolidados", tema, unidade=unidade),
                    "geral",
                )
            else:
                st.info("Selecione uma série da DRE na barra lateral.")
        st.subheader("Os números por trás da leitura")
        tabela_executiva(filtrado, unidade, tema)
    with abas[1], st.container(border=True):
        explicar_grafico("cascata", mostrar_explicacoes)
        mostrar(cascata_dre(filtrado.iloc[-1], tema, unidade), "cascata")
        st.caption(
            "Custos e despesas mantêm o sinal da DFP. Operacionais incluem equivalência patrimonial; subtotais não são somados duas vezes."
        )
        analise_vertical(filtrado, tema, mostrar_explicacoes)
    with abas[2], st.container(border=True):
        explicar_grafico("margens", mostrar_explicacoes)
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
        explicar_grafico("retornos", mostrar_explicacoes)
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
    with abas[3], st.container(border=True):
        explicar_grafico("liquidez", mostrar_explicacoes)
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
        explicar_grafico("endividamento", mostrar_explicacoes)
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
    with abas[4], st.container(border=True):
        explicar_grafico("balanco", mostrar_explicacoes)
        dados = dados_grafico(
            filtrado, ("passivo_circulante", "passivo_nao_circulante", "patrimonio_liquido")
        ).copy()
        dados["bilhoes"] = dados.valor / config.UNIDADES_VISUAIS[unidade][0]
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
        mostrar(
            estilizar(fig, "Como os ativos são financiados", config.UNIDADES_VISUAIS[unidade][1], tema),
            "balanco",
        )
        st.caption(
            "Passivo circulante + passivo não circulante + patrimônio líquido = ativo total. Identidade validada antes da geração do snapshot."
        )
        composicao_balanco(filtrado.iloc[-1], tema)
    with abas[5], st.container(border=True):
        st.subheader("Dois exercícios, uma comparação clara")
        explicar_grafico("comparacao", mostrar_explicacoes)
        comparar(df, filtrado, tema)
        st.subheader("Variações anuais no calendário completo")
        campo = st.selectbox(
            "Conta para análise horizontal anual",
            ["receita_liquida", "lucro_liquido", "lucro_bruto"],
            format_func=lambda c: config.NOMES[c],
            key="conta_horizontal",
            bind="query-params",
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
            mostrar(estilizar(fig, config.NOMES[campo] + " · variação anual", "%", tema), "horizontal")
            st.caption(
                "Base completa do calendário: ocultar um ano não altera a variação do seguinte. Base zero ou ausente gera n/d."
            )
    with abas[6], st.container(border=True):
        renderizar_projecoes(tema, unidade)
    with abas[7], st.container(border=True):
        sobre(metadados)
    st.markdown(
        f'<div class="rodape">{" · ".join(config.AUTORES)}<br>Projeto Integrador III · 2026 · Licença MIT · <a href="{config.REPOSITORIO}" target="_blank" rel="noopener noreferrer">Código, dados e metodologia ↗</a></div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
