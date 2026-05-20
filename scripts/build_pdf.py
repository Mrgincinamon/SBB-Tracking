"""Convert presentation Markdown to PDF via markdown-pdf library."""

import sys
from pathlib import Path

from markdown_pdf import MarkdownPdf, Section


SRC = Path(__file__).parent.parent / "presentation" / "SBB_Tracker_Praesentation.md"
DST = Path(__file__).parent.parent / "presentation" / "SBB_Tracker_Praesentation.pdf"

CSS = """
body { font-family: sans-serif; line-height: 1.45; }
h1 { color: #1a4d80; border-bottom: 2px solid #1a4d80; padding-bottom: 4px; }
h2 { color: #2c5f9b; margin-top: 1.5em; }
h3 { color: #444; }
table { border-collapse: collapse; margin: 1em 0; }
th, td { border: 1px solid #ddd; padding: 4px 8px; }
th { background: #f0f4f8; }
code { background: #f6f8fa; padding: 2px 4px; border-radius: 3px; font-size: 0.9em; }
pre { background: #f6f8fa; padding: 8px; border-radius: 4px; overflow-x: auto; }
blockquote { border-left: 4px solid #ccc; padding-left: 12px; color: #555; }
"""


def main() -> int:
    if not SRC.exists():
        print(f"FEHLER: {SRC} nicht gefunden")
        return 1
    text = SRC.read_text(encoding="utf-8")
    pdf = MarkdownPdf(toc_level=2, optimize=True)
    pdf.add_section(Section(text, toc=True), user_css=CSS)
    pdf.meta["title"] = "SBB Tracker — Praesentation"
    pdf.meta["author"] = "Joel Hasler & Patrick Ferreira"
    pdf.save(str(DST))
    print(f"OK: PDF erstellt {DST}")
    print(f"     Groesse: {DST.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
