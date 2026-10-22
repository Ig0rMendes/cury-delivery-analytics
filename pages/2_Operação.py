import streamlit as st

from src.insights.operations import operations_insights
from src.metrics.operations import city_table, daypart_table, hourly_profile, weekday_hour_matrix
from src.metrics.summary import summarize
from src.ui.components import plot, render_insights, safe_insights, section, show_table
from src.ui.layout import setup_page
from src.utils.labels import pt
from src.visuals import charts, theme

# configura a pagina e pega a base filtrada
ctx = setup_page("Operação", "🔎")
df, sla = ctx.df_f, ctx.sla

# insights de operacao (pico, atraso por hora, simultaneas, cidades)
render_insights(safe_insights(operations_insights, df, sla))
st.divider()

# mapa de calor dia da semana x hora
section("Quando a demanda acontece", "Pedidos por dia da semana e hora do pedido.")
m = weekday_hour_matrix(df)
plot(charts.heatmap(m.to_numpy(), m.columns, m.index, xtitle="Hora do pedido", zlabel="pedidos", height=330))

c1, c2 = st.columns(2)
with c1:
    # quatro graficos em grade: volume x tempo, periodo do dia, simultaneas e tipo de area
    section("Volume x tempo por hora", "O tempo sobe quando o volume sobe? Tracejado: SLA.")
    h = hourly_profile(df, sla)
    plot(charts.dual_axis(h["order_hour"].astype(int).astype(str) + "h", h["n"], h["mean_delivery"],
                          "Pedidos", "Tempo médio de entrega (min)", hline=sla, hline_label="SLA"))
with c2:
    section("Atraso por período do dia", f"% das entregas acima de {sla} min.")
    dp = daypart_table(df, sla)
    plot(charts.bar_simple(dp["daypart"], dp["late_rate"] * 100, color=theme.BAD, ytitle="% atrasadas", fmt="%{y:.1f}%"))

c3, c4 = st.columns(2)
with c3:
    section("Entregas simultâneas", "Quantas entregas o entregador carrega ao mesmo tempo.")
    t = summarize(df, "multiple_deliveries", sla, min_n=30).sort_values("multiple_deliveries")
    plot(charts.bar_ci([int(x) for x in t["multiple_deliveries"]], t["mean_delivery"], t["ci_low"], t["ci_high"],
                       ytitle="Tempo médio de entrega (min)", hline=sla, hline_label="SLA"))
with c4:
    section("Tipo de área", "Médias com intervalo de confiança de 95%.")
    t = summarize(df, "area_type", sla, min_n=30)
    plot(charts.bar_ci([pt("area_type", x) for x in t["area_type"]], t["mean_delivery"], t["ci_low"], t["ci_high"],
                       ytitle="Tempo médio de entrega (min)", hline=sla, hline_label="SLA"))

# mapa + tabela das cidades. a cidade vem do codigo do id do entregador
section("Cidades", "Cidade extraída do código do ID do entregador. Bolha = volume; cor = tempo médio de entrega.")
ct = city_table(df, sla)
left, right = st.columns([1, 1])
with left:
    show_table(
        ct[["city", "n", "share", "mean_delivery", "late_rate", "distance"]].assign(
            share=lambda x: x["share"] * 100, late_rate=lambda x: x["late_rate"] * 100,
        ).rename(columns={"city": "Cidade", "n": "Pedidos", "share": "% do total", "mean_delivery": "Entrega (min)",
                          "late_rate": "% atrasadas", "distance": "Distância (km)"}),
        column_config={
            "% do total": st.column_config.NumberColumn(format="%.1f"),
            "Entrega (min)": st.column_config.NumberColumn(format="%.1f"),
            "% atrasadas": st.column_config.NumberColumn(format="%.1f"),
            "Distância (km)": st.column_config.NumberColumn(format="%.1f"),
        },
    )
with right:
    if ct[["lat", "lon"]].dropna().empty:
        st.info("Sem coordenadas válidas para desenhar o mapa neste recorte.")
    else:
        plot(charts.city_map(ct))
