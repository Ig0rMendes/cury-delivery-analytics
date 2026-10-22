import streamlit as st

from src.config import MIN_ORDERS_RESTAURANT
from src.insights.restaurants import restaurant_insights
from src.metrics.restaurants import (pareto, prep_by, prep_granularity, prep_granularity_text, restaurant_table, top_share,
                                     with_restaurant)
from src.ui.components import data_note, kpi_row, plot, render_insights, safe_insights, section, show_table
from src.ui.layout import setup_page
from src.utils.formatting import fmt_int, fmt_min, fmt_pct
from src.utils.labels import pt
from src.visuals import charts, theme

# pagina de restaurantes. lembra: restaurante e proxy (cidade + coordenada)
ctx = setup_page("Restaurantes", "🍽️")
df, sla = ctx.df_f, ctx.sla

st.caption("Restaurante = ID aproximado (cidade + coordenada), pois a base não traz identificador. "
           "Pedidos sem localização válida ficam fora desta página.")

# se o preparo so tem poucos valores, mostra a nota de limite da base logo no topo
gran = prep_granularity(df)
if gran["coarse"]:
    data_note(
        "Nota sobre os dados: o tempo de preparo é registrado em poucos valores",
        f"Na base, o preparo (hora da retirada menos hora do pedido) assume apenas {gran['distinct']} valores: "
        f"{prep_granularity_text(gran)}. Como a fonte não registra minutos exatos, as médias por restaurante variam pouco e o "
        "painel não consegue separar cozinhas rápidas de lentas com precisão. Leia o preparo \"uniforme\" e o ranking abaixo "
        "como **limite de resolução da fonte**, e não como prova de que todas as cozinhas operam igual. Para avaliar a cozinha "
        "com segurança, seria necessário um registro de horário em minutos (ou segundos) por pedido.",
    )

# minimo de pedidos por restaurante
min_orders = st.slider("Mínimo de pedidos por restaurante para entrar no ranking", 5, 100, MIN_ORDERS_RESTAURANT, step=5,
                       key="min_orders_restaurant")

# so pedidos com localisacao valida. se nao sobrar nenhum, para a pagina
d = with_restaurant(df)
if d.empty:
    st.info("Nenhum pedido com localização válida nos filtros atuais.")
    st.stop()

# tabela por restaurante + kpis
table = restaurant_table(df, sla, min_orders)
kpi_row([
    {"label": "Restaurantes (proxy)", "value": fmt_int(d["restaurant_id"].nunique())},
    {"label": "Preparo médio", "value": fmt_min(d["prep_time_min"].mean())},
    {"label": "Preparo: 9 em 10 até", "value": fmt_min(d["prep_time_min"].quantile(0.9), 0)},
    {"label": "20% maiores concentram", "value": fmt_pct(top_share(d, 0.2), 0), "help": "Parcela dos pedidos."},
])

# insights da pagina
render_insights(safe_insights(restaurant_insights, df, table, sla, min_orders))
st.divider()

# pareto de concentracao e histograma do preparo
c1, c2 = st.columns(2)
with c1:
    section("Concentração da demanda")
    par = pareto(d)
    plot(charts.pareto_chart(par))
with c2:
    section("Distribuição do tempo de preparo")
    plot(charts.histogram(d["prep_time_min"], xtitle="Minutos de preparo", color=theme.ACCENT))

c3, c4 = st.columns(2)
with c3:
    section("Preparo por tipo de pedido")
    t = prep_by(d, "order_type", sla)
    plot(charts.bar_simple([pt("order_type", x) for x in t["order_type"]], t["mean_prep"], color=theme.ACCENT,
                           ytitle="Preparo médio (min)", fmt="%{y:.1f}"))
with c4:
    section("Preparo por período do dia")
    t = prep_by(d, "daypart", sla)
    plot(charts.bar_simple(t["daypart"], t["mean_prep"], color=theme.ACCENT, ytitle="Preparo médio (min)", fmt="%{y:.1f}"))

# ranking com 3 formas de ordenar (mais pedidos, preparo mais lento, mais atrasos)
section("Ranking de restaurantes", f"Restaurantes com pelo menos {min_orders} pedidos. 'Preparo lento' = acima da média além do ruído estatístico.")
if table.empty:
    st.info("Nenhum restaurante atinge o mínimo de pedidos. Reduza o mínimo ou amplie o período.")
else:
    order = st.radio("Ordenar por", ["Mais pedidos", "Preparo mais lento", "Mais atrasos"], horizontal=True, key="rest_order")
    col, asc = {"Mais pedidos": ("orders", False), "Preparo mais lento": ("mean_prep", False), "Mais atrasos": ("late_rate", False)}[order]
    view = table.sort_values(col, ascending=asc).head(25)
    show_table(
        view[["restaurant_id", "city", "orders", "mean_prep", "mean_delivery", "mean_total", "late_rate", "slow_prep"]].assign(
            late_rate=lambda x: x["late_rate"] * 100, slow_prep=lambda x: x["slow_prep"].map({True: "Sim", False: "Não"}),
        ).rename(columns={
            "restaurant_id": "Restaurante", "city": "Cidade", "orders": "Pedidos", "mean_prep": "Preparo (min)",
            "mean_delivery": "Entrega (min)", "mean_total": "Espera total (min)", "late_rate": "% entregas atrasadas",
            "slow_prep": "Preparo lento"}),
        column_config={
            "Preparo (min)": st.column_config.NumberColumn(format="%.1f"),
            "Entrega (min)": st.column_config.NumberColumn(format="%.1f"),
            "Espera total (min)": st.column_config.NumberColumn(format="%.1f"),
            "% entregas atrasadas": st.column_config.NumberColumn(format="%.1f"),
        },
    )
