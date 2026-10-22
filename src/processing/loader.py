"""Localização e leitura da base bruta (`train`).

A leitura é feita SEMPRE como texto: a base original traz espaços sobrando,
textos 'NaN ' e valores como '(min) 24'. Converter tipos é papel da limpeza,
onde cada decisão fica registrada.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from src.config import DATA_DIR, DATA_ENV_VAR, DATA_EXTENSIONS, DATA_NAME

# Colunas da base original (train.csv) necessárias para o projeto.
# colunas que precisam existir no csv, se faltar alguma o painel avisa em vez de quebrar
REQUIRED_RAW_COLUMNS = [
    "ID", "Delivery_person_ID", "Delivery_person_Age", "Delivery_person_Ratings",
    "Restaurant_latitude", "Restaurant_longitude",
    "Delivery_location_latitude", "Delivery_location_longitude",
    "Order_Date", "Time_Orderd", "Time_Order_picked",
    "Weatherconditions", "Road_traffic_density", "Vehicle_condition",
    "Type_of_order", "Type_of_vehicle", "multiple_deliveries", "Festival",
    "City", "Time_taken(min)",
]

# Variações de grafia conhecidas em cópias da base.
# algumas copias da base vem com o nome da coluna escrito diferente, aqui a gente acerta
COLUMN_ALIASES = {"Time_Ordered": "Time_Orderd", "Time_taken (min)": "Time_taken(min)"}


# erros proprios pra mostrar mensagem clara na tela (e nao um traceback gigante)
class DataNotFoundError(FileNotFoundError):
    """A base `train` não foi encontrada em data/."""


class SchemaError(ValueError):
    """A base não tem as colunas esperadas."""


def expected_location() -> Path:
    return DATA_DIR / f"{DATA_NAME}.csv"


# procura o arquivo da base. ordem: caminho passado > variavel de ambiente > pasta data
def find_data_file(path: str | os.PathLike | None = None) -> Path:
    """Descobre o arquivo da base.

    Ordem de busca: argumento `path` -> variável de ambiente DELIVERY_DATA_PATH ->
    data/train.csv|.xlsx|.xls (sem diferenciar maiúsculas/minúsculas).
    """
    # se a pessoa deu um caminho, usa ele e pronto (e reclama se nao existir)
    explicit = path or os.environ.get(DATA_ENV_VAR)
    if explicit:
        p = Path(explicit).expanduser()
        if p.is_file():
            return p
        raise DataNotFoundError(f"Arquivo informado não existe: {p}")

    # senao, tenta data/train.csv, .xlsx e .xls
    for ext in DATA_EXTENSIONS:
        candidate = DATA_DIR / f"{DATA_NAME}{ext}"
        if candidate.is_file():
            return candidate

    # ultima tentativa: ignora maiuscula e minuscula no nome (Train.CSV, por exemplo)
    if DATA_DIR.is_dir():
        for f in sorted(DATA_DIR.iterdir()):
            if f.is_file() and f.stem.lower() == DATA_NAME and f.suffix.lower() in DATA_EXTENSIONS:
                return f

    raise DataNotFoundError(
        f"Base '{DATA_NAME}' não encontrada. Coloque o arquivo '{DATA_NAME}.csv' em: {DATA_DIR}"
    )


# tira espaco do nome das colunas e aplica os apelidos
def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=lambda c: str(c).strip())
    return df.rename(columns={k: v for k, v in COLUMN_ALIASES.items() if k in df.columns})


# confere se todas as colunas obrigatorias estao la
def validate_schema(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_RAW_COLUMNS if c not in df.columns]
    if missing:
        raise SchemaError(
            "A base não tem as colunas esperadas do 'train': " + ", ".join(missing)
        )


# le tudo como texto de proposito: a limpeza que converte, assim cada decisao fica registrada
def read_raw(path: str | os.PathLike | None = None) -> tuple[pd.DataFrame, Path]:
    """Lê a base bruta como texto. Devolve (DataFrame, caminho_usado)."""
    file = find_data_file(path)
    suffix = file.suffix.lower()

    if suffix == ".csv":
        df = None
        # tenta utf-8 primeiro, se der erro de acento cai pro latin-1 (que le qualquer byte)
        for enc in ("utf-8-sig", "latin-1"):
            try:
                df = pd.read_csv(file, dtype=str, keep_default_na=False, encoding=enc)
                break
            except UnicodeDecodeError:
                continue
        if df is None:  # pragma: no cover - latin-1 decodifica qualquer byte
            raise RuntimeError(f"Não foi possível decodificar {file}")
    else:
        try:
            df = pd.read_excel(file, dtype=str)
        except ImportError as exc:  # pragma: no cover
            raise ImportError("Para ler Excel instale o openpyxl: pip install openpyxl") from exc

    # arruma os nomes e valida antes de devolver
    df = _normalize_columns(df)
    validate_schema(df)
    return df, file
