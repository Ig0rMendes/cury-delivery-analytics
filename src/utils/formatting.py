"""Formatação de números no padrão brasileiro (1.234,5)."""
from __future__ import annotations

import math

# traco que aparece quando o numero nao existe (em vez de 'nan')
DASH = "—"


# checa se o valor e vazio/NaN
def _bad(x) -> bool:
    try:
        return x is None or (isinstance(x, float) and math.isnan(x)) or x != x
    except Exception:  # noqa: BLE001
        return True


# troca virgula por ponto e vice-versa: 1,234.5 vira 1.234,5 (padrao brasileiro)
def _swap_sep(text: str) -> str:
    return text.replace(",", "§").replace(".", ",").replace("§", ".")


# formatadores de numero em pt-BR: inteiro, decimal, porcentagem, minutos e com sinal
def fmt_int(x) -> str:
    if _bad(x):
        return DASH
    return _swap_sep(f"{int(round(float(x))):,}")


def fmt_num(x, decimals: int = 1) -> str:
    if _bad(x):
        return DASH
    return _swap_sep(f"{float(x):,.{decimals}f}")


def fmt_pct(ratio, decimals: int = 1) -> str:
    """Recebe uma FRAÇÃO (0,123) e devolve '12,3%'."""
    if _bad(ratio):
        return DASH
    return _swap_sep(f"{float(ratio) * 100:,.{decimals}f}") + "%"


def fmt_min(x, decimals: int = 1) -> str:
    if _bad(x):
        return DASH
    return f"{fmt_num(x, decimals)} min"


def fmt_signed(x, decimals: int = 1, unit: str = "") -> str:
    """'+2,3 min' / '-1,0 min'."""
    if _bad(x):
        return DASH
    sign = "+" if float(x) > 0 else ("-" if float(x) < 0 else "")
    return f"{sign}{fmt_num(abs(float(x)), decimals)}{(' ' + unit) if unit else ''}"


def fmt_signed_pct(ratio, decimals: int = 1) -> str:
    if _bad(ratio):
        return DASH
    sign = "+" if float(ratio) > 0 else ("-" if float(ratio) < 0 else "")
    return f"{sign}{fmt_pct(abs(float(ratio)), decimals)}"
