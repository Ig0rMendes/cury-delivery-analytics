"""Gera, a partir dos dados reais, o texto de "Principais resultados" (README e docs).

Reaproveita o mesmo motor de insights do dashboard: o que está no README é, por construção,
o que o painel mostra sem filtros. Nada é digitado à mão.
"""
from __future__ import annotations

import pandas as pd

from src.insights.couriers import courier_insights
from src.insights.executive import executive_insights
from src.insights.experience import experience_insights
from src.insights.external import external_insights
from src.insights.operations import operations_insights
from src.insights.restaurants import restaurant_insights
from src.metrics.couriers import courier_table, with_expected
from src.metrics.models import fit_delivery_model
from src.metrics.restaurants import restaurant_table
from src.processing.cleaning import CleaningReport
from src.config import MIN_ORDERS_COURIER, MIN_ORDERS_RESTAURANT
from src.utils.formatting import fmt_int, fmt_pct

# lista de paginas na ordem em que aparecem no README
PAGES = [
    ("Visão Executiva", "exec"), ("Operação", "ops"), ("Fatores Externos", "ext"),
    ("Entregadores", "cour"), ("Restaurantes", "rest"), ("Experiência do Cliente", "exp"),
]
# marcadores dentro do README: o script troca so o que fica entre eles
MARK_START, MARK_END = "<!-- FINDINGS:START -->", "<!-- FINDINGS:END -->"


# roda o mesmo motor de insights das paginas, sem filtros. o README sempre sai dos dados reais
def collect_insights(df: pd.DataFrame, sla: int = 30) -> dict:
    model = fit_delivery_model(df)
    expected_model = fit_delivery_model(df, extended=True)
    d = with_expected(df, expected_model)
    return {
        "exec": executive_insights(df, sla),
        "ops": operations_insights(df, sla),
        "ext": external_insights(df, sla, model),
        "cour": courier_insights(d, courier_table(d, sla, MIN_ORDERS_COURIER), expected_model, MIN_ORDERS_COURIER),
        "rest": restaurant_insights(df, restaurant_table(df, sla, MIN_ORDERS_RESTAURANT), sla, MIN_ORDERS_RESTAURANT),
        "exp": experience_insights(df, sla),
    }


# monta o markdown. versao curta (so titulos) pro README e versao completa pro docs/RESULTADOS.md
def findings_markdown(df: pd.DataFrame, report: CleaningReport, sla: int = 30, full: bool = False) -> str:
    """Markdown dos resultados. `full=False` traz só headlines (README); `full=True` inclui detalhes e ações."""
    data = collect_insights(df, sla)
    lines = [
        f"> Gerado automaticamente a partir de `{report.source}`: {fmt_int(report.raw_rows)} registros brutos, "
        f"{fmt_int(report.final_rows)} pedidos analisados ({fmt_pct(report.retention)}), prazo de entrega de {sla} min, sem filtros.",
        "",
    ]
    for title, key in PAGES:
        lines.append(f"**{title}**")
        lines.append("")
        for ins in data[key]:
            if not full and ins.kind == "info":
                continue
            lines.append(f"- {ins.icon} **{ins.headline}**")
            if full:
                if ins.detail:
                    lines.append(f"  - {ins.detail}")
                if ins.action:
                    lines.append(f"  - *Ação sugerida:* {ins.action}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# troca o miolo entre os marcadores. se os marcadores nao existirem, avisa em vez de estragar o README
def replace_block(text: str, new_block: str) -> str:
    """Troca o conteúdo entre os marcadores FINDINGS no README."""
    start, end = text.find(MARK_START), text.find(MARK_END)
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"Marcadores {MARK_START} / {MARK_END} não encontrados no README.")
    return text[: start + len(MARK_START)] + "\n" + new_block + text[end:]
