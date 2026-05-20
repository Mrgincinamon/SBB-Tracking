"""Screenshot the Covid reference React app (running on :3000)."""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent.parent / "presentation" / "screenshots" / "covid_reference_app.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_context(viewport={"width": 1440, "height": 900},
                               device_scale_factor=2).new_page()
    page.set_default_timeout(60_000)
    page.goto("http://localhost:3000", wait_until="networkidle")
    time.sleep(6)
    page.screenshot(path=str(OUT), full_page=True)
    print(f"OK: {OUT.name} ({OUT.stat().st_size/1024:.0f} KB)")
    browser.close()
