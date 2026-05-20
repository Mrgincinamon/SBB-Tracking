"""Download SBB Ist-Daten (actual data) per day and convert to filtered Parquet.

Source: opentransportdata.swiss — CKAN dataset 'istdaten'.
For each day in range:
  1. Look up resource URL via CKAN API
  2. Stream-download CSV
  3. Filter PRODUKT_ID == 'Zug' and BETREIBER_ABK == 'SBB' (in chunks)
  4. Compute delay_arr_sec / delay_dep_sec
  5. Save as Parquet, delete raw CSV

Usage:
    python download_istdaten.py                       # last 3 available days (pilot)
    python download_istdaten.py 2026-02-01 2026-04-30 # explicit date range
"""

from __future__ import annotations

import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

DATASET_PAGE = "https://data.opentransportdata.swiss/dataset/istdaten"
BASE_URL = "https://data.opentransportdata.swiss"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
CHUNK_ROWS = 250_000
HTTP_BUF = 1 << 16
SLEEP_BETWEEN = 1.5  # politeness

OUT_DIR = Path(__file__).parent.parent / "data" / "raw" / "istdaten"
COLS_TO_PARSE = ["BETRIEBSTAG", "ANKUNFTSZEIT", "AN_PROGNOSE", "ABFAHRTSZEIT", "AB_PROGNOSE"]

# Regex extracts: full path = /dataset/<dsuuid>/resource/<resuuid>/download/YYYY-MM-DD_istdaten.csv
RES_RE = re.compile(
    r"/dataset/[0-9a-f-]+/resource/[0-9a-f-]+/download/(\d{4}-\d{2}-\d{2})_istdaten\.csv"
)


def get_resource_map() -> dict[str, str]:
    """Scrape dataset HTML page for daily resource URLs (CKAN API is 403-blocked)."""
    print(f"Lade Dataset-Page: {DATASET_PAGE}")
    r = requests.get(DATASET_PAGE, timeout=30, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    html = r.text
    out: dict[str, str] = {}
    for m in RES_RE.finditer(html):
        path = m.group(0)
        d = m.group(1)
        fname = f"{d}_istdaten.csv"
        if fname not in out:  # erste Treffer bevorzugen (latest version)
            out[fname] = BASE_URL + path
    print(f"  {len(out)} tägliche Ist-Daten-Resources auf der Seite gelistet")
    return out


def parse_date_range(argv: list[str], available: list[date]) -> list[date]:
    """Return list of dates to download."""
    if len(argv) == 0:
        # Pilot: last 3 verfügbare Tage
        recent = sorted(available, reverse=True)[:3]
        return sorted(recent)
    if len(argv) != 2:
        raise SystemExit("Brauche genau START_DATE und END_DATE (YYYY-MM-DD) oder gar keine Args")
    start = datetime.strptime(argv[0], "%Y-%m-%d").date()
    end = datetime.strptime(argv[1], "%Y-%m-%d").date()
    if end < start:
        raise SystemExit("END_DATE liegt vor START_DATE")
    days = [start + timedelta(d) for d in range((end - start).days + 1)]
    return days


def stream_download(url: str, dst: Path) -> int:
    """Stream-download to dst. Returns bytes written."""
    r = requests.get(url, stream=True, timeout=300,
                     headers={"User-Agent": USER_AGENT}, allow_redirects=True)
    r.raise_for_status()
    n = 0
    with open(dst, "wb") as f:
        for chunk in r.iter_content(HTTP_BUF):
            if chunk:
                f.write(chunk)
                n += len(chunk)
    return n


def filter_to_parquet(csv_path: Path, parquet_path: Path) -> tuple[int, int]:
    """Read CSV in chunks, filter to Zug+SBB, save Parquet. Returns (raw_rows, kept_rows)."""
    raw_total = 0
    kept_chunks: list[pd.DataFrame] = []
    for chunk in pd.read_csv(
        csv_path,
        sep=";",
        chunksize=CHUNK_ROWS,
        low_memory=False,
        dtype={"BPUIC": "Int64", "LINIEN_ID": "string", "LINIEN_TEXT": "string"},
    ):
        raw_total += len(chunk)
        mask = (chunk["PRODUKT_ID"] == "Zug") & (chunk["BETREIBER_ABK"] == "SBB")
        sub = chunk.loc[mask].copy()
        if len(sub) == 0:
            continue
        # Datetime-Spalten konvertieren
        for c in COLS_TO_PARSE:
            if c in sub.columns:
                sub[c] = pd.to_datetime(sub[c], errors="coerce", dayfirst=True)
        # Verspätungen in Sekunden
        sub["delay_arr_sec"] = (sub["AN_PROGNOSE"] - sub["ANKUNFTSZEIT"]).dt.total_seconds()
        sub["delay_dep_sec"] = (sub["AB_PROGNOSE"] - sub["ABFAHRTSZEIT"]).dt.total_seconds()
        kept_chunks.append(sub)
    if not kept_chunks:
        return raw_total, 0
    df = pd.concat(kept_chunks, ignore_index=True)
    df.columns = df.columns.str.lower()
    df.to_parquet(parquet_path, compression="snappy", index=False)
    return raw_total, len(df)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    resources = get_resource_map()
    available_dates = sorted({
        datetime.strptime(n[:10], "%Y-%m-%d").date()
        for n in resources.keys()
    })
    if not available_dates:
        raise SystemExit("Keine Daily-Resources gefunden — CKAN-Schema geändert?")
    print(f"  Datumsbereich verfügbar: {available_dates[0]} bis {available_dates[-1]}")

    wanted = parse_date_range(sys.argv[1:], available_dates)
    print(f"Geplant: {len(wanted)} Tag(e): {wanted[0]} bis {wanted[-1]}")

    grand_raw, grand_kept, errors = 0, 0, []
    for d in wanted:
        fname = f"{d.isoformat()}_istdaten.csv"
        pq_path = OUT_DIR / f"{d.isoformat()}_sbb.parquet"
        if pq_path.exists():
            print(f"[{d}] Parquet existiert bereits — skip")
            continue
        if fname not in resources:
            print(f"[{d}] FEHLT in CKAN — skip (Archiv-Tag?)")
            errors.append(d)
            continue
        url = resources[fname]
        csv_path = OUT_DIR / fname
        t0 = time.time()
        print(f"[{d}] Download...", end=" ", flush=True)
        try:
            n_bytes = stream_download(url, csv_path)
            dl_s = time.time() - t0
            print(f"{n_bytes/1024/1024:.1f} MB in {dl_s:.0f}s", end=" | ", flush=True)
            t1 = time.time()
            raw, kept = filter_to_parquet(csv_path, pq_path)
            filt_s = time.time() - t1
            csv_path.unlink()
            pq_kb = pq_path.stat().st_size / 1024
            print(f"Filter: {raw:,} -> {kept:,} ({filt_s:.0f}s) | Parquet: {pq_kb:,.0f} KB")
            grand_raw += raw
            grand_kept += kept
        except Exception as e:
            print(f"FEHLER: {e}")
            if csv_path.exists():
                csv_path.unlink()
            errors.append(d)
        time.sleep(SLEEP_BETWEEN)

    print("\n=== ZUSAMMENFASSUNG ===")
    print(f"Tage erfolgreich: {len(wanted) - len(errors)}/{len(wanted)}")
    print(f"Roh-Records gesamt: {grand_raw:,}")
    print(f"Gefiltert (Zug+SBB): {grand_kept:,} ({100*grand_kept/max(grand_raw,1):.1f}%)")
    if errors:
        print(f"Fehler-Tage: {errors}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
