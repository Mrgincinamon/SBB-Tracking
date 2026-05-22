# SBB Tracker: Pünktlichkeitsanalyse der Schweizerischen Bundesbahnen

ZHAW Scientific Programming, FS2026 (Gruppenarbeit)
Autoren: Joël Hasler & Patrick Ferreira
Dozent: Mario Gellrich

## Worum es geht

Die SBB veröffentlicht eine Gesamt-Pünktlichkeit von rund 92.5 %. Diese eine
Zahl sagt einem aber wenig, wenn man wissen will, wann und wo es konkret hakt.
Wir haben deshalb die offenen Ist-Daten der SBB ausgewertet und uns vier Fragen
gestellt:

1. Sind Züge an Werktagen unpünktlicher als am Wochenende?
2. Hat der Linientyp (S-Bahn, IC, IR, RE …) einen Einfluss auf die Verspätung?
3. Hängt das Wetter (Regen, Temperatur) mit der Verspätung zusammen?
4. Welche Faktoren erklären die Verspätung zusammen in einem Regressionsmodell?

## Wichtigste Ergebnisse

Grundlage sind 48 Betriebstage (31.03.–19.05.2026) mit 2.74 Millionen gemessenen
Zug-Halten (Status REAL, aus 3.2 Millionen Rohdaten gefiltert).

| Frage | Ergebnis | Effektstärke |
|---|---|---|
| F1 Werktag vs. Wochenende | 50.1 s vs. 34.6 s, t = 95.0, p < 10⁻³⁰⁰ | Cohen's d = 0.12 (klein) |
| F2 Linientyp (ANOVA) | F = 8'450, p < 10⁻³⁰⁰ | η² = 0.039 (klein) |
| F3 Wetter und Verspätung | alle p < 10⁻⁸⁰ | \|r\| < 0.04 (trivial) |
| F4 OLS-Regression | R² = 0.043 | erklärt nur ~4 % der Varianz |

Bei 2.7 Millionen Beobachtungen wird fast jeder Unterschied statistisch
signifikant. Genau deshalb berichten wir zusätzlich die Effektstärken, und die
fallen durchweg klein aus. Die Unterschiede sind also real, aber für die
Reiseplanung kaum spürbar. Der grösste Teil der Verspätung lässt sich mit
unseren Variablen nicht erklären; sie entsteht überwiegend aus einzelnen,
schwer vorhersehbaren Ereignissen. Auffällig ist die Geografie: die grössten
Verspätungen treten an den Grenzbahnhöfen auf, weil internationale Züge ihre
Verspätung aus dem Ausland mitbringen.

Die ausführlichen Resultate mit p-Werten, Konfidenzintervallen und
Robustheits-Checks stehen in `notebooks/03_analyse_visualisierung.ipynb` und in
`presentation/SBB_Tracker_Praesentation.pdf`.

## Datenquellen

- opentransportdata.swiss: tägliche Ist-Daten (Soll/Ist-Vergleich der SBB), CC-BY
- data.sbb.ch: Stammdaten der Schweizer Bahnhöfe, CC-BY
- MeteoSchweiz: stündliche Wetterdaten von 15 Stationen, Open Data
- Anthropic Claude Sonnet 4.6: LLM für die qualitative Analyse der Krisen-Tage

## Projektstruktur

```
project/
├── notebooks/
│   ├── 01_datenbank_speicherung.ipynb     SQLite-DB + SQL-Beispielqueries
│   ├── 02_datenaufbereitung.ipynb         Filter, Wetter-Join, Klassifikation
│   ├── 03_analyse_visualisierung.ipynb    4 Statistik-Tests + Plots
│   └── 04_llm_verspaetungsgruende.ipynb   LLM-Analyse der Krisen-Tage
├── scripts/                               Download-, Build- und Stats-Skripte
├── app/
│   ├── streamlit_app.py                   Webapp (4 Tabs, SBB-Theme)
│   └── utils.py                           Geteilte Helfer (DB, KDTree, Klassifikation)
├── tests/
│   └── test_utils.py                      pytest-Suite (27 Tests)
├── data/
│   ├── raw/        (gitignored, ~720 MB)
│   └── processed/  (gitignored, ~770 MB DB + Parquet)
├── .streamlit/
│   └── config.toml                        SBB-Theme (primaryColor #EB0000)
└── presentation/
    ├── SBB_Tracker_Praesentation.md       Quelle (Markdown)
    ├── SBB_Tracker_Praesentation.pdf      Abgabe-Dokument
    ├── SBB_Tracker_Praesentation.pptx     Foliendeck fürs Video (mit Sprechernotizen)
    ├── computed_results/results.json      maschinell berechnete Statistik-Werte
    ├── notebook_renders/                  Notebooks als HTML
    └── screenshots/                       Webapp- und Notebook-Plots
```

Die Skripte in `scripts/` erzeugen die Notebooks (`build_notebook_NN.py`), die
Statistik-Werte (`compute_results.py`), das PDF (`build_pdf.py`), die PowerPoint
(`build_pptx.py`) sowie die Plots und Screenshots.

## Installation und Ausführung

```powershell
# 1. Repo klonen
git clone https://github.com/Mrgincinamon/SBB-Tracking
cd SBB-Tracking

# 2. Virtuelle Umgebung + Abhängigkeiten
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. API-Key hinterlegen
Copy-Item .env.example .env
notepad .env    # ANTHROPIC_API_KEY eintragen

# 4. Jupyter-Kernel registrieren (für die Notebooks)
& venv\Scripts\python.exe -m ipykernel install --user --name sbb-tracker --display-name "Python (SBB Tracker)"

# 5. Daten holen (dauert wegen der ~50 Tagesdateien gut eine halbe bis ganze Stunde)
& venv\Scripts\python.exe scripts\download_stations.py
& venv\Scripts\python.exe scripts\download_weather.py
& venv\Scripts\python.exe scripts\download_istdaten.py 2026-03-31 2026-05-19

# 6. Notebooks ausführen (in VS Code "Run All" oder über die Build-Skripte)
& venv\Scripts\python.exe scripts\build_notebook_01.py
& venv\Scripts\python.exe scripts\build_notebook_02.py
& venv\Scripts\python.exe scripts\build_notebook_03.py
& venv\Scripts\python.exe scripts\build_notebook_04.py

# 7. Webapp starten
& venv\Scripts\streamlit.exe run app\streamlit_app.py
# läuft auf http://localhost:8501

# 8. Optional: Tests, Statistik und Präsentation neu erzeugen
& venv\Scripts\python.exe -m pytest tests\ -q
& venv\Scripts\python.exe scripts\compute_results.py
& venv\Scripts\python.exe scripts\build_pdf.py
& venv\Scripts\python.exe scripts\build_pptx.py
```

## Die Webapp

Die Streamlit-App hat vier Tabs:

- Karte: eine Folium-Heatmap der Verspätung pro Bahnhof. Über zwei Regler
  (Mindestanzahl Halte und Mindest-Verspätung) lassen sich die Hotspots
  herausfiltern.
- Time-of-Day: eine interaktive Heatmap Stunde × Wochentag mit Drilldown.
- Pendler-Insight: ein Berater auf Basis von Claude Sonnet 4.6, der nur mit den
  Zahlen aus dem Projekt antwortet und nichts dazuerfindet.
- Über: Datenquellen und Lizenzen.

Das Erscheinungsbild ist über `.streamlit/config.toml` einheitlich im SBB-Rot
gehalten.

## Verwendete Technologien

- Python 3.12 (Kursvorgabe)
- pandas, numpy, scipy, statsmodels für Daten und Statistik. Neben den Tests
  berechnen wir auch Effektstärken, Konfidenzintervalle, Tukey-HSD,
  den Breusch-Pagan-Test und VIF.
- matplotlib, seaborn, plotly für die Visualisierungen
- sqlite3 als Datenbank (3 Tabellen, SQL-Abfragen)
- folium und streamlit-folium für die Karte
- streamlit für die Webapp
- anthropic und python-dotenv für die LLM-Anbindung
- pyarrow für das Parquet-Format
- pytest für die Tests (27 Stück)
- markdown-pdf und python-pptx für die Präsentation
- nbformat und nbclient für die Notebook-Erzeugung

## Lizenzen

Code unter MIT, Daten unter CC-BY (SBB, opentransportdata.swiss, MeteoSchweiz).

## KI-Deklaration

### KI-Tools

Wir haben Claude von Anthropic eingesetzt, hauptsächlich über das
Kommandozeilen-Werkzeug Claude Code (Modelle der Opus- und Sonnet-Reihe).
Zusätzlich läuft in der Webapp Claude Sonnet 4.6 als Antwort-Modell für den
Pendler-Insight-Tab.

Eingesetzt wurde die KI breit: beim Schreiben und Debuggen des Python-Codes
(Download-Skripte, Notebooks, Streamlit-App, Tests), beim Aufbau der
statistischen Auswertung und der Visualisierungen sowie beim Verfassen der
Dokumentation und der Präsentation. Auch die Folien der Video-Präsentation
(inkl. der 6 User-Story-Slides mit selbst generierten Charakter-Illustrationen)
wurden mit Claude erstellt.

Eigene Leistung: _[bitte ehrlich ergänzen: Themen- und Fragestellung, Auswahl
der Datenquellen, inhaltliche Entscheidungen, Prüfung und Korrektur der
KI-Ausgaben, Interpretation der Ergebnisse, Aufnahme des Videos. Hier ausserdem
die Aufteilung zwischen Joël und Patrick festhalten.]_

### Prompt-Vorgehen

Wir haben iterativ gearbeitet: Aufgabe und Kontext beschreiben, Vorschlag
prüfen, nachschärfen. Bei der Statistik haben wir gezielt auf wissenschaftliche
Sorgfalt geachtet (Effektstärken statt nur p-Werte, ehrliche Limitationen).
_[bitte ergänzen: ein bis zwei konkrete Beispiel-Prompts, falls gewünscht.]_

### Reflexion

Die KI hat vor allem Tempo und Breite gebracht; ein Einzelner hätte Pipeline,
Webapp und Auswertung in der Zeit kaum in dieser Tiefe gebaut. Gleichzeitig war
ständige Kontrolle nötig: An einer Stelle hat das Modell einen Fachpunkt falsch
eingeordnet, an anderer Stelle hätten unsaubere Quelldaten unbemerkt das
Ergebnis verzerrt. Wir haben das abgesichert, indem alle Zahlen über
reproduzierbare Skripte und Tests entstehen und nicht von Hand übernommen
werden. _[bitte ergänzen: eigene Einschätzung zu Nutzen und Grenzen.]_

## Abgabe

Eine Checkliste steht in [`SUBMISSION.md`](SUBMISSION.md). Kurz zusammengefasst:
Auf Moodle kommt ein ZIP mit `SBB_Tracker_Praesentation.pdf` und dem
Video (`SBB_Tracker_Video.mp4`). Das Video (rund 10 Minuten) zeigt eine
Live-Demo der Webapp und die wichtigsten Punkte aus den Notebooks; als
Foliengrundlage dient die PowerPoint mit Sprechernotizen. Frist ist der
27.05.2026, 23:59.
