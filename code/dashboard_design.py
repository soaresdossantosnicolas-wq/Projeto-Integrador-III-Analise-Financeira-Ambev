"""Identidade visual compartilhada; transformações restritas à apresentação."""

from functools import lru_cache
from html import escape

import plotly.graph_objects as go
import streamlit as st

import config


@lru_cache(maxsize=1)
def ler_estilo() -> str:
    """Lê o CSS local uma vez por processo, sem rede obrigatória."""
    return (config.RAIZ_PROJETO / "assets" / "estilo.css").read_text(encoding="utf-8")


def aplicar_tema(tema: str, apresentacao: bool = False) -> None:
    """Único ponto de injeção do tema, com tokens vindos exclusivamente do config."""
    css = ler_estilo()
    for chave, valor in {**config.TEMAS_DASHBOARD[tema], **config.PALETA}.items():
        css = css.replace(f"__{chave}__", valor)
    if apresentacao:
        css += '[data-testid="stSidebar"]{display:none;} .block-container{max-width:1320px;}'
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def criar_template_plotly(tema: str) -> go.layout.Template:
    """Template próprio, com legenda superior, fundo transparente e grade discreta."""
    t = config.TEMAS_DASHBOARD[tema]
    return go.layout.Template(
        layout=go.Layout(
            colorway=config.CORES_CATEGORICAS,
            font=dict(family="Manrope, sans-serif", size=12, color=t["texto"]),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=15, r=15, t=85, b=25),
            height=390,
            title=dict(font=dict(size=17, family="Manrope, sans-serif"), x=0, xanchor="left"),
            separators=",.",
            hovermode="x unified",
            dragmode=False,
            legend=dict(orientation="h", y=1.12, x=0, yanchor="bottom", font=dict(size=11), title_text=""),
            hoverlabel=dict(
                bgcolor=t["superficie"], bordercolor=t["borda"], font=dict(color=t["texto"], size=12)
            ),
            xaxis=dict(showgrid=False, zeroline=False, linecolor=t["borda"], tickfont=dict(size=11)),
            yaxis=dict(gridcolor=t["grade"], zerolinecolor=t["borda"], tickfont=dict(size=11)),
            transition=dict(duration=180),
        )
    )


def estilizar_figura(fig: go.Figure, titulo: str, eixo: str, tema: str) -> go.Figure:
    """Aplica o mesmo vocabulário visual a figuras históricas e preditivas."""
    fig.update_layout(
        template=criar_template_plotly(tema),
        title=dict(text=titulo, y=0.98, yanchor="top", x=0, xanchor="left"),
        yaxis_title=eixo,
        legend_title_text="",
        legend=dict(orientation="h", y=1.10, x=0, yanchor="bottom"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(title=None, showgrid=False)
    fig.update_yaxes(rangemode="tozero", automargin=True)
    return fig


def insight(titulo: str, valor: str, texto: str) -> None:
    """Card acessível; dados interpolados são escapados antes de gerar HTML."""
    st.markdown(
        f'<div class="insight-card"><div class="eyebrow">{escape(titulo)}</div>'
        f'<div class="valor-foco">{escape(valor)}</div><p>{escape(texto)}</p></div>',
        unsafe_allow_html=True,
    )
