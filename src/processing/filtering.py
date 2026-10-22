"""Filtros puros (sem Streamlit): período, trânsito e clima."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


# os filtros da barra lateral, guardados num objeto imutavel (frozen) pra nao mudar sem querer
@dataclass(frozen=True)
class Filters:
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    traffic: tuple
    weather: tuple


# aplica periodo + transito + clima. a data final conta inclusive, por isso soma 1 dia
def filter_frame(df: pd.DataFrame, f: Filters) -> pd.DataFrame:
    """Aplica os três filtros. A data final é inclusiva."""
    end = pd.Timestamp(f.end_date) + pd.Timedelta(days=1)
    mask = (
        (df["order_date"] >= pd.Timestamp(f.start_date))
        & (df["order_date"] < end)
        & df["traffic"].isin(list(f.traffic))
        & df["weather"].isin(list(f.weather))
    )
    return df[mask]
