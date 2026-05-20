"""Automatisiert Screenshots der Streamlit-Webapp via Playwright.

Voraussetzung: Streamlit läuft auf http://localhost:8501
Output: presentation/screenshots/webapp_NN_*.png
"""

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"
OUT_DIR = Path(__file__).parent.parent / "presentation" / "screenshots"

TABS = [
    ("01_karte", "Karte"),
    ("02_time_of_day", "Time-of-Day"),
    ("03_pendler_insight", "Pendler-Insight"),
    ("04_about", "ber"),  # 'Über' Substring-Match
]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  device_scale_factor=2)
        page = ctx.new_page()
        page.set_default_timeout(60_000)

        print(f"Lade {URL} ...")
        page.goto(URL, wait_until="networkidle")
        # Streamlit braucht extra Zeit für Initial-Render der ersten Daten
        time.sleep(5)
        page.wait_for_selector("h1", timeout=30_000)

        # Page-screenshot der ganzen App (Default-Tab)
        whole = OUT_DIR / "00_overview.png"
        page.screenshot(path=str(whole), full_page=True)
        print(f"  Saved: {whole.name} ({whole.stat().st_size / 1024:.0f} KB)")

        # Tabs durchklicken und screenshoten
        for slug, tab_text in TABS:
            print(f"Klicke Tab fuer '{slug}' (Match: '{tab_text}')")
            try:
                # Streamlit-Tabs sind <button role="tab">; per Text-Substring matchen
                # weil Emoji nicht in Bytestream-Print darstellbar ist
                import re
                page.get_by_role("tab").filter(has_text=re.compile(tab_text)).first.click()
                time.sleep(3)
                if "karte" in slug or "time_of_day" in slug:
                    time.sleep(6)
            except Exception as e:
                print(f"  WARN: Konnte Tab nicht klicken: {type(e).__name__}")
                continue

            out = OUT_DIR / f"webapp_{slug}.png"
            page.screenshot(path=str(out), full_page=True)
            print(f"  Saved: {out.name} ({out.stat().st_size / 1024:.0f} KB)")

        browser.close()

    print(f"\nFertig. {len(list(OUT_DIR.glob('*.png')))} Screenshots in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
