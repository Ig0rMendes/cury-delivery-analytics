"""Insights da página Experiência do Cliente."""
from __future__ import annotations

import pandas as pd

from src.config import MIN_GROUP_N
from src.insights.base import Insight, too_small
from src.metrics.experience import dimension_spread, rating_granularity
from src.metrics.stats import spearman, welch_test
from src.utils.formatting import fmt_int, fmt_num, fmt_pct, fmt_signed
from src.utils.labels import value_label


# quanto atrasar custa em nota (diferenca de nota entre atrasado e no prazo)
def _delay_cost(df: pd.DataFrame, sla: float, is_attr: bool) -> list[Insight]:
    # atrasado = passou do SLA
    late_mask = df["delivery_time_min"] > sla
    late, ok = df.loc[late_mask, "rating"], df.loc[~late_mask, "rating"]
    test = welch_test(late, ok)
    out: list[Insight] = []
    if not test:
        return out
    if test["significant"] and abs(test["diff"]) >= 0.02:
        # impacto na nota media geral = % de atrasos * diferenca de nota
        overall = late_mask.mean() * test["diff"]
        low = df["rating"] < 4.0
        low_late = (low & late_mask).sum() / low.sum() if low.sum() else float("nan")
        txt = (f"Pedidos acima de {sla:.0f} min têm nota {fmt_num(late.mean(), 2)} contra {fmt_num(ok.mean(), 2)} no prazo "
               f"({fmt_signed(test['diff'], 2)}; IC95%: {fmt_num(test['ci_low'], 2)} a {fmt_num(test['ci_high'], 2)}). "
               f"Como {fmt_pct(late_mask.mean(), 0)} das entregas atrasam, os atrasos custam {fmt_num(abs(overall), 2)} ponto na nota "
               "média geral.")
        if pd.notna(low_late) and low.sum() >= MIN_GROUP_N:
            if low_late >= 1.0:
                txt += (f" Todas as notas abaixo de 4,0 vêm de entregas atrasadas, que são {fmt_pct(late_mask.mean(), 0)} do total "
                        "(padrão muito regular, típico de base pública).")
            else:
                low_late_txt = "Mais de 99%" if low_late >= 0.995 else fmt_pct(low_late, 0)
                txt += (f" {low_late_txt} das notas abaixo de 4,0 vêm de entregas atrasadas, que são "
                        f"{fmt_pct(late_mask.mean(), 0)} do total.")
        if is_attr:
            txt += " Como a nota é do entregador, isso indica que entregadores mais bem avaliados também entregam mais rápido."
        out.append(Insight(
            "finding" if is_attr else "opportunity",
            ("Atrasar custa nota" if not is_attr else "Entrega rápida anda junto com entregador bem avaliado")
            + f": {fmt_signed(test['diff'], 2)} ponto",
            txt, "Tratar o cumprimento do prazo como alavanca direta de satisfação." if not is_attr else ""))
    else:
        out.append(Insight(
            "info", "Atrasos não derrubam a nota de forma mensurável",
            f"Nota {fmt_num(late.mean(), 2)} (atrasados) contra {fmt_num(ok.mean(), 2)} (no prazo), diferença de "
            f"{fmt_signed(test['diff'], 2)} (IC95%: {fmt_num(test['ci_low'], 2)} a {fmt_num(test['ci_high'], 2)}). "
            "A nota, nesta base, não é um bom termômetro de atraso: acompanhe tempo e satisfação separadamente."))
    return out


# monta os insights da pagina de experiencia
def experience_insights(df: pd.DataFrame, sla: float) -> list[Insight]:
    small = too_small(df)
    if small:
        return small
    out: list[Insight] = []
    # primeiro checa se a nota e por entrega ou do entregador, e isso muda como ler o resto
    gran = rating_granularity(df)
    is_attr = gran["is_courier_attribute"]
    r = df["rating"]
    low = (r < 4.0).mean()
    top = (r >= 4.5).mean()

    # se a nota for do entregador, avisa. senao confirma que e por entrega
    if is_attr:
        out.append(Insight(
            "info", f"A nota parece ser do ENTREGADOR, não de cada entrega ({fmt_pct(gran['constant_share'], 0)} têm nota única)",
            "Quando a nota é a média histórica do entregador, comparações por pedido mostram o perfil de quem atende cada "
            "situação, e não a reação do cliente àquela entrega. Leia as demais conclusões desta página com essa ressalva.",
            "Para medir satisfação de verdade, coletar a avaliação por pedido."))
    elif gran["couriers"] > 0:
        out.append(Insight(
            "info", "A nota varia entre pedidos do mesmo entregador: é avaliação de cada entrega",
            f"{'Nenhum entregador com 2+ pedidos tem nota única' if gran['constant_share'] < 0.005 else fmt_pct(gran['constant_share'], 0) + ' dos entregadores com 2+ pedidos têm nota única'}. Isso permite ligar a nota "
            "à experiência de cada entrega (tempo, trânsito, clima), e não só ao perfil do entregador."))

    out.append(Insight(
        "finding", f"Nota média {fmt_num(r.mean(), 2)}: {fmt_pct(top, 0)} dos pedidos com 4,5 ou mais e {fmt_pct(low, 0)} abaixo de 4,0",
        "O patamar de partida é alto. O que interessa operacionalmente é a cauda abaixo de 4,0, onde está o risco de perda de cliente."))

    out += _delay_cost(df, sla, is_attr)

    # correlacao entre tempo de entrega e nota
    rho = spearman(df["delivery_time_min"], df["rating"])
    if pd.notna(rho):
        out.append(Insight("finding" if abs(rho) >= 0.1 else "info",
                           f"Correlação entre tempo de entrega e nota: {fmt_num(rho, 2)} (Spearman)",
                           "Valores perto de zero indicam que o tempo, sozinho, explica pouco da nota."
                           if abs(rho) < 0.1 else "Quanto mais demorada a entrega, menor tende a ser a nota; é a relação mais forte desta página."))

    # dimensões (a faixa de tempo fica de fora: é o próprio atraso, não uma causa independente)
    # dimensao que mais separa a nota (fora o tempo)
    spread = dimension_spread(df, min_n=MIN_GROUP_N)
    if not spread.empty:
        sig = spread[spread["significant"] & (spread["spread"] >= 0.05)]
        if not sig.empty:
            s = sig.iloc[0]
            out.append(Insight(
                "finding", f"Fora o tempo, a maior diferença de nota está em {s['dimension'].lower()} ({fmt_num(s['spread'], 2)} ponto)",
                f"{value_label(s['column'], s['best'])} tem a melhor nota ({fmt_num(s['best_mean'], 2)}) e "
                f"{value_label(s['column'], s['worst'])} a pior ({fmt_num(s['worst_mean'], 2)}). "
                f"Foram comparadas {len(spread)} dimensões; esta é a de maior amplitude com diferença estatisticamente clara. "
                "Parte disso pode ser o próprio efeito do tempo (ex.: trânsito pesado atrasa e, por isso, derruba a nota).",
                "Priorizar melhorias onde a nota é menor, começando por essa dimensão."))
        else:
            out.append(Insight("info", "Fora o tempo de entrega, a nota é estável entre as dimensões analisadas",
                               f"Nenhuma das {len(spread)} dimensões separa a nota de forma clara e relevante. "
                               "Reforça que o tempo de entrega é o que mais importa para a satisfação nesta base."))

    # concentração da nota baixa
    # entregadores com nota media abaixo de 4,0
    by_c = df.groupby("courier_id").agg(rating=("rating", "mean"), n=("order_id", "size"))
    weak = by_c[by_c["rating"] < 4.0]
    if len(by_c) >= 30 and len(weak) > 0:
        out.append(Insight(
            "opportunity", f"{fmt_int(len(weak))} entregadores ({fmt_pct(len(weak) / len(by_c), 0)}) têm nota média abaixo de 4,0",
            f"Eles respondem por {fmt_pct(weak['n'].sum() / len(df), 0)} dos pedidos. Atuar em um grupo pequeno e identificável "
            "é mais barato do que ações gerais.",
            "Acompanhamento individual (feedback, treinamento) e revisão de alocação desse grupo."))
    return out
