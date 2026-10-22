"""Séries e tabelas da visão operacional."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.metrics.summary import summarize
from src.utils.labels import DAYPART_ORDER, WEEKDAYS_PT, sort_by_order


# serie por dia
def daily_series(df: pd.DataFrame, sla: float) -> pd.DataFrame:
    t = summarize(df, "order_date", sla)
    return t.sort_values("order_date")[["order_date", "n", "mean_delivery", "mean_prep", "late_rate", "rating"]]


# perfil por hora do dia
def hourly_profile(df: pd.DataFrame, sla: float, min_n: int = 1) -> pd.DataFrame:
    t = summarize(df, "order_hour", sla, min_n=min_n)
    return t.sort_values("order_hour")


# matriz dia da semana x hora com o numero de pedidos (alimenta o mapa de calor)
def weekday_hour_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Pedidos por dia da semana (linhas) x hora (colunas)."""
    m = df.pivot_table(index="weekday", columns="order_hour", values="order_id", aggfunc="size", observed=True)
    m = m.reindex([d for d in WEEKDAYS_PT if d in m.index])
    return m.fillna(0).astype(int)


# resumo por periodo do dia, na ordem manha -> noite
def daypart_table(df: pd.DataFrame, sla: float) -> pd.DataFrame:
    return sort_by_order(summarize(df, "daypart", sla), "daypart", DAYPART_ORDER)


# resumo por cidade + centro dos restaurantes (so locais validos) pra desenhar no mapa
def city_table(df: pd.DataFrame, sla: float, min_n: int = 1) -> pd.DataFrame:
    """Resumo por cidade + centróide dos restaurantes (apenas localizações válidas)."""
    t = summarize(df, "city", sla, min_n=min_n)
    valid = df[df["has_valid_location"]]
    if not valid.empty:
        cent = valid.groupby("city").agg(lat=("rest_lat", "mean"), lon=("rest_lon", "mean"))
        t = t.merge(cent, left_on="city", right_index=True, how="left")
    else:
        t["lat"], t["lon"] = np.nan, np.nan
    return t.sort_values("n", ascending=False).reset_index(drop=True)


# parcela do total que as maiores categorias concentram
def concentration(counts: pd.Series, top: int) -> float:
    """Parcela do total que as `top` maiores categorias concentram."""
    counts = counts.sort_values(ascending=False)
    total = counts.sum()
    return float(counts.head(top).sum() / total) if total else float("nan")
