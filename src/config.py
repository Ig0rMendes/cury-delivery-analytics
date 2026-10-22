"""Configuração central do projeto: caminhos, nomes e regras de negócio/qualidade.

Todos os caminhos são calculados a partir da localização deste arquivo, então o
projeto funciona em qualquer computador (Windows, macOS, Linux) sem editar nada.
"""
from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------- caminhos
# aqui a gente descobre onde o projeto ta, sem fixar caminho de ninguem.
# assim roda no pc de qualquer pessoa (windows, mac, linux) sem mexer em nada
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
ASSETS_DIR = ROOT_DIR / "assets"

# A base de dados pública se chama "train" (train.csv). Coloque-a em data/.
# nome da base publica. o usuario so precisa jogar o train.csv na pasta data
DATA_NAME = "train"
DATA_EXTENSIONS = (".csv", ".xlsx", ".xls")
DATA_ENV_VAR = "DELIVERY_DATA_PATH"  # opcional: caminho completo para outro arquivo

LOGO_NAME = "logo.png"  # procurado em assets/ sem diferenciar maiúsculas/minúsculas

APP_TITLE = "Cury Company · Inteligência de Entregas"
VERSION = "4.2"
APP_ICON = "🛵"

# ------------------------------------------------------------ regras de negócio
# regras de negocio: o que e atraso, quantos pedidos precisa pra ranquear alguem etc.
# mexeu aqui, muda o painel inteiro, entao cuidado
DEFAULT_SLA_MIN = 30          # prazo padrão da etapa de ENTREGA (minutos)
SLA_RANGE = (15, 60)          # limites do controle deslizante
MIN_ORDERS_COURIER = 20       # mínimo de pedidos para ranquear um entregador
MIN_ORDERS_RESTAURANT = 10    # mínimo de pedidos para ranquear um restaurante
MIN_GROUP_N = 30              # grupos menores que isso não geram conclusões
Z_95 = 1.96
# 3 erros-padrao em vez de 1,96: com centenas de entregadores o 1,96 aponta muita gente por puro acaso
Z_FLAG = 3.0                  # limiar p/ apontar entregador/restaurante (centenas de comparações: 1,96 geraria falsos positivos)
MIN_EFFECT_MIN = 1.0          # diferença mínima (min) para valer como achado

# --------------------------------------------------------- regras de qualidade
# regras de qualidade: o que passar disso e erro de registro e a linha sai na limpeza
AGE_RANGE = (18, 60)
RATING_RANGE = (1.0, 5.0)
DELIVERY_TIME_RANGE = (1, 180)     # minutos
PREP_TIME_RANGE = (0, 90)          # minutos
MULTIPLE_DELIVERIES_RANGE = (0, 3)
VEHICLE_CONDITION_RANGE = (0, 3)   # escala da base (sentido não documentado)
MAX_DISTANCE_KM = 50.0
MAX_SPEED_KMH = 80.0
INDIA_LAT_RANGE = (6.0, 37.5)
INDIA_LON_RANGE = (68.0, 98.0)

# ------------------------------------------------- valores categóricos válidos
# valores categoricos validos. o que nao estiver aqui vira vazio na limpeza
VALID_TRAFFIC = ("Low", "Medium", "High", "Jam")
VALID_WEATHER = ("Sunny", "Cloudy", "Fog", "Stormy", "Sandstorms", "Windy")
VALID_AREA = ("Metropolitan", "Urban", "Semi-Urban")
VALID_VEHICLE = ("motorcycle", "scooter", "electric_scooter", "bicycle")
VALID_ORDER_TYPE = ("Snack", "Meal", "Drinks", "Buffet")
VALID_FESTIVAL = ("Yes", "No")

# Código de cidade embutido no ID do entregador (ex.: INDORES13DEL02 -> INDO).
# o id do entregador carrega a cidade (ex INDORES13DEL02 = Indore).
# a coluna City da base na verdade e tipo de area, por isso a gente tira a cidade daqui
CITY_CODES = {
    "INDO": "Indore", "BANG": "Bangalore", "COIMB": "Coimbatore", "CHEN": "Chennai",
    "HYD": "Hyderabad", "RANCHI": "Ranchi", "MYS": "Mysore", "DEH": "Dehradun",
    "KOL": "Kolkata", "JAP": "Jaipur", "KNP": "Kanpur", "LUDH": "Ludhiana",
    "PUNE": "Pune", "SUR": "Surat", "VAD": "Vadodara", "MUM": "Mumbai",
    "AURG": "Aurangabad", "AGR": "Agra", "ALH": "Allahabad", "BHP": "Bhopal",
    "GOA": "Goa", "KOC": "Kochi",
}
UNKNOWN_CITY = "Outras"
