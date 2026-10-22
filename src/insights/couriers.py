"""Insights da página Entregadores."""
from __future__ import annotations

import pandas as pd

from src.config import MIN_EFFECT_MIN, MIN_ORDERS_COURIER
from src.insights.base import Insight, too_small
from src.metrics.couriers import load_concentration, opportunity
from src.metrics.models import DeliveryModel
from src.metrics.stats import spearman
from src.utils.formatting import fmt_int, fmt_num, fmt_pct, fmt_signed

# chance de passar de 3 erros padrao so por acaso (uns 0,135% de cada lado)
CHANCE_ONE_SIDE = 0.00135  # P(Z > 3)


# diferenca de excesso (em minutos) entre os 10% mais ocupados e o resto
def _busy_gap(table) -> float:
    """Excesso médio (min vs esperado) dos 10% entregadores mais ocupados menos o dos demais."""
    cut = table["orders"].quantile(0.9)
    top, rest = table[table["orders"] >= cut], table[table["orders"] < cut]
    return float(top["excess"].mean() - rest["excess"].mean()) if len(top) and len(rest) else float("nan")


# insights da pagina de entregadores. sem modelo ou sem dado, devolve aviso em vez de quebrar
def courier_insights(df: pd.DataFrame, table: pd.DataFrame, model: DeliveryModel | None,
                     min_orders: int = MIN_ORDERS_COURIER) -> list[Insight]:
    """`df` precisa ter `excess_min` (with_expected); `table` vem de courier_table."""
    small = too_small(df)
    if small:
        return small
    out: list[Insight] = []
    if table is None or table.empty:
        return [Insight("info", "Nenhum entregador com pedidos suficientes",
                        f"Reduza o mínimo de pedidos (hoje {min_orders}) ou amplie os filtros.")]

    if model is None or table["excess"].isna().all():
        out.append(Insight("info", "Ranking sem ajuste por contexto",
                           "Não há dados suficientes para estimar o tempo esperado; o ranking usa o tempo bruto e "
                           "penaliza quem pega rotas longas ou trânsito pesado."))
        return out

    n = len(table)
    slow = table[table["status"] == "Mais lento que o esperado"]
    fast = table[table["status"] == "Mais rápido que o esperado"]
    p10, p90 = table["excess"].quantile(0.1), table["excess"].quantile(0.9)
    # quantos foram apontados x quantos o acaso explicaria (com 720 entregadores, uns 2)
    flagged = len(slow) + len(fast)
    chance = CHANCE_ONE_SIDE * n

    # se quase ninguem foge do esperado, a conclusao e: desempenho individual e homogeneo, nao vale ranking
    if flagged <= max(3, 0.01 * n):
        out.append(Insight(
            "finding", "Desempenho individual é homogêneo: quase ninguém foge do esperado para o contexto",
            f"Entre {fmt_int(n)} entregadores, só {fmt_int(flagged)} diferem de forma clara (mais de 3 erros-padrão e 1 min); "
            f"por puro acaso esperaríamos cerca de {fmt_num(2 * chance, 0)}. Os 10% melhores e os 10% piores ficam entre "
            f"{fmt_signed(p10)} e {fmt_signed(p90)} min do esperado. O 'esperado' já desconta trânsito, clima, período, carga, "
            "idade e condição do veículo: o que sobra é o desempenho próprio de cada pessoa.",
            "Não gastar energia em ranking individual; atuar nos fatores de contexto (carga simultânea, rotas, trânsito).",
        ))
    else:
        opp = opportunity(table, len(df), df["delivery_time_min"].mean())
        worth = opp["pct"] >= 0.01
        out.append(Insight(
            "opportunity" if worth else "finding",
            f"{fmt_int(len(slow))} entregadores ({fmt_pct(len(slow) / n, 1)}) são claramente mais lentos que o esperado"
            + ("" if worth else ", mas o ganho é pequeno"),
            f"Já descontados distância, trânsito × clima, período, carga e veículo, eles ficam acima do esperado (acaso explicaria "
            f"cerca de {fmt_num(chance, 0)}) e fazem {fmt_int(opp['orders'])} pedidos. Se voltassem ao esperado, a média geral cairia "
            f"{fmt_num(opp['mean_gain'], 2)} min ({fmt_pct(opp['pct'], 1)}). No extremo oposto, {fmt_int(len(fast))} são claramente mais "
            "rápidos: bons candidatos a mentores.",
            ("Revisar a operação dos mais lentos (treinamento, rota, veículo) e estudar as práticas dos mais rápidos." if worth else
             "Acompanhar esses casos, mas priorizar alavancas de contexto: o retorno de mexer em indivíduos é baixo."),
        ))

    # carga de trabalho: quem faz mais pedido fica mais lento? so alerta se o efeito passar de 1 minuto
    conc = load_concentration(df, 0.10)
    rho = spearman(table["orders"], table["excess"])
    gap = _busy_gap(table)
    if pd.notna(rho) and rho >= 0.2 and pd.notna(gap) and abs(gap) < MIN_EFFECT_MIN:
        out.append(Insight(
            "info", f"Mais pedidos anda junto com um leve atraso, mas o efeito é pequeno ({fmt_num(gap)} min)",
            f"Há correlação (Spearman {fmt_num(rho, 2)}), mas os 10% mais ocupados, que fazem {fmt_pct(conc, 0)} dos pedidos, ficam em média "
            f"só {fmt_num(gap)} min mais lentos que os demais (contra o esperado). Não justifica mexer na distribuição de volume."))
    elif pd.notna(rho) and rho >= 0.2:
        out.append(Insight(
            "risk", f"Quem faz mais pedidos tende a ficar mais lento que o esperado (Spearman {fmt_num(rho, 2)})",
            f"Os 10% mais ocupados fazem {fmt_pct(conc, 0)} dos pedidos e, em média, ficam {fmt_num(_busy_gap(table))} min mais lentos (contra o esperado) que os demais. "
            "O modelo já considera trânsito, clima, período e carga simultânea, então a associação pode refletir fadiga ou algo não medido (rotas, turnos). Verifique antes de agir.",
            "Testar, em piloto, redistribuir volume dos mais ocupados e comparar o desempenho."))
    elif pd.notna(rho) and rho <= -0.2:
        out.append(Insight(
            "finding", f"Quem faz mais pedidos tende a ser mais rápido que o esperado (Spearman {fmt_num(rho, 2)})",
            f"Os 10% mais ocupados fazem {fmt_pct(conc, 0)} dos pedidos; experiência parece compensar o volume."))
    else:
        out.append(Insight(
            "finding", f"Volume de trabalho não explica desempenho: os 10% mais ocupados fazem {fmt_pct(conc, 0)} dos pedidos",
            "Não há relação clara entre quantidade de pedidos e desempenho relativo ao esperado."))

    # abaixo: efeitos isolados do modelo (idade, veiculo, condicao do veiculo)
    t = model.table
    # idade: mostra o efeito, mas avisa que nunca pode virar criterio de contratacao (discriminacao)
    age = t[t["term"] == "courier_age"]
    if not age.empty:
        a = age.iloc[0]
        clear = (a["ci_low"] > 0 or a["ci_high"] < 0) and abs(a["effect"]) >= 0.5
        out.append(Insight(
            "finding" if clear else "info",
            (f"Idade: cada 10 anos a mais está associado a {fmt_signed(a['effect'])} min na entrega, com o resto igual" if clear
             else "Idade do entregador não explica o tempo de entrega"),
            f"Efeito isolado de {fmt_signed(a['effect'])} min (IC95%: {fmt_num(a['ci_low'])} a {fmt_num(a['ci_high'])}). "
            + ("Pode refletir veículo, jornada ou treino que acompanham a idade." if clear else ""),
            "Investigar a causa (carga, veículo, treinamento) e nunca usar idade como critério individual de contratação ou alocação."
            if clear else "",
        ))
    # tipo de veiculo: so comenta se alguma diferenca for clara
    veh = t[t["group"] == "Veículo"]
    if not veh.empty:
        clear = veh[(veh["ci_low"] > 0.5) | (veh["ci_high"] < -0.5)]
        if clear.empty:
            out.append(Insight("info", "O tipo de veículo não muda o tempo de entrega de forma clara",
                               "Após isolar distância e contexto, nenhum veículo difere do de referência com segurança."))
        else:
            v = clear.loc[clear["effect"].abs().idxmax()]
            out.append(Insight("finding",
                               f"{v['label'].replace('Veículo: ', '')} difere do veículo de referência em {fmt_signed(v['effect'])} min",
                               f"IC95%: {fmt_num(v['ci_low'])} a {fmt_num(v['ci_high'])} min, com {fmt_int(v['n'])} pedidos.",
                               "Direcionar rotas longas para os veículos mais eficientes."))
    # condicao do veiculo: a escala 0-3 nao e documentada, entao pede confirmacao do sentido
    vc = t[t["term"] == "vehicle_condition"]
    if not vc.empty:
        v = vc.iloc[0]
        if v["ci_low"] > 0 or v["ci_high"] < 0:
            out.append(Insight(
                "finding", f"Condição do veículo: +1 nível está associado a {fmt_signed(v['effect'])} min na entrega",
                f"IC95%: {fmt_num(v['ci_low'])} a {fmt_num(v['ci_high'])}. A base não documenta o sentido da escala (0–3); "
                "confirme com a fonte antes de agir.",
                "Se a escala indicar que nível maior é melhor estado, priorizar a renovação dos veículos de nível baixo."))

    # aviso final: com poucos pedidos por entregador o resultado oscila por acaso
    median_orders = table["orders"].median()
    if median_orders < 3 * min_orders:
        out.append(Insight("info", "Cuidado com amostras pequenas por entregador",
                           f"A mediana é de {fmt_int(median_orders)} pedidos por entregador. Com poucos pedidos, o desempenho "
                           "oscila ao acaso; por isso a classificação exige diferença de mais de 3 erros-padrão E de pelo menos 1 minuto."))
    return out
