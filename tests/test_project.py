"""Verificações estruturais: sintaxe, pastas e (se instalados) montagem real dos gráficos."""
import py_compile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


# todos os .py compilam (pega erro de sintaxe)
def test_all_python_files_compile():
    files = [p for p in ROOT.rglob("*.py") if ".venv" not in p.parts and "venv" not in p.parts]
    assert len(files) > 30
    for f in files:
        py_compile.compile(str(f), doraise=True)


# a pasta data tem que estar vazia (so o .gitkeep)
def test_data_folder_is_empty_placeholder():
    items = [p.name for p in (ROOT / "data").iterdir()]
    # o repositório distribui a pasta vazia; se o usuário já colocou o train.csv, tudo bem
    assert ".gitkeep" in items or any(n.lower().startswith("train") for n in items)


# as 6 paginas existem e com numero na frente
def test_pages_exist_and_are_numbered():
    pages = sorted(p.name for p in (ROOT / "pages").glob("*.py"))
    assert [p.split("_")[0] for p in pages] == ["1", "2", "3", "4", "5", "6"]


# monta os graficos com plotly de verdade (pula se nao tiver instalado)
def test_charts_build_with_real_plotly(df):
    pytest.importorskip("plotly")
    from src.metrics.external import traffic_table, weather_traffic_matrix
    from src.metrics.models import fit_delivery_model
    from src.metrics.operations import city_table, daily_series, weekday_hour_matrix
    from src.metrics.restaurants import pareto
    from src.metrics.couriers import courier_table, with_expected
    from src.visuals import charts

    t = traffic_table(df, 30)
    assert charts.bar_ci(t["traffic"], t["mean_delivery"], t["ci_low"], t["ci_high"], hline=30)
    d = daily_series(df, 30)
    assert charts.dual_axis(d["order_date"].dt.strftime("%d/%m"), d["n"], d["mean_delivery"], "A", "B", hline=30)
    m = weekday_hour_matrix(df)
    assert charts.heatmap(m.to_numpy(), m.columns, m.index)
    means, _ = weather_traffic_matrix(df)
    assert charts.heatmap(means.to_numpy(), means.columns, means.index, texttemplate="%{z:.1f}")
    model = fit_delivery_model(df)
    assert charts.effects_chart(model.table)
    assert charts.city_map(city_table(df, 30))
    assert charts.pareto_chart(pareto(df))
    assert charts.courier_scatter(courier_table(with_expected(df, model), 30, 20))
    assert charts.histogram(df["delivery_time_min"], vline=30)
    assert charts.stacked_composition(t["traffic"], t["mean_prep"], t["mean_delivery"])
    assert charts.bar_simple(t["traffic"], t["n"])
    assert charts.bar_simple(t["traffic"], t["n"], horizontal=True)
