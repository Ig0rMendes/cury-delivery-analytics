"""Experiência do cliente (nota de avaliação)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import MIN_GROUP_N
from src.metrics.stats import group_stats, welch_test

# faixas da nota na ordem certa de exibicao
RATING_BAND_ORDER = ["Abaixo de 4,0", "4,0 a 4,4", "4,5 a 4,9", "5,0"]

# Dimensões comparáveis: rótulo -> coluna
# dimensoes que da pra comparar com a nota (rotulo na tela -> coluna)
DIMENSIONS = {
    "Trânsito": "traffic",
    "Clima": "weather",
    "Tipo de área": "area_type",
    "Veículo": "vehicle_type",
    "Período do dia": "daypart",
    "Faixa de tempo de entrega": "time_band",
    "Faixa etária do entregador": "age_band",
    "Entregas simultâneas": "multiple_deliveries",
    "Tipo de pedido": "order_type",
    "Condição do veículo": "vehicle_condition",
    "Cidade": "city",
}


# joga cada nota numa faixa
def rating_band(rating: pd.Series) -> pd.Series:
    r = rating.to_numpy()
    out = np.select([r < 4.0, r < 4.5, r < 5.0], RATING_BAND_ORDER[:3], default="5,0")
    return pd.Series(out, index=rating.index, dtype=object)


# quantos pedidos e que % tem em cada faixa de nota
def rating_distribution(df: pd.DataFrame) -> pd.DataFrame:
    counts = rating_band(df["rating"]).value_counts().reindex(RATING_BAND_ORDER).fillna(0).astype(int)
    out = counts.rename_axis("band").reset_index(name="n")
    out["share"] = out["n"] / out["n"].sum() if out["n"].sum() else 0.0
    return out


# teste importante: a nota varia dentro do mesmo entregador?
# se nao varia, a nota seria do entregador e nao de cada entrega (nos seus dados varia, entao e por entrega)
def rating_granularity(df: pd.DataFrame) -> dict:
    """A nota varia entre pedidos do MESMO entregador?

    Se quase todo entregador tem nota única, a nota é um atributo do entregador (média
    histórica) e NÃO a avaliação de cada entrega: comparações por pedido refletem o perfil
    dos entregadores, não a reação do cliente a cada entrega.
    """
    g = df.groupby("courier_id")["rating"].agg(["nunique", "size"])
    g = g[g["size"] >= 2]
    if g.empty:
        return {"couriers": 0, "constant_share": float("nan"), "is_courier_attribute": False}
    share = float((g["nunique"] == 1).mean())
    return {"couriers": int(len(g)), "constant_share": share, "is_courier_attribute": share >= 0.9}


# nota media com IC por grupo
def rating_by(df: pd.DataFrame, col: str, min_n: int = MIN_GROUP_N) -> pd.DataFrame:
    return group_stats(df, col, "rating", min_n=min_n)


# qual dimensao separa mais a nota: diferenca entre o melhor e o pior grupo + teste se e clara
# a faixa de tempo fica de fora porque ela e o proprio atraso, nao uma causa
def dimension_spread(df: pd.DataFrame, min_n: int = MIN_GROUP_N, exclude: tuple = ("time_band",)) -> pd.DataFrame:
    """Para cada dimensão: amplitude da nota média entre seus grupos (e se é estatisticamente clara)."""
    rows = []
    for label, col in DIMENSIONS.items():
        if col not in df.columns or col in exclude:  # faixa de tempo é o próprio resultado do atraso, não uma causa
            continue
        t = group_stats(df, col, "rating", min_n=min_n)
        if len(t) < 2:
            continue
        hi, lo = t.loc[t["mean"].idxmax()], t.loc[t["mean"].idxmin()]
        test = welch_test(df.loc[df[col] == hi[col], "rating"], df.loc[df[col] == lo[col], "rating"])
        rows.append({
            "dimension": label, "column": col, "spread": hi["mean"] - lo["mean"],
            "best": hi[col], "best_mean": hi["mean"], "worst": lo[col], "worst_mean": lo["mean"],
            "significant": bool(test and test["significant"]), "groups": len(t),
        })
    return pd.DataFrame(rows).sort_values("spread", ascending=False).reset_index(drop=True) if rows else pd.DataFrame()
