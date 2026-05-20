"""Download Swiss train stations master data from SBB Open Data.

Source: data.sbb.ch — dataset 'dienststellen-gemass-opentransportdataswiss'
Saves a filtered CSV to data/raw/stations.csv with only active train stations
that have geographic coordinates. The 'number' column is the BPUIC join key
used by the Ist-Daten delay dataset.
"""

import sys
from pathlib import Path
import pandas as pd

URL = (
    "https://data.sbb.ch/api/explore/v2.1/catalog/datasets/"
    "dienststellen-gemass-opentransportdataswiss/exports/csv"
)

OUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUT_FILE = OUT_DIR / "stations.csv"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Lade Stationen-CSV von {URL[:80]}...")
    df = pd.read_csv(URL, sep=";", low_memory=False)
    print(f"Geladen: {len(df):,} Rohrecords, {df.shape[1]} Spalten")

    # Filter: aktive Bahn-Stationen mit Geo.
    # validto nutzt Sentinel '9999-12-31' für aktive Records (keine NaNs).
    # meansoftransport hat exakt 'TRAIN' oder Kombis wie 'BUS|TRAIN'.
    mask = (
        df["meansoftransport"].fillna("").str.contains("TRAIN", case=False)
        & (df["hasgeolocation"] == True)
        & (df["validto"] == "9999-12-31")
    )
    df_train = df.loc[mask].copy()
    print(f"Nach Filter (TRAIN, aktiv, mit Geo): {len(df_train):,} Stationen")

    # geopos = "lat, lon"-String (mit Leerzeichen) → in lat/lon splitten
    coords = df_train["geopos"].str.split(",", expand=True)
    df_train["lat"] = coords[0].str.strip().astype(float)
    df_train["lon"] = coords[1].str.strip().astype(float)

    # Schlanke Auswahl der für uns relevanten Spalten
    keep = [
        "number",  # BPUIC, Join-Key zu Ist-Daten
        "sloid",
        "designationofficial",
        "abbreviation",
        "cantonabbreviation",
        "cantonname",
        "lat",
        "lon",
        "meansoftransport",
    ]
    df_out = df_train[keep].copy()
    df_out.columns = df_out.columns.str.lower()

    df_out.to_csv(OUT_FILE, sep=";", index=False, encoding="utf-8")
    size_kb = OUT_FILE.stat().st_size / 1024
    rel = OUT_FILE.relative_to(OUT_DIR.parent.parent)
    print(f"OK: Gespeichert: {rel} ({size_kb:.1f} KB)")
    print(f"    Spalten: {list(df_out.columns)}")
    print(f"    Beispiel: {df_out.iloc[0].to_dict()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
