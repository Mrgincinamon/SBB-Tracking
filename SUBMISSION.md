# Abgabe — SBB Tracker

**Frist:** 27.05.2026, 23:59 · **Plattform:** Moodle · **Gruppe:** Joël Hasler & Patrick Ferreira

## Was abgegeben wird (ZIP auf Moodle)

```
projectwork_SP_FS2026_group_XX.zip      (XX = eure Gruppennummer)
├── SBB_Tracker_Praesentation.pdf       offizielles Präsentationsdokument
└── SBB_Tracker_Video.mp4               ~10-Min-Video (Demo + Erklärung)
```

Der Code liegt zusätzlich öffentlich auf GitHub: https://github.com/Mrgincinamon/SBB-Tracking

## Status-Checkliste

| Artefakt | Status | Pfad |
|---|---|---|
| 4 Jupyter-Notebooks (DB, Aufbereitung, Analyse, LLM) | ✅ fertig | `notebooks/` |
| Statistik mit p-Werten **und Effektstärken** (4 Tests) | ✅ fertig | `notebooks/03_*` |
| Streamlit-Webapp (4 Tabs, SBB-Theme) | ✅ fertig | `app/streamlit_app.py` |
| SQLite-DB (3 Tabellen, SQL-Queries) | ✅ fertig | `notebooks/01_*` |
| LLM-Integration (Claude Sonnet 4.6) | ✅ fertig | `notebooks/04_*` + Webapp |
| Test-Suite (27 Tests) | ✅ grün | `tests/` |
| Öffentliches GitHub-Repo | ✅ public | GitHub-Link oben |
| Präsentation PDF | ✅ fertig | `presentation/SBB_Tracker_Praesentation.pdf` |
| PowerPoint-Foliendeck (für Video) | ✅ fertig | `presentation/SBB_Tracker_Praesentation.pptx` |
| **Video aufnehmen** | ⏳ offen | du + Patrick |
| **ZHAW-Recherche** (Statista/Factiva/Scopus) | ⏳ optional | siehe `WAKEUP_STATUS.md` |
| **ZIP packen + Moodle-Upload** | ⏳ offen | am 27.05. |

## Video-Drehbuch (~10 Min, Foliendeck = `.pptx` mit Sprechernotizen)

Die PowerPoint hat zu **jeder Slide Sprechernotizen** — im Präsentationsmodus
(Referentenansicht) sichtbar. Grober Ablauf:

| Zeit | Inhalt | Slides |
|---|---|---|
| 0:00–1:00 | Intro: Wer + Was + Forschungsfragen | 1–3 |
| 1:00–2:30 | Datengrundlage + Methodik | 4–5 |
| 2:30–5:30 | Ergebnisse F1–F4 (Fokus: signifikant **aber klein**) | 6–9 |
| 5:30–6:30 | Zeitliches Muster (Heatmap) | 10 |
| 6:30–8:30 | **Webapp Live-Demo**: Karte + Hotspot-Regler, Pendler-Insight-Frage | 11–13 |
| 8:30–10:00 | Limitationen + Schlussfolgerungen + GitHub | 14–16 |

**Tipp:** Die Webapp-Demo ist der visuelle Höhepunkt — Karte live filtern und
eine LLM-Frage stellen. Webapp vorher starten: `streamlit run app/streamlit_app.py`.

## Letzte Reproduzierbarkeits-Checks vor Abgabe

```powershell
& venv\Scripts\python.exe -m pytest tests\ -q        # 27 grün?
& venv\Scripts\python.exe scripts\build_pdf.py        # PDF aktuell?
& venv\Scripts\python.exe scripts\build_pptx.py       # PPTX aktuell?
```
