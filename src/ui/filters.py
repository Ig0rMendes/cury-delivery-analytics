"""Barra lateral compartilhada por todas as páginas (período, trânsito, clima e SLA).

Como os filtros sobrevivem à troca de página
--------------------------------------------
O Streamlit apaga o estado de qualquer widget que não foi desenhado na execução anterior.
Por isso a escolha do usuário fica em chaves "salvas" (`saved_*`), que não são widgets e
persistem entre páginas. Cada widget lê seu valor inicial dessas chaves e, ao mudar, grava
de volta (`on_change`). Assim não há conflito entre `value=` e `st.session_state`.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import DEFAULT_SLA_MIN, SLA_RANGE
from src.processing.filtering import Filters, filter_frame
from src.utils.formatting import fmt_int
from src.utils.labels import TRAFFIC_ORDER, pt

# nomes das chaves: saved_* guarda a escolha (nao e widget), w_* e o widget em si
SAVED_PERIOD, SAVED_TRAFFIC, SAVED_WEATHER, SAVED_SLA = "saved_period", "saved_traffic", "saved_weather", "saved_sla"
W_PERIOD, W_TRAFFIC, W_WEATHER, W_SLA = "w_period", "w_traffic", "w_weather", "w_sla"


# quando o widget muda, copia o valor pra chave salva
def _sync(saved_key: str, widget_key: str) -> None:
    st.session_state[saved_key] = st.session_state[widget_key]


# opcoes de transito na ordem certa (baixo -> congestionado)
def _traffic_options(values) -> list:
    values = list(pd.unique(values))
    return [t for t in TRAFFIC_ORDER if t in values] + sorted(v for v in values if v not in TRAFFIC_ORDER)


# desenha a barra lateral. o estado fica em saved_* porque o streamlit apaga o estado dos widgets quando troca de pagina
def sidebar_filters(df: pd.DataFrame) -> tuple[Filters, int]:
    """Desenha os filtros e devolve (Filters, SLA em minutos)."""
    min_date = df["order_date"].min().date()
    max_date = df["order_date"].max().date()
    traffic_opts = _traffic_options(df["traffic"].dropna().unique())
    weather_opts = sorted(df["weather"].dropna().unique())

    # estado salvo: cria se não existir e saneia se a base mudou
    # cria o estado salvo se nao existir (ou arruma se a base mudou)
    saved = st.session_state.get(SAVED_PERIOD)
    valid = (isinstance(saved, (tuple, list)) and 1 <= len(saved) <= 2
             and all(min_date <= d <= max_date for d in saved))
    if not valid:
        st.session_state[SAVED_PERIOD] = (min_date, max_date)
    for key, opts in ((SAVED_TRAFFIC, traffic_opts), (SAVED_WEATHER, weather_opts)):
        current = st.session_state.get(key)
        st.session_state[key] = list(opts) if current is None else [v for v in current if v in opts]
    sla_saved = st.session_state.get(SAVED_SLA)
    if not isinstance(sla_saved, int) or not SLA_RANGE[0] <= sla_saved <= SLA_RANGE[1]:
        st.session_state[SAVED_SLA] = DEFAULT_SLA_MIN

    # botao limpar filtros: volta o salvo pro padrao e apaga os widgets pra eles recomecarem
    def _reset():
        st.session_state[SAVED_PERIOD] = (min_date, max_date)
        st.session_state[SAVED_TRAFFIC] = list(traffic_opts)
        st.session_state[SAVED_WEATHER] = list(weather_opts)
        st.session_state[SAVED_SLA] = DEFAULT_SLA_MIN
        for w in (W_PERIOD, W_TRAFFIC, W_WEATHER, W_SLA):  # força os widgets a recomeçar do valor salvo
            st.session_state.pop(w, None)

    # aqui desenha os 4 filtros: periodo, transito, clima e SLA
    st.sidebar.header("Filtros")
    st.sidebar.date_input(
        "Período", value=tuple(st.session_state[SAVED_PERIOD]), min_value=min_date, max_value=max_date,
        key=W_PERIOD, format="DD/MM/YYYY", on_change=_sync, args=(SAVED_PERIOD, W_PERIOD),
    )
    st.sidebar.multiselect(
        "Trânsito", traffic_opts, default=st.session_state[SAVED_TRAFFIC], key=W_TRAFFIC,
        format_func=lambda v: pt("traffic", v), on_change=_sync, args=(SAVED_TRAFFIC, W_TRAFFIC),
    )
    st.sidebar.multiselect(
        "Clima", weather_opts, default=st.session_state[SAVED_WEATHER], key=W_WEATHER,
        format_func=lambda v: pt("weather", v), on_change=_sync, args=(SAVED_WEATHER, W_WEATHER),
    )
    st.sidebar.slider(
        "Prazo (SLA) da entrega, em min", SLA_RANGE[0], SLA_RANGE[1], value=int(st.session_state[SAVED_SLA]), step=1,
        key=W_SLA, on_change=_sync, args=(SAVED_SLA, W_SLA),
        help="Define o que conta como entrega no prazo. Vale só para a etapa de entrega (o preparo não entra).",
    )
    st.sidebar.button("↺ Limpar filtros", on_click=_reset)

    # se o usuario escolheu so a data inicial, espera ele escolher a final
    period = st.session_state[SAVED_PERIOD]
    if not isinstance(period, (tuple, list)) or len(period) < 2:
        st.sidebar.info("Selecione também a data final do período.")
        st.stop()

    flt = Filters(
        start_date=pd.Timestamp(period[0]), end_date=pd.Timestamp(period[1]),
        traffic=tuple(st.session_state[SAVED_TRAFFIC]), weather=tuple(st.session_state[SAVED_WEATHER]),
    )
    return flt, int(st.session_state[SAVED_SLA])


# desenha filtros, filtra a base e para a pagina se nao sobrar nenhum pedido
def apply_sidebar(df: pd.DataFrame):
    """Desenha os filtros, filtra e interrompe a página se o recorte ficar vazio."""
    flt, sla = sidebar_filters(df)
    df_f = filter_frame(df, flt)
    st.sidebar.caption(f"{fmt_int(len(df_f))} de {fmt_int(len(df))} pedidos selecionados")
    if df_f.empty:
        st.warning("Nenhum pedido nos filtros selecionados. Amplie o período ou marque mais condições de trânsito/clima.")
        st.stop()
    return df_f, flt, sla
