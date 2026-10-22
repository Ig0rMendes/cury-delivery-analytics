"""Varredura de segmentos: onde estão os minutos perdidos e quanto vale resolvê-los."""
from __future__ import annotations

import pandas as pd

from src.config import MIN_GROUP_N
from src.metrics.summary import late_flag
from src.utils.labels import pt

# as dimensoes que a varredura olha. periodo do dia aparece na tabela mas nao vira alavanca (ver insights)
SEGMENT_DIMENSIONS = {
    "traffic": "Trânsito",
    "weather": "Clima",
    "area_type": "Tipo de área",
    "multiple_deliveries": "Entregas simultâneas",
    "vehicle_type": "Veículo",
    "daypart": "Período do dia",
    "festival": "Festival",
    "city": "Cidade",
}


# nome legivel do valor (ex 2 simultaneas)
def _value_label(col: str, v) -> str:
    if col == "multiple_deliveries":
        n = int(v)
        return "sem simultâneas" if n == 0 else f"{n} simultânea{'s' if n != 1 else ''}"
    return pt(col, v)


# a tabela 'onde estao os minutos perdidos': compara cada segmento com o RESTANTE da base
def segment_table(df: pd.DataFrame, dims: dict | None = None, sla: float = 30,
                  min_n: int = MIN_GROUP_N) -> pd.DataFrame:
    """Para cada valor de cada dimensão: compara o segmento com o RESTANTE da base.

    Colunas: dimension, segment, n, share, mean_delivery, rest_mean, diff, late_rate,
    rest_late_rate, late_share (parcela dos atrasos totais), extra_minutes (minutos totais a mais
    que o restante da base consumiria) e potential_gain (queda da média geral se o segmento
    operasse como o restante).
    """
    dims = dims or SEGMENT_DIMENSIONS
    total_n = len(df)
    if total_n == 0:
        return pd.DataFrame()
    # totais da base inteira, calculados uma vez so pra nao recalcular no loop
    late = late_flag(df, sla)
    total_late = late.sum()
    sum_t, sum_l = df["delivery_time_min"].sum(), late.sum()
    rows = []
    # passa por cada dimensao e cada valor dela
    for col, dim_label in dims.items():
        if col not in df.columns:
            continue
        for value, sub in df.groupby(col, observed=True):
            n = len(sub)
            rest_n = total_n - n
            if n < min_n or rest_n < min_n:
                continue
            mean_seg = sub["delivery_time_min"].mean()
            # media do resto sai por subtracao dos totais (mais rapido que filtrar de novo)
            rest_mean = (sum_t - sub["delivery_time_min"].sum()) / rest_n
            late_seg = late.loc[sub.index].sum()
            diff = mean_seg - rest_mean
            rows.append({
                "dimension": dim_label, "column": col, "value": value,
                "segment": f"{dim_label}: {_value_label(col, value)}",
                "n": n, "share": n / total_n,
                "mean_delivery": mean_seg, "rest_mean": rest_mean, "diff": diff,
                "late_rate": late_seg / n, "rest_late_rate": (sum_l - late_seg) / rest_n,
                "late_share": late_seg / total_late if total_late else float("nan"),
                "extra_minutes": diff * n,
                # ganho potencial = o quanto a media geral cairia se o segmento fosse igual ao resto (so conta se for pior)
                "potential_gain": max(diff, 0.0) * n / total_n,
            })
    return pd.DataFrame(rows)
