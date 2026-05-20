"""Helper module for building Jupyter notebooks programmatically.

Provides:
- md(text): markdown cell
- code(text): code cell
- header_cell(): Gellrich-Konvention header (libraries + settings)
- footer_cell(): Gellrich-Konvention system info footer
- save_and_run(notebook, path): write .ipynb, execute it, print summary
"""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

import nbformat
from nbclient import NotebookClient


def _strip_first_line_indent(text: str) -> str:
    """Strip the indent of the first non-empty line from every line that starts with it.

    Robuster als textwrap.dedent, weil eingebettete Triple-Quote-Strings mit
    0-Indent-Content nicht stoeren (sie behalten ihren originalen Indent).
    """
    if text.startswith("\n"):
        text = text[1:]
    lines = text.split("\n")
    first = next((l for l in lines if l.strip()), "")
    indent = len(first) - len(first.lstrip())
    prefix = " " * indent
    out = []
    for line in lines:
        if line.startswith(prefix):
            out.append(line[indent:])
        else:
            out.append(line)
    return "\n".join(out).rstrip() + "\n"


def md(text: str) -> dict:
    """Markdown cell from text (auto-dedented)."""
    return nbformat.v4.new_markdown_cell(_strip_first_line_indent(text))


def code(text: str) -> dict:
    """Code cell from text (auto-dedented). Tolerant gegenueber eingebetteten Strings."""
    return nbformat.v4.new_code_cell(_strip_first_line_indent(text))


HEADER_CODE = dedent('''
    # Bibliotheken und Einstellungen
    import os
    import sqlite3
    import warnings
    from pathlib import Path

    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns

    warnings.filterwarnings("ignore")
    sns.set_theme(color_codes=True)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.width", 140)

    PROJECT_ROOT = Path.cwd()
    if PROJECT_ROOT.name == "notebooks":
        PROJECT_ROOT = PROJECT_ROOT.parent
    DATA_RAW = PROJECT_ROOT / "data" / "raw"
    DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    print("Aktuelles Verzeichnis:", os.getcwd())
    print("Projekt-Root:", PROJECT_ROOT)
''').strip()


FOOTER_CODE = dedent('''
    # System-Info (Reproduzierbarkeits-Footer)
    import platform
    from platform import python_version
    from datetime import datetime

    print("-----------------------------------")
    print(os.name.upper())
    print(platform.system(), "|", platform.release())
    print("Datetime:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("Python Version:", python_version())
    print("-----------------------------------")
''').strip()


def header_cell() -> dict:
    return code(HEADER_CODE)


def footer_cell() -> dict:
    return code(FOOTER_CODE)


def build_notebook(cells: list, title: str) -> nbformat.NotebookNode:
    """Wrap cells into a notebook object with proper metadata."""
    nb = nbformat.v4.new_notebook()
    nb.cells = cells
    nb.metadata = {
        "kernelspec": {
            "display_name": "Python (SBB Tracker)",
            "language": "python",
            "name": "sbb-tracker",
        },
        "language_info": {
            "name": "python",
            "version": "3.12.10",
            "mimetype": "text/x-python",
            "file_extension": ".py",
        },
        "title": title,
    }
    return nb


def save_and_run(nb: nbformat.NotebookNode, path: Path, run: bool = True) -> bool:
    """Write notebook, optionally execute it, save again with outputs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, path)
    print(f"[notebook] Geschrieben: {path.name}  ({len(nb.cells)} Cells)")
    if not run:
        return True
    try:
        client = NotebookClient(
            nb,
            timeout=600,
            kernel_name="sbb-tracker",
            resources={"metadata": {"path": str(path.parent)}},
        )
        client.execute()
        nbformat.write(nb, path)
        n_err = sum(
            1 for cell in nb.cells
            if cell.cell_type == "code"
            and any(o.get("output_type") == "error" for o in cell.get("outputs", []))
        )
        print(f"[notebook] Ausgefuehrt OK. Fehler-Cells: {n_err}/"
              f"{sum(1 for c in nb.cells if c.cell_type == 'code')}")
        return n_err == 0
    except Exception as e:
        print(f"[notebook] EXECUTE FEHLER: {type(e).__name__}: {e}")
        nbformat.write(nb, path)
        return False
