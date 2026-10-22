"""Engenharia de variáveis: tempo total, distância, velocidade, faixas e cidade real."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import CITY_CODES, MAX_DISTANCE_KM, MAX_SPEED_KMH, UNKNOWN_CITY
from src.utils.labels import WEEKDAYS_PT

# raio medio da terra em km, usado na formula de haversine
EARTH_RADIUS_KM = 6371.0088


# distancia em linha reta entre dois pontos (nao e a rota de verdade, ta?)
def haversine_km(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Distância em linha reta (km) entre pares de coordenadas em graus."""
    lat1, lon1, lat2, lon2 = (np.radians(np.asarray(x, dtype=float)) for x in (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


# agrupa a hora do pedido em periodo do dia (manha, almoco, tarde, jantar, noite)
def daypart_from_hour(hour: pd.Series) -> pd.Series:
    h = hour.to_numpy()
    out = np.select(
        [(h >= 6) & (h <= 10), (h >= 11) & (h <= 14), (h >= 15) & (h <= 17), (h >= 18) & (h <= 21)],
        ["Manhã", "Almoço", "Tarde", "Jantar"],
        default="Noite",
    )
    return pd.Series(out, index=hour.index, dtype=object)


# faixas de idade do entregador, pra comparar grupos
def age_band(age: pd.Series) -> pd.Series:
    a = age.to_numpy()
    out = np.select(
        [a <= 24, a <= 29, a <= 34, a <= 39], ["18–24", "25–29", "30–34", "35–39"], default="40+"
    )
    return pd.Series(out, index=age.index, dtype=object)


# faixas do tempo de entrega, usada na pagina de experiencia
def time_band(minutes: pd.Series) -> pd.Series:
    m = minutes.to_numpy()
    out = np.select(
        [m <= 20, m <= 30, m <= 40], ["Até 20 min", "21–30 min", "31–40 min"], default="Mais de 40 min"
    )
    return pd.Series(out, index=minutes.index, dtype=object)


# pega a cidade no id do entregador. se o codigo nao ta no mapa, usa o proprio codigo
def extract_city(courier_id: pd.Series) -> pd.DataFrame:
    """Código e nome da cidade a partir do ID do entregador (padrão CIDADE+RES+nn+DEL+nn)."""
    code = courier_id.str.extract(r"^([A-Z]+?)RES\d+DEL\d+$")[0]
    city = code.map(CITY_CODES)
    city = city.where(city.notna(), np.where(code.notna(), code, UNKNOWN_CITY))
    return pd.DataFrame({"city_code": code.fillna("NA"), "city": city})


# nao existe id de restaurante na base, entao inventa um proxy: cidade + coordenada arredondada
# limitacao: dois restaurantes no mesmo ponto viram um so
def build_restaurant_id(df: pd.DataFrame) -> pd.Series:
    """A base não traz ID de restaurante: usamos um proxy = cidade + coordenada (4 casas).

    Só existe para pedidos com localização válida; os demais ficam sem ID.
    """
    ids = pd.Series(np.nan, index=df.index, dtype=object)
    valid = df["has_valid_location"]
    if not valid.any():
        return ids
    key = (
        df.loc[valid, "city_code"] + "|"
        + df.loc[valid, "rest_lat"].round(4).astype(str) + "|"
        + df.loc[valid, "rest_lon"].round(4).astype(str)
    )
    numbering = {k: i + 1 for i, k in enumerate(sorted(key.unique()))}
    code = df.loc[valid, "city_code"]
    ids.loc[valid] = [f"{c}-{numbering[k]:04d}" for c, k in zip(code, key)]
    return ids


# cria as colunas novas que as paginas usam
def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # hora do pedido e data completa
    seconds = df["time_ordered"].dt.total_seconds()
    df["order_hour"] = ((seconds // 3600) % 24).astype(int)
    df["order_datetime"] = df["order_date"] + df["time_ordered"]
    df = df.drop(columns=["time_ordered"])

    # dia da semana, periodo do dia e as faixas
    df["weekday_num"] = df["order_date"].dt.dayofweek.astype(int)
    df["weekday"] = df["weekday_num"].map(dict(enumerate(WEEKDAYS_PT)))
    df["daypart"] = daypart_from_hour(df["order_hour"])
    df["age_band"] = age_band(df["courier_age"])
    df["time_band"] = time_band(df["delivery_time_min"])

    # tempo total = preparo + entrega (o que o cliente realmente espera)
    # Premissa confirmada: o tempo de entrega NÃO inclui o preparo.
    df["total_time_min"] = df["prep_time_min"] + df["delivery_time_min"]

    # cidade real vem do id do entregador
    df = pd.concat([df, extract_city(df["courier_id"])], axis=1)

    # distancia: so conta se a localizacao e valida e nao passa de 50km (senao e coordenada quebrada)
    dist = pd.Series(
        haversine_km(df["rest_lat"], df["rest_lon"], df["dest_lat"], df["dest_lon"]), index=df.index
    )
    dist = dist.where(df["has_valid_location"] & (dist <= MAX_DISTANCE_KM))
    df["distance_km"] = dist
    # velocidade media so pra checar se os dados fazem sentido
    speed = dist / (df["delivery_time_min"] / 60.0)
    df["speed_kmh"] = speed.where(speed <= MAX_SPEED_KMH)

    # por fim o id proxy do restaurante
    df["restaurant_id"] = build_restaurant_id(df)
    return df
