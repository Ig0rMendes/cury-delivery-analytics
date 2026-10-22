"""Entregadores: desempenho ajustado ao contexto (esperado vs. realizado)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import MIN_EFFECT_MIN, MIN_ORDERS_COURIER, Z_FLAG
from src.metrics.models import DeliveryModel
from src.metrics.summary import late_flag, summarize
from src.utils.labels import AGE_BAND_ORDER, sort_by_order


# pra cada pedido calcula o tempo que o modelo esperava e o excesso (real - esperado)
# excesso positivo = demorou mais do que o contexto explica
def with_expected(df: pd.DataFrame, model: DeliveryModel | None) -> pd.DataFrame:
    """Acrescenta `expected_time_min` e `excess_min` (realizado - esperado para o contexto)."""
    out = df.copy()
    if model is None:
        out["expected_time_min"] = np.nan
    else:
        out["expected_time_min"] = model.predict(out)
    out["excess_min"] = out["delivery_time_min"] - out["expected_time_min"]
    return out


# so marca entregador como lento/rapido se passar de 3 erros padrao E de 1 minuto
# o 3 e por causa das comparacoes multiplas (muita gente comparada = muitos falso positivo)
def classify(excess: float, se: float) -> str:
    """Classe só quando a diferença é clara (> 3 erros-padrão) E relevante (>= 1 min).

    Com centenas de entregadores, o limiar clássico de 1,96 apontaria ~2,5% por puro acaso em
    cada ponta; 3 erros-padrão reduz isso para ~0,1%.
    """
    if pd.isna(excess) or pd.isna(se):
        return "Indefinido"
    # o limite e o maior entre 3 erros padrao e 1 min: precisa ser claro e tambem importar na pratica
    limit = max(Z_FLAG * se, MIN_EFFECT_MIN)
    if excess > limit:
        return "Mais lento que o esperado"
    if excess < -limit:
        return "Mais rápido que o esperado"
    return "Dentro do esperado"


# uma linha por entregador, ja com o excesso medio e a classificacao
def courier_table(df: pd.DataFrame, sla: float, min_orders: int = MIN_ORDERS_COURIER) -> pd.DataFrame:
    """Uma linha por entregador. Requer `excess_min` (use with_expected antes)."""
    if df.empty:
        return pd.DataFrame()
    d = df.assign(_late=late_flag(df, sla))
    g = d.groupby("courier_id").agg(
        orders=("order_id", "size"),
        city=("city", "first"),
        vehicle=("vehicle_type", lambda s: s.mode().iat[0]),
        age=("courier_age", "median"),
        rating=("rating", "mean"),
        mean_delivery=("delivery_time_min", "mean"),
        late_rate=("_late", "mean"),
        excess=("excess_min", "mean"),
        excess_std=("excess_min", "std"),
        n_expected=("excess_min", "count"),
    )
    # erro padrao do excesso medio, e so depois corta quem tem poucos pedidos
    g["excess_se"] = g["excess_std"] / np.sqrt(g["n_expected"].clip(lower=1))
    g = g[g["orders"] >= min_orders].copy()
    g["status"] = [classify(e, s) for e, s in zip(g["excess"], g["excess_se"])]
    return g.reset_index()


# que parte dos pedidos os 10% entregadores mais ocupados fazem
def load_concentration(df: pd.DataFrame, top_frac: float = 0.10) -> float:
    """Parcela dos pedidos feita pelos `top_frac` entregadores mais ocupados."""
    counts = df["courier_id"].value_counts()
    if counts.empty:
        return float("nan")
    k = max(1, int(np.ceil(len(counts) * top_frac)))
    return float(counts.head(k).sum() / counts.sum())


# tabelas simples de perfil (veiculo, idade, condicao do veiculo)
def vehicle_table(df: pd.DataFrame, sla: float) -> pd.DataFrame:
    return summarize(df, "vehicle_type", sla).sort_values("mean_delivery").reset_index(drop=True)


def age_table(df: pd.DataFrame, sla: float) -> pd.DataFrame:
    return sort_by_order(summarize(df, "age_band", sla), "age_band", AGE_BAND_ORDER).reset_index(drop=True)


def condition_table(df: pd.DataFrame, sla: float) -> pd.DataFrame:
    return summarize(df, "vehicle_condition", sla).sort_values("vehicle_condition").reset_index(drop=True)


# ganho se os 'mais lentos que o esperado' voltassem ao esperado (soma dos excessos / total de pedidos)
def opportunity(table: pd.DataFrame, total_orders: int, overall_mean: float) -> dict:
    """Ganho se os entregadores 'mais lentos que o esperado' operassem no esperado."""
    slow = table[table["status"] == "Mais lento que o esperado"]
    if slow.empty or total_orders == 0:
        return {"couriers": 0, "orders": 0, "minutes": 0.0, "mean_gain": 0.0, "pct": 0.0}
    minutes = float((slow["excess"] * slow["n_expected"]).sum())
    gain = minutes / total_orders
    return {"couriers": int(len(slow)), "orders": int(slow["orders"].sum()), "minutes": minutes,
            "mean_gain": gain, "pct": gain / overall_mean if overall_mean else float("nan")}
