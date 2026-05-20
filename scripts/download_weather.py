"""Download MeteoSchweiz hourly weather data for top Swiss railway hubs.

Source: data.geo.admin.ch — Collection ch.meteoschweiz.ogd-smn (Automated Weather Stations)
URL pattern:
  https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/<abbr-lower>/ogd-smn_<abbr-lower>_h_<scope>.csv
  scope = recent (last ~12 months) | historical (older)

Output:
  data/raw/weather/meta_stations.csv
  data/raw/weather/<abbr>_hourly_recent.parquet  per station
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import requests

USER_AGENT = "SBB-Tracker-Student/0.1 (haslejoe@protonmail.com)"
META_URL = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/ogd-smn_meta_stations.csv"
DATA_URL = ("https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/"
            "{abbr_lc}/ogd-smn_{abbr_lc}_h_{scope}.csv")

OUT_DIR = Path(__file__).parent.parent / "data" / "raw" / "weather"

# Top weather stations near major Swiss railway hubs (manuell ausgewählt).
# Mapping zum nächstgelegenen Bahnhof wird im Analysis-Notebook per KDTree gemacht.
STATIONS = [
    "SMA",  # Zürich / Fluntern → Zürich HB, Oerlikon, Stadelhofen
    "KLO",  # Zürich / Kloten → Zürich Flughafen
    "BER",  # Bern / Zollikofen → Bern
    "GVE",  # Genève / Cointrin → Genève, Genève-Aéroport
    "BAS",  # Basel / Binningen → Basel SBB
    "LUG",  # Lugano → Lugano
    "LUZ",  # Luzern → Luzern
    "STG",  # St. Gallen → St. Gallen, Winterthur
    "SIO",  # Sion → Sion, Brig
    "DAV",  # Davos → Davos
    "CHU",  # Chur → Chur
    "NEU",  # Neuchâtel → Neuchâtel, Yverdon
    "INT",  # Interlaken → Interlaken
    "WYN",  # Wynau (Mittelland) → Olten
    "MAG",  # Magadino-Cadenazzo → Bellinzona
]
SCOPES = ["recent"]  # "historical" könnten wir später für 2019-2024 dazunehmen


def download_meta() -> pd.DataFrame:
    print(f"Lade Meta-Stationen: {META_URL}")
    r = requests.get(META_URL, timeout=30, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    meta_path = OUT_DIR / "meta_stations.csv"
    meta_path.write_bytes(r.content)
    # MeteoSchweiz-CSVs sind ISO-8859-1 (enthalten é, ü, ö in Stationsnamen)
    df = pd.read_csv(meta_path, sep=";", encoding="latin-1")
    print(f"  {len(df)} Stationen in Meta-CSV")
    return df


def download_one(abbr: str, scope: str) -> tuple[bool, str, int]:
    """Download + Parquet-konvertieren. Return (ok, msg, n_rows)."""
    url = DATA_URL.format(abbr_lc=abbr.lower(), scope=scope)
    out_pq = OUT_DIR / f"{abbr}_hourly_{scope}.parquet"
    if out_pq.exists():
        return True, "skip (existiert)", 0
    try:
        r = requests.get(url, timeout=120, headers={"User-Agent": USER_AGENT})
        if r.status_code == 404:
            return False, "404 (Station/Scope nicht verfuegbar)", 0
        r.raise_for_status()
    except Exception as e:
        return False, f"FEHLER: {e}", 0
    tmp_csv = OUT_DIR / f"{abbr}_hourly_{scope}.csv"
    tmp_csv.write_bytes(r.content)
    df = pd.read_csv(tmp_csv, sep=";", encoding="latin-1")
    if "reference_timestamp" in df.columns:
        df["reference_timestamp"] = pd.to_datetime(
            df["reference_timestamp"], errors="coerce", dayfirst=True
        )
    df.columns = df.columns.str.lower()
    df.to_parquet(out_pq, compression="snappy", index=False)
    tmp_csv.unlink()
    return True, f"{out_pq.stat().st_size / 1024:.0f} KB", len(df)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = download_meta()

    available = set(meta["station_abbr"].dropna().str.upper().tolist())
    print(f"\nGeplante Stationen: {len(STATIONS)} | "
          f"davon in Meta: {sum(s in available for s in STATIONS)}")

    ok, fail = 0, []
    for abbr in STATIONS:
        if abbr not in available:
            print(f"  [{abbr}] NICHT in Meta — skip")
            fail.append(abbr)
            continue
        for scope in SCOPES:
            success, msg, n = download_one(abbr, scope)
            tag = "OK" if success else "ERR"
            print(f"  [{abbr}/{scope}] {tag}: {msg} ({n:,} Zeilen)")
            if success:
                ok += 1
            else:
                fail.append(f"{abbr}/{scope}")
            time.sleep(0.4)

    print(f"\nFertig: {ok}/{len(STATIONS)*len(SCOPES)} Files. Fehler: {fail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
