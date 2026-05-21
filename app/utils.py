"""Geteilte Helper-Funktionen für SBB Tracker Notebooks und Webapp.

Wird sowohl von den Jupyter Notebooks (01-03) als auch von der Streamlit-App
importiert. Bündelt:
- DB-Zugriff (`get_connection`, `query`)
- Verspätungs-Klassifizierung (`classify_delay`)
- Stations↔Wetter-Mapping über KDTree (`nearest_weather_station`)
- Zeit-Features (`add_time_features`)
"""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Pfade
# ---------------------------------------------------------------------------

def project_root() -> Path:
    """Find the project root by walking upwards until we see app/ + notebooks/."""
    p = Path.cwd()
    for parent in [p, *p.parents]:
        if (parent / "app").is_dir() and (parent / "notebooks").is_dir():
            return parent
    # Fallback: this file's grandparent (app/utils.py → project root)
    return Path(__file__).resolve().parent.parent


def db_path() -> Path:
    return project_root() / "data" / "processed" / "sbb_tracker.db"


# ---------------------------------------------------------------------------
# Datenbank
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """Open a connection to the SBB Tracker SQLite DB."""
    p = db_path()
    if not p.exists():
        raise FileNotFoundError(
            f"DB nicht gefunden unter {p}. Erst Notebook 01 ausführen, "
            "um die Datenbank zu erstellen."
        )
    return sqlite3.connect(p)


def query(sql: str, params: tuple | None = None) -> pd.DataFrame:
    """Run a parameterized SQL query and return a DataFrame. Connection auto-closed."""
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Verspätungs-Klassifizierung (klassisches SBB-Schema)
# ---------------------------------------------------------------------------

DELAY_BUCKETS = [
    (-np.inf, -30, "frueh_30+s"),
    (-30, 0, "frueh_unter_30s"),
    (0, 60, "puenktlich_unter_1min"),
    (60, 180, "leicht_1_3min"),
    (180, 300, "verspaetet_3_5min"),
    (300, 600, "stark_5_10min"),
    (600, np.inf, "extrem_ueber_10min"),
]


def classify_delay(seconds: float) -> str:
    """Map a delay value in seconds to a human-readable bucket label."""
    if pd.isna(seconds):
        return "unbekannt"
    for low, high, label in DELAY_BUCKETS:
        if low <= seconds < high:
            return label
    return "unbekannt"


def add_delay_class(df: pd.DataFrame, col: str = "delay_arr_sec",
                    out: str = "delay_class") -> pd.DataFrame:
    """Add a delay-class column based on `col` (e.g. delay_arr_sec)."""
    df = df.copy()
    df[out] = df[col].apply(classify_delay)
    return df


def is_classically_delayed(seconds: float, threshold: float = 180.0) -> bool:
    """SBB-offizielle Definition: Ankunft >3 Min nach Soll = Verspätung."""
    if pd.isna(seconds):
        return False
    return seconds > threshold


# ---------------------------------------------------------------------------
# Plausibilitäts-Filter für Verspätungswerte
# ---------------------------------------------------------------------------

# Ankünfte mehr als 10 Minuten VOR Fahrplan sind an getakteten SBB-Halten
# physikalisch nicht möglich. Stichproben zeigen: solche Werte stammen aus
# fehlerhaften Soll-Zeitstempeln im Quell-Feed (z.B. Soll-Datum mehrere Tage
# nach dem Betriebstag, v.a. bei Nacht-/Auslandszügen NJ/EC). Wir entfernen sie.
# Grosse POSITIVE Verspätungen bleiben erhalten — sie sind reale Störungen
# (z.B. Auslandszüge, die im Ausland Verspätung akkumulieren).
MIN_PLAUSIBLE_DELAY_SEC = -600.0


def filter_implausible_delays(df: pd.DataFrame, col: str = "delay_arr_sec",
                              min_sec: float = MIN_PLAUSIBLE_DELAY_SEC) -> pd.DataFrame:
    """Entferne physikalisch unmögliche Negativ-Verspätungen (korrupte
    Soll-Zeitstempel). Behält NaN-Werte NICHT (die werden separat gefiltert)
    und alle Werte >= `min_sec`."""
    return df.loc[df[col] >= min_sec].copy()


# ---------------------------------------------------------------------------
# Zeit-Features
# ---------------------------------------------------------------------------

WEEKDAY_NAMES_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def add_time_features(df: pd.DataFrame, ts_col: str = "ankunftszeit") -> pd.DataFrame:
    """Add hour, weekday, is_weekend, rush_hour columns derived from a timestamp column."""
    df = df.copy()
    ts = pd.to_datetime(df[ts_col], errors="coerce")
    df["hour"] = ts.dt.hour
    df["weekday_num"] = ts.dt.weekday  # 0=Mo … 6=So
    df["weekday"] = df["weekday_num"].apply(
        lambda i: WEEKDAY_NAMES_DE[int(i)] if pd.notna(i) and 0 <= i < 7 else None
    )
    df["is_weekend"] = df["weekday_num"].isin([5, 6])
    # Rush Hour = Stunden 6-8 (06:00-08:59) und 16-18 (16:00-18:59) an Werktagen.
    # `between` ist inklusiv -> 6,7,8 bzw. 16,17,18.
    df["is_rush_hour"] = (~df["is_weekend"]) & (
        df["hour"].between(6, 8) | df["hour"].between(16, 18)
    )
    return df


# ---------------------------------------------------------------------------
# Stations → nächstgelegene Wetterstation via KDTree
# ---------------------------------------------------------------------------

# Mapping MeteoSchweiz-Stations-Abk. → (lat, lon) (manuell aus meta_stations.csv)
WEATHER_STATION_COORDS = {
    "SMA": (47.3784, 8.5660),
    "KLO": (47.4800, 8.5360),
    "BER": (46.9908, 7.4646),
    "GVE": (46.2477, 6.1276),
    "BAS": (47.5418, 7.5836),
    "LUG": (46.0044, 8.9601),
    "LUZ": (47.0367, 8.3010),
    "STG": (47.4253, 9.3996),
    "SIO": (46.2188, 7.3308),
    "DAV": (46.8127, 9.8438),
    "CHU": (46.8703, 9.5302),
    "NEU": (47.0000, 6.9533),
    "INT": (46.6724, 7.8704),
    "WYN": (47.2538, 7.7878),
    "MAG": (46.1601, 8.9337),
}


@lru_cache(maxsize=1)
def _weather_kdtree():
    """Build (and cache) a scipy KDTree over weather station coords."""
    from scipy.spatial import cKDTree
    abbrs = list(WEATHER_STATION_COORDS.keys())
    coords = np.array([WEATHER_STATION_COORDS[a] for a in abbrs])
    return abbrs, cKDTree(coords)


def nearest_weather_station(lat: float, lon: float) -> tuple[str, float]:
    """Return (station_abbr, distance_km) of the closest weather station."""
    abbrs, tree = _weather_kdtree()
    dist, idx = tree.query([lat, lon])
    # KDTree returns Euclidean in degrees; rough conversion to km
    # 1 deg lat ≈ 111 km, 1 deg lon ≈ 111 km * cos(lat)
    return abbrs[int(idx)], float(dist * 111)


def map_stations_to_weather(stations: pd.DataFrame,
                            lat_col: str = "lat",
                            lon_col: str = "lon") -> pd.DataFrame:
    """Add `nearest_weather_abbr` and `weather_distance_km` columns to a stations DF."""
    out = stations.copy()
    res = out.apply(
        lambda r: nearest_weather_station(r[lat_col], r[lon_col]),
        axis=1, result_type="expand"
    )
    res.columns = ["nearest_weather_abbr", "weather_distance_km"]
    return pd.concat([out, res], axis=1)
