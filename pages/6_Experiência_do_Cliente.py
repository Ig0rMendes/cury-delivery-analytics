import streamlit as st

from src.insights.experience import experience_insights
from src.metrics.experience import DIMENSIONS, dimension_spread, rating_by, rating_distribution, rating_granularity
from src.ui.components import kpi_row, plot, render_insights, safe_insights, section, show_table
from src.ui.layout import setup_page
from src.utils.formatting import fmt_num, fmt_pct
from src.utils.labels import TIME_BAND_ORDER, sort_by_order, value_label
from src.visuals import charts, theme

# pagina de experiencia do cliente (a nota)
ctx = setup_page("Experiência do Cliente", "⭐")
df, sla = ctx.df_f, ctx.sla

# kpis de nota, incluindo o teste se a nota e por entrega ou do entregador
gran = rating_granularity(df)
r = df["rating"]
kpi_row([
    {"label": "Nota média", "value": fmt_num(r.mean(), 2)},
    {"label": "Notas de 4,5 ou mais", "value": fmt_pct((r >= 4.5).mean(), 0)},
    {"label": "Notas abaixo de 4,0", "value": fmt_pct((r < 4.0).mean(), 0), "help": "A cauda onde está o risco de perder clientes."},
    {"label": "Entregadores com nota única", "value": fmt_pct(gran["constant_share"], 0),
     "help": "Se for próximo de 100%, a nota é um atributo do entregador, não a avaliação de cada pedido."},
])

# insights de nota
render_insights(safe_insights(experience_insights, df, sla))
st.divider()

# distribuicao das notas e nota por faixa de tempo
c1, c2 = st.columns(2)
with c1:
    section("Distribuição das notas")
    dist = rating_distribution(df)
    plot(charts.bar_simple(dist["band"], dist["share"] * 100, color=theme.ACCENT, ytitle="% dos pedidos", fmt="%{y:.1f}%"))
with c2:
    section("Nota por faixa de tempo de entrega")
    t = rating_by(df, "time_band")
    t = sort_by_order(t, "time_band", TIME_BAND_ORDER)
    plot(charts.bar_ci(t["time_band"], t["mean"], t["ci_low"], t["ci_high"], ytitle="Nota média", fmt="%{y:.2f}"))

# o usuario escolhe uma dimensao e ve a nota media com IC95%
section("Explorar por dimensão", "Nota média com IC95%. Grupos com menos de 30 pedidos não aparecem.")
label = st.selectbox("Dimensão", list(DIMENSIONS), key="exp_dimension")
col = DIMENSIONS[label]
t = rating_by(df, col)
if len(t) < 2:
    st.info("Grupos insuficientes nesta dimensão para os filtros atuais.")
else:
    names = [value_label(col, x) for x in t[col]]
    plot(charts.bar_ci(names, t["mean"], t["ci_low"], t["ci_high"], ytitle="Nota média", fmt="%{y:.2f}"))

# tabela com a amplitude (melhor x pior grupo) e se a diferenca e clara. tempo de entrega fica de fora
section("Qual dimensão mais separa a nota?", "Amplitude entre o melhor e o pior grupo de cada dimensão.")
sp = dimension_spread(df)
if sp.empty:
    st.info("Sem dados suficientes para comparar dimensões.")
else:
    show_table(
        sp[["dimension", "column", "spread", "best", "best_mean", "worst", "worst_mean", "significant"]].assign(
            best=lambda x: [value_label(c, v) for c, v in zip(x["column"], x["best"])],
            worst=lambda x: [value_label(c, v) for c, v in zip(x["column"], x["worst"])],
            significant=lambda x: x["significant"].map({True: "Sim", False: "Não"}),
        ).drop(columns="column").rename(columns={"dimension": "Dimensão", "spread": "Amplitude", "best": "Melhor grupo", "best_mean": "Nota (melhor)",
                          "worst": "Pior grupo", "worst_mean": "Nota (pior)", "significant": "Diferença clara?"}),
        column_config={
            "Amplitude": st.column_config.NumberColumn(format="%.2f"),
            "Nota (melhor)": st.column_config.NumberColumn(format="%.2f"),
            "Nota (pior)": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    st.caption("A faixa de tempo de entrega fica de fora desta comparação: ela é o próprio atraso, não uma causa independente.")
