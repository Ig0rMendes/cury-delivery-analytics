import pytest

from src.insights.base import Insight
from src.insights.couriers import courier_insights
from src.insights.executive import executive_insights
from src.insights.experience import experience_insights
from src.insights.external import external_insights
from src.insights.operations import operations_insights
from src.insights.restaurants import restaurant_insights
from src.metrics.couriers import courier_table, with_expected
from src.metrics.models import fit_delivery_model
from src.metrics.restaurants import restaurant_table

SLA = 30


# monta tudo uma vez: modelos, tabelas de entregadores e restaurantes
@pytest.fixture(scope="module")
def ctx(df):
    model = fit_delivery_model(df)
    emodel = fit_delivery_model(df, extended=True)
    d = with_expected(df, emodel)
    return {"df": df, "d": d, "model": model, "emodel": emodel, "ct": courier_table(d, SLA, 20), "rt": restaurant_table(df, SLA, 10)}


# roda os insights de todas as paginas de uma vez
def _all(c, df=None, d=None, ct=None, rt=None, model="keep"):
    df = c["df"] if df is None else df
    d = c["d"] if d is None else d
    ct = c["ct"] if ct is None else ct
    rt = c["rt"] if rt is None else rt
    model = c["model"] if model == "keep" else model
    return {
        "exec": executive_insights(df, SLA),
        "ops": operations_insights(df, SLA),
        "ext": external_insights(df, SLA, model),
        "cour": courier_insights(d, ct, c["emodel"] if model == c["model"] else model),
        "rest": restaurant_insights(df, rt, SLA),
        "exp": experience_insights(df, SLA),
    }


# toda pagina gera insight valido, sem '~', '$' ou 'nan' no texto
def test_every_page_produces_valid_insights(ctx):
    out = _all(ctx)
    for page, items in out.items():
        assert items, page
        assert all(isinstance(i, Insight) and i.headline for i in items), page
        for i in items:
            text = i.headline + i.detail + i.action
            assert "~" not in text and "$" not in text and "nan" not in text.lower().replace("finan", ""), (page, i.headline)
            assert i.kind in {"finding", "opportunity", "risk", "info"}


# com 40 pedidos so sai aviso, nunca erro
def test_insights_survive_tiny_subsets(ctx):
    tiny = ctx["df"].head(40)
    d = with_expected(tiny, ctx["emodel"])
    out = _all(ctx, df=tiny, d=d, ct=courier_table(d, SLA, 1), rt=restaurant_table(tiny, SLA, 1))
    for page, items in out.items():
        assert items and items[0].kind == "info", page


# sem modelo cai pro ranking sem ajuste
def test_insights_without_model(ctx):
    d = with_expected(ctx["df"], None)
    ct = courier_table(d, SLA, 20)
    out = _all(ctx, d=d, ct=ct, model=None)
    assert out["cour"][0].headline.startswith("Ranking sem ajuste")


# funciona tambem com filtro aplicado (so transito congestionado)
def test_insights_on_filtered_segment(ctx):
    sub = ctx["df"][ctx["df"]["traffic"] == "Jam"]
    d = with_expected(sub, ctx["emodel"])
    out = _all(ctx, df=sub, d=d, ct=courier_table(d, SLA, 5), rt=restaurant_table(sub, SLA, 5))
    assert all(out.values())


# os efeitos plantados aparecem nos textos
def test_planted_effects_show_up_in_texts(ctx):
    ext = " ".join(i.headline + i.detail for i in external_insights(ctx["df"], SLA, ctx["model"]))
    assert "Congestionado" in ext or "congestionado" in ext
    ops = " ".join(i.headline for i in operations_insights(ctx["df"], SLA))
    assert "simultânea" in ops


# caso classico: pico lento so por causa do transito nao pode virar 'falta de capacidade'
def test_peak_caused_by_traffic_is_not_called_capacity():
    """Pico coincide com trânsito pesado e o tempo só depende do trânsito: não é gargalo de capacidade."""
    import numpy as np
    import pandas as pd
    from src.insights.operations import operations_insights, stratified_gap

    rng = np.random.default_rng(3)
    n = 6000
    hours = np.arange(8, 23)
    weights = np.where(np.isin(hours, [19, 20, 21]), 5.0, 1.0)
    hour = rng.choice(hours, n, p=weights / weights.sum())
    peak = np.isin(hour, [19, 20, 21])
    traffic = np.where(peak, rng.choice(["Jam", "Low"], n, p=[0.85, 0.15]), rng.choice(["Jam", "Low"], n, p=[0.1, 0.9]))
    time = 20 + np.where(traffic == "Jam", 12, 0) + rng.normal(0, 2, n)
    frame = pd.DataFrame({"order_hour": hour, "traffic": traffic, "delivery_time_min": time,
                          "multiple_deliveries": 0, "city": "A", "weekday": "Seg", "order_id": range(n),
                          "prep_time_min": 10.0, "total_time_min": time + 10, "rating": 4.5, "distance_km": 5.0,
                          "has_valid_location": False, "rest_lat": 0.0, "rest_lon": 0.0})
    gap = stratified_gap(frame, frame["order_hour"].isin([19, 20, 21]))
    assert abs(gap) < 0.5
    heads = " ".join(i.headline for i in operations_insights(frame, 30))
    assert "trânsito, não falta de entregador" in heads and "sinal de capacidade" not in heads


# segmento majoritario nunca e a maior alavanca
def test_majority_segment_is_never_the_main_lever(ctx):
    from src.insights.executive import MAX_SEGMENT_SHARE
    from src.metrics.segments import segment_table
    seg = segment_table(ctx["df"], sla=SLA)
    shown = seg[(seg["diff"] > 0) & (seg["share"] <= MAX_SEGMENT_SHARE)]
    assert (shown["share"] <= 0.5).all()
    heads = " ".join(i.headline for i in executive_insights(ctx["df"], SLA))
    for _, row in seg[seg["share"] > MAX_SEGMENT_SHARE].iterrows():
        assert row["segment"] not in heads


# titulo vazio tem que ser texto vazio mesmo (sem 'undefined')
def test_charts_title_is_never_undefined():
    from src.visuals import theme

    class Fig:
        kw = {}
        def update_layout(self, **k): self.kw = k
        def update_yaxes(self, **k): pass
        def update_xaxes(self, **k): pass

    f = theme.apply_layout(Fig(), None)
    assert f.kw["title"]["text"] == ""


# preparo com 3 valores gera o insight de limite da base
def test_coarse_prep_adds_data_limit_insight(ctx):
    import numpy as np
    coarse = ctx["df"].copy()
    coarse["prep_time_min"] = np.random.default_rng(0).choice([5.0, 10.0, 15.0], len(coarse))
    coarse["total_time_min"] = coarse["prep_time_min"] + coarse["delivery_time_min"]
    heads = " ".join(i.headline for i in restaurant_insights(coarse, restaurant_table(coarse, SLA, 10), SLA))
    assert "Limite da base" in heads


# insight do festival mostra o efeito isolado tambem
def test_festival_insight_mentions_isolated_effect(ctx):
    texts = " ".join(i.headline + i.detail for i in external_insights(ctx["df"], SLA, ctx["model"]))
    assert "Mantendo trânsito, clima e demais fatores iguais" in texts
