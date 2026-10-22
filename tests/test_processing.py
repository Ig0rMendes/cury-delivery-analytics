import numpy as np
import pandas as pd
import pytest

from src.config import AGE_RANGE, RATING_RANGE
from src.processing.cleaning import clean_orders
from src.processing.features import add_features, haversine_km, extract_city, daypart_from_hour
from src.processing.filtering import Filters, filter_frame
from src.processing.loader import DataNotFoundError, SchemaError, find_data_file, read_raw
from src.processing.pipeline import load_analytical_data, process
from tests.synthetic import make_raw


# ----------------------------------------------------------------- loader
# sem arquivo na pasta data: erro com mensagem amigavel
def test_find_data_file_missing_gives_friendly_message(tmp_path, monkeypatch):
    monkeypatch.setattr("src.processing.loader.DATA_DIR", tmp_path)
    monkeypatch.delenv("DELIVERY_DATA_PATH", raising=False)
    with pytest.raises(DataNotFoundError) as exc:
        find_data_file()
    assert "train" in str(exc.value)


# Train.CSV em maiuscula tambem tem que ser achado
def test_find_data_file_is_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setattr("src.processing.loader.DATA_DIR", tmp_path)
    monkeypatch.delenv("DELIVERY_DATA_PATH", raising=False)
    (tmp_path / "Train.CSV").write_text("x")
    assert find_data_file().name == "Train.CSV"


# a variavel de ambiente DELIVERY_DATA_PATH manda no caminho
def test_env_var_overrides(tmp_path, monkeypatch):
    f = tmp_path / "outra.csv"
    f.write_text("x")
    monkeypatch.setenv("DELIVERY_DATA_PATH", str(f))
    assert find_data_file() == f


# arquivo sem as colunas certas = SchemaError
def test_read_raw_rejects_wrong_schema(tmp_path):
    f = tmp_path / "train.csv"
    pd.DataFrame({"a": [1]}).to_csv(f, index=False)
    with pytest.raises(SchemaError):
        read_raw(f)


# teste ponta a ponta: do csv ate a base pronta
def test_load_analytical_data_end_to_end(tmp_path):
    f = tmp_path / "train.csv"
    make_raw(1500, seed=2).to_csv(f, index=False)
    df, rep = load_analytical_data(f)
    assert len(df) == rep.final_rows > 1000
    assert rep.source == "train.csv"


# --------------------------------------------------------------- cleaning
# as linhas removidas no funil tem que bater com bruto - final
def test_funnel_is_consistent(report, raw):
    assert report.raw_rows == len(raw)
    assert report.final_rows == report.steps[-1]["remaining"] == report.raw_rows - sum(s["removed"] for s in report.steps)
    prev = report.raw_rows
    for s in report.steps:
        assert s["remaining"] == prev - s["removed"]
        prev = s["remaining"]


# depois da limpeza nao pode sobrar vazio nos campos essenciais
def test_no_missing_in_essentials(df):
    for c in ["courier_id", "courier_age", "rating", "weather", "traffic", "area_type", "vehicle_type",
              "order_type", "multiple_deliveries", "delivery_time_min", "prep_time_min", "order_hour"]:
        assert df[c].notna().all(), c


# nada fora das faixas permitidas (idade, nota, tempos...)
def test_value_ranges_and_categories(df):
    assert df["courier_age"].between(*AGE_RANGE).all()
    assert df["rating"].between(*RATING_RANGE).all()
    assert set(df["traffic"]) <= {"Low", "Medium", "High", "Jam"}
    assert set(df["area_type"]) <= {"Metropolitan", "Urban", "Semi-Urban"}
    assert not df["weather"].str.contains("conditions").any()
    assert not df["traffic"].str.contains(" ").any()


# ids duplicados tem que sumir
def test_duplicates_removed_and_ids_unique(df, raw):
    assert df["order_id"].is_unique
    assert len(raw) > raw["ID"].nunique()


# sinal da coordenada corrigido e localizacao invalida marcada
def test_coordinates_fixed_and_invalid_flagged(df, report):
    assert (df[["rest_lat", "rest_lon", "dest_lat", "dest_lon"]] >= 0).all().all()
    assert report.coords_sign_fixed > 0
    assert report.invalid_location_rows > 0
    assert df["has_valid_location"].sum() == len(df) - report.invalid_location_rows
    bad = df[~df["has_valid_location"]]
    assert bad["distance_km"].isna().all() and bad["restaurant_id"].isna().all()


# festival sem info fica vazio (nao vira 'No' escondido)
def test_festival_unknown_is_kept_as_missing(df, report):
    assert df["festival"].isna().sum() > 0
    assert report.festival_unknown >= df["festival"].isna().sum()


# monta uma linha unica pra testar casos especificos
def _one_row(**over):
    base = make_raw(5, seed=1, dirty=False).iloc[[0]].copy()
    for k, v in over.items():
        base[k] = v
    return base


# pedido as 23:55 e retirada 00:05 (dia seguinte) = 10 min, e nao um numero negativo
def test_prep_time_wraps_around_midnight():
    r = _one_row(Time_Orderd="23:55:00", Time_Order_picked="00:05:00")
    out, _ = clean_orders(r)
    assert out["prep_time_min"].iloc[0] == pytest.approx(10.0)


# '(min) 24' vira 24 e 'NaN ' vira vazio
def test_delivery_time_text_and_nan_tokens():
    r = _one_row(**{"Time_taken(min)": "(min) 24"})
    out, _ = clean_orders(r)
    assert out["delivery_time_min"].iloc[0] == 24
    r2 = _one_row(Road_traffic_density="NaN ")
    out2, rep2 = clean_orders(r2)
    assert len(out2) == 0 and rep2.steps[2]["removed"] == 1


# Metropolitian com erro de grafia vira Metropolitan
def test_metropolitian_typo_fixed():
    out, _ = clean_orders(_one_row(City="Metropolitian "))
    assert out["area_type"].iloc[0] == "Metropolitan"


# se a limpeza remover tudo, nao pode quebrar
def test_empty_after_cleaning_does_not_crash():
    raw = make_raw(20, seed=3)
    raw["Delivery_person_Age"] = "10"
    out, rep = clean_orders(raw)
    assert len(out) == 0 and rep.final_rows == 0


# --------------------------------------------------------------- features
# distancia conhecida entre duas cidades confere
def test_haversine_known_distance():
    # Nova Délhi -> Mumbai ≈ 1.150 km
    d = haversine_km(28.6139, 77.2090, 19.0760, 72.8777)
    assert 1100 < float(d) < 1200


# horas caindo no periodo do dia certo
def test_daypart_bins():
    s = pd.Series([6, 10, 11, 14, 15, 17, 18, 21, 22, 3])
    assert daypart_from_hour(s).tolist() == ["Manhã", "Manhã", "Almoço", "Almoço", "Tarde", "Tarde", "Jantar", "Jantar", "Noite", "Noite"]


# cidade extraida do id do entregador
def test_city_extraction():
    c = extract_city(pd.Series(["INDORES13DEL02", "BANGRES01DEL10", "XYZRES01DEL01", "lixo"]))
    assert c["city"].tolist() == ["Indore", "Bangalore", "XYZ", "Outras"]


# total = preparo + entrega
def test_total_time_is_prep_plus_delivery(df):
    assert np.allclose(df["total_time_min"], df["prep_time_min"] + df["delivery_time_min"])


# distancias e velocidades nao podem ser absurdas
def test_distance_and_speed_are_plausible(df):
    d = df["distance_km"].dropna()
    assert d.between(0, 50).all() and len(d) > 0.9 * len(df)
    assert (df["speed_kmh"].dropna() <= 80).all()


# mesma coordenada = mesmo id de restaurante
def test_restaurant_id_is_stable_per_coordinate(df):
    v = df[df["has_valid_location"]]
    per_coord = v.groupby(["city_code", v["rest_lat"].round(4), v["rest_lon"].round(4)])["restaurant_id"].nunique()
    assert (per_coord == 1).all()


# o processamento nao pode alterar a base original
def test_process_does_not_mutate_input(raw):
    before = raw.copy()
    process(raw)
    pd.testing.assert_frame_equal(raw, before)


# -------------------------------------------------------------- filtering
# filtros combinam e a data final conta inclusive
def test_filter_frame_is_inclusive_and_combines(df):
    d0 = df["order_date"].min()
    f = Filters(d0, d0, ("Low", "Jam"), tuple(df["weather"].unique()))
    out = filter_frame(df, f)
    assert (out["order_date"] == d0).all()
    assert set(out["traffic"]) <= {"Low", "Jam"}
    assert len(out) > 0
