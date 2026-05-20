"""Extrahiert alle PNG-Plots aus den ausgefuehrten Notebooks als einzelne Dateien.

Liest die ipynb-JSON-Files, sucht jede Output-Cell mit `image/png`-Output und
schreibt sie als nummerierte PNGs in presentation/screenshots/notebooks/.

Sinn: Wir koennen die Plots direkt in die PDF einbetten oder im Anhang zeigen,
ohne Screenshots manuell machen zu muessen.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

NB_DIR = Path(__file__).parent.parent / "notebooks"
OUT_DIR = Path(__file__).parent.parent / "presentation" / "screenshots" / "notebooks"


def extract_from_notebook(nb_path: Path) -> int:
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    stem = nb_path.stem
    count = 0
    for cell_idx, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        for out_idx, out in enumerate(cell.get("outputs", [])):
            data = out.get("data", {})
            png_b64 = data.get("image/png")
            if not png_b64:
                continue
            png_bytes = base64.b64decode(png_b64)
            count += 1
            out_path = OUT_DIR / f"{stem}_cell{cell_idx:02d}_plot{out_idx}.png"
            out_path.write_bytes(png_bytes)
    print(f"  [{stem}] {count} Plot(s) extrahiert")
    return count


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for nb_path in sorted(NB_DIR.glob("*.ipynb")):
        if ".ipynb_checkpoints" in str(nb_path):
            continue
        total += extract_from_notebook(nb_path)
    print(f"\nFertig: {total} Plots in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
