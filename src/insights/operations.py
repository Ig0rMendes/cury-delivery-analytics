"""Insights da página Operação."""
from __future__ import annotations

import pandas as pd

from src.config import MIN_GROUP_N
from src.insights.base import Insight, too_small
from src.metrics.operations import city_table, concentration, hourly_profile
from src.metrics.stats import spearman, welch_test
from src.metrics.summary import summarize
from src.utils.formatting import fmt_int, fmt_min, fmt_num, fmt_pct, fmt_signed

# transito considerado pesado
HEAVY_TRAFFIC = ("High", "Jam")


# a diferenca entre grupo e resto DENTRO de cada nivel de transito (ponderada pelo tamanho)
# isso evita confudimento: o pico parece lento so porque pega transito pesado
def stratified_gap(df: pd.DataFrame, in_group: pd.Series, by: str = "traffic", min_n: int = MIN_GROUP_N) -> float:
    """Diferença média de tempo (grupo - resto) DENTRO de cada nível de `by`, ponderada pelo tamanho do grupo.

    Responde "a diferença continua se compararmos pedidos sob o mesmo trânsito?". Sem isso, um
    período que coincide com trânsito pesado parece 'gargalo de capacidade' sem ser.
    """
    num = den = 0.0
    for _, sub in df.groupby(by):
        mask = in_group.loc[sub.index]
        a, b = sub.loc[mask, "delivery_time_min"], sub.loc[~mask, "delivery_time_min"]
        if len(a) >= min_n and len(b) >= min_n:
            num += (a.mean() - b.mean()) * len(a)
            den += len(a)
    return num / den if den else float("nan")


# insight do pico: acha as 3 horas com mais pedidos e compara o tempo dentro e fora delas
def _peak_insight(df: pd.DataFrame, sla: float) -> Insight | None:
    h = hourly_profile(df, sla, min_n=MIN_GROUP_N)
    if len(h) < 6:
        return None
    top = h.sort_values("n", ascending=False).head(3)
    hours = sorted(top["order_hour"].astype(int))
    label = ", ".join(f"{x}h" for x in hours)
    in_peak = df["order_hour"].isin(hours)
    share = in_peak.mean()
    peak, off = df.loc[in_peak, "delivery_time_min"], df.loc[~in_peak, "delivery_time_min"]
    test = welch_test(peak, off)
    rho = spearman(h["n"], h["mean_delivery"])
    # diferenca ajustada: igualando o transito, o pico ainda e mais lento?
    adj = stratified_gap(df, in_peak)

    if test and test["significant"] and test["diff"] >= 1.0:
        heavy_peak = df.loc[in_peak, "traffic"].isin(HEAVY_TRAFFIC).mean()
        heavy_off = df.loc[~in_peak, "traffic"].isin(HEAVY_TRAFFIC).mean()
        base = (f"No pico ({label}, {fmt_pct(share, 0)} dos pedidos) a entrega leva {fmt_min(peak.mean())} contra "
                f"{fmt_min(off.mean())} fora dele ({fmt_signed(test['diff'])} min). ")
        # se continua >= 1 min mesmo igualando o transito, ai sim e sinal de capacidade
        if pd.notna(adj) and adj >= 1.0:
            return Insight(
                "risk", f"O pico piora a entrega em {fmt_num(adj)} min mesmo com o trânsito igualado: sinal de capacidade",
                base + f"Comparando pedidos sob o MESMO nível de trânsito, a diferença segue em {fmt_signed(adj)} min.",
                "Reforçar a escala nessas horas (turnos escalonados, incentivo por hora de pico).")
        return Insight(
            "finding", f"O pico é mais lento ({fmt_signed(test['diff'])} min), mas o motivo é o trânsito, não falta de entregador",
            base + f"{fmt_pct(heavy_peak, 0)} dos pedidos do pico pegam trânsito alto ou congestionado, contra "
                   f"{fmt_pct(heavy_off, 0)} fora dele. Igualando o trânsito, a diferença cai para {fmt_signed(adj if pd.notna(adj) else 0)} min.",
            "Contratar para o pico resolveria pouco; priorize roteirização e janelas de saída nos horários de trânsito pesado.")
    return Insight(
        "finding", f"O pico ({label}) concentra {fmt_pct(share, 0)} dos pedidos sem piorar a entrega",
        f"No pico a entrega leva {fmt_min(peak.mean())} e fora dele {fmt_min(off.mean())}"
        + (f" (correlação entre volume e tempo por hora: {fmt_num(rho, 2)})" if pd.notna(rho) else "")
        + ". A frota absorve a demanda; o tempo é explicado por outros fatores.",
        "Não priorizar contratação para o pico; priorizar roteirização e controle de entregas simultâneas.",
    )


# entregas simultaneas: quanto custam e quanto valeria limitar. ja tem o ajuste por transito
def _multiple_insight(df: pd.DataFrame, sla: float) -> Insight | None:
    t = summarize(df, "multiple_deliveries", sla, min_n=MIN_GROUP_N).sort_values("multiple_deliveries")
    if len(t) < 2:
        return None
    lo, hi = t.iloc[0], t.iloc[-1]
    if hi["multiple_deliveries"] <= lo["multiple_deliveries"]:
        return None
    steps = " → ".join(f"{int(r['multiple_deliveries'])}: {fmt_num(r['mean_delivery'])}" for _, r in t.iterrows())
    # 'sobrecarga' = 2 ou mais entregas ao mesmo tempo
    heavy = df["multiple_deliveries"] >= 2
    n_heavy = int(heavy.sum())
    if n_heavy < MIN_GROUP_N:
        return None
    base_mean = df.loc[~heavy, "delivery_time_min"].mean()
    gap = df.loc[heavy, "delivery_time_min"].mean() - base_mean
    adj = stratified_gap(df, heavy)
    # ganho aproximado: diferenca * parcela dos pedidos afetados
    gain = gap * n_heavy / len(df)
    late_hi = (df.loc[heavy, "delivery_time_min"] > sla).mean()
    late_lo = (df.loc[~heavy, "delivery_time_min"] > sla).mean()
    kind = "opportunity" if gap >= 2.0 else "finding"
    return Insight(
        kind,
        f"{fmt_pct(n_heavy / len(df), 0)} dos pedidos saem com 2+ entregas simultâneas e levam {fmt_num(gap)} min a mais",
        f"Tempo médio de entrega por nº de entregas simultâneas (min): {steps}. Com 2+ simultâneas, {fmt_pct(late_hi, 0)} "
        f"passam do prazo, contra {fmt_pct(late_lo, 0)} nos demais. Igualando o trânsito, a diferença é de {fmt_signed(adj)} min. "
        f"Limitar a 1 entrega por vez tiraria cerca de {fmt_num(gain)} min da média geral ({fmt_pct(gain / df['delivery_time_min'].mean(), 1)}). "
        "É um dos poucos fatores diretamente controláveis pela operação.",
        "Definir teto de entregas simultâneas e agrupar pedidos só quando o desvio de rota for pequeno." if gap >= 2.0 else "",
    )


# compara a cidade mais lenta com a mais rapida. so vira oportunidade se a diferenca for clara e >= 2 min
def _city_insight(df: pd.DataFrame, sla: float) -> Insight | None:
    c = city_table(df, sla, min_n=100)
    if len(c) < 3:
        return None
    all_counts = df["city"].value_counts()
    top3 = concentration(all_counts, 3)
    slow, fast = c.sort_values("mean_delivery").iloc[-1], c.sort_values("mean_delivery").iloc[0]
    test = welch_test(df.loc[df["city"] == slow["city"], "delivery_time_min"],
                      df.loc[df["city"] == fast["city"], "delivery_time_min"])
    gap = slow["mean_delivery"] - fast["mean_delivery"]
    sig = bool(test and test["significant"] and gap >= 2.0)
    if sig:
        dist_note = ""
        if pd.notna(slow["distance"]) and pd.notna(fast["distance"]):
            dist_note = (f" Distância média: {fmt_num(slow['distance'])} km em {slow['city']} "
                         f"contra {fmt_num(fast['distance'])} km em {fast['city']}.")
        return Insight(
            "opportunity", f"{slow['city']} é a mais lenta: {fmt_min(slow['mean_delivery'])}, {fmt_num(gap)} min acima de {fast['city']}",
            f"As 3 maiores cidades somam {fmt_pct(top3, 0)} dos pedidos ({fmt_int(len(all_counts))} cidades)." + dist_note
            + " Parte da diferença pode vir de distância e trânsito locais, não só de gestão.",
            f"Abrir diagnóstico local em {slow['city']} (escala, cobertura, restaurantes parceiros).")
    return Insight(
        "finding", "As cidades têm tempos de entrega praticamente iguais",
        f"Entre {fmt_int(len(all_counts))} cidades, a mais lenta ({slow['city']}, {fmt_min(slow['mean_delivery'])}) está só "
        f"{fmt_num(gap)} min acima da mais rápida ({fast['city']}, {fmt_min(fast['mean_delivery'])}), e as 3 maiores somam "
        f"{fmt_pct(top3, 0)} dos pedidos. O problema não é local: ações por cidade teriam pouco retorno.",
        "Tratar a operação como rede única e priorizar as alavancas globais (trânsito, entregas simultâneas).")


# hora com mais e menos atraso (so mostra se a diferenca passar de 8 pontos percentuais)
def _hour_extremes(df: pd.DataFrame, sla: float) -> Insight | None:
    h = hourly_profile(df, sla, min_n=50)
    if len(h) < 6:
        return None
    worst = h.loc[h["late_rate"].idxmax()]
    best = h.loc[h["late_rate"].idxmin()]
    if worst["late_rate"] - best["late_rate"] < 0.08:
        return None
    return Insight(
        "finding", f"A taxa de atraso vai de {fmt_pct(best['late_rate'], 0)} ({int(best['order_hour'])}h) a "
                   f"{fmt_pct(worst['late_rate'], 0)} ({int(worst['order_hour'])}h)",
        f"Quase todo atraso se concentra nas horas de pior desempenho: pedidos das {int(worst['order_hour'])}h atrasam em "
        f"{fmt_pct(worst['late_rate'], 0)} dos casos. Use o mapa de calor para ver quais dias agravam o quadro.",
        f"Planejar escala e prazo prometido por faixa horária, começando pelas {int(worst['order_hour'])}h.",
    )


# monta a lista da pagina, mais o insight de dia da semana no final
def operations_insights(df: pd.DataFrame, sla: float) -> list[Insight]:
    small = too_small(df)
    if small:
        return small
    out = [i for i in (_peak_insight(df, sla), _hour_extremes(df, sla), _multiple_insight(df, sla),
                       _city_insight(df, sla)) if i]
    wd = summarize(df, "weekday", sla, min_n=MIN_GROUP_N)
    if len(wd) >= 5:
        hi, lo = wd.loc[wd["n"].idxmax()], wd.loc[wd["n"].idxmin()]
        ratio = hi["n"] / lo["n"] if lo["n"] else float("nan")
        if ratio >= 1.25:
            out.append(Insight(
                "finding", f"{hi['weekday']} tem {fmt_num(ratio, 1)}x o volume de {lo['weekday']}",
                f"{fmt_int(hi['n'])} pedidos contra {fmt_int(lo['n'])}. Tempo médio de entrega: "
                f"{fmt_min(hi['mean_delivery'])} e {fmt_min(lo['mean_delivery'])}.",
                "Ajustar a escala semanal à curva de demanda."))
    return out
