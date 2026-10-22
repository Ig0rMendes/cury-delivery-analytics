"""Gerador de dados SINTÉTICOS no formato BRUTO do `train.csv`.

Reproduz as sujeiras da base real (espaços, 'NaN ', '(min) 24', 'conditions Sunny',
latitude com sinal invertido, coordenadas zeradas, idades/avaliações impossíveis,
duplicados) com efeitos conhecidos, para que os testes verifiquem se o pipeline e as
métricas recuperam o que foi colocado nos dados. NÃO são dados reais.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRAFFIC_EFFECT = {"Low": 0.0, "Medium": 3.0, "High": 6.0, "Jam": 10.0}
WEATHER_EFFECT = {"Sunny": 0.0, "Cloudy": 2.0, "Fog": 3.0, "Stormy": 4.0, "Sandstorms": 4.0, "Windy": 1.0}
CITY_BASE = {"INDO": (22.7, 75.9), "BANG": (12.9, 77.6), "HYD": (17.4, 78.4), "PUNE": (18.5, 73.8), "MUM": (19.1, 72.9)}
COLS = [
    "ID", "Delivery_person_ID", "Delivery_person_Age", "Delivery_person_Ratings",
    "Restaurant_latitude", "Restaurant_longitude", "Delivery_location_latitude",
    "Delivery_location_longitude", "Order_Date", "Time_Orderd", "Time_Order_picked",
    "Weatherconditions", "Road_traffic_density", "Vehicle_condition", "Type_of_order",
    "Type_of_vehicle", "multiple_deliveries", "Festival", "City", "Time_taken(min)",
]


# gera uma base fake no formato bruto do train, com efeitos plantados (ex congestionamento +10 min)
# assim da pra provar que o metodo recupera o que a gente sabe que existe
def make_raw(n: int = 3000, seed: int = 7, dirty: bool = True) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    codes = list(CITY_BASE)

    # entregadores com idade e nota fixas (+ pequena variação) e uma "velocidade" própria
    couriers = []
    for code in codes:
        for r in range(1, 9):
            for d in range(1, 6):
                couriers.append((f"{code}RES{r:02d}DEL{d:02d}", code, r))
    cid = [c[0] for c in couriers]
    c_age = dict(zip(cid, rng.integers(20, 39, len(cid))))
    c_rating = dict(zip(cid, np.round(rng.uniform(3.8, 5.0, len(cid)), 1)))
    c_skill = dict(zip(cid, rng.normal(0, 1.2, len(cid))))

    idx = rng.integers(0, len(couriers), n)
    ids = [couriers[i][0] for i in idx]
    code = [couriers[i][1] for i in idx]
    res = [couriers[i][2] for i in idx]

    traffic = rng.choice(list(TRAFFIC_EFFECT), n, p=[0.3, 0.3, 0.25, 0.15])
    weather = rng.choice(list(WEATHER_EFFECT), n)
    multi = rng.choice([0, 1, 2, 3], n, p=[0.35, 0.5, 0.1, 0.05])
    vcond = rng.integers(0, 4, n)
    vehicle = rng.choice(["motorcycle", "scooter", "electric_scooter", "bicycle"], n, p=[0.5, 0.3, 0.15, 0.05])
    festival = rng.choice(["No", "Yes"], n, p=[0.97, 0.03])
    area = rng.choice(["Metropolitian", "Urban", "Semi-Urban"], n, p=[0.5, 0.4, 0.1])
    otype = rng.choice(["Snack", "Meal", "Drinks", "Buffet"], n)

    base = np.array([CITY_BASE[c] for c in code])
    rest_lat = base[:, 0] + res_off(res, 0.03)
    rest_lon = base[:, 1] + res_off(res, 0.05)
    off_lat = rng.uniform(0.01, 0.09, n)
    off_lon = rng.uniform(0.01, 0.09, n)
    dest_lat, dest_lon = rest_lat + off_lat, rest_lon + off_lon

    dist = np.sqrt((off_lat * 111) ** 2 + (off_lon * 111 * np.cos(np.radians(rest_lat))) ** 2)
    age = np.array([c_age[i] for i in ids])
    skill = np.array([c_skill[i] for i in ids])
    delivery = (
        8 + 1.6 * dist
        + np.array([TRAFFIC_EFFECT[t] for t in traffic])
        + np.array([WEATHER_EFFECT[w] for w in weather])
        + 3.0 * multi + 0.8 * vcond * 0 + 2.0 * (festival == "Yes")
        + skill + rng.normal(0, 2.0, n)
    )
    delivery = np.clip(np.round(delivery), 5, 80).astype(int)

    start = pd.Timestamp("2022-02-11")
    day = rng.integers(0, 55, n)
    dates = (start + pd.to_timedelta(day, unit="D")).strftime("%d-%m-%Y")
    hour = rng.integers(8, 24, n)
    minute = rng.integers(0, 60, n)
    prep = rng.choice([5, 10, 15], n)
    t_order = pd.to_timedelta(hour * 60 + minute, unit="m")
    t_pick = t_order + pd.to_timedelta(prep, unit="m")

    def hms(td):
        total = (td.total_seconds().to_numpy() % 86400).astype(int)
        return [f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}" for s in total]

    rating = np.array([c_rating[i] for i in ids]) + rng.choice([0, 0, 0, -0.1, 0.1], n)
    rating = np.clip(np.round(rating, 1), 1, 5)

    df = pd.DataFrame({
        "ID": [f"0x{i:04x}" for i in range(n)],
        "Delivery_person_ID": ids,
        "Delivery_person_Age": age.astype(str),
        "Delivery_person_Ratings": rating.astype(str),
        "Restaurant_latitude": rest_lat.round(6).astype(str),
        "Restaurant_longitude": rest_lon.round(6).astype(str),
        "Delivery_location_latitude": dest_lat.round(6).astype(str),
        "Delivery_location_longitude": dest_lon.round(6).astype(str),
        "Order_Date": dates,
        "Time_Orderd": hms(t_order),
        "Time_Order_picked": hms(t_pick),
        "Weatherconditions": ["conditions " + w for w in weather],
        "Road_traffic_density": [t + " " for t in traffic],
        "Vehicle_condition": vcond.astype(str),
        "Type_of_order": [o + " " for o in otype],
        "Type_of_vehicle": [v + " " for v in vehicle],
        "multiple_deliveries": multi.astype(str),
        "Festival": [f + " " for f in festival],
        "City": [a + " " for a in area],
        "Time_taken(min)": ["(min) " + str(d) for d in delivery],
    })[COLS]

    if dirty:
        k = max(5, n // 100)
        pick = lambda: rng.choice(n, k, replace=False)  # noqa: E731
        neg = pick()
        df.loc[neg, "Restaurant_latitude"] = "-" + df.loc[neg, "Restaurant_latitude"]
        df.loc[neg, "Delivery_location_latitude"] = "-" + df.loc[neg, "Delivery_location_latitude"]
        zero = pick()
        for c in ["Restaurant_latitude", "Restaurant_longitude", "Delivery_location_latitude", "Delivery_location_longitude"]:
            df.loc[zero, c] = "0.0"
        df.loc[pick(), "Delivery_person_Age"] = "NaN "
        df.loc[pick(), "Delivery_person_Ratings"] = "NaN "
        df.loc[pick(), "Road_traffic_density"] = "NaN "
        df.loc[pick(), "Weatherconditions"] = "conditions NaN"
        df.loc[pick(), "Festival"] = "NaN "
        df.loc[pick(), "Delivery_person_Age"] = "15"
        df.loc[pick(), "Delivery_person_Ratings"] = "6.0"
        dup = df.iloc[:k].copy()
        df = pd.concat([df, dup], ignore_index=True)
    return df


# funcaozinha auxiliar: multiplica um array por um fator (usada na geracao das coordenadas)
def res_off(res, scale):
    return np.array(res, dtype=float) * scale
