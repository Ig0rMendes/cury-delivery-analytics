"""Acesso aos dados no app, com cache. A chave do cache inclui data e tamanho do arquivo,
então trocar o `train.csv` por outro invalida o cache automaticamente."""
from __future__ import annotations

import streamlit as st

from src.metrics.models import DeliveryModel, fit_delivery_model
from src.processing.loader import find_data_file
from src.processing.pipeline import load_analytical_data


# cache: a leitura so roda de novo se o arquivo mudar (a chave e caminho + data + tamanho)
@st.cache_data(show_spinner="Lendo e tratando a base…")
def _load(path: str, mtime: float, size: int):
    return load_analytical_data(path)


# modelo de efeitos isolados, ajustado na base completa (nao muda com filtro)
@st.cache_data(show_spinner="Ajustando o modelo de efeitos…")
def _fit(path: str, mtime: float, size: int) -> DeliveryModel | None:
    df, _ = _load(path, mtime, size)
    return fit_delivery_model(df)


# modelo estendido, usado so pra calcular o tempo esperado dos entregadores
@st.cache_data(show_spinner="Ajustando o modelo de tempo esperado…")
def _fit_expected(path: str, mtime: float, size: int) -> DeliveryModel | None:
    df, _ = _load(path, mtime, size)
    return fit_delivery_model(df, extended=True)


# identidade do arquivo: se trocar o train.csv, essa assinatura muda e o cache recalcula
def _signature():
    file = find_data_file()
    stat = file.stat()
    return str(file), stat.st_mtime, stat.st_size


# entrega a base limpa + o relatorio de limpeza
def get_data():
    """Devolve (base analítica, relatório de limpeza). Pode levantar DataNotFoundError/SchemaError."""
    return _load(*_signature())


def get_model() -> DeliveryModel | None:
    """Modelo de efeitos isolados (trânsito, clima, distância…), ajustado na base completa."""
    return _fit(*_signature())


def get_expected_model() -> DeliveryModel | None:
    """Modelo de tempo ESPERADO por pedido (trânsito × clima + período), base completa, p/ ranquear entregadores."""
    return _fit_expected(*_signature())
