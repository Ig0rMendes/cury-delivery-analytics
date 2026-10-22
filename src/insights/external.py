"""Insights da página Fatores Externos."""
from __future__ import annotations

import pandas as pd

from src.config import MIN_GROUP_N
from src.insights.base import Insight, too_small
from src.metrics.external import festival_effect, traffic_table, weather_traffic_matrix
from src.metrics.models import DeliveryModel
from src.metrics.stats import welch_test
from src.utils.formatting import fmt_int, fmt_min, fmt_num, fmt_pct, fmt_signed, fmt_signed_pct
from src.utils.labels import pt


# custo do transito pior vs o mais leve, com IC e quanto dos minutos totais e transito
def _traffic_insight(df: pd.DataFrame, sla: float) -> Insight | None:
    t = traffic_table(df, sla)
    t = t[t["n"] >= MIN_GROUP_N]
    if len(t) < 2:
        return None
    base, worst = t.iloc[0], t.iloc[-1]
    test = welch_test(df.loc[df["traffic"] == worst["traffic"], "delivery_time_min"],
                      df.loc[df["traffic"] == base["traffic"], "delivery_time_min"])
    heavy = t[t["traffic"].isin(["High", "Jam"])]
    exposure = heavy["n"].sum() / len(df)
    lost = (t["extra_vs_base"] * t["n"]).clip(lower=0).sum()
    total_min = df["delivery_time_min"].sum()
    ci = f" (IC95%: {fmt_num(test['ci_low'])} a {fmt_num(test['ci_high'])} min)" if test else ""
    return Insight(
        "finding",
        f"Trânsito {pt('traffic', worst['traffic']).lower()} adiciona {fmt_signed(worst['extra_vs_base'])} min "
        f"({fmt_signed_pct(worst['extra_pct'], 0)}) à entrega",
        f"Média de {fmt_min(worst['mean_delivery'])} contra {fmt_min(base['mean_delivery'])} em trânsito "
        f"{pt('traffic', base['traffic']).lower()}{ci}. {fmt_pct(exposure, 0)} dos pedidos já são feitos em trânsito alto ou "
        f"congestionado, e o trânsito inteiro responde por {fmt_pct(lost / total_min, 0)} de todos os minutos de entrega.",
        "Incluir o trânsito previsto na promessa de prazo e na distribuição de pedidos por entregador.",
    )


# o transito pesa igual em todo clima? (nos dados nao: +14 min na neblina, +2 no sol)
def _traffic_by_weather(df: pd.DataFrame) -> Insight | None:
    """O custo do trânsito é o mesmo em qualquer clima? Se não, a média esconde o essencial."""
    means, counts = weather_traffic_matrix(df)
    if means.shape[0] < 2 or means.shape[1] < 2:
        return None
    lo_t, hi_t = means.columns[0], means.columns[-1]
    cost = (means[hi_t] - means[lo_t]).dropna()
    if len(cost) < 2:
        return None
    worst_w, best_w = cost.idxmax(), cost.idxmin()
    spread = cost.max() - cost.min()
    if spread < 5.0:
        return Insight(
            "info", f"O custo do trânsito {pt('traffic', hi_t).lower()} é parecido em todos os climas",
            f"Varia de {fmt_signed(cost.min())} a {fmt_signed(cost.max())} min entre os climas, então um prazo único por nível de trânsito é razoável.")
    return Insight(
        "finding",
        f"O trânsito só pesa de verdade em certos climas: {fmt_signed(cost.max())} min com {pt('weather', worst_w).lower()} "
        f"contra {fmt_signed(cost.min())} min com {pt('weather', best_w).lower()}",
        f"Custo do trânsito {pt('traffic', hi_t).lower()} em relação ao {pt('traffic', lo_t).lower()}, por clima (tempo médio de entrega). "
        "Por isso as médias isoladas de trânsito e de clima subestimam a combinação ruim e superestimam as demais.",
        "Definir o prazo prometido pela COMBINAÇÃO clima × trânsito, e não por cada fator separadamente.",
    )


# insights que vem do modelo (efeito isolado, mantendo o resto igual)
def _isolated_insights(df: pd.DataFrame, model: DeliveryModel | None) -> list[Insight]:
    if model is None or model.table.empty:
        return []
    t = model.table
    out: list[Insight] = []

    # congestionamento x distancia: compara com a faixa real de distancia (5o a 95o percentil)
    jam = t[t["term"] == "traffic=Jam"]
    dist = t[t["term"] == "distance_km"]
    if not jam.empty and not dist.empty:
        j, d = jam.iloc[0], dist.iloc[0]
        d5 = df["distance_km"].quantile(0.05)
        d95 = df["distance_km"].quantile(0.95)
        range_effect = d["effect"] / 5.0 * (d95 - d5) if pd.notna(d95) else float("nan")
        if pd.notna(range_effect) and j["effect"] > 0:
            ratio = j["effect"] / range_effect if range_effect > 0 else float("inf")
            extra = ""
            if range_effect > 0:
                km = j["effect"] / (d["effect"] / 5.0)
                if km <= d95:
                    extra = f" Em distância, o congestionamento equivale a {fmt_num(km)} km a mais."
            out.append(Insight(
                "finding",
                f"Isolando os demais fatores, o congestionamento soma {fmt_signed(j['effect'])} min; ir do pedido mais perto ao mais longe soma {fmt_signed(range_effect)} min",
                f"Mantendo clima, carga e veículo iguais: congestionamento {fmt_signed(j['effect'])} min "
                f"(IC95%: {fmt_num(j['ci_low'])} a {fmt_num(j['ci_high'])}); percorrer de {fmt_num(d5)} a {fmt_num(d95)} km (do 5º ao 95º percentil) "
                f"soma {fmt_signed(range_effect)} min. "
                + (f"O trânsito pesa {fmt_num(ratio, 1)}x mais que toda a variação de distância." if range_effect > 0 and ratio >= 1.5 and ratio < 100 else
                   f"A variação de distância pesa {fmt_num(1 / ratio, 1)}x mais que o congestionamento." if range_effect > 0 and ratio < 1 / 1.5 else
                   "Trânsito e distância pesam de forma parecida." if range_effect > 0 else
                   "A distância pesa pouco frente ao trânsito.") + extra,
                ("Usar o trânsito, e não a distância, como critério principal de prazo e de alocação de pedidos."
                 if (range_effect <= 0 or ratio >= 1.5) else
                 "Considerar distância e trânsito juntos na promessa de prazo e na alocação de pedidos."),
            ))

    # clima mais custoso, so se o IC nao incluir zero
    w = t[t["group"] == "Clima"].sort_values("effect", ascending=False)
    if not w.empty:
        top = w.iloc[0]
        clear = top["ci_low"] > 0
        out.append(Insight(
            "finding" if clear else "info",
            (f"{top['label'].replace('Clima: ', '')} é o clima mais custoso: {fmt_signed(top['effect'])} min por entrega, em média"
             if clear else "Nenhum clima tem efeito claro após isolar trânsito e distância"),
            f"Em relação à referência ({top['reference']}), com IC95% de {fmt_num(top['ci_low'])} a {fmt_num(top['ci_high'])} min "
            f"({fmt_int(top['n'])} pedidos nesse clima). É uma média entre todos os níveis de trânsito: veja o cruzamento clima × trânsito.",
            "Ativar prazo dinâmico por clima apenas para os climas com efeito claro." if clear else "",
        ))

    # fator categorico de maior peso = efeito * % dos pedidos expostos (efeito grande em grupo minusculo nao move a media)
    # peso real = efeito x parcela de pedidos expostos (efeito grande em grupo minúsculo não move a média)
    cat = t[t["group"] != "Contínuo"].copy()
    cat["share"] = cat["n"] / model.n
    cat["contribution"] = cat["effect"] * cat["share"]
    clear_up = cat[cat["ci_low"] > 0]
    if not clear_up.empty:
        big = clear_up.loc[clear_up["contribution"].idxmax()]
        out.append(Insight(
            "opportunity",
            f"Fator categórico de maior peso: {big['label']} (+{fmt_num(big['contribution'])} min na média geral)",
            f"Efeito isolado de {fmt_signed(big['effect'])} min em {fmt_pct(big['share'], 1)} dos pedidos. Entre {len(t)} termos "
            f"testados (R² = {fmt_num(model.r2, 2)}, {fmt_int(model.n)} pedidos), é o que mais empurra a média para cima. "
            "O modelo mede associação, não causalidade.",
        ))
        rare = clear_up[(clear_up["share"] < 0.03) & (clear_up["effect"] >= 5.0) & (clear_up["term"] != big["term"])]
        if not rare.empty:
            r = rare.loc[rare["effect"].idxmax()]
            out.append(Insight(
                "info", f"Efeito grande, mas raro: {r['label']} ({fmt_signed(r['effect'])} min em {fmt_pct(r['share'], 1)} dos pedidos)",
                f"São {fmt_int(r['n'])} pedidos: dói para quem recebe, mas move pouco a média geral. Trate como caso específico (cobertura, "
                "prazo diferenciado), não como prioridade da operação."))
    return out


# melhor e pior combinacao clima + transito
def _interaction_insight(df: pd.DataFrame) -> Insight | None:
    means, counts = weather_traffic_matrix(df)
    if means.shape[0] < 2 or means.shape[1] < 2 or means.isna().all().all():
        return None
    stacked = means.stack().dropna()
    if stacked.empty:
        return None
    (w_worst, t_worst), worst = stacked.idxmax(), stacked.max()
    (w_best, t_best), best = stacked.idxmin(), stacked.min()
    n_worst = int(counts.loc[w_worst, t_worst])
    return Insight(
        "finding",
        f"Pior combinação: {pt('weather', w_worst).lower()} + trânsito {pt('traffic', t_worst).lower()} ({fmt_min(worst)})",
        f"A melhor combinação ({pt('weather', w_best).lower()} + trânsito {pt('traffic', t_best).lower()}) leva "
        f"{fmt_min(best)}, uma diferença de {fmt_num(worst - best)} min. A pior tem {fmt_int(n_worst)} pedidos na base filtrada.",
    )


# festival: mostra o efeito bruto e o isolado, que sao bem diferentes porque festival traz transito junto
def _festival_insight(df: pd.DataFrame, model: DeliveryModel | None = None) -> Insight | None:
    f = festival_effect(df)
    if f is None:
        return Insight("info", "Dados insuficientes para avaliar festivais",
                       "Há poucos pedidos em dias de festival (ou sem a informação) neste recorte.")
    known = df["festival"].notna().sum()
    share = f["n_a"] / known if known else float("nan")
    if f["significant"] and abs(f["diff"]) >= 0.5:
        iso = ""
        if model is not None and not model.table.empty:
            row = model.table[model.table["term"] == "festival=Yes"]
            if not row.empty:
                r0 = row.iloc[0]
                iso = (f" Mantendo trânsito, clima e demais fatores iguais, o efeito do festival é de {fmt_signed(r0['effect'])} min "
                       f"(IC95%: {fmt_num(r0['ci_low'])} a {fmt_num(r0['ci_high'])}): a diferença para o valor bruto vem de trânsito e clima "
                       "que acompanham esses dias.")
        return Insight(
            "risk" if f["diff"] > 0 else "finding",
            f"Dias de festival {'atrasam' if f['diff'] > 0 else 'aceleram'} a entrega em {fmt_num(abs(f['diff']))} min",
            f"{fmt_min(f['mean_yes'])} em festival contra {fmt_min(f['mean_no'])} em dias normais "
            f"(IC95% da diferença: {fmt_num(f['ci_low'])} a {fmt_num(f['ci_high'])} min). Atinge {fmt_pct(share, 1)} dos pedidos "
            f"({fmt_int(f['n_a'])}): pouco na média geral, mas é a maior penalidade individual da base." + iso,
            "Calendário de festivais entra no planejamento de escala e na promessa de prazo." if f["diff"] > 0 else "",
        )
    return Insight(
        "info", "Festivais não mostram efeito mensurável no tempo de entrega",
        f"Diferença de {fmt_signed(f['diff'])} min, IC95% de {fmt_num(f['ci_low'])} a {fmt_num(f['ci_high'])} "
        f"({fmt_int(f['n_a'])} pedidos em festival). Ausência de evidência aqui não é evidência de ausência: a amostra pode ser pequena.",
    )


# junta os insights da pagina, festival primeiro porque e a maior penalidade
def external_insights(df: pd.DataFrame, sla: float, model: DeliveryModel | None) -> list[Insight]:
    small = too_small(df)
    if small:
        return small
    out = [_festival_insight(df, model), _traffic_insight(df, sla), _traffic_by_weather(df)]
    out += _isolated_insights(df, model)
    out += [_interaction_insight(df)]
    return [i for i in out if i]
