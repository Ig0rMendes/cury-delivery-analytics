import streamlit as st

from src.insights.external import external_insights
from src.metrics.external import traffic_table, weather_table, weather_traffic_matrix
from src.metrics.summary import summarize
from src.ui.components import plot, render_insights, safe_insights, section
from src.ui.data_access import get_model
from src.ui.layout import setup_page
from src.utils.labels import pt
from src.visuals import charts, theme

# pagina de fatores externos: transito, clima, festival e distancia
ctx = setup_page("Fatores Externos", "🌦️")
df, sla = ctx.df_f, ctx.sla
# pega o modelo de efeitos isolados (ja em cache, ajustado na base completa)
model = get_model()

# insights do modelo e das comparacoes
render_insights(safe_insights(external_insights, df, sla, model))
st.divider()

c1, c2 = st.columns(2)
with c1:
    # transito e clima com intervalo de confianca
    section("Trânsito", "Tempo médio de entrega com IC95%. Tracejado: SLA.")
    t = traffic_table(df, sla)
    plot(charts.bar_ci([pt("traffic", x) for x in t["traffic"]], t["mean_delivery"], t["ci_low"], t["ci_high"],
                       colors=[theme.TRAFFIC_COLORS.get(x, theme.NEUTRAL) for x in t["traffic"]],
                       ytitle="Tempo médio de entrega (min)", hline=sla, hline_label="SLA"))
with c2:
    section("Clima", "Do mais lento ao mais rápido, com IC95%.")
    w = weather_table(df, sla)
    plot(charts.bar_ci([pt("weather", x) for x in w["weather"]], w["mean_delivery"], w["ci_low"], w["ci_high"],
                       ytitle="Tempo médio de entrega (min)", hline=sla, hline_label="SLA"))

# matriz clima x transito, celulas com menos de 30 pedidos ficam vazias
section("Clima x trânsito", "Tempo médio de entrega (min) em cada combinação. Células com menos de 30 pedidos ficam vazias.")
means, counts = weather_traffic_matrix(df)
if means.empty:
    st.info("Recorte pequeno demais para cruzar clima e trânsito.")
else:
    plot(charts.heatmap(means.to_numpy(), [pt("traffic", c) for c in means.columns], [pt("weather", i) for i in means.index],
                        colorscale=theme.HEAT_SCALE, texttemplate="%{z:.1f}", zlabel="min", height=380))

c3, c4 = st.columns(2)
with c3:
    # festival e distancia
    section("Festival", "Pedidos sem a informação ficam de fora desta comparação.")
    f = summarize(df[df["festival"].notna()], "festival", sla, min_n=30)
    if len(f) < 2:
        st.info("Poucos pedidos em dias de festival neste recorte.")
    else:
        plot(charts.bar_ci([pt("festival", x) for x in f["festival"]], f["mean_delivery"], f["ci_low"], f["ci_high"],
                           ytitle="Tempo médio de entrega (min)"))
with c4:
    section("Distância x tempo", "Tempo médio por faixa de distância (km), só localizações válidas.")
    d = df.dropna(subset=["distance_km"]).copy()
    if len(d) < 100:
        st.info("Poucos pedidos com distância válida neste recorte.")
    else:
        d["faixa"] = (d["distance_km"] // 3 * 3).astype(int)
        s = summarize(d, "faixa", sla, min_n=30).sort_values("faixa")
        plot(charts.bar_ci([f"{int(a)}–{int(a) + 3} km" for a in s["faixa"]], s["mean_delivery"], s["ci_low"], s["ci_high"],
                           ytitle="Tempo médio de entrega (min)"))

# grafico e tabela dos efeitos isolados da regressao (mantendo o resto igual)
section("Efeito isolado de cada fator",
        "Regressão linear: o efeito de cada fator mantendo os demais constantes (referência indicada no rótulo da tabela). "
        "Vermelho = aumenta o tempo com segurança; verde = reduz; cinza = indistinguível de zero. Associação, não causalidade.")
if model is None:
    st.info("Amostra insuficiente para ajustar o modelo.")
else:
    plot(charts.effects_chart(model.table))
    st.caption(f"Modelo ajustado na base completa: {model.n:,} pedidos com dados completos; R² = {model.r2:.2f}.".replace(",", "."))
    with st.expander("Ver a tabela de efeitos"):
        view = model.table[["label", "reference", "effect", "ci_low", "ci_high", "n"]].rename(columns={
            "label": "Fator", "reference": "Referência", "effect": "Efeito (min)", "ci_low": "IC95% inf.",
            "ci_high": "IC95% sup.", "n": "Pedidos"})
        st.dataframe(view, hide_index=True, column_config={
            "Efeito (min)": st.column_config.NumberColumn(format="%.2f"),
            "IC95% inf.": st.column_config.NumberColumn(format="%.2f"),
            "IC95% sup.": st.column_config.NumberColumn(format="%.2f")})
