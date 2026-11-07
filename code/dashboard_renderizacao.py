"""Renderização responsiva independente do módulo de tema já carregado."""

import plotly.graph_objects as go
import streamlit as st


def mostrar_figura(fig: go.Figure, **opcoes):
    """Título responsivo fora do canvas; preserva a figura original para exportação."""
    if fig.layout.title.text:
        st.subheader(fig.layout.title.text)
    exibicao = go.Figure(fig)
    exibicao.update_layout(
        title=dict(text=""),
        margin=dict(t=28, b=55, autoexpand=True),
        legend=dict(orientation="h", y=-0.20, x=0, yanchor="top", xanchor="left"),
    )
    return st.plotly_chart(exibicao, **opcoes)
