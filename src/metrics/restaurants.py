"""Restaurantes (ID proxy = cidade + coordenada; só pedidos com localização válida)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import MIN_EFFECT_MIN, MIN_ORDERS_RESTAURANT, Z_FLAG
from src.metrics.summary import late_flag, summarize
from src.utils.labels import DAYPART_ORDER, sort_by_order


# so pedidos que tem id de restaurante (localizacao valida)
def with_restaurant(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["restaurant_id"].notna()]


# uma linha por restaurante com preparo, entrega, atraso e se o preparo e lento
def restaurant_table(df: pd.DataFrame, sla: float, min_orders: int = MIN_ORDERS_RESTAURANT) -> pd.DataFrame:
    d = with_restaurant(df)
    if d.empty:
        return pd.DataFrame()
    d = d.assign(_late=late_flag(d, sla))
    g = d.groupby("restaurant_id").agg(
        orders=("order_id", "size"),
        city=("city", "first"),
        mean_prep=("prep_time_min", "mean"),
        std_prep=("prep_time_min", "std"),
        mean_delivery=("delivery_time_min", "mean"),
        mean_total=("total_time_min", "mean"),
        late_rate=("_late", "mean"),
        rating=("rating", "mean"),
    )
    g = g[g["orders"] >= min_orders].copy()
    g["prep_se"] = g["std_prep"] / np.sqrt(g["orders"])
    overall = d["prep_time_min"].mean()
    g["prep_vs_avg"] = g["mean_prep"] - overall
    # preparo lento = acima da media da rede por mais de 3 erros padrao e 1 min (mesma logica dos entregadores)
    g["slow_prep"] = g["prep_vs_avg"] > np.maximum(Z_FLAG * g["prep_se"].fillna(0), MIN_EFFECT_MIN)
    return g.reset_index()


# curva de concentracao: quanto % dos pedidos vem de quanto % dos restaurantes
def pareto(df: pd.DataFrame) -> pd.DataFrame:
    """Curva de concentração: % acumulado de restaurantes x % acumulado de pedidos."""
    counts = with_restaurant(df)["restaurant_id"].value_counts().sort_values(ascending=False)
    if counts.empty:
        return pd.DataFrame(columns=["rank_pct", "cum_orders_pct"])
    cum = counts.cumsum() / counts.sum()
    return pd.DataFrame({"rank_pct": np.arange(1, len(counts) + 1) / len(counts), "cum_orders_pct": cum.to_numpy()})


# parcela dos pedidos que os 20% maiores restaurantes fazem
def top_share(df: pd.DataFrame, frac: float = 0.2) -> float:
    counts = with_restaurant(df)["restaurant_id"].value_counts()
    if counts.empty:
        return float("nan")
    k = max(1, int(np.ceil(len(counts) * frac)))
    return float(counts.head(k).sum() / counts.sum())


# preparo medio por grupo (tipo de pedido ou periodo)
def prep_by(df: pd.DataFrame, col: str, sla: float) -> pd.DataFrame:
    t = summarize(df, col, sla)
    if col == "daypart":
        return sort_by_order(t, "daypart", DAYPART_ORDER).reset_index(drop=True)
    return t.sort_values("mean_prep", ascending=False).reset_index(drop=True)


# detecta se o preparo tem pouquissimos valores diferentes (na base original so 5, 10 e 15)
# isso e limite da fonte, nao erro do painel, e a pagina mostra um aviso por causa disso
def prep_granularity(df: pd.DataFrame, max_distinct: int = 6) -> dict:
    """O tempo de preparo assume poucos valores distintos? (limite de precisão da fonte, não do painel)

    Retorna `coarse` (True se há no máximo `max_distinct` valores), `distinct` e `values`
    (lista de (minutos, parcela dos pedidos), do mais frequente ao menos).
    """
    s = df["prep_time_min"].dropna() if "prep_time_min" in df.columns else pd.Series(dtype=float)
    if s.empty:
        return {"coarse": False, "distinct": 0, "values": []}
    shares = s.round(0).value_counts(normalize=True)
    values = [(float(k), float(v)) for k, v in shares.sort_index().items()]
    return {"coarse": len(values) <= max_distinct, "distinct": len(values), "values": values}


# monta a frase tipo '5 min (34%), 10 min (33%) e 15 min (33%)'
def prep_granularity_text(g: dict) -> str:
    """Ex.: '5 min (33%), 10 min (34%) e 15 min (33%)'."""
    parts = [f"{int(m)} min ({round(sh * 100):d}%)" for m, sh in g["values"]]
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " e " + parts[-1]
