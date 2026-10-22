"""Componentes de interface reutilizáveis, tolerantes a versões diferentes do Streamlit."""
from __future__ import annotations

import inspect

import pandas as pd
import streamlit as st

from src.insights.base import Insight

# `use_container_width` foi descontinuado em versões novas (substituído por `width`).
try:
    _PLOTLY_HAS_WIDTH = "width" in inspect.signature(st.plotly_chart).parameters
except (TypeError, ValueError):  # pragma: no cover
    _PLOTLY_HAS_WIDTH = False


# mostra o grafico plotly. versoes novas do streamlit trocaram use_container_width por width, entao a gente testa qual existe
def plot(fig, key: str | None = None) -> None:
    kwargs = {} if _PLOTLY_HAS_WIDTH else {"use_container_width": True}
    if key:
        kwargs["key"] = key
    st.plotly_chart(fig, **kwargs)


# tabela padrao sem indice
def show_table(df: pd.DataFrame, column_config: dict | None = None, height: int | None = None) -> None:
    kwargs = {"hide_index": True}
    if column_config:
        kwargs["column_config"] = column_config
    if height:
        kwargs["height"] = height
    st.dataframe(df, **kwargs)


# caixinha com borda (versao antiga nao tem borda, ai vai sem)
def card():
    """Contêiner com borda (Streamlit >= 1.29); sem borda em versões antigas."""
    try:
        return st.container(border=True)
    except TypeError:
        return st.container()


# linha de numeros grandes (kpis) no topo da pagina
def kpi_row(items: list[dict]) -> None:
    """items: [{label, value, delta (opcional), inverse (bool), help}]"""
    cols = st.columns(len(items))
    for col, it in zip(cols, items):
        kwargs = {}
        if it.get("delta") is not None:
            kwargs["delta"] = it["delta"]
            kwargs["delta_color"] = "inverse" if it.get("inverse") else "normal"
        if it.get("help"):
            kwargs["help"] = it["help"]
        col.metric(it["label"], it["value"], **kwargs)


# aviso sobre limite dos dados, no estilo nota metodologica
def data_note(title: str, body: str) -> None:
    """Nota metodológica: aviso sobre limite da fonte de dados (não é erro do painel)."""
    st.info(f"**{title}**\n\n{body}")


# titulo de secao com legenda opcional
def section(title: str, caption: str | None = None) -> None:
    st.subheader(title)
    if caption:
        st.caption(caption)


# desenha os cartoes de insight (achado, oportunidade, risco...)
def render_insights(insights: list[Insight], title: str = "Insights desta página") -> None:
    """Cartões de insight: achado, oportunidade, risco ou ressalva, com a ação sugerida."""
    st.subheader(title)
    if not insights:
        st.info("Sem insights para os filtros atuais.")
        return
    for ins in insights:
        with card():
            st.markdown(ins.as_markdown())


# se der qualquer erro inesperado, a pagina nao cai: mostra um aviso no lugar do insight
def safe_insights(fn, *args, **kwargs) -> list[Insight]:
    """Executa um gerador de insights sem derrubar a página se algo inesperado ocorrer."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        return [Insight("info", "Não foi possível gerar os insights para este recorte", f"Detalhe técnico: {exc}")]
