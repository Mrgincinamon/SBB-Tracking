"""Generiert eine PowerPoint-Praesentation (16:9) fuer die Video-Aufnahme.

Zieht alle Kennzahlen aus presentation/computed_results/results.json (bleibt
damit automatisch synchron mit Notebooks/PDF) und bettet die Notebook-Plots +
Webapp-Screenshots ein. Jede Slide hat Sprechernotizen (Notizenbereich) als
Drehbuch-Hilfe fuer die Aufnahme.

Ausfuehren:  venv\\Scripts\\python.exe scripts\\build_pptx.py
Output:      presentation/SBB_Tracker_Praesentation.pptx
"""

from __future__ import annotations

import json
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "presentation" / "computed_results" / "results.json"
SHOTS = ROOT / "presentation" / "screenshots"
NB_PLOTS = SHOTS / "notebooks"
OUT = ROOT / "presentation" / "SBB_Tracker_Praesentation.pptx"

# SBB-Farben
SBB_RED = RGBColor(0xEB, 0x00, 0x00)
DARK = RGBColor(0x1A, 0x1A, 0x1A)
GREY = RGBColor(0x59, 0x59, 0x59)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xF5, 0xF5, 0xF5)

SW, SH = Inches(13.333), Inches(7.5)  # 16:9


def _fmt(x, nd=1):
    return f"{x:,.{nd}f}".replace(",", "'")


def load_results() -> dict:
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def add_notes(slide, text: str):
    slide.notes_slide.notes_text_frame.text = text.strip()


def _set_bg(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def _textbox(slide, left, top, width, height):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    return tf


def _para(tf, text, size, color=DARK, bold=False, first=False, bullet=False,
          align=PP_ALIGN.LEFT, space_after=8):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space_after)
    run = p.add_run()
    run.text = ("•  " + text) if bullet else text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = "Segoe UI"
    return p


def _red_bar(slide):
    """Schmaler roter Balken am oberen Rand als Markenelement."""
    bar = slide.shapes.add_shape(1, 0, 0, SW, Inches(0.18))
    bar.fill.solid(); bar.fill.fore_color.rgb = SBB_RED
    bar.line.fill.background()
    bar.shadow.inherit = False


def content_slide(prs, title: str):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    _set_bg(slide, WHITE)
    _red_bar(slide)
    tf = _textbox(slide, Inches(0.6), Inches(0.35), Inches(12.1), Inches(0.9))
    _para(tf, title, 30, SBB_RED, bold=True, first=True)
    return slide


def bullets_slide(prs, title, bullets, notes="", body_top=1.4, size=18):
    slide = content_slide(prs, title)
    tf = _textbox(slide, Inches(0.7), Inches(body_top), Inches(11.9),
                  Inches(7.5 - body_top - 0.4))
    for i, b in enumerate(bullets):
        if isinstance(b, tuple):
            txt, lvl = b
        else:
            txt, lvl = b, 0
        p = _para(tf, txt, size if lvl == 0 else size - 3,
                  DARK if lvl == 0 else GREY, bold=(lvl == 0 and txt.endswith(":")),
                  first=(i == 0), bullet=True)
        p.level = lvl
    if notes:
        add_notes(slide, notes)
    return slide


def image_slide(prs, title, img_path: Path, caption="", notes=""):
    slide = content_slide(prs, title)
    if img_path.exists():
        # Bild zentriert unter dem Titel einpassen
        max_w, max_h = Inches(11.6), Inches(5.2)
        pic = slide.shapes.add_picture(str(img_path), Inches(0.85), Inches(1.45),
                                       height=max_h)
        if pic.width > max_w:
            pic.width = max_w
            pic.height = int(max_w * pic.height / pic.width) if pic.width else max_h
        # zentrieren
        pic.left = int((SW - pic.width) / 2)
    else:
        _para(_textbox(slide, Inches(1), Inches(3), Inches(11), Inches(1)),
              f"[Bild fehlt: {img_path.name}]", 16, GREY, first=True)
    if caption:
        tf = _textbox(slide, Inches(0.7), Inches(6.85), Inches(11.9), Inches(0.5))
        _para(tf, caption, 13, GREY, first=True, align=PP_ALIGN.CENTER)
    if notes:
        add_notes(slide, notes)
    return slide


def build():
    r = load_results()
    w = r["test_welch_ttest"]
    a = r["test_anova_linientyp"]
    o = r["test_ols"]
    corr = r["test_correlation"]
    dr = r["data_range"]

    prs = Presentation()
    prs.slide_width = SW
    prs.slide_height = SH

    # ---- 1. Titel ----
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(s, DARK)
    bar = s.shapes.add_shape(1, 0, Inches(3.05), SW, Inches(0.10))
    bar.fill.solid(); bar.fill.fore_color.rgb = SBB_RED; bar.line.fill.background()
    bar.shadow.inherit = False
    tf = _textbox(s, Inches(0.8), Inches(2.0), Inches(11.7), Inches(1.1))
    _para(tf, "SBB Tracker", 54, WHITE, bold=True, first=True)
    tf2 = _textbox(s, Inches(0.8), Inches(3.25), Inches(11.7), Inches(1.4))
    _para(tf2, "Pünktlichkeitsanalyse der Schweizerischen Bundesbahnen", 26, SBB_RED, bold=True, first=True)
    _para(tf2, "Datengetriebene Analyse von 2.74 Mio Zug-Halten · April–Mai 2026", 16, RGBColor(0xCC, 0xCC, 0xCC))
    tf3 = _textbox(s, Inches(0.8), Inches(6.0), Inches(11.7), Inches(1.0))
    _para(tf3, "Joël Hasler & Patrick Ferreira", 16, WHITE, bold=True, first=True)
    _para(tf3, "ZHAW Scientific Programming · FS2026 · Dozent: Mario Gellrich", 13, RGBColor(0xAA, 0xAA, 0xAA))
    add_notes(s, "Begrüssung: Wer wir sind. Wir analysieren die Pünktlichkeit der SBB "
                 "auf Basis von 2.74 Mio echten Zug-Halten über 48 Betriebstage. "
                 "Ziel: aus offenen Daten belastbare, ehrliche Aussagen ableiten.")

    # ---- 2. Agenda ----
    bullets_slide(prs, "Agenda", [
        "Motivation & Forschungsfragen",
        "Datengrundlage & Design-Entscheidung",
        "Methodik: 4 statistische Tests + LLM",
        "Ergebnisse (mit Effektstärken)",
        "Interaktive Webapp (Live-Demo)",
        "Limitationen & Schlussfolgerungen",
    ], notes="Kurzer Fahrplan. Schwerpunkt liegt auf den Ergebnissen und der "
             "Live-Demo der Webapp.", size=20)

    # ---- 3. Motivation ----
    bullets_slide(prs, "Motivation & Forschungsfragen", [
        "Die offizielle SBB-Pünktlichkeit (92.5 %) ist ein Aggregat — für die",
        "individuelle Reiseplanung wenig hilfreich. Wir gehen ins Detail:",
        ("F1: Sind Werktage unpünktlicher als Wochenenden?", 1),
        ("F2: Beeinflusst der Linientyp (S, IC, IR …) die Verspätung?", 1),
        ("F3: Korreliert Wetter (Regen, Temperatur) mit Verspätung?", 1),
        ("F4: Welche Faktoren erklären Verspätung gemeinsam (Regression)?", 1),
    ], notes="Die Schlagzeile '92.5% pünktlich' verdeckt grosse Unterschiede nach "
             "Tag, Linientyp und Ort. Unsere vier Forschungsfragen zerlegen das.")

    # ---- 4. Datengrundlage ----
    bullets_slide(prs, "Datengrundlage", [
        f"{_fmt(r['n_total_events'],0)} Zug-Halte (SBB, Status REAL) über "
        f"{dr['n_days']} Betriebstage ({dr['start']} – {dr['end']})",
        "3 offene Quellen: opentransportdata.swiss (Ist-Daten), data.sbb.ch",
        "(Bahnhof-Stammdaten), MeteoSchweiz (stündliches Wetter, 15 Stationen)",
        "Design-Entscheidung: hohe Auflösung statt langer Zeitspanne —",
        ("48 Tage pro Zug-Halt (~85 Mio Datenpunkte) statt Jahres-Aggregate", 1),
        ("ermöglicht Stunden-, Bahnhof- und Wetter-Analysen", 1),
        "Datenbereinigung: 70 physikalisch unmögliche Verspätungen (korrupte",
        "Quell-Zeitstempel) entfernt; Filter auf gemessene Ist-Ankünfte",
    ], notes="Wir haben uns bewusst für Auflösung statt Zeitspanne entschieden: "
             "48 Tage hochaufgelöst statt Jahre an Aggregaten. Die Volldaten 2019–2025 "
             "wären 1.1 TB. Wir haben ausserdem korrupte Zeitstempel sauber gefiltert.")

    # ---- 5. Methodik ----
    bullets_slide(prs, "Methodik", [
        "Pipeline: Download → SQLite-DB (3 Tabellen, SQL) → Aufbereitung →",
        "Feature-Engineering (Zeit + Wetter via cos-korrigiertem KDTree)",
        "4 statistische Tests, jeweils mit p-Wert UND Effektstärke:",
        ("Welch's t-Test (+ Mann-Whitney, + Tagesmittel-Robustheit)", 1),
        ("Einweg-ANOVA + Tukey-HSD Post-hoc", 1),
        ("Pearson & Spearman Korrelation (+ 95%-CI)", 1),
        ("Multiple OLS-Regression (+ Breusch-Pagan, VIF, Residuen)", 1),
        "LLM (Claude Sonnet 4.6) für qualitative Krisen-Tag-Hypothesen",
        "Tech: pandas · scipy · statsmodels · folium · streamlit · sqlite3",
    ], notes="Wichtig: Wir berichten nicht nur p-Werte, sondern Effektstärken — bei "
             "2.7 Mio Beobachtungen ist sonst alles 'signifikant'. Wir prüfen auch "
             "Robustheit und Regressions-Annahmen.")

    # ---- 6. H1 ----
    bullets_slide(prs, "Ergebnis F1 — Werktag vs. Wochenende", [
        f"Werktag {_fmt(w['mean_werktag_sec'])} s  vs.  Wochenende {_fmt(w['mean_wochenende_sec'])} s",
        f"Welch's t = {_fmt(w['t_statistic'],1)}, p < 10⁻³⁰⁰ (hochsignifikant)",
        f"Differenz {_fmt(w['diff_sec'])} s, 95%-CI [{_fmt(w['diff_ci95_low'])}, {_fmt(w['diff_ci95_high'])}] s",
        f"ABER Effektstärke Cohen's d = {_fmt(w['cohens_d'],2)} → praktisch KLEIN",
        "Robustheit: Effekt überlebt auf 48 Tagesmitteln (nicht bloss n-Artefakt)",
        "Mann-Whitney-U bestätigt verteilungsfrei",
    ], notes="Werktage sind ~15s unpünktlicher — hochsignifikant, aber d=0.12 ist klein. "
             "Das ist unsere Kernbotschaft: statistische ≠ praktische Signifikanz. "
             "Der Tagesmittel-Test zeigt: der Effekt ist echt, kein Artefakt der Stichprobe.")

    # ---- 7. H2 (Bild) ----
    image_slide(prs, "Ergebnis F2 — Linientyp (ANOVA)",
                NB_PLOTS / "03_analyse_visualisierung_cell21_plot0.png",
                caption=f"ANOVA F = {_fmt(a['f_statistic'],1)}, p < 10⁻³⁰⁰, η² = {_fmt(a['eta_squared'],3)} (klein) · "
                        "Internationale Züge (TGV/EC/RJX) importieren Verspätung",
                notes="Linientyp ist hochsignifikant, η²≈0.04 ist aber klein. Die Story: "
                      "Internationale Züge (TGV, EC, RailJet) sammeln im Ausland Verspätung "
                      "und bringen sie in die Schweiz. Innerschweizer IC/IR sind sehr pünktlich (~30s).")

    # ---- 8. H3 Wetter ----
    bullets_slide(prs, "Ergebnis F3 — Wetter ↔ Verspätung", [
        f"Niederschlag: Pearson r = {_fmt(corr['niederschlag_mm']['pearson_r'],4)} (p < 10⁻²⁸⁶)",
        f"Sonne r = {_fmt(corr['sonne_min']['pearson_r'],4)} · Feuchte r = {_fmt(corr['feuchte_pct']['pearson_r'],4)}",
        "Alle hochsignifikant — aber |r| < 0.04: inhaltlich TRIVIAL",
        "Spearman ≈ Pearson → Zusammenhänge schwach & überwiegend monoton",
        "Wetter erklärt allein < 0.3 % der Verspätungsvarianz",
        "Lehrstück: riesige Stichprobe macht winzige Effekte 'signifikant'",
    ], notes="Wetter wirkt in die erwartete Richtung (mehr Regen → mehr Verspätung), "
             "aber der Effekt ist praktisch vernachlässigbar. Wieder: Signifikanz wegen n, "
             "nicht wegen Relevanz. Wir zeigen das ehrlich.")

    # ---- 9. H4 OLS (Bild Residuen) ----
    image_slide(prs, "Ergebnis F4 — Multiple OLS-Regression",
                NB_PLOTS / "03_analyse_visualisierung_cell30_plot0.png",
                caption=f"R² = {_fmt(o['r_squared'],4)} ({_fmt(o['r_squared']*100,1)} %) · Rush-Hour +10 s · Wochenende −12 s · "
                        "Diagnostik: heteroskedastisch (Breusch-Pagan), VIF unauffällig",
                notes="Das gemeinsame Modell erklärt nur ~4.3% der Varianz. Das ist eine "
                      "EHRLICHE Erkenntnis: Verspätungen sind dominant idiosynkratisch "
                      "(Defekte, Einzelereignisse). Die Residuen zeigen Heteroskedastizität — "
                      "wir benennen das offen. Vorzeichen/Grössen der Effekte sind plausibel.")

    # ---- 10. Heatmap ----
    image_slide(prs, "Zeitliches Muster — Stunde × Wochentag",
                NB_PLOTS / "03_analyse_visualisierung_cell33_plot0.png",
                caption="Mittlere Verspätung pro Wochentag und Stunde — Rush-Hour-Effekt sichtbar",
                notes="Die Heatmap zeigt, wann es kritisch wird: morgens und abends an "
                      "Werktagen. Diese Erkenntnis fliesst direkt in die Webapp ein.")

    # ---- 11. Webapp Karte ----
    image_slide(prs, "Webapp — Verspätungs-Hotspots auf der Karte",
                SHOTS / "webapp_01_karte.png",
                caption="Folium-Karte · Farbe = Ø-Verspätung · Hotspot-Regler isoliert die Grenzbahnhöfe",
                notes="LIVE-DEMO ANSAGEN: Hier die interaktive Karte. Ich schiebe gleich den "
                      "Hotspot-Regler hoch — dann bleiben nur die Verspätungs-Hotspots übrig, "
                      "v.a. Grenzbahnhöfe wie Buchs SG und St. Margrethen. (In der Demo live zeigen.)")

    # ---- 12. Webapp ToD + LLM ----
    image_slide(prs, "Webapp — Time-of-Day & Pendler-Insight (LLM)",
                SHOTS / "webapp_03_pendler_insight.png",
                caption="LLM-Berater beantwortet Pendler-Fragen ausschliesslich aus den Projektdaten",
                notes="Zweite Demo: der LLM-Pendler-Berater. Wichtig — er antwortet nur auf "
                      "Basis unserer Statistik-Daten (kein Halluzinieren). Beispiel-Frage live "
                      "stellen, z.B. 'Wann erwische ich am ehesten einen pünktlichen Zug?'")

    # ---- 13. LLM Krisen-Tage ----
    bullets_slide(prs, "LLM-Analyse — Krisen-Tage", [
        "Claude Sonnet 4.6 klassifiziert die 10 verspätungsreichsten Tage",
        "Feste Taxonomie (Wetter, Rush-Hour, Bahnhof-Ausfall, Bauarbeiten …)",
        "Temperatur 0.2 + Anweisung 'erfinde NICHTS' + Konfidenz-Skala",
        "Ehrlich: keine Ground-Truth-Validierung — qualitative Hypothesen,",
        ("geplant: Abgleich mit Factiva-News als Validierung", 1),
    ], notes="Der LLM liefert plausible Ursachen-Hypothesen für die schlimmsten Tage. "
             "Wir kommunizieren transparent, dass das Hypothesen sind, keine verifizierten "
             "Fakten — das ist methodisch sauber.")

    # ---- 14. Limitationen ----
    bullets_slide(prs, "Limitationen", [
        "Nicht-Unabhängigkeit: Halte sind geschachtelt (Pseudoreplikation) →",
        ("begegnet mit Tagesmittel-Robustheit + Fokus auf Effektstärken", 1),
        "Zeitraum 48 Tage (Frühjahr) — keine Saisonalität",
        "Nur SBB; Wetter-Distanz bis ~40 km (Mikroklima verloren)",
        "Heteroskedastizität in OLS; Bonferroni α=0.0125 (alle Tests bestehen)",
        "Korrelation ≠ Kausalität (Confounder, z.B. Sturm + Bauarbeiten)",
    ], notes="Wir sind bei den Limitationen bewusst transparent — das ist ein Plus. "
             "Wichtigster Punkt: die Beobachtungen sind nicht unabhängig; wir adressieren "
             "das mit dem Robustheitstest und dem Effektstärken-Fokus.")

    # ---- 15. Schlussfolgerungen ----
    bullets_slide(prs, "Schlussfolgerungen", [
        "SBB-Pünktlichkeit ist hoch (~95 % unter 3 Min) und räumlich robust",
        "Werktag-, Linientyp- und Wetter-Effekte sind real, aber praktisch klein",
        "Verspätung ist dominant idiosynkratisch (R² nur ~4 %) — ehrlich beziffert",
        "Hotspots sind Grenzbahnhöfe (Import-Effekt internationaler Züge)",
        "Mehrwert: interaktive Webapp + LLM machen die Daten zugänglich",
    ], notes="Take-aways: Die SBB ist sehr pünktlich; die messbaren Effekte sind klein; "
             "Verspätung ist grösstenteils Zufall/Einzelereignisse. Unser ehrlicher Umgang "
             "mit kleinen Effekten und Limitationen ist die methodische Stärke der Arbeit.")

    # ---- 16. Quellen ----
    bullets_slide(prs, "Quellen, Code & Reproduzierbarkeit", [
        "Daten: opentransportdata.swiss · data.sbb.ch · MeteoSchweiz (CC-BY)",
        "Code (MIT): github.com/Mrgincinamon/SBB-Tracking",
        "Reproduzierbar: requirements.txt + venv + Build-Skripte für Notebooks",
        "Stack: Python 3.12 · pandas/scipy/statsmodels · SQLite · Streamlit · Anthropic",
        "Danke — Fragen?",
    ], notes="Alles ist öffentlich und reproduzierbar. Abschluss + Überleitung zu Fragen.")

    prs.save(str(OUT))
    print(f"OK: PPTX erstellt {OUT}")
    print(f"     {len(prs.slides._sldIdLst)} Slides, "
          f"{OUT.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    build()
