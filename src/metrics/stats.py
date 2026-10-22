"""Estatística básica sem dependências extras (só numpy/pandas)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.config import Z_95


# media, mediana, desvio e intervalo de confianca de 95% por grupo
# o IC e media +/- 1,96 * erro padrao (erro padrao = desvio / raiz de n)
def group_stats(df: pd.DataFrame, by, value: str, min_n: int = 1, z: float = Z_95) -> pd.DataFrame:
    """Média, mediana, desvio e IC95% de `value` por grupo `by` (coluna ou lista)."""
    g = df.groupby(by, observed=True)[value].agg(n="size", mean="mean", median="median", std="std")
    g["sem"] = g["std"] / np.sqrt(g["n"])
    g["ci_low"] = g["mean"] - z * g["sem"]
    g["ci_high"] = g["mean"] + z * g["sem"]
    return g[g["n"] >= min_n].reset_index()


# compara duas medias sem assumir que a variancia e igual nos dois grupos (teste de welch)
# o p-valor sai da normal mesmo, com muito dado a diferenca pra t-student e minima
def welch_test(a, b, z: float = Z_95) -> dict | None:
    """Diferença de médias (a - b) com erro-padrão de Welch e p-valor (aproximação normal)."""
    a = pd.Series(a).dropna().astype(float)
    b = pd.Series(b).dropna().astype(float)
    if len(a) < 2 or len(b) < 2:
        return None
    diff = a.mean() - b.mean()
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    # caso esquisito: tudo igual dentro dos grupos, entao nao tem como dividir por zero
    if se == 0:
        return {"diff": diff, "se": 0.0, "z": math.inf if diff else 0.0, "p": 0.0 if diff else 1.0,
                "ci_low": diff, "ci_high": diff, "significant": bool(diff), "n_a": len(a), "n_b": len(b)}
    stat = diff / se
    p = math.erfc(abs(stat) / math.sqrt(2))
    return {"diff": diff, "se": se, "z": stat, "p": p, "ci_low": diff - z * se, "ci_high": diff + z * se,
            "significant": p < 0.05, "n_a": len(a), "n_b": len(b)}


# intervalo de confianca pra proporcao (tipo % de atraso). ta aqui e testado, mas o painel ainda nao mostra
def wilson_ci(k: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """IC de Wilson para uma proporção."""
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


# correlacao de spearman = pearson em cima dos ranks. nao precisa ser linear e aguenta outlier
def spearman(x, y) -> float:
    """Correlação de Spearman = Pearson dos postos (sem scipy)."""
    s = pd.concat([pd.Series(x).reset_index(drop=True), pd.Series(y).reset_index(drop=True)], axis=1).dropna()
    if len(s) < 3 or s.iloc[:, 0].nunique() < 2 or s.iloc[:, 1].nunique() < 2:
        return float("nan")
    return float(s.iloc[:, 0].rank().corr(s.iloc[:, 1].rank()))


# regressao linear na mao (minimos quadrados) com erro padrao robusto HC1
# robusto porque o erro do tempo de entrega nao tem variancia constante
def ols_hc1(X: pd.DataFrame, y: pd.Series, add_const: bool = True) -> dict:
    """Mínimos quadrados com erros-padrão robustos HC1."""
    names = (["const"] if add_const else []) + list(X.columns)
    Xm = X.to_numpy(dtype=float)
    if add_const:
        Xm = np.column_stack([np.ones(len(Xm)), Xm])
    ym = y.to_numpy(dtype=float)
    n, k = Xm.shape
    # acha os coeficientes (beta) e os residuos
    beta, *_ = np.linalg.lstsq(Xm, ym, rcond=None)
    resid = ym - Xm @ beta
    # formula sanduiche do HC1: pao * recheio * pao, com a correcao n/(n-k)
    bread = np.linalg.pinv(Xm.T @ Xm)
    scores = Xm * resid[:, None]
    cov = bread @ (scores.T @ scores) @ bread * (n / max(n - k, 1))
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    # R2 = quanto da variacao o modelo explica
    ss_tot = float(((ym - ym.mean()) ** 2).sum())
    r2 = 1 - float((resid**2).sum()) / ss_tot if ss_tot > 0 else float("nan")
    return {
        "params": pd.Series(beta, index=names),
        "se": pd.Series(se, index=names),
        "r2": r2,
        "n": n,
        "resid": resid,
    }
