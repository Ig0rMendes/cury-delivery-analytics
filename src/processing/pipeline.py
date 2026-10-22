"""Pipeline completo e independente de Streamlit: arquivo bruto -> base analítica."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from src.processing.cleaning import CleaningReport, clean_orders
from src.processing.features import add_features
from src.processing.loader import read_raw


# limpa e cria as features em sequencia (sem depender de streamlit)
def process(raw: pd.DataFrame, source: str = "") -> tuple[pd.DataFrame, CleaningReport]:
    """Limpa e enriquece uma base bruta já carregada em memória."""
    clean, report = clean_orders(raw, source=source)
    return add_features(clean), report


# atalho completo: le o arquivo, limpa e enriquece. devolve a base pronta + relatorio
def load_analytical_data(path: str | os.PathLike | None = None) -> tuple[pd.DataFrame, CleaningReport]:
    """Lê `train` (data/train.csv por padrão) e devolve (base analítica, relatório)."""
    raw, file = read_raw(path)
    return process(raw, source=Path(file).name)
