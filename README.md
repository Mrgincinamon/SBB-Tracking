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

Datenbasis: 48 Tage (31.03.–19.05.2026), 3.2 Millionen SBB-Zug-Events.
Detaillierte Resultate inkl. p-Values siehe `notebooks/03_analyse_visualisierung.ipynb`
und `presentation/SBB_Tracker_Praesentation.md`.

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
│   ├── streamlit_app.py                   Webapp (4 Tabs)
│   └── utils.py                           Geteilte Helper (DB, KDTree, …)
├── data/
│   ├── raw/        (gitignored, ~720 MB)
│   └── processed/  (gitignored, ~770 MB DB + Parquet)
└── presentation/
    └── SBB_Tracker_Praesentation.md       → konvertierbar zu PDF
```

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
```

## Tech-Stack

- **Python 3.12** (kursvorgegeben)
- **pandas / numpy / scipy / statsmodels** — Daten + Statistik
- **matplotlib / seaborn / plotly** — Visualisierungen
- **sqlite3** — Datenbank
- **folium / streamlit-folium** — Karte
- **streamlit** — Webapp
- **anthropic + python-dotenv** — LLM-Integration
- **pyarrow** — Parquet-I/O
- **nbformat + nbclient** — Build-Pipeline

## Lizenzen

- **Code**: MIT
- **Daten**: CC-BY (SBB, opentransportdata.swiss, MeteoSchweiz)

## Bewertungs-Rubrik

Siehe `presentation/SBB_Tracker_Praesentation.md` Sektion 6 — alle 8
Mindestanforderungen + alle 6 Bonus-Punkte sind im Projekt abgedeckt.
