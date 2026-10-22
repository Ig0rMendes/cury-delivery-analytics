"""KPIs executivos."""
from __future__ import annotations

import numpy as np
import pandas as pd


# numeros principais do topo das paginas. se o recorte estiver vazio devolve NaN em vez de dar erro
def compute_kpis(df: pd.DataFrame, sla: float) -> dict:
    """Indicadores-chave do recorte. Nunca levanta erro com recorte vazio."""
    n = len(df)
    if n == 0:
        keys = ["orders", "couriers", "restaurants", "days", "orders_per_day", "avg_delivery",
                "median_delivery", "p90_delivery", "avg_prep", "avg_total", "p90_total",
                "on_time_rate", "avg_rating", "avg_distance", "avg_speed", "prep_share"]
        return {k: float("nan") for k in keys} | {"orders": 0}
    # conta dias e monta o dicionario de kpis
    days = df["order_date"].nunique()
    avg_total = df["total_time_min"].mean()
    return {
        "orders": n,
        "couriers": int(df["courier_id"].nunique()),
        "restaurants": int(df["restaurant_id"].nunique()),
        "days": int(days),
        "orders_per_day": n / days if days else float("nan"),
        "avg_delivery": df["delivery_time_min"].mean(),
        "median_delivery": df["delivery_time_min"].median(),
        "p90_delivery": df["delivery_time_min"].quantile(0.9),
        "avg_prep": df["prep_time_min"].mean(),
        "avg_total": avg_total,
        "p90_total": df["total_time_min"].quantile(0.9),
        # % no prazo: entregas ate o SLA / total
        "on_time_rate": float((df["delivery_time_min"] <= sla).mean()),
        "avg_rating": df["rating"].mean(),
        "avg_distance": df["distance_km"].mean(),
        "avg_speed": df["speed_kmh"].mean(),
        # quanto do tempo total e cozinha (preparo / total)
        "prep_share": df["prep_time_min"].mean() / avg_total if avg_total else float("nan"),
    }


# variacao relativa pro st.metric. se nao der pra calcular devolve None
def delta(current: float, baseline: float) -> float | None:
    """Variação relativa para st.metric; None se não calculável."""
    if baseline is None or pd.isna(baseline) or baseline == 0 or pd.isna(current):
        return None
    return (current - baseline) / baseline
