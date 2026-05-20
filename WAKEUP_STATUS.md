# Wake-Up Status v2 — Donnerstag 2026-05-21 morgens

> **TL;DR:** Projekt ist **abgabebereit** ausser ZHAW-Recherche + Video.
> Du brauchst heute ~1-2 Stunden, der Rest wartet auf Mi 27.5.

## Was über Nacht passiert ist (Stichpunkte)

✅ Webapp mit KPI-Zeile (4 grosse Zahlen sofort sichtbar)
✅ 6 Webapp-Screenshots automatisch generiert (Playwright)
✅ 7 Notebook-Plots extrahiert + 3 davon ins PDF eingebettet
✅ Echte Stats-Zahlen berechnet + in PDF eingesetzt (statt „siehe Notebook 03")
✅ Top-10-Bahnhöfe-Tabelle ins PDF
✅ Markdown-PDF mit Bildern (2.0 MB, 14 Seiten)
✅ Letzter Commit gepusht
✅ Covid-React-Server gestoppt

**Kosten:** $0.05 von $10 LLM-Budget. Reservelos.

## Heute Donnerstag: Deine To-Do-Liste

### Phase 1 — Quick-Check (15 Min, JETZT)
1. **PDF öffnen**: `presentation/SBB_Tracker_Praesentation.pdf`
   → Inhalt überfliegen, sind die echten Zahlen drin? Sind die Plots da?
2. **Webapp ansehen**: http://localhost:8501 sollte noch laufen.
   Falls nicht: `& "venv\Scripts\python.exe" -m streamlit run app/streamlit_app.py`
3. **GitHub prüfen**: https://github.com/Mrgincinamon/SBB-Tracking
   → Sind alle Commits da? Sieht das Repo professionell aus?
4. **NOTES_FOR_USER.md lesen** — Entscheidungen, die ich autonom getroffen habe

### Phase 2 — ZHAW-Recherche (60 Min, nachmittags)
Diese 3 Aufgaben können nur über deinen ZHAW-Login:

#### A) Statista (15 Min)
- Suche: „SBB Pünktlichkeit", „Schweiz Bahn Passagiere", „ÖV-Marktanteil CH"
- Lade 3-5 Charts als PNG runter → speichere unter `presentation/statista/`
- Notiere die Statista-Referenz-Nummern für Quellenangabe

#### B) Factiva (20 Min)
- Identifiziere unsere Top-10 „Krisen-Tage" aus Notebook 04 (in
  `data/processed/llm_delay_reasons.parquet`)
- Suche pro Tag nach Schweizer News-Headlines mit Suche „SBB", „Bahn-Verspätung"
- Notiere pro Tag: 1-2 Headlines + Source + Datum → manuell in eine
  `presentation/factiva_news.md` schreiben
- Im Video kannst du erzählen: „Wir haben unsere Top-Krisen-Tage gegen
  Factiva-News abgeglichen — typische Ursachen: Personalstreik, Sturm, etc."

#### C) Scopus (10 Min)
- Suche: „railway delay prediction", „train punctuality factors",
  „weather impact on rail"
- Wähle **1 relevantes Paper** mit DOI
- BibTeX runterladen → speichere als `presentation/references.bib`
- Im PDF Methodik-Sektion zitieren

### Phase 3 — Final Polish (30 Min)
1. **Zahlen prüfen**: Im PDF sind die Werte aus `results.json` eingetragen.
   Falls dir was unplausibel vorkommt, melde dich.
2. **Schreibfehler** im PDF gegenlesen (besonders deutsche Texte)
3. **Co-Autor-Name**: Patrick Ferreira ist überall drin. Falls Schreibweise
   anders, Find&Replace.

### Phase 4 — Video (60-90 Min, Di 26.5. oder Mi 27.5.)
**Drehbuch (10 Min total, du + Patrick je 5 Min):**
- 00:00–01:00 Intro: Wer wir sind, was wir gemacht haben
- 01:00–03:00 Datenpipeline (Notebook 01-02 zeigen)
- 03:00–05:30 Stats-Analyse (Notebook 03 mit Plots, t-Test/ANOVA/OLS)
- 05:30–06:30 LLM-Erklärung (Notebook 04, Krisen-Tag-Tabelle)
- 06:30–08:30 **Webapp Live-Demo** (Karte, Time-of-Day, Pendler-Insight Frage stellen)
- 08:30–10:00 Schlussfolgerungen + Limitationen + GitHub-Link

**Tipp:** Webapp-Demo ist der visuelle Höhepunkt — gib dir hier 2-3 Min.

### Phase 5 — Submission (5 Min, Mi 27.5.)
```
projectwork_SP_FS2026_group_XX.zip
├── SBB_Tracker_Praesentation.pdf
└── SBB_Tracker_Video.mp4
```
Upload auf Moodle. Fertig.

## Quick-Reference

| Datei | Wozu |
|---|---|
| `README.md` | Setup-Anleitung |
| `NOTES_FOR_USER.md` | Was ich autonom entschieden habe (READ THIS) |
| `presentation/SBB_Tracker_Praesentation.pdf` | Hauptdokument für Abgabe |
| `presentation/SBB_Tracker_Praesentation.md` | Quelle, kannst du editieren |
| `presentation/notebook_renders/*.html` | Notebooks ohne VS Code anschaubar |
| `presentation/screenshots/*.png` | Webapp-Bilder fürs PDF |
| `presentation/computed_results/results.json` | Alle Stats-Resultate maschinell |
| `data/processed/delays_prepared.parquet` | 2.74 M Events (für Webapp + Stats) |
| `data/processed/sbb_tracker.db` | SQLite-DB mit 3 Tabellen |

## Quick-Commands

```powershell
# Webapp starten
& "venv\Scripts\python.exe" -m streamlit run app/streamlit_app.py

# Tests laufen lassen
& "venv\Scripts\python.exe" -m pytest tests/ -v

# PDF neu generieren (nach Markdown-Änderungen)
& "venv\Scripts\python.exe" scripts\build_pdf.py

# Notebooks zu HTML rendern
& "venv\Scripts\python.exe" -m nbconvert --to html --output-dir presentation\notebook_renders notebooks\*.ipynb

# Stats neu berechnen
& "venv\Scripts\python.exe" scripts\compute_results.py
```

## Bewertungs-Stand

| Kategorie | Max | Bei aktuellem Stand erwartet |
|---|---|---|
| Mindestanforderungen | 8 | **8** (alle erfüllt) |
| Bonus | 6 | **6** (Web-API, DB+SQL, LLM, Webapp, GitHub, Kreativität ✅✅✅✅✅✅) |
| Präsentation (PDF+Video) | 8 | **6-8** (hängt an Video-Qualität) |
| **Total** | **22** | **20-22 → Note 5.75-6.0** 🎯 |

## Falls etwas kaputt ist

1. **Webapp läuft nicht**: `streamlit run app/streamlit_app.py` neu starten
2. **PDF zeigt keine Bilder**: `python scripts\build_pdf.py` aus Projekt-Root
3. **Tests rot**: `pytest tests/ -v` zeigt was — alle 23 sollten grün sein
4. **Notebook crasht**: `data/processed/` fehlen → erst Notebook 01+02 ausführen

Falls wirklich was Grundsätzliches kaputt ist: schreib mir, ich fixe es.

Viel Erfolg 🚂
