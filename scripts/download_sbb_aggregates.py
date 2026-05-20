"""Download SBB monthly customer-punctuality aggregates (lightweight, for trend analysis).

Source: data.sbb.ch — dataset 'kundenpunktlichkeit-monat'.
Tries the Opendatasoft export URL first, with a few naming-variant fallbacks.

Output:
  data/raw/sbb_aggregates/punktlichkeit_monat.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import requests

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
OUT_DIR = Path(__file__).parent.parent / "data" / "raw" / "sbb_aggregates"

CANDIDATES = [
    # (label, url) — first that gives 200 wins
    ("v2.1-csv kundenpunktlichkeit-monat",
     "https://data.sbb.ch/api/explore/v2.1/catalog/datasets/"
     "kundenpunktlichkeit-monat/exports/csv?delimiter=%3B&use_labels=false"),
    ("v2.1-csv punktlichkeit-monat",
     "https://data.sbb.ch/api/explore/v2.1/catalog/datasets/"
     "punktlichkeit-monat/exports/csv?delimiter=%3B&use_labels=false"),
    ("v2.1-csv puenktlichkeit-monat",
     "https://data.sbb.ch/api/explore/v2.1/catalog/datasets/"
     "puenktlichkeit-monat/exports/csv?delimiter=%3B&use_labels=false"),
    ("v1-csv kundenpunktlichkeit-monat",
     "https://data.sbb.ch/api/records/1.0/download/?"
     "dataset=kundenpunktlichkeit-monat&format=csv&delimiter=%3B"),
    ("v2.1-csv kundenpunktlichkeit-fernverkehr-monat",
     "https://data.sbb.ch/api/explore/v2.1/catalog/datasets/"
     "kundenpunktlichkeit-fernverkehr-monat/exports/csv?delimiter=%3B"),
]


def try_download(label: str, url: str, out_path: Path) -> tuple[bool, str]:
    try:
        r = requests.get(url, timeout=60, headers={"User-Agent": USER_AGENT}, allow_redirects=True)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        # Schnelle Sanity: enthält Inhalt überhaupt etwas wie CSV?
        head = r.text[:300].lower()
        if "<html" in head or "doctype" in head:
            return False, "HTML statt CSV"
        if len(r.content) < 100:
            return False, f"zu klein ({len(r.content)} Bytes)"
        out_path.write_bytes(r.content)
        return True, f"{len(r.content)/1024:.1f} KB"
    except Exception as e:
        return False, f"Exception: {e}"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for label, url in CANDIDATES:
        out_path = OUT_DIR / f"{label.split()[1]}.csv"
        print(f"Versuch [{label}] ...", end=" ", flush=True)
        ok, msg = try_download(label, url, out_path)
        print(f"{'OK' if ok else 'FAIL'}: {msg}")
        if ok:
            preview = out_path.read_text(encoding="utf-8", errors="replace")[:500]
            print("\n--- Vorschau (erste 500 Zeichen) ---")
            print(preview)
            return 0
    print("\nKeine Variante hat funktioniert. Manueller Browser-Download notwendig.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
