import streamlit as st

from src.insights.executive import executive_insights
from src.metrics.kpis import compute_kpis, delta
from src.metrics.operations import daily_series
from src.metrics.segments import segment_table
from src.metrics.summary import summarize
from src.ui.components import kpi_row, plot, render_insights, safe_insights, section, show_table
from src.ui.layout import setup_page
from src.utils.formatting import fmt_int, fmt_min, fmt_num, fmt_pct, fmt_signed_pct
from src.utils.labels import TRAFFIC_ORDER, pt, sort_by_order
from src.visuals import charts

# tudo comeca aqui: carrega, aplica filtros e devolve a base filtrada (df) e o SLA
ctx = setup_page("Visão Executiva", "📊")
df, sla = ctx.df_f, ctx.sla

# kpis do recorte atual e, se tiver filtro, da base toda (pra mostrar a variacao)
k = compute_kpis(df, sla)
base = compute_kpis(ctx.df, sla) if ctx.filtered else None


def d(key, inverse=False):
    if base is None:
        return None
    v = delta(k[key], base[key])
    return None if v is None else fmt_signed_pct(v)


st.caption("Deltas comparam o recorte filtrado com a base completa." if ctx.filtered else
           "Sem filtros ativos: os números abaixo cobrem toda a base tratada.")
# primeira linha de kpis: espera, entrega, preparo e prazo
kpi_row([
    {"label": "Pedidos", "value": fmt_int(k["orders"]), "delta": d("orders")},
    {"label": f"Entregas em até {sla} min", "value": fmt_pct(k["on_time_rate"]),
     "delta": d("on_time_rate"), "help": "Só a etapa de entrega conta para o prazo."},
    {"label": "Tempo de entrega (média)", "value": fmt_min(k["avg_delivery"]), "delta": d("avg_delivery"), "inverse": True},
    {"label": "Espera total (preparo + entrega)", "value": fmt_min(k["avg_total"]), "delta": d("avg_total"), "inverse": True,
     "help": "O que o cliente de fato espera, do pedido até a porta."},
])
kpi_row([
    {"label": "Entrega: 9 em 10 até", "value": fmt_min(k["p90_delivery"], 0), "help": "Percentil 90 do tempo de entrega."},
    {"label": "Nota média", "value": fmt_num(k["avg_rating"], 2), "delta": d("avg_rating")},
    {"label": "Pedidos por dia", "value": fmt_int(k["orders_per_day"]), "help": f"{k['days']} dias com pedidos."},
    {"label": "Distância média", "value": f"{fmt_num(k['avg_distance'])} km",
     "help": "Linha reta entre restaurante e cliente; só pedidos com localização válida."},
])

st.divider()
# insights da pagina (alavancas, tendencia...), calculados em cima dos filtros
render_insights(safe_insights(executive_insights, df, sla))
st.divider()

# grafico do dia a dia: barras de pedidos e linha do tempo medio
section("Evolução diária", "Barras: pedidos. Linha: tempo médio de entrega. Tracejado: prazo (SLA).")
daily = daily_series(df, sla)
plot(charts.dual_axis(
    daily["order_date"].dt.strftime("%d/%m"), daily["n"], daily["mean_delivery"],
    "Pedidos", "Tempo médio de entrega (min)", hline=sla, hline_label="Prazo (SLA)",
))

c1, c2 = st.columns(2)
with c1:
    # dois graficos lado a lado: composicao da espera por transito e histograma
    section("De onde vem a espera", "Preparo + entrega, por nível de trânsito.")
    t = sort_by_order(summarize(df, "traffic", sla), "traffic", TRAFFIC_ORDER)
    plot(charts.stacked_composition([pt("traffic", x) for x in t["traffic"]], t["mean_prep"], t["mean_delivery"]))
with c2:
    section("Distribuição do tempo de entrega", "Cada barra agrupa pedidos com tempos próximos.")
    plot(charts.histogram(df["delivery_time_min"], vline=sla, vline_label="SLA"))

# tabela de segmentos: ordena pelo ganho potencial, so mostra quem e pior que o resto
section("Onde estão os minutos perdidos",
        "Cada linha compara um segmento com o restante da base. 'Ganho potencial' = quanto a média geral cairia "
        "se o segmento operasse como o restante.")
seg = segment_table(df, sla=sla)
if seg.empty:
    st.info("Recorte pequeno demais para comparar segmentos.")
else:
    view = seg[seg["diff"] > 0].sort_values("potential_gain", ascending=False).head(10)
    show_table(
        view[["segment", "share", "mean_delivery", "rest_mean", "diff", "late_share", "potential_gain"]].assign(
            share=lambda x: x["share"] * 100, late_share=lambda x: x["late_share"] * 100,
        ).rename(columns={
            "segment": "Segmento", "share": "% dos pedidos", "mean_delivery": "Entrega (min)", "rest_mean": "Restante (min)",
            "diff": "Diferença (min)", "late_share": "% dos atrasos", "potential_gain": "Ganho potencial (min)"}),
        column_config={
            "% dos pedidos": st.column_config.NumberColumn(format="%.1f"),
            "% dos atrasos": st.column_config.NumberColumn(format="%.1f"),
            "Entrega (min)": st.column_config.NumberColumn(format="%.1f"),
            "Restante (min)": st.column_config.NumberColumn(format="%.1f"),
            "Diferença (min)": st.column_config.NumberColumn(format="%.1f"),
            "Ganho potencial (min)": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    st.caption("Como ler: segmentos que são a maioria dos pedidos (acima de 50%) e o período do dia (que coincide com trânsito "
               "pesado) descrevem a operação, mas não indicam onde agir. Os insights acima os desconsideram como alavanca.")
