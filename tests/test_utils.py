"""Unit-Tests fuer app/utils.py — Helper-Funktionen.

Ausfuehren: pytest tests/ -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
import utils


# ---------------------------------------------------------------------------
# classify_delay
# ---------------------------------------------------------------------------

class TestClassifyDelay:
    def test_nan_returns_unbekannt(self):
        assert utils.classify_delay(np.nan) == "unbekannt"
        assert utils.classify_delay(None) == "unbekannt"

    def test_punktlich(self):
        assert utils.classify_delay(0) == "puenktlich_unter_1min"
        assert utils.classify_delay(30) == "puenktlich_unter_1min"
        assert utils.classify_delay(59.9) == "puenktlich_unter_1min"

    def test_leicht_verspaetet(self):
        assert utils.classify_delay(60) == "leicht_1_3min"
        assert utils.classify_delay(120) == "leicht_1_3min"
        assert utils.classify_delay(179.9) == "leicht_1_3min"

    def test_klassisch_verspaetet(self):
        assert utils.classify_delay(180) == "verspaetet_3_5min"
        assert utils.classify_delay(299.9) == "verspaetet_3_5min"

    def test_stark_verspaetet(self):
        assert utils.classify_delay(300) == "stark_5_10min"
        assert utils.classify_delay(599.9) == "stark_5_10min"

    def test_extrem(self):
        assert utils.classify_delay(600) == "extrem_ueber_10min"
        assert utils.classify_delay(10_000) == "extrem_ueber_10min"

    def test_frueh(self):
        assert utils.classify_delay(-5) == "frueh_unter_30s"
        assert utils.classify_delay(-29.9) == "frueh_unter_30s"
        # -30 ist die untere Grenze des "frueh_unter_30s"-Buckets (low-inclusive)
        assert utils.classify_delay(-30) == "frueh_unter_30s"
        assert utils.classify_delay(-30.01) == "frueh_30+s"
        assert utils.classify_delay(-300) == "frueh_30+s"


class TestIsClassicallyDelayed:
    def test_nan_is_false(self):
        assert utils.is_classically_delayed(np.nan) is False

    def test_below_threshold(self):
        assert utils.is_classically_delayed(0) is False
        assert utils.is_classically_delayed(180) is False  # genau am Grenzwert: nicht verspaetet
        assert utils.is_classically_delayed(180.01) is True

    def test_above_threshold(self):
        assert utils.is_classically_delayed(181) is True
        assert utils.is_classically_delayed(3600) is True

    def test_custom_threshold(self):
        assert utils.is_classically_delayed(50, threshold=30) is True
        assert utils.is_classically_delayed(20, threshold=30) is False


# ---------------------------------------------------------------------------
# add_delay_class
# ---------------------------------------------------------------------------

def test_add_delay_class_adds_column():
    df = pd.DataFrame({"delay_arr_sec": [0, 200, 400, np.nan, -50]})
    out = utils.add_delay_class(df)
    assert "delay_class" in out.columns
    assert len(out) == 5
    assert out["delay_class"].iloc[0] == "puenktlich_unter_1min"
    assert out["delay_class"].iloc[1] == "verspaetet_3_5min"
    assert out["delay_class"].iloc[3] == "unbekannt"
    assert out["delay_class"].iloc[4] == "frueh_30+s"


def test_add_delay_class_does_not_mutate():
    df = pd.DataFrame({"delay_arr_sec": [100]})
    out = utils.add_delay_class(df)
    assert "delay_class" not in df.columns
    assert "delay_class" in out.columns


# ---------------------------------------------------------------------------
# filter_implausible_delays
# ---------------------------------------------------------------------------

class TestFilterImplausibleDelays:
    def test_removes_impossible_early_arrivals(self):
        df = pd.DataFrame({"delay_arr_sec": [-173092.0, -601.0, -600.0, -300.0, 0.0, 4000.0]})
        out = utils.filter_implausible_delays(df)
        # -173092 und -601 raus; -600 (genau Grenze) und alles darueber bleibt
        assert out["delay_arr_sec"].tolist() == [-600.0, -300.0, 0.0, 4000.0]

    def test_keeps_large_positive_delays(self):
        # Reale Auslands-Zug-Verspaetungen (Stunden) duerfen NICHT entfernt werden
        df = pd.DataFrame({"delay_arr_sec": [14620.0, 7200.0, 100.0]})
        out = utils.filter_implausible_delays(df)
        assert len(out) == 3

    def test_does_not_mutate_input(self):
        df = pd.DataFrame({"delay_arr_sec": [-5000.0, 10.0]})
        out = utils.filter_implausible_delays(df)
        assert len(df) == 2 and len(out) == 1

    def test_custom_threshold(self):
        df = pd.DataFrame({"delay_arr_sec": [-100.0, -50.0, 0.0]})
        out = utils.filter_implausible_delays(df, min_sec=-60.0)
        assert out["delay_arr_sec"].tolist() == [-50.0, 0.0]


# ---------------------------------------------------------------------------
# add_time_features
# ---------------------------------------------------------------------------

class TestAddTimeFeatures:
    def test_basic_features(self):
        df = pd.DataFrame({
            "ankunftszeit": pd.to_datetime([
                "2026-04-13 08:30:00",   # Montag, 08:30, Rush-Hour
                "2026-04-18 14:00:00",   # Samstag, 14:00, weekend
                "2026-04-15 12:00:00",   # Mittwoch, mittags, kein Rush
                "2026-04-13 17:30:00",   # Montag, 17:30, Rush-Hour
            ])
        })
        out = utils.add_time_features(df)
        assert list(out.columns) == ["ankunftszeit", "hour", "weekday_num",
                                     "weekday", "is_weekend", "is_rush_hour"]
        assert out["hour"].tolist() == [8, 14, 12, 17]
        assert out["weekday"].tolist() == ["Mo", "Sa", "Mi", "Mo"]
        assert out["is_weekend"].tolist() == [False, True, False, False]
        assert out["is_rush_hour"].tolist() == [True, False, False, True]

    def test_rush_hour_only_weekdays(self):
        # Samstag 08:00 ist KEINE Rush-Hour
        df = pd.DataFrame({"ankunftszeit": pd.to_datetime(["2026-04-18 08:00:00"])})
        out = utils.add_time_features(df)
        assert out["is_rush_hour"].iloc[0] is np.False_ or out["is_rush_hour"].iloc[0] == False

    def test_handles_invalid_dates(self):
        df = pd.DataFrame({"ankunftszeit": ["not-a-date", "2026-04-13 08:00:00"]})
        out = utils.add_time_features(df)
        assert pd.isna(out["hour"].iloc[0])
        assert out["hour"].iloc[1] == 8


# ---------------------------------------------------------------------------
# nearest_weather_station (KDTree)
# ---------------------------------------------------------------------------

class TestNearestWeatherStation:
    def test_zurich_returns_sma(self):
        # Zuerich HB liegt etwa bei 47.378, 8.540
        abbr, dist_km = utils.nearest_weather_station(47.378, 8.540)
        assert abbr == "SMA"
        assert dist_km < 5  # SMA ist sehr nah am HB

    def test_bern_returns_ber(self):
        # Bern HB ~46.948, 7.439
        abbr, dist_km = utils.nearest_weather_station(46.948, 7.439)
        assert abbr == "BER"

    def test_lugano_returns_lug(self):
        abbr, _ = utils.nearest_weather_station(46.005, 8.951)
        assert abbr == "LUG"

    def test_returns_in_taxonomy(self):
        # Egal welcher Punkt — Antwort muss in unserer Liste sein
        from app.utils import WEATHER_STATION_COORDS
        abbr, _ = utils.nearest_weather_station(46.5, 7.5)
        assert abbr in WEATHER_STATION_COORDS


def test_map_stations_to_weather():
    stations = pd.DataFrame({
        "name": ["Zuerich HB", "Bern HB"],
        "lat": [47.378, 46.948],
        "lon": [8.540, 7.439],
    })
    out = utils.map_stations_to_weather(stations)
    assert "nearest_weather_abbr" in out.columns
    assert "weather_distance_km" in out.columns
    assert out["nearest_weather_abbr"].iloc[0] == "SMA"
    assert out["nearest_weather_abbr"].iloc[1] == "BER"
    assert (out["weather_distance_km"] >= 0).all()


# ---------------------------------------------------------------------------
# DELAY_BUCKETS sanity
# ---------------------------------------------------------------------------

def test_delay_buckets_cover_continuum():
    """Buckets duerfen keine Luecken haben."""
    sorted_buckets = sorted(utils.DELAY_BUCKETS, key=lambda x: x[0])
    for i in range(len(sorted_buckets) - 1):
        assert sorted_buckets[i][1] == sorted_buckets[i+1][0], \
            f"Luecke zwischen {sorted_buckets[i]} und {sorted_buckets[i+1]}"


def test_delay_buckets_labels_unique():
    labels = [b[2] for b in utils.DELAY_BUCKETS]
    assert len(labels) == len(set(labels))
