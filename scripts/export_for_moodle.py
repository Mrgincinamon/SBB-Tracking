"""Schnürt ein sauberes, lauffähiges Paket fürs Weitergeben (z.B. Moodle / Kollege).

Enthält: gesamter Code (app, scripts, notebooks, tests), Präsentation (PDF/PPTX),
und das fertige `delays_prepared.parquet` (~65 MB) — damit die App + Notebook 03
OHNE den langen Daten-Download laufen.

Ausgeschlossen (bewusst!):
  - .env            -> enthaelt deinen geheimen API-Key, NIE weitergeben
  - venv/           -> nicht portabel; Empfaenger macht `pip install -r requirements.txt`
  - data/raw/       -> ~720 MB Rohdaten, fuer die App nicht noetig
  - sbb_tracker.db  -> ~735 MB; nur mit --with-db einschliessen (fuer Notebook 01/02)
  - Caches, Temp-, Git-Dateien

Ausfuehren:
    venv\\Scripts\\python.exe scripts\\export_for_moodle.py            # ohne DB (~75 MB)
    venv\\Scripts\\python.exe scripts\\export_for_moodle.py --with-db  # mit DB (~800 MB)
Output: dist/SBB_Tracker_paket.zip
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = ROOT / "dist" / "SBB_Tracker_paket.zip"

# Verzeichnis-Namen, die komplett uebersprungen werden (an beliebiger Tiefe)
SKIP_DIRS = {
    "venv", ".git", ".claude", "__pycache__", ".ipynb_checkpoints",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist",
}
# Einzelne Pfade (relativ zum Projekt-Root), die ausgeschlossen werden
SKIP_RELPATHS = {
    ".env",                                  # GEHEIM: API-Key
    "data/processed/sbb_tracker.db",         # gross; nur mit --with-db
}


def should_skip(rel: Path, with_db: bool) -> bool:
    parts = set(rel.parts)
    if parts & SKIP_DIRS:
        return True
    posix = rel.as_posix()
    # Rohdaten ausschliessen (ausser dem .gitkeep zur Ordnerstruktur)
    if posix.startswith("data/raw/") and rel.name != ".gitkeep":
        return True
    # Temp-/Hilfsdateien aus scripts/
    if rel.parent.as_posix() == "scripts" and rel.name.startswith("_"):
        return True
    if rel.suffix in {".pyc", ".log"}:
        return True
    if rel.name == "sbb_tracker.db" and not with_db:
        return True
    if posix in SKIP_RELPATHS and not (with_db and posix.endswith("sbb_tracker.db")):
        return True
    return False


def main() -> int:
    with_db = "--with-db" in sys.argv[1:]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()

    leaked_env = False
    n_files = 0
    has_parquet = False
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            if should_skip(rel, with_db):
                continue
            if rel.name == ".env":          # doppelte Sicherheitsnaht
                leaked_env = True
                continue
            if rel.name == "delays_prepared.parquet":
                has_parquet = True
            zf.write(path, rel.as_posix())
            n_files += 1

    size_mb = OUT.stat().st_size / 1024**2
    print(f"OK: {OUT.relative_to(ROOT)}")
    print(f"    {n_files} Dateien, {size_mb:.0f} MB  (DB {'dabei' if with_db else 'NICHT dabei'})")
    print(f"    delays_prepared.parquet enthalten: {'JA' if has_parquet else 'NEIN (erst Notebook 02 ausfuehren!)'}")
    print(f"    .env (API-Key) ausgeschlossen: JA  <- nie weitergeben")
    if not has_parquet:
        print("    WARNUNG: kein Parquet gefunden -> Empfaenger muesste Daten selbst erzeugen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
