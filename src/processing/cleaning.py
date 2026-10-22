"""Limpeza e padronização da base bruta, com funil de qualidade auditável.

Princípios:
  * nada some em silêncio: cada etapa registra quantas linhas removeu e por quê;
  * corrigir quando a correção é segura (espaços, prefixos, sinal de coordenada);
  * sinalizar quando não dá para corrigir (localização inválida) sem perder o pedido;
  * remover só quando o dado é impossível ou essencial e ausente.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from src.config import (
    AGE_RANGE, DELIVERY_TIME_RANGE, INDIA_LAT_RANGE, INDIA_LON_RANGE,
    MULTIPLE_DELIVERIES_RANGE, PREP_TIME_RANGE, RATING_RANGE,
    VALID_AREA, VALID_FESTIVAL, VALID_ORDER_TYPE, VALID_TRAFFIC,
    VALID_VEHICLE, VALID_WEATHER, VEHICLE_CONDITION_RANGE,
)

# Mapa do esquema bruto (inglês, inconsistente) -> esquema limpo (snake_case).
# de-para: nome da coluna original -> nome limpo (em ingles, padrao snake_case)
RAW_TO_CLEAN = {
    "ID": "order_id",
    "Delivery_person_ID": "courier_id",
    "Delivery_person_Age": "courier_age",
    "Delivery_person_Ratings": "rating",
    "Restaurant_latitude": "rest_lat",
    "Restaurant_longitude": "rest_lon",
    "Delivery_location_latitude": "dest_lat",
    "Delivery_location_longitude": "dest_lon",
    "Order_Date": "order_date",
    "Time_Orderd": "time_ordered",
    "Time_Order_picked": "time_picked",
    "Weatherconditions": "weather",
    "Road_traffic_density": "traffic",
    "Vehicle_condition": "vehicle_condition",
    "Type_of_order": "order_type",
    "Type_of_vehicle": "vehicle_type",
    "multiple_deliveries": "multiple_deliveries",
    "Festival": "festival",
    "City": "area_type",
    "Time_taken(min)": "delivery_time_min",
}

# textos que significam vazio na base (inclusive o famoso 'NaN ' com espaco)
NA_TOKENS = {"", "nan", "none", "null", "na", "n/a", "<na>", "nat"}

# Campos sem os quais o pedido não pode ser analisado de forma confiável.
# sem esses campos o pedido nao serve pra analise, porisso a linha sai (imputar distorceria os efeitos)
ESSENTIAL_FIELDS = [
    "courier_id", "courier_age", "rating", "order_date", "time_ordered", "time_picked",
    "weather", "traffic", "vehicle_condition", "order_type", "vehicle_type",
    "multiple_deliveries", "area_type", "delivery_time_min",
]


# o 'diario' da limpeza: guarda quantas linhas sairam em cada etapa
# e isso que vai virar o funil que aparece na Home
@dataclass
class CleaningReport:
    """Resumo auditável do tratamento. Alimenta a Home e o README."""

    source: str = ""
    raw_rows: int = 0
    final_rows: int = 0
    steps: list[dict] = field(default_factory=list)
    missing_by_field: dict = field(default_factory=dict)
    coords_sign_fixed: int = 0
    invalid_location_rows: int = 0
    festival_unknown: int = 0

    # registra uma etapa do funil
    def add_step(self, label: str, removed: int, remaining: int, detail: str = "") -> None:
        self.steps.append({"label": label, "removed": int(removed), "remaining": int(remaining), "detail": detail})

    # propriedades calculadas, pra nao ficar guardando numero repetido
    @property
    def removed_total(self) -> int:
        return self.raw_rows - self.final_rows

    @property
    def retention(self) -> float:
        return self.final_rows / self.raw_rows if self.raw_rows else float("nan")

    @property
    def invalid_location_share(self) -> float:
        return self.invalid_location_rows / self.final_rows if self.final_rows else float("nan")

    def to_dict(self) -> dict:
        return asdict(self)


# ------------------------------------------------------------------ utilitários
# tira espacos e transforma os 'vazios' em NaN de verdade
def _text(series: pd.Series) -> pd.Series:
    """Texto limpo: strip + tokens de ausência (inclui o 'NaN ' da base) viram NaN."""
    s = series.astype("string").str.strip()
    s = s.mask(s.str.lower().isin(NA_TOKENS))
    return s.astype(object).where(s.notna(), np.nan)


# arruma maiuscula/minuscula e joga fora o que nao esta na lista permitida
def _category(series: pd.Series, valid: tuple, case: str = "title") -> pd.Series:
    """Normaliza capitalização e invalida valores fora do conjunto permitido."""
    s = series
    if case == "title":
        s = s.str.title()
    elif case == "lower":
        s = s.str.lower()
    s = s.where(s.isin(valid), np.nan)
    return s


# datas no formato dia-mes-ano. se quase nada converter, tenta outro formato (excel)
def _parse_dates(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, format="%d-%m-%Y", errors="coerce")
    if parsed.isna().mean() > 0.5:  # Excel ou outro formato
        parsed = pd.to_datetime(series, errors="coerce", dayfirst=True, format="mixed")
    return parsed.dt.normalize()


# a coordenada ta dentro do retangulo da india? (zero ou fora disso e invalida)
def _in_india(lat: pd.Series, lon: pd.Series) -> pd.Series:
    return (
        lat.between(*INDIA_LAT_RANGE) & lon.between(*INDIA_LON_RANGE)
    )


# --------------------------------------------------------------------- principal
# funcao principal da limpeza. entra a base bruta, sai a base limpa + o relatorio
def clean_orders(raw: pd.DataFrame, source: str = "") -> tuple[pd.DataFrame, CleaningReport]:
    """Converte a base bruta no esquema limpo. Devolve (df, relatório)."""
    report = CleaningReport(source=str(source), raw_rows=len(raw))

    # passo 1: copia as colunas ja renomeadas e com texto limpo
    df = pd.DataFrame(index=raw.index)
    for raw_col, col in RAW_TO_CLEAN.items():
        df[col] = _text(raw[raw_col])

    # --- tipagem e padronização -------------------------------------------------
    # passo 2: converte tipos. o tempo vem como '(min) 24', entao pega so o numero
    df["delivery_time_min"] = pd.to_numeric(
        df["delivery_time_min"].str.extract(r"(\d+(?:\.\d+)?)")[0], errors="coerce"
    )
    for col in ("courier_age", "rating", "vehicle_condition", "multiple_deliveries",
                "rest_lat", "rest_lon", "dest_lat", "dest_lon"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # padroniza as categorias (tira o prefixo 'conditions' do clima e corrige Metropolitian)
    df["weather"] = _category(
        df["weather"].str.replace(r"^conditions\s+", "", regex=True, case=False), VALID_WEATHER
    )
    df["traffic"] = _category(df["traffic"], VALID_TRAFFIC)
    df["area_type"] = _category(
        df["area_type"].str.replace("Metropolitian", "Metropolitan", case=False, regex=False),
        VALID_AREA,
    )
    df["vehicle_type"] = _category(df["vehicle_type"], VALID_VEHICLE, case="lower")
    df["order_type"] = _category(df["order_type"], VALID_ORDER_TYPE)
    df["festival"] = _category(df["festival"], VALID_FESTIVAL)  # ausente permanece NaN

    # datas e horas. o preparo e retirada menos pedido, e o modulo de 24h resolve pedido perto da meia-noite
    df["order_date"] = _parse_dates(df["order_date"])
    t_order = pd.to_timedelta(df["time_ordered"], errors="coerce")
    t_pick = pd.to_timedelta(df["time_picked"], errors="coerce")
    # preparo = retirada - pedido; módulo 24h trata pedidos feitos perto da meia-noite
    df["prep_time_min"] = ((t_pick - t_order).dt.total_seconds() / 60.0) % 1440.0
    df["time_ordered"] = t_order
    df = df.drop(columns=["time_picked"])

    df["courier_id"] = df["courier_id"].str.upper()

    # --- ausências por campo (informativo, antes de qualquer remoção) ----------
    # foto de quantos vazios tinha ANTES de remover qualquer coisa (so informativo)
    report.missing_by_field = {
        c: int(df[c].isna().sum()) for c in ESSENTIAL_FIELDS + ["festival"]
        if c in df.columns and int(df[c].isna().sum()) > 0
    }
    report.festival_unknown = int(df["festival"].isna().sum())

    # --- funil de remoção ------------------------------------------------------
    # mini funcao do funil: filtra e anota quantas linhas sairam. toda remocao passa por aqui
    def keep(mask: pd.Series, label: str, detail: str = "") -> None:
        nonlocal df
        before = len(df)
        df = df[mask.fillna(False)]
        report.add_step(label, before - len(df), len(df), detail)

    # passo 3: o funil de remocao. cada keep() e uma regra de qualidade
    keep(df["order_id"].notna(), "ID do pedido ausente")
    before = len(df)
    df = df.drop_duplicates(subset="order_id", keep="first")
    report.add_step("Pedidos duplicados (mesmo ID)", before - len(df), len(df))

    # campos essenciais ausentes: remove a linha. festival fica de fora desse filtro de proposito
    essential = [c for c in ESSENTIAL_FIELDS if c != "time_picked"] + ["prep_time_min"]
    keep(df[essential].notna().all(axis=1), "Campos essenciais ausentes",
         "entrega, entregador, trânsito, clima, veículo, horários etc.")
    # valores impossiveis (idade, nota, tempos...) = erro de registro, sai
    keep(df["courier_age"].between(*AGE_RANGE), "Idade do entregador fora de 18–60 anos")
    keep(df["rating"].between(*RATING_RANGE), "Avaliação fora da escala 1–5")
    keep(df["delivery_time_min"].between(*DELIVERY_TIME_RANGE), "Tempo de entrega fora de 1–180 min")
    keep(df["prep_time_min"].between(*PREP_TIME_RANGE), "Tempo de preparo fora de 0–90 min")
    keep(df["multiple_deliveries"].between(*MULTIPLE_DELIVERIES_RANGE),
         "Entregas simultâneas fora de 0–3")
    keep(df["vehicle_condition"].between(*VEHICLE_CONDITION_RANGE), "Condição do veículo fora de 0–3")

    # agora que nao tem mais vazio nessas colunas da pra voltar pra inteiro
    df = df.copy()
    for col in ("courier_age", "multiple_deliveries", "vehicle_condition"):
        df[col] = df[col].astype(int)

    # --- geografia: corrigir sinais, sinalizar o que não tem conserto ----------
    # passo 4: geografia. primeiro conserta sinal, depois marca o que nao tem conserto
    coords = ["rest_lat", "rest_lon", "dest_lat", "dest_lon"]
    negative = (df[coords] < 0).any(axis=1)
    report.coords_sign_fixed = int(negative.sum())
    # india fica no hemisferio norte/leste, entao sinal negativo e erro e a gente usa abs()
    for c in coords:  # a Índia está no hemisfério Norte/Leste: sinal negativo é erro de registro
        df[c] = df[c].abs()

    # coordenada zerada ou fora da india: mantem o pedido mas marca invalido (a distancia fica vazia depois)
    nonzero = (df[coords] != 0).all(axis=1)
    df["has_valid_location"] = (
        nonzero & _in_india(df["rest_lat"], df["rest_lon"]) & _in_india(df["dest_lat"], df["dest_lon"])
    )
    report.invalid_location_rows = int((~df["has_valid_location"]).sum())
    df["coords_fixed"] = negative

    # fecha o relatorio e devolve com o indice zerado
    report.final_rows = len(df)
    return df.reset_index(drop=True), report
