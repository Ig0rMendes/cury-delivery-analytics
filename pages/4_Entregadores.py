import streamlit as st

from src.config import MIN_ORDERS_COURIER
from src.insights.couriers import courier_insights
from src.metrics.couriers import age_table, condition_table, courier_table, vehicle_table, with_expected
from src.ui.components import kpi_row, plot, render_insights, safe_insights, section, show_table
from src.ui.data_access import get_expected_model
from src.ui.layout import setup_page
from src.utils.formatting import fmt_int, fmt_num
from src.utils.labels import pt
from src.visuals import charts, theme

# pagina de entregadores
ctx = setup_page("Entregadores", "🛵")
df, sla = ctx.df_f, ctx.sla
# usa o modelo estendido (transito x clima + periodo) pra saber o tempo esperado de cada pedido
model = get_expected_model()

# o usuario escolhe o minimo de pedidos pra entrar no ranking (default 20)
min_orders = st.slider("Mínimo de pedidos por entregador para entrar no ranking", 5, 100, MIN_ORDERS_COURIER, step=5,
                       key="min_orders_courier",
                       help="Poucos pedidos tornam o desempenho instável. Aumente para um ranking mais confiável.")

# acrescenta tempo esperado e excesso, e agrupa por entregador
d = with_expected(df, model)
table = courier_table(d, sla, min_orders)

if not table.empty:
    kpi_row([
        {"label": "Entregadores no ranking", "value": fmt_int(len(table))},
        {"label": "Mais lentos que o esperado", "value": fmt_int((table["status"] == "Mais lento que o esperado").sum()),
         "help": "Diferença clara E de pelo menos 1 minuto, já descontado o contexto."},
        {"label": "Mais rápidos que o esperado", "value": fmt_int((table["status"] == "Mais rápido que o esperado").sum())},
        {"label": "Mediana de pedidos/entregador", "value": fmt_int(table["orders"].median())},
    ])

# insights de entregadores
render_insights(safe_insights(courier_insights, d, table, model, min_orders))
st.divider()

# dispersao pedidos x excesso: cada ponto e um entregador
section("Desempenho ajustado ao contexto",
        "O 'esperado' considera distância, combinação trânsito × clima, período do dia, entregas simultâneas, veículo e festival. "
        "Acima de zero = mais lento do que o esperado para as entregas que a pessoa realmente fez.")
if table.empty:
    st.info("Nenhum entregador atinge o mínimo de pedidos nos filtros atuais. Reduza o mínimo ou amplie o período.")
elif table["excess"].isna().all():
    st.info("Sem modelo de tempo esperado para este recorte; veja a tabela de tempos brutos abaixo.")
else:
    plot(charts.courier_scatter(table))

if not table.empty:
    # duas tabelas impilhadas: os mais lentos e os mais rapidos contra o esperado
    for col_name, ascending in (("Mais lentos (maior excesso)", False), ("Mais rápidos (menor excesso)", True)):
        st.markdown(f"**{col_name}**")
        sort_col = "excess" if not table["excess"].isna().all() else "mean_delivery"
        view = table.sort_values(sort_col, ascending=ascending).head(10)
        show_table(
            view[["courier_id", "city", "orders", "mean_delivery", "excess", "rating", "status"]].rename(columns={
                "courier_id": "Entregador", "city": "Cidade", "orders": "Pedidos", "mean_delivery": "Entrega (min)",
                "excess": "Vs. esperado (min)", "rating": "Nota", "status": "Classe"}),
            column_config={
                "Entrega (min)": st.column_config.NumberColumn(format="%.1f"),
                "Vs. esperado (min)": st.column_config.NumberColumn(format="%.1f"),
                "Nota": st.column_config.NumberColumn(format="%.2f"),
            },
        )

st.divider()
# perfis brutos por veiculo, idade e condicao do veiculo, e distribuicao de carga
section("Perfil dos entregadores", "Médias brutas com IC95%. O efeito isolado de cada um está na página Fatores Externos.")
c3, c4, c5 = st.columns(3)
with c3:
    v = vehicle_table(df, sla)
    plot(charts.bar_ci([pt("vehicle_type", x) for x in v["vehicle_type"]], v["mean_delivery"], v["ci_low"], v["ci_high"],
                       title="Por veículo", ytitle="Entrega (min)", height=320))
with c4:
    a = age_table(df, sla)
    plot(charts.bar_ci(a["age_band"], a["mean_delivery"], a["ci_low"], a["ci_high"], title="Por faixa etária",
                       ytitle="Entrega (min)", height=320))
with c5:
    cdt = condition_table(df, sla)
    plot(charts.bar_ci([int(x) for x in cdt["vehicle_condition"]], cdt["mean_delivery"], cdt["ci_low"], cdt["ci_high"],
                       title="Por condição do veículo", ytitle="Entrega (min)", height=320))
st.caption("A escala de condição do veículo (0–3) não tem sentido documentado na base; confirme com a fonte.")

section("Distribuição de carga", "Quantos pedidos cada entregador faz no período.")
plot(charts.histogram(df["courier_id"].value_counts(), xtitle="Pedidos por entregador", color=theme.SECONDARY))
