"""Modelo de regressão do tempo de entrega (isola o efeito de cada fator).

Ele existe para responder duas perguntas que médias simples não respondem:
  1. "Quanto cada fator pesa, mantendo os demais iguais?" (efeitos isolados)
  2. "Quanto este entregador/restaurante foge do ESPERADO para o contexto dele?"

É uma associação estatística (OLS com erros robustos HC1), não prova de causalidade.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.config import Z_95
from src.metrics.stats import ols_hc1
from src.utils.labels import pt

# categoria com menos de 30 pedidos e descartada do modelo, se nao o efeito seria so ruido
MIN_LEVEL_N = 30

# modelo simples: cada fator entra sozinho, a referencia e o nivel de comparacao (ex: transito baixo)
CATEGORICAL = {  # coluna -> (referência preferida, rótulo do grupo)
    "traffic": ("Low", "Trânsito"),
    "weather": ("Sunny", "Clima"),
    "festival": ("No", "Festival"),
    "vehicle_type": (None, "Veículo"),
    "area_type": (None, "Tipo de área"),
}
# Modelo "estendido" (usado só para o tempo ESPERADO de cada pedido, p/ ranquear entregadores):
# trânsito e clima entram combinados, porque na base real o efeito de um depende do outro,
# e o período do dia entra para não confundir turno de pico com desempenho individual.
# modelo estendido, so pra calcular o tempo esperado de cada pedido
CATEGORICAL_EXTENDED = {
    "traffic_weather": (None, "Trânsito × clima"),
    "daypart": (None, "Período do dia"),
    "festival": ("No", "Festival"),
    "vehicle_type": (None, "Veículo"),
    "area_type": (None, "Tipo de área"),
}
# variaveis numericas e a unidade em que o efeito e mostrado (ex: a cada +5 km)
NUMERIC = {  # coluna -> (rótulo, unidade do efeito)
    "distance_km": ("Distância (+5 km)", 5.0),
    "multiple_deliveries": ("Entregas simultâneas (+1)", 1.0),
    "courier_age": ("Idade do entregador (+10 anos)", 10.0),
    "vehicle_condition": ("Condição do veículo (+1 nível)", 1.0),
}
TARGET = "delivery_time_min"


# guarda o modelo ja ajustado: tabela de efeitos, R2 e os coeficientes
@dataclass
class DeliveryModel:
    table: pd.DataFrame                 # efeitos em minutos, com IC95%
    r2: float
    n: int
    params: pd.Series
    spec: dict = field(default_factory=dict)      # coluna -> {"ref":..., "levels":[...]}
    numeric: list = field(default_factory=list)
    categories: dict = field(default_factory=lambda: CATEGORICAL)

    # monta a matriz do modelo: uma coluna 0/1 pra cada nivel (dummy) mais as numericas
    # 'ok' diz quais linhas tem tudo preenchido e podem ser usadas
    def design(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        """Matriz de desenho e máscara de linhas utilizáveis."""
        ok = pd.Series(True, index=df.index)
        cols = {}
        for col, s in self.spec.items():
            allowed = [s["ref"]] + s["levels"]
            values = _values(df, col)
            ok &= values.isin(allowed)
            for lvl in s["levels"]:
                cols[f"{col}={lvl}"] = (values == lvl).astype(float)
        for col in self.numeric:
            ok &= df[col].notna()
            cols[col] = df[col].astype(float)
        X = pd.DataFrame(cols, index=df.index)
        return X, ok

    # tempo esperado de cada pedido segundo o modelo (vazio se faltar dado)
    def predict(self, df: pd.DataFrame) -> pd.Series:
        """Tempo esperado (min) para cada pedido; NaN quando faltam dados do modelo."""
        X, ok = self.design(df)
        out = pd.Series(np.nan, index=df.index, dtype=float)
        if ok.any():
            cols = [c for c in self.params.index if c != "const"]
            Xo = X.loc[ok, cols].to_numpy(dtype=float)
            out.loc[ok] = self.params["const"] + Xo @ self.params[cols].to_numpy(dtype=float)
        return out

    # busca o efeito de um termo especifico na tabela
    def effect(self, term: str) -> pd.Series | None:
        row = self.table[self.table["term"] == term]
        return None if row.empty else row.iloc[0]


# no modelo estendido transito e clima viram uma coluna so (ex Jam|Fog) pra pegar a interacao
def _values(df: pd.DataFrame, col: str) -> pd.Series:
    """Valores de uma variável categórica do modelo (inclui a combinação trânsito|clima)."""
    if col == "traffic_weather":
        return df["traffic"] + "|" + df["weather"]
    return df[col]


# monta o nome bonitinho do termo pra mostrar na tabela
def _label(categories: dict, col: str, level) -> str:
    return f"{categories[col][1]}: {pt(col, level)}"


# ajusta o modelo. com menos de 200 linhas devolve None (nao confia)
def fit_delivery_model(df: pd.DataFrame, z: float = Z_95, extended: bool = False) -> DeliveryModel | None:
    """Ajusta o modelo. Devolve None se a amostra for pequena demais para ser confiável.

    `extended=True` troca trânsito e clima (separados) pela combinação dos dois e acrescenta o
    período do dia: melhor para estimar o tempo ESPERADO; o modelo simples é melhor para ler efeitos.
    """
    if len(df) < 200:
        return None

    # passo 1: decide quais niveis entram e qual e a referencia de cada fator
    categories = CATEGORICAL_EXTENDED if extended else CATEGORICAL
    spec = {}
    for col, (pref, _) in categories.items():
        counts = _values(df, col).value_counts()
        kept = counts[counts >= MIN_LEVEL_N]
        if len(kept) < 2:
            continue
        ref = pref if pref in kept.index else kept.idxmax()
        spec[col] = {"ref": ref, "levels": [lvl for lvl in kept.index if lvl != ref]}
    # passo 2: so usa numericas que tem dado e variam
    numeric = [c for c in NUMERIC if df[c].notna().any() and df[c].nunique() > 1]

    model = DeliveryModel(table=pd.DataFrame(), r2=float("nan"), n=0, params=pd.Series(dtype=float),
                          spec=spec, numeric=numeric, categories=categories)
    # passo 3: monta X e y so com as linhas completas
    X, ok = model.design(df)
    X = X.loc[ok]
    y = df.loc[ok, TARGET]
    X = X.loc[:, X.nunique() > 1]  # remove colunas constantes
    if X.shape[1] == 0 or len(X) < max(200, 10 * (X.shape[1] + 1)):
        return None

    # passo 4: roda a regressao
    fit = ols_hc1(X, y)
    params, se = fit["params"], fit["se"]

    # passo 5: transforma coeficientes em minutos, com IC95%
    rows = []
    for term in X.columns:
        if term in NUMERIC:
            label, unit = NUMERIC[term]
            beta, s, n_obs, group, ref = params[term] * unit, se[term] * unit, int(X[term].notna().sum()), "Contínuo", ""
        else:
            col, lvl = term.split("=", 1)
            label = _label(categories, col, lvl)
            beta, s, n_obs = params[term], se[term], int(X[term].sum())
            group, ref = categories[col][1], pt(col, spec[col]["ref"])
        rows.append({"term": term, "label": label, "group": group, "reference": ref,
                     "effect": beta, "se": s, "ci_low": beta - z * s, "ci_high": beta + z * s, "n": n_obs})

    # guarda tudo no objeto e limpa o que nao entrou no ajuste
    model.table = pd.DataFrame(rows)
    model.r2 = fit["r2"]
    model.n = fit["n"]
    model.params = params
    # restringe spec/numeric ao que de fato entrou no ajuste
    kept_terms = set(X.columns)
    model.numeric = [c for c in numeric if c in kept_terms]
    for col in list(model.spec):
        model.spec[col]["levels"] = [l for l in model.spec[col]["levels"] if f"{col}={l}" in kept_terms]
        if not model.spec[col]["levels"]:
            del model.spec[col]
    return model
