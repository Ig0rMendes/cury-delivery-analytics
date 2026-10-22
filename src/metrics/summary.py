"""Tabela-resumo genérica por grupo e utilitários de matriz (usadas por quase todas as páginas)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import Z_95


# 1 se a entrega passou do prazo. o preparo nao conta no SLA
def late_flag(df: pd.DataFrame, sla: float) -> pd.Series:
    """1.0 se a ENTREGA passou do prazo (o preparo não entra no SLA)."""
    return (df["delivery_time_min"] > sla).astype(float)


# tabelao padrao por grupo: volume, tempos, % de atraso, nota, distancia e IC. quase todas as paginas usam
def summarize(df: pd.DataFrame, by, sla: float, min_n: int = 1) -> pd.DataFrame:
    """Indicadores por grupo: volume, tempos, atraso, nota, distância e IC95% da média de entrega."""
    cols = ["n", "share", "mean_delivery", "median_delivery", "p90_delivery", "std_delivery",
            "mean_prep", "mean_total", "late_rate", "rating", "distance", "sem", "ci_low", "ci_high"]
    if df.empty:
        return pd.DataFrame(columns=([by] if isinstance(by, str) else list(by)) + cols)
    # marca atrasado (1/0) e agrupa. a media do 1/0 ja e a taxa de atraso
    d = df.assign(_late=late_flag(df, sla))
    g = d.groupby(by, observed=True).agg(
        n=("order_id", "size"),
        mean_delivery=("delivery_time_min", "mean"),
        median_delivery=("delivery_time_min", "median"),
        p90_delivery=("delivery_time_min", lambda s: s.quantile(0.9)),
        std_delivery=("delivery_time_min", "std"),
        mean_prep=("prep_time_min", "mean"),
        mean_total=("total_time_min", "mean"),
        late_rate=("_late", "mean"),
        rating=("rating", "mean"),
        distance=("distance_km", "mean"),
    )
    # participacao do grupo e intervalo de confianca da media de entrega
    g["share"] = g["n"] / len(df)
    g["sem"] = g["std_delivery"] / np.sqrt(g["n"])
    g["ci_low"] = g["mean_delivery"] - Z_95 * g["sem"]
    g["ci_high"] = g["mean_delivery"] + Z_95 * g["sem"]
    g = g[g["n"] >= min_n].reset_index()
    return g


# matriz de medias (ex clima x transito). celula com menos de 30 pedidos fica vazia pra nao enganar
def pivot_mean(df: pd.DataFrame, index: str, columns: str, value: str, min_n: int = 30):
    """Matriz de médias e de contagens; células com poucos pedidos viram NaN."""
    means = df.pivot_table(index=index, columns=columns, values=value, aggfunc="mean", observed=True)
    counts = df.pivot_table(index=index, columns=columns, values=value, aggfunc="size", observed=True)
    means = means.where(counts >= min_n)
    return means, counts.reindex_like(means)


# variacao em % entre dois numeros, sem quebrar se o de base for zero
def relative_change(current: float, baseline: float) -> float:
    """Variação relativa (fração). NaN se a base for zero/ausente."""
    if baseline is None or baseline == 0 or pd.isna(baseline) or pd.isna(current):
        return float("nan")
    return (current - baseline) / baseline
