import math

import numpy as np
import pandas as pd
import pytest

from src.metrics.couriers import classify, courier_table, with_expected, opportunity
from src.metrics.experience import dimension_spread, rating_distribution, rating_granularity
from src.metrics.external import festival_effect, traffic_table, weather_traffic_matrix
from src.metrics.kpis import compute_kpis, delta
from src.metrics.models import fit_delivery_model
from src.metrics.operations import city_table, weekday_hour_matrix
from src.metrics.restaurants import pareto, restaurant_table, top_share
from src.metrics.segments import segment_table
from src.metrics.stats import group_stats, ols_hc1, spearman, welch_test, wilson_ci
from src.metrics.summary import summarize
from src.utils import formatting as F
from src.utils.labels import pt

SLA = 30


# ------------------------------------------------------------------ stats
# welch acha diferenca real e da p=1 pra grupos iguais
def test_welch_detects_difference_and_symmetry():
    rng = np.random.default_rng(0)
    a, b = rng.normal(10, 2, 500), rng.normal(11, 2, 500)
    t = welch_test(b, a)
    assert t["significant"] and 0.7 < t["diff"] < 1.3 and t["ci_low"] < t["diff"] < t["ci_high"]
    assert welch_test(a, a)["p"] == pytest.approx(1.0)
    assert welch_test([1], [2]) is None


# intervalo de wilson fica entre 0 e 1 e em volta da proporcao
def test_wilson_ci_bounds():
    lo, hi = wilson_ci(50, 100)
    assert 0.40 < lo < 0.5 < hi < 0.60
    assert all(math.isnan(x) for x in wilson_ci(0, 0))


# spearman = 1 pra relacao crescente e NaN quando nao varia
def test_spearman_monotonic_and_degenerate():
    x = np.arange(50)
    assert spearman(x, x**3) == pytest.approx(1.0)
    assert math.isnan(spearman(x, np.ones(50)))


# a regressao feita na mao recupera os coeficientes verdadeiros
def test_ols_recovers_coefficients():
    rng = np.random.default_rng(1)
    X = pd.DataFrame({"a": rng.normal(size=2000), "b": rng.normal(size=2000)})
    y = 3 + 2 * X["a"] - 1 * X["b"] + rng.normal(0, 0.5, 2000)
    fit = ols_hc1(X, y)
    assert fit["params"]["a"] == pytest.approx(2, abs=0.1) and fit["params"]["b"] == pytest.approx(-1, abs=0.1)
    assert (fit["se"] > 0).all() and fit["r2"] > 0.9


# a media tem que ficar dentro do proprio IC
def test_group_stats_ci_contains_mean(df):
    t = group_stats(df, "traffic", "delivery_time_min")
    assert ((t["ci_low"] <= t["mean"]) & (t["mean"] <= t["ci_high"])).all()


# -------------------------------------------------------------- kpis / summary
# kpis batem com o calculo direto
def test_kpis_consistent(df):
    k = compute_kpis(df, SLA)
    assert k["orders"] == len(df)
    assert k["on_time_rate"] == pytest.approx((df["delivery_time_min"] <= SLA).mean())
    assert k["avg_total"] == pytest.approx(k["avg_delivery"] + k["avg_prep"])
    assert 0 < k["prep_share"] < 1


# recorte vazio nao quebra os kpis
def test_kpis_empty_does_not_crash(df):
    k = compute_kpis(df.iloc[0:0], SLA)
    assert k["orders"] == 0 and math.isnan(k["avg_delivery"])


# variacao relativa e casos sem base
def test_delta():
    assert delta(110, 100) == pytest.approx(0.1)
    assert delta(1, 0) is None and delta(float("nan"), 1) is None


# as participacoes somam 100%
def test_summarize_shares_sum_to_one(df):
    t = summarize(df, "traffic", SLA)
    assert t["share"].sum() == pytest.approx(1.0) and t["n"].sum() == len(df)
    assert summarize(df.iloc[0:0], "traffic", SLA).empty


# mais transito = mais tempo (nos dados fake)
def test_traffic_table_is_monotonic_in_synthetic_data(df):
    t = traffic_table(df, SLA)
    assert list(t["traffic"]) == ["Low", "Medium", "High", "Jam"]
    assert t["mean_delivery"].is_monotonic_increasing and t["extra_vs_base"].iloc[0] == 0


# celula com poucos pedidos fica vazia
def test_weather_traffic_matrix_masks_small_cells(df):
    means, counts = weather_traffic_matrix(df, min_n=10**6)
    assert means.isna().all().all()


# festival atrasa (efeito plantado)
def test_festival_effect_positive(df):
    f = festival_effect(df)
    assert f is not None and f["diff"] > 0


# confere a conta do ganho potencial na mao
def test_segment_table_math(df):
    seg = segment_table(df, sla=SLA)
    assert not seg.empty
    row = seg[seg["column"] == "traffic"].set_index("value").loc["Jam"]
    sub = df[df["traffic"] == "Jam"]
    rest = df[df["traffic"] != "Jam"]
    assert row["diff"] == pytest.approx(sub["delivery_time_min"].mean() - rest["delivery_time_min"].mean())
    assert row["potential_gain"] == pytest.approx(row["diff"] * len(sub) / len(df))
    # as parcelas de atraso de uma dimensão somam 100%
    assert seg[seg["column"] == "traffic"]["late_share"].sum() == pytest.approx(1.0)


# ------------------------------------------------------------------ modelo
# o modelo acha os efeitos plantados (+10 min congestionado, +3 simultaneas etc)
def test_model_recovers_planted_effects(df):
    m = fit_delivery_model(df)
    assert m is not None and m.r2 > 0.7
    eff = m.table.set_index("term")["effect"]
    assert eff["traffic=Jam"] == pytest.approx(10, abs=0.8)
    assert eff["traffic=High"] == pytest.approx(6, abs=0.8)
    assert eff["multiple_deliveries"] == pytest.approx(3, abs=0.4)
    assert eff["distance_km"] == pytest.approx(8, abs=1.0)  # +5 km
    pred = m.predict(df)
    assert pred.notna().mean() > 0.9
    assert (df["delivery_time_min"] - pred).abs().mean() < 4


# amostra pequena = sem modelo
def test_model_returns_none_for_tiny_sample(df):
    assert fit_delivery_model(df.head(50)) is None


# se o filtro deixa um nivel so, o modelo nao quebra
def test_model_handles_single_level_after_filter(df):
    m = fit_delivery_model(df[df["traffic"] == "Low"])
    assert m is not None and not any(t.startswith("traffic=") for t in m.table["term"])
    assert m.predict(df).notna().any()


# --------------------------------------------------------------- entregadores
# so classifica entregador se for claro (3 EP) E relevante (1 min)
def test_classify_requires_clear_and_relevant_gap():
    assert classify(3.0, 0.5) == "Mais lento que o esperado"
    assert classify(1.2, 0.5) == "Dentro do esperado"      # 2,4 erros-padrão: não basta (limiar é 3)
    assert classify(-3.0, 0.5) == "Mais rápido que o esperado"
    assert classify(0.5, 0.1) == "Dentro do esperado"      # claro, mas < 1 min
    assert classify(2.0, 5.0) == "Dentro do esperado"      # grande, mas incerto
    assert classify(float("nan"), 1.0) == "Indefinido"


# entregador lento de proposito tem que ser apontado
def test_courier_table_flags_slow_skill(df):
    m = fit_delivery_model(df, extended=True)
    d = with_expected(df, m)
    t = courier_table(d, SLA, min_orders=20)
    assert not t.empty and (t["orders"] >= 20).all()
    assert (t["status"] == "Mais lento que o esperado").any() and (t["status"] == "Mais rápido que o esperado").any()
    opp = opportunity(t, len(d), d["delivery_time_min"].mean())
    assert opp["mean_gain"] > 0 and opp["couriers"] > 0


# sem modelo tudo fica 'Indefinido'
def test_courier_table_without_model_does_not_crash(df):
    t = courier_table(with_expected(df, None), SLA, 20)
    assert (t["status"] == "Indefinido").all()


# --------------------------------------------------------------- restaurantes
# tabela de restaurantes e curva de concentracao
def test_restaurant_table_and_pareto(df):
    t = restaurant_table(df, SLA, min_orders=10)
    assert not t.empty and (t["orders"] >= 10).all()
    p = pareto(df)
    assert p["cum_orders_pct"].iloc[-1] == pytest.approx(1.0) and p["cum_orders_pct"].is_monotonic_increasing
    assert 0.2 <= top_share(df, 0.2) <= 1.0


# ---------------------------------------------------------------- experiência
# detecta quando a nota e atributo do entregador
def test_rating_granularity_detects_courier_attribute(df):
    flat = df.copy()
    flat["rating"] = flat.groupby("courier_id")["rating"].transform("first")
    g = rating_granularity(flat)
    assert g["is_courier_attribute"] and g["constant_share"] == pytest.approx(1.0)
    assert not rating_granularity(df)["is_courier_attribute"]


# distribuicao de notas soma 100%
def test_rating_distribution_sums_to_one(df):
    assert rating_distribution(df)["share"].sum() == pytest.approx(1.0)


# dimensoes ordenadas da maior pra menor amplitude
def test_dimension_spread_sorted(df):
    s = dimension_spread(df)
    assert not s.empty and s["spread"].is_monotonic_decreasing


# ----------------------------------------------------------------- operação
# matriz de dia x hora e tabela de cidades
def test_weekday_matrix_and_city_table(df):
    m = weekday_hour_matrix(df)
    assert m.to_numpy().sum() == len(df)
    c = city_table(df, SLA)
    assert c["n"].sum() == len(df) and c[["lat", "lon"]].notna().all().all()


# --------------------------------------------------------------- formatação
# formatacao em portugues: 1.234,5 e afins
def test_formatting_pt_br():
    assert F.fmt_int(1234567) == "1.234.567"
    assert F.fmt_num(1234.567, 1) == "1.234,6"
    assert F.fmt_pct(0.1234) == "12,3%"
    assert F.fmt_min(28.44) == "28,4 min"
    assert F.fmt_signed(2.34) == "+2,3" and F.fmt_signed(-1.0) == "-1,0" and F.fmt_signed(0) == "0,0"
    assert F.fmt_int(float("nan")) == F.DASH == F.fmt_pct(None)
    assert F.fmt_signed_pct(0.05) == "+5,0%"
    assert pt("traffic", "Jam") == "Congestionado" and pt("weather", "???") == "???"


# --------------------------------------------------- modelo estendido / acaso
# modelo estendido usa transito x clima junto e preve
def test_extended_model_uses_combined_traffic_weather_and_predicts(df):
    m = fit_delivery_model(df, extended=True)
    assert m is not None and "traffic_weather" in m.spec and "traffic" not in m.spec
    pred = m.predict(df)
    assert pred.notna().mean() > 0.9 and (df["delivery_time_min"] - pred).abs().mean() < 4


# se o transito so pesa na neblina, o estendido acerta e o simples erra
def test_extended_model_captures_interaction():
    """Trânsito só pesa quando o clima é ruim: o modelo aditivo erra, o estendido acerta."""
    rng = np.random.default_rng(5)
    n = 6000
    traffic = rng.choice(["Low", "Jam"], n)
    weather = rng.choice(["Sunny", "Fog"], n)
    t = 20 + np.where((traffic == "Jam") & (weather == "Fog"), 15, 0) + rng.normal(0, 1, n)
    frame = pd.DataFrame({"traffic": traffic, "weather": weather, "festival": "No", "vehicle_type": "motorcycle",
                          "area_type": "Urban", "daypart": "Jantar", "distance_km": rng.uniform(1, 10, n),
                          "multiple_deliveries": 0, "courier_age": 30, "vehicle_condition": 1, "delivery_time_min": t})
    add = fit_delivery_model(frame)
    ext = fit_delivery_model(frame, extended=True)
    err_add = (frame["delivery_time_min"] - add.predict(frame)).abs().mean()
    err_ext = (frame["delivery_time_min"] - ext.predict(frame)).abs().mean()
    assert err_ext < 1.0 < err_add


# sem habilidade individual (id embaralhado) quase ninguem e apontado
def test_pure_noise_couriers_are_not_flagged(df):
    """Sem habilidade individual, o limiar de 3 erros-padrão quase não aponta ninguém."""
    rng = np.random.default_rng(0)
    noisy = df.copy()
    noisy["courier_id"] = rng.permutation(noisy["courier_id"].to_numpy())  # desfaz a ligação entregador-pedido
    m = fit_delivery_model(noisy, extended=True)
    t = courier_table(with_expected(noisy, m), SLA, 20)
    flagged = (t["status"].isin(["Mais lento que o esperado", "Mais rápido que o esperado"])).mean()
    assert flagged < 0.03


# rotulos legiveis e faixa de tempo fora do ranking da nota
def test_value_label_and_experience_excludes_time_band(df):
    from src.utils.labels import value_label
    assert value_label("traffic", "Jam") == "Congestionado" and value_label("multiple_deliveries", 2.0) == "2"
    assert value_label("daypart", "Jantar") == "Jantar"
    assert "time_band" not in set(dimension_spread(df)["column"])


# detecta preparo com poucos valores (5, 10, 15)
def test_prep_granularity_detects_coarse_values(df):
    from src.metrics.restaurants import prep_granularity, prep_granularity_text
    coarse = df.copy()
    coarse["prep_time_min"] = np.random.default_rng(0).choice([5.0, 10.0, 15.0], len(coarse))
    g = prep_granularity(coarse)
    assert g["coarse"] and g["distinct"] == 3
    assert prep_granularity_text(g).count("min (") == 3 and " e 15 min" in prep_granularity_text(g)
    fine = df.copy()
    fine["prep_time_min"] = np.random.default_rng(1).uniform(1, 40, len(fine))
    assert not prep_granularity(fine)["coarse"]
