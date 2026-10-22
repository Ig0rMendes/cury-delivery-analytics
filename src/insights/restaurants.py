"""Insights da página Restaurantes."""
from __future__ import annotations

import pandas as pd

from src.config import MIN_GROUP_N, MIN_ORDERS_RESTAURANT
from src.insights.base import Insight, too_small
from src.metrics.restaurants import prep_by, prep_granularity, prep_granularity_text, top_share, with_restaurant
from src.metrics.stats import spearman, welch_test
from src.utils.formatting import fmt_int, fmt_min, fmt_num, fmt_pct
from src.utils.labels import pt


# insights da pagina de restaurantes
def restaurant_insights(df: pd.DataFrame, table: pd.DataFrame, sla: float,
                        min_orders: int = MIN_ORDERS_RESTAURANT) -> list[Insight]:
    small = too_small(df)
    if small:
        return small
    d = with_restaurant(df)
    out: list[Insight] = []
    # primeiro avisa que restaurante e proxy e quantos pedidos tem esse id
    coverage = len(d) / len(df)
    out.append(Insight(
        "info", f"Restaurantes identificados por proxy em {fmt_pct(coverage, 0)} dos pedidos",
        "A base não traz ID de restaurante: ele é aproximado por cidade + coordenada. Pedidos com localização inválida "
        "(coordenadas zeradas ou fora da Índia) ficam fora desta página, mas contam nas demais. Se dois restaurantes "
        "compartilham o mesmo ponto, aparecem como um só.",
    ))
    if len(d) < 100:
        return out

    # se o preparo tem so uns poucos valores, avisa que e limite da base
    gran = prep_granularity(d)
    if gran["coarse"]:
        out.append(Insight(
            "info", f"Limite da base: o preparo só aparece em {gran['distinct']} valores ({prep_granularity_text(gran)})",
            "O registro de horário da fonte não tem resolução de minutos, então diferenças entre restaurantes ficam "
            "achatadas. Resultados como 'preparo uniforme na rede' refletem essa resolução e não devem ser lidos como "
            "prova de que as cozinhas são iguais.",
            "Se o objetivo é gerir a cozinha, passar a registrar horários de preparo em minutos exatos."))

    # concentração
    # concentracao: poucos restaurantes dominam ou a demanda e espalhada?
    top20 = top_share(d, 0.2)
    n_rest = d["restaurant_id"].nunique()
    if top20 >= 0.5:
        out.append(Insight("risk", f"20% dos restaurantes concentram {fmt_pct(top20, 0)} dos pedidos",
                           f"Entre {fmt_int(n_rest)} restaurantes, a demanda é dependente de poucos parceiros.",
                           "Proteger o relacionamento com os grandes e abrir espaço para novos parceiros."))
    else:
        out.append(Insight("finding", f"Demanda pulverizada: 20% dos restaurantes fazem {fmt_pct(top20, 0)} dos pedidos",
                           f"São {fmt_int(n_rest)} restaurantes; uma distribuição uniforme daria 20%. Não há dependência "
                           "relevante de poucos parceiros, mas também não há 'grandes contas' para negociar prazo.",
                           "Padronizar metas de preparo para toda a rede, em vez de tratar por exceção."))

    # preparo
    # quanto o preparo pesa na espera total
    prep = d["prep_time_min"]
    share = prep.mean() / d["total_time_min"].mean()
    out.append(Insight(
        "finding", f"Preparo médio de {fmt_min(prep.mean())}: {fmt_pct(share, 0)} da espera total do cliente",
        f"Mediana de {fmt_min(prep.median())}; 9 em 10 pedidos levam até {fmt_min(prep.quantile(0.9), 0)}. "
        "Esta etapa não aparece em métricas de entrega, mas pesa na experiência."))

    # restaurantes com preparo lento. se o ganho de corrigir e minusculo, diz que o preparo e uniforme
    if table is not None and not table.empty:
        slow = table[table["slow_prep"]]
        spread = table["mean_prep"].quantile(0.9) - table["mean_prep"].quantile(0.1)
        gain = (slow["prep_vs_avg"] * slow["orders"]).sum() / len(d) if len(slow) else 0.0
        if len(slow) > 0 and gain < 0.05:
            out.append(Insight(
                "finding", "Poucos restaurantes preparam mais devagar, e o ganho de corrigi-los é irrelevante",
                f"{fmt_int(len(slow))} {'restaurante fica' if len(slow) == 1 else 'restaurantes ficam'} claramente acima da média; mesmo trazendo "
                f"{'ele' if len(slow) == 1 else 'eles'} para a média, o preparo geral cairia só "
                f"{fmt_num(gain, 2)} min. O preparo é, na prática, uniforme na rede.",
                "Não abrir frentes por restaurante; se quiser reduzir a espera, mude o padrão da rede inteira."))
        elif len(slow) > 0:
            out.append(Insight(
                "opportunity",
                f"{fmt_int(len(slow))} restaurantes ({fmt_pct(len(slow) / len(table), 1)}) demoram claramente mais para preparar",
                f"Eles ficam acima da média da rede por mais de 3 erros-padrão e 1 min (mínimo de {min_orders} pedidos cada). Se "
                f"preparassem na média, o preparo médio de toda a base cairia {fmt_num(gain)} min. Os 10% mais rápidos e os 10% "
                f"mais lentos diferem em {fmt_num(spread)} min.",
                "Abrir plano de ação com esses parceiros (fila de cozinha, cardápio, horário de pico)."))
        else:
            out.append(Insight(
                "finding", "Nenhum restaurante é claramente mais lento no preparo",
                f"Com o mínimo de {min_orders} pedidos, as diferenças entre restaurantes ficam dentro do ruído estatístico "
                f"(amplitude P10-P90 de {fmt_num(spread)} min). O preparo é um traço da rede, não de parceiros específicos."))

    # tipo de pedido
    # tipo de pedido muda o preparo?
    t = prep_by(d, "order_type", sla)
    t = t[t["n"] >= MIN_GROUP_N]
    if len(t) >= 2:
        hi, lo = t.iloc[0], t.iloc[-1]
        test = welch_test(d.loc[d["order_type"] == hi["order_type"], "prep_time_min"],
                          d.loc[d["order_type"] == lo["order_type"], "prep_time_min"])
        if test and test["significant"] and test["diff"] >= 0.5:
            out.append(Insight(
                "finding", f"{pt('order_type', hi['order_type'])} demora {fmt_num(test['diff'])} min mais para preparar que {pt('order_type', lo['order_type']).lower()}",
                f"{fmt_min(hi['mean_prep'])} contra {fmt_min(lo['mean_prep'])} (IC95% da diferença: {fmt_num(test['ci_low'])} a {fmt_num(test['ci_high'])} min).",
                "Ajustar o prazo prometido por tipo de pedido."))
        else:
            out.append(Insight("info", "O tipo de pedido não altera o preparo de forma relevante",
                               "Não use o tipo de pedido para prometer prazos diferentes."))

    # preparo lento puxa a entrega pra cima ou pra baixo? (nos dados, nada: -0,01)
    rho = spearman(d["prep_time_min"], d["delivery_time_min"])
    if pd.notna(rho) and abs(rho) < 0.1:
        out.append(Insight(
            "finding", "Preparo lento não é compensado nem agravado na entrega",
            f"A correlação entre preparo e entrega é de {fmt_num(rho, 2)}: são etapas independentes. Reduzir um não "
            "resolve o outro; o tempo total é a soma das duas.", "Atacar as duas etapas com metas separadas."))
    return out
