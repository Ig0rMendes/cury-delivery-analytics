"""Insights da Visão Executiva."""
from __future__ import annotations

import pandas as pd

from src.insights.base import Insight, too_small
from src.metrics.kpis import compute_kpis
from src.metrics.segments import segment_table
from src.utils.formatting import fmt_int, fmt_min, fmt_num, fmt_pct, fmt_signed

# período do dia fica de fora: coincide com trânsito pesado e pareceria "gestão" sem ser
# fatores que a operacao consegue mexer de verdade
CONTROLLABLE = {"multiple_deliveries", "vehicle_type", "city"}
MAX_SEGMENT_SHARE = 0.5  # segmento majoritário não é alavanca: comparar "maioria x resto" confunde

# acao sugerida pra cada tipo de fator (o texto que aparece no insight)
ACTIONS = {
    "traffic": "Ajustar roteirização e janelas de saída nos horários de trânsito pesado e escalar os entregadores mais "
               "rápidos para essas janelas.",
    "weather": "Adotar prazo dinâmico por clima (informando o cliente no app) e reforçar a frota quando o tempo fechar.",
    "area_type": "Revisar raio de entrega e cobertura nessa área; avaliar pontos de apoio (dark stores) para reduzir percurso.",
    "multiple_deliveries": "Limitar entregas simultâneas por entregador e agrupar rotas por proximidade.",
    "vehicle_type": "Revisar a alocação de pedidos por tipo de veículo (distâncias longas para veículos mais rápidos).",
    "daypart": "Redistribuir a escala para cobrir esse período com mais entregadores.",
    "festival": "Planejar capacidade extra e prazos maiores em dias de festival.",
    "city": "Abrir diagnóstico local (cobertura, escala e restaurantes parceiros) nessa cidade.",
}


# insights de 'onde agir': usa a tabela de segmentos e escolhe a maior alavanca
def _driver_insights(df: pd.DataFrame, sla: float) -> list[Insight]:
    seg = segment_table(df, sla=sla)
    # período do dia coincide com trânsito pesado (ver página Operação): comparar o pico "cru" induziria a contratar sem resolver
    # filtros importantes: so segmentos piores que o resto, que nao sejam maioria (>50%) e sem periodo do dia
    # periodo do dia coincide com transito pesado, apontar ele faria o ceo contratar sem resolver a causa
    seg = seg[(seg["diff"] > 0) & (seg["share"] <= MAX_SEGMENT_SHARE) & (seg["column"] != "daypart")] if not seg.empty else seg
    if seg.empty:
        return []
    out = []
    # a maior alavanca e a que tem maior ganho potencial (minutos na media geral)
    top = seg.sort_values("potential_gain", ascending=False).iloc[0]
    out.append(Insight(
        "opportunity",
        f"Maior alavanca de tempo: {top['segment']}",
        f"Responde por {fmt_pct(top['share'])} dos pedidos, mas por {fmt_pct(top['late_share'])} dos atrasos. "
        f"A entrega aqui é {fmt_num(top['diff'])} min mais lenta que no restante da base "
        f"({fmt_min(top['mean_delivery'])} contra {fmt_min(top['rest_mean'])}). "
        f"Se esse segmento operasse como o restante, a média geral cairia {fmt_num(top['potential_gain'])} min.",
        ACTIONS.get(top["column"], ""),
    ))
    # segunda alavanca: a maior entre as que a operacao controla (so 2+ entregas simultaneas contam como sobrecarga)
    ctrl = seg[seg["column"].isin(CONTROLLABLE)]
    # 0 e 1 entrega simultânea são o patamar normal da operação; só 2+ é "sobrecarga"
    ctrl = ctrl[~((ctrl["column"] == "multiple_deliveries") & (pd.to_numeric(ctrl["value"], errors="coerce") < 2))]
    if not ctrl.empty:
        c = ctrl.sort_values("potential_gain", ascending=False).iloc[0]
        if c["segment"] != top["segment"] and c["potential_gain"] >= 0.1:
            out.append(Insight(
                "opportunity",
                f"Maior alavanca sob gestão direta: {c['segment']}",
                f"Fatores como trânsito e clima não se controlam; este sim. São {fmt_pct(c['share'])} dos pedidos, "
                f"{fmt_num(c['diff'])} min mais lentos que o restante, o que vale {fmt_num(c['potential_gain'])} min "
                f"na média geral e {fmt_pct(c['late_share'])} dos atrasos.",
                ACTIONS.get(c["column"], ""),
            ))
    return out


# compara a ultima semana da base com a anterior. 'ultimos 7 dias' e da base, nao de hoje
def _trend_insight(df: pd.DataFrame) -> Insight | None:
    daily = df.groupby("order_date").agg(n=("order_id", "size"), t=("delivery_time_min", "mean"))
    if len(daily) < 14:
        return None
    last_day = daily.index.max()
    recent = df[df["order_date"] > last_day - pd.Timedelta(days=7)]
    prev = df[(df["order_date"] <= last_day - pd.Timedelta(days=7)) & (df["order_date"] > last_day - pd.Timedelta(days=14))]
    if len(recent) < 50 or len(prev) < 50:
        return None
    dt = recent["delivery_time_min"].mean() - prev["delivery_time_min"].mean()
    dv = len(recent) / len(prev) - 1
    kind = "risk" if dt > 1.0 else "finding"
    trend = "piorou" if dt > 1.0 else ("melhorou" if dt < -1.0 else "ficou estável")
    return Insight(
        kind,
        f"Últimos 7 dias da base: tempo de entrega {trend} ({fmt_signed(dt)} min) com volume {fmt_signed(dv * 100, 0)}%",
        f"Semana mais recente: {fmt_min(recent['delivery_time_min'].mean())} em {fmt_int(len(recent))} pedidos; "
        f"semana anterior: {fmt_min(prev['delivery_time_min'].mean())} em {fmt_int(len(prev))}.",
        "Se o tempo sobe junto com o volume, o problema é capacidade; se sobe sem o volume, investigue trânsito/clima."
        if dt > 1.0 else "",
    )


# junta tudo da pagina: atraso geral, alavancas, preparo e tendencia
def executive_insights(df: pd.DataFrame, sla: float) -> list[Insight]:
    small = too_small(df)
    if small:
        return small
    k = compute_kpis(df, sla)
    # primeiro insight: % de atraso, tempo medio e o P90
    late = 1 - k["on_time_rate"]
    out = [Insight(
        "risk" if late > 0.25 else "finding",
        f"{fmt_pct(late)} das entregas passam de {sla:.0f} min; 1 em 10 leva mais de {fmt_min(k['p90_delivery'], 0)}",
        f"A etapa de entrega leva {fmt_min(k['avg_delivery'])} em média (mediana {fmt_min(k['median_delivery'])}). "
        f"Somando o preparo ({fmt_min(k['avg_prep'])}), o cliente espera {fmt_min(k['avg_total'])} no total, e 1 em 10 "
        f"espera mais de {fmt_min(k['p90_total'], 0)}. Medir só a entrega esconde {fmt_pct(k['prep_share'], 0)} da espera real.",
        "Acompanhar o tempo TOTAL (pedido até a porta) como indicador principal, não só a entrega.",
    )]
    out += _driver_insights(df, sla)
    # so fala do preparo se ele pesar pelo menos 20% da espera
    if k["prep_share"] >= 0.2:
        out.append(Insight(
            "opportunity",
            f"O preparo é {fmt_pct(k['prep_share'], 0)} da espera do cliente",
            f"Enquanto a logística concentra atenção na entrega, a cozinha consome {fmt_min(k['avg_prep'])} por pedido. "
            "Para o cliente, 2 min a menos de preparo valem o mesmo que 2 min a menos de entrega.",
            "Definir metas de preparo para a rede e, antes de cobrar restaurantes individualmente, registrar horários em minutos exatos: "
            "a base atual só tem poucos valores de preparo (veja a nota na página Restaurantes).",
        ))
    t = _trend_insight(df)
    if t:
        out.append(t)
    return out
