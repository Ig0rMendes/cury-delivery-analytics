"""Fatores externos: trânsito, clima e festival."""
from __future__ import annotations

import pandas as pd

from src.config import MIN_GROUP_N
from src.metrics.stats import welch_test
from src.metrics.summary import pivot_mean, summarize
from src.utils.labels import TRAFFIC_ORDER, sort_by_order


# quanto cada nivel de transito custa em minutos e em % contra o transito mais leve
def traffic_table(df: pd.DataFrame, sla: float) -> pd.DataFrame:
    """Resumo por trânsito com custo em minutos vs. trânsito baixo (ou o mais leve disponível)."""
    t = sort_by_order(summarize(df, "traffic", sla), "traffic", TRAFFIC_ORDER).reset_index(drop=True)
    if t.empty:
        return t
    base = t.iloc[0]["mean_delivery"]
    t["extra_vs_base"] = t["mean_delivery"] - base
    t["extra_pct"] = t["mean_delivery"] / base - 1
    return t


# resumo por clima, do mais lento pro mais rapido
def weather_table(df: pd.DataFrame, sla: float) -> pd.DataFrame:
    return summarize(df, "weather", sla).sort_values("mean_delivery", ascending=False).reset_index(drop=True)


# matriz clima x transito (tempo medio). celula pequena fica vazia
def weather_traffic_matrix(df: pd.DataFrame, min_n: int = MIN_GROUP_N):
    means, counts = pivot_mean(df, "weather", "traffic", "delivery_time_min", min_n=min_n)
    cols = [c for c in TRAFFIC_ORDER if c in means.columns]
    means, counts = means[cols], counts[cols]
    means = means.loc[means.mean(axis=1).sort_values().index]
    return means, counts.loc[means.index]


# festival x dia normal com o teste de welch. quem nao tem info de festival fica de fora
def festival_effect(df: pd.DataFrame) -> dict | None:
    """Festival (Sim) vs. dia normal (Não); pedidos sem informação ficam de fora."""
    yes = df.loc[df["festival"] == "Yes", "delivery_time_min"]
    no = df.loc[df["festival"] == "No", "delivery_time_min"]
    if len(yes) < MIN_GROUP_N or len(no) < MIN_GROUP_N:
        return None
    res = welch_test(yes, no)
    if res is not None:
        res["mean_yes"], res["mean_no"] = yes.mean(), no.mean()
    return res
