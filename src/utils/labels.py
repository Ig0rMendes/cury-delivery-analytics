"""Rótulos em português e ordens canônicas das categorias."""
from __future__ import annotations

# ordens canonicas pra tabelas e graficos sairem na sequencia certa
TRAFFIC_ORDER = ["Low", "Medium", "High", "Jam"]
DAYPART_ORDER = ["Manhã", "Almoço", "Tarde", "Jantar", "Noite"]
AGE_BAND_ORDER = ["18–24", "25–29", "30–34", "35–39", "40+"]
TIME_BAND_ORDER = ["Até 20 min", "21–30 min", "31–40 min", "Mais de 40 min"]
WEEKDAYS_PT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

# traducoes dos valores da base pra portugues
TRAFFIC_PT = {"Low": "Baixo", "Medium": "Médio", "High": "Alto", "Jam": "Congestionado"}
WEATHER_PT = {
    "Sunny": "Ensolarado", "Cloudy": "Nublado", "Fog": "Neblina",
    "Stormy": "Tempestade", "Sandstorms": "Tempestade de areia", "Windy": "Ventoso",
}
AREA_PT = {"Metropolitan": "Metropolitana", "Urban": "Urbana", "Semi-Urban": "Semiurbana"}
VEHICLE_PT = {
    "motorcycle": "Moto", "scooter": "Scooter",
    "electric_scooter": "Scooter elétrica", "bicycle": "Bicicleta",
}
ORDER_TYPE_PT = {"Snack": "Lanche", "Meal": "Refeição", "Drinks": "Bebidas", "Buffet": "Buffet"}
FESTIVAL_PT = {"Yes": "Sim", "No": "Não"}

# qual dicionario de traducao usar pra cada tipo de coluna
_MAPS = {
    "traffic": TRAFFIC_PT, "weather": WEATHER_PT, "area_type": AREA_PT,
    "vehicle_type": VEHICLE_PT, "order_type": ORDER_TYPE_PT, "festival": FESTIVAL_PT,
}


# traduz um valor. se nao conhecer, devolve o proprio texto
def pt(kind: str, value) -> str:
    """Traduz um valor categórico. Valores desconhecidos voltam como texto."""
    return _MAPS.get(kind, {}).get(value, str(value))


# rotulo legivel de qualquer dimensao (numeros viram inteiro, categorias sao traduzidas)
def value_label(col: str, value) -> str:
    """Rótulo legível de qualquer valor de dimensão (categorias traduzidas; números como inteiro)."""
    if col in ("multiple_deliveries", "vehicle_condition"):
        try:
            return str(int(value))
        except (TypeError, ValueError):
            return str(value)
    return pt(col, value)


# ordena o dataframe pela ordem canonica (o que nao esta na lista vai pro fim)
def sort_by_order(frame, column: str, order: list[str]):
    """Ordena um DataFrame pela ordem canônica de `column` (valores fora da ordem vão ao fim)."""
    rank = {v: i for i, v in enumerate(order)}
    key = frame[column].map(lambda v: rank.get(v, len(order)))
    return frame.assign(_k=key).sort_values("_k", kind="stable").drop(columns="_k")
