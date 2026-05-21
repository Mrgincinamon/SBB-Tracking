# SBB Tracker — Verspätungsanalyse Schweizer Bahnverbindungen

**ZHAW Scientific Programming** · FS2026 · Gruppenarbeit
**Autoren**: Joël Hasler & Patrick Ferreira
**Dozent**: Mario Gellrich

## Forschungsfragen

1. Unterscheidet sich die mittlere SBB-Verspätung zwischen Werktagen und Wochenende?
2. Beeinflusst der Linientyp (S-Bahn, IC, IR, RE) die Verspätung?
3. Korreliert Niederschlag oder Temperatur mit der Verspätung?
4. Welche Faktoren erklären Verspätung gemeinsam in einem multivariaten Modell?

## Hauptbefunde

Datenbasis: **48 Betriebstage** (31.03.–19.05.2026), **2.74 Mio** gemessene
Zug-Halte (Status REAL, aus 3.2 Mio Roh-Events gefiltert).

| Forschungsfrage | Ergebnis | Effektstärke |
|---|---|---|
| F1 Werktag vs. Wochenende | 50.1 s vs. 34.6 s, t = 95.0, p < 10⁻³⁰⁰ | **Cohen's d = 0.12 (klein)** |
| F2 Linientyp (ANOVA) | F = 8'450, p < 10⁻³⁰⁰ | **η² = 0.039 (klein)** |
| F3 Wetter ↔ Verspätung | alle p < 10⁻⁸⁰ | **\|r\| < 0.04 (trivial)** |
| F4 OLS-Regression | R² = 0.043 | erklärt nur ~4 % der Varianz |

**Kernaussage**: Bei n ≈ 2.7 Mio ist *jeder* Effekt statistisch signifikant —
die **Effektstärken** zeigen aber, dass die Unterschiede praktisch klein sind.
Verspätung ist dominant idiosynkratisch. Verspätungs-Hotspots sind die
**Grenzbahnhöfe** (Import-Effekt internationaler Züge). Detaillierte Resultate
inkl. p-Werten, CIs und Robustheits-Checks: `notebooks/03_analyse_visualisierung.ipynb`
und `presentation/SBB_Tracker_Praesentation.pdf`.

## Datenquellen

- **opentransportdata.swiss** — tägliche Ist-Daten (SBB-Soll/Ist-Vergleich), CC-BY
- **data.sbb.ch** — Stammdaten der Schweizer Bahnhöfe, CC-BY
- **MeteoSchweiz** — stündliche Wetterdaten, 15 Stationen, Open Data BY
- **Anthropic Claude Sonnet 4.6** — LLM für qualitative Krisen-Tag-Analyse

## Projektstruktur

```
project/
├── notebooks/
│   ├── 01_datenbank_speicherung.ipynb     SQLite-DB + 5 SQL-Beispielqueries
│   ├── 02_datenaufbereitung.ipynb         Filter, Wetter-Join, Klassifikation
│   ├── 03_analyse_visualisierung.ipynb    4 Stats-Tests + Plots
│   └── 04_llm_verspaetungsgruende.ipynb   LLM-Krisen-Tag-Analyse
├── scripts/
│   ├── download_stations.py               Bahnhof-Stammdaten
│   ├── download_istdaten.py               Tägliche Ist-Daten (Stream-Filter)
│   ├── download_weather.py                MeteoSchweiz, 15 Stationen
│   ├── _nb_builder.py                     Notebook-Build-Pipeline
│   └── build_notebook_NN.py               Re-build der Notebooks
├── app/
│   ├── streamlit_app.py                   Webapp (4 Tabs, SBB-Theme)
│   └── utils.py                           Geteilte Helper (DB, KDTree, Klassifikation)
├── tests/
│   └── test_utils.py                      pytest-Suite (27 Tests)
├── data/
│   ├── raw/        (gitignored, ~720 MB)
│   └── processed/  (gitignored, ~770 MB DB + Parquet)
├── .streamlit/
│   └── config.toml                        SBB-Theme (primaryColor #EB0000)
└── presentation/
    ├── SBB_Tracker_Praesentation.md       Quelle (Markdown)
    ├── SBB_Tracker_Praesentation.pdf      Abgabe-Dokument (markdown-pdf)
    ├── SBB_Tracker_Praesentation.pptx     Foliendeck für Video (mit Sprechernotizen)
    ├── computed_results/results.json      Maschinell berechnete Stats (Single Source)
    ├── notebook_renders/                  Notebooks als HTML
    └── screenshots/                       Webapp- + Notebook-Plots
```

Build-Skripte (`scripts/`): `build_notebook_NN.py`, `compute_results.py`
(Stats → results.json), `build_pdf.py`, `build_pptx.py`, `extract_notebook_plots.py`,
`capture_webapp_screenshots.py`.

## Setup (Reproduzierbarkeit)

```powershell
# 1. Repo klonen
git clone https://github.com/Mrgincinamon/SBB-Tracking
cd SBB-Tracking

# 2. Virtual Env + Dependencies
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Anthropic API-Key konfigurieren
Copy-Item .env.example .env
notepad .env    # ANTHROPIC_API_KEY eintragen

# 4. Jupyter-Kernel registrieren (für Notebooks)
& venv\Scripts\python.exe -m ipykernel install --user --name sbb-tracker --display-name "Python (SBB Tracker)"

# 5. Daten holen (kann ~30-90 Min dauern wegen 50 Daily-Ist-Daten-Files)
& venv\Scripts\python.exe scripts\download_stations.py
& venv\Scripts\python.exe scripts\download_weather.py
& venv\Scripts\python.exe scripts\download_istdaten.py 2026-03-31 2026-05-19

# 6. Notebooks 01-04 ausführen (entweder in VS Code öffnen + "Run All"
#    oder via Build-Scripts:)
& venv\Scripts\python.exe scripts\build_notebook_01.py
& venv\Scripts\python.exe scripts\build_notebook_02.py
& venv\Scripts\python.exe scripts\build_notebook_03.py
& venv\Scripts\python.exe scripts\build_notebook_04.py

# 7. Webapp starten
& venv\Scripts\streamlit.exe run app\streamlit_app.py
# Öffnet auf http://localhost:8501

# 8. (optional) Tests, Stats + Präsentation regenerieren
& venv\Scripts\python.exe -m pytest tests\ -q
& venv\Scripts\python.exe scripts\compute_results.py   # results.json
& venv\Scripts\python.exe scripts\build_pdf.py         # PDF
& venv\Scripts\python.exe scripts\build_pptx.py        # PowerPoint
```

## Webapp-Features (4 Tabs)

- **🗺️ Karte** — Folium-Heatmap der Bahnhof-Verspätungen; zwei Regler
  (Rauschfilter + Hotspot-Schwelle) isolieren die Verspätungs-Hotspots.
- **🕐 Time-of-Day** — interaktive Plotly-Heatmap Stunde × Wochentag mit Drilldown.
- **🤖 Pendler-Insight** — LLM-Berater (Claude Sonnet 4.6), antwortet
  ausschliesslich auf Basis der Projektdaten (keine Halluzination).
- **ℹ️ Über** — Datenquellen + Lizenzen.

Einheitliches SBB-Theme (`.streamlit/config.toml`, primaryColor `#EB0000`).

## Tech-Stack

- **Python 3.12** (kursvorgegeben)
- **pandas / numpy / scipy / statsmodels** — Daten + Statistik (inkl. Effektstärken,
  Konfidenzintervalle, Tukey-HSD, Breusch-Pagan, VIF)
- **matplotlib / seaborn / plotly** — Visualisierungen
- **sqlite3** — Datenbank (3 Tabellen, SQL-Queries)
- **folium / streamlit-folium** — Karte
- **streamlit** — Webapp
- **anthropic + python-dotenv** — LLM-Integration
- **pyarrow** — Parquet-I/O
- **pytest** — Test-Suite (27 Tests)
- **markdown-pdf / python-pptx** — Präsentation (PDF + PowerPoint)
- **nbformat + nbclient** — Notebook-Build-Pipeline

## Lizenzen

- **Code**: MIT
- **Daten**: CC-BY (SBB, opentransportdata.swiss, MeteoSchweiz)

## Bewertungs-Rubrik

Siehe `presentation/SBB_Tracker_Praesentation.pdf` Sektion 6 — alle 8
Mindestanforderungen + alle 6 Bonus-Punkte sind im Projekt abgedeckt.

## Abgabe

Details + Checkliste in [`SUBMISSION.md`](SUBMISSION.md). Kurz:

- **Abgabe (Moodle)**: ZIP mit `SBB_Tracker_Praesentation.pdf` + `SBB_Tracker_Video.mp4`
- **Video** (~10 Min): Live-Demo der Webapp + Notebook-Highlights — die
  PowerPoint (`presentation/SBB_Tracker_Praesentation.pptx`, mit Sprechernotizen)
  dient als Foliendeck.
- **Frist**: 27.05.2026, 23:59
