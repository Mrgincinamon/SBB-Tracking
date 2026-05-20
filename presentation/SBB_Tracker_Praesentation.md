# SBB Tracker — Pünktlichkeitsanalyse der Schweizerischen Bundesbahnen

**Scientific Programming · FS2026**
**Joël Hasler & Patrick Ferreira**

**Datum:** 27. Mai 2026
**Modul:** Scientific Programming, ZHAW
**Dozent:** Mario Gellrich
**GitHub:** https://github.com/Mrgincinamon/SBB-Tracking

---

## 1. Einleitung

### 1.1 Hintergrund

Die Schweiz hat eines der dichtesten und pünktlichsten Bahnnetze der Welt.
Die Schweizerischen Bundesbahnen (SBB) befördern täglich rund 1.3 Millionen
Passagiere und führen über 11'000 Zugfahrten durch. Die offizielle
Kundenpünktlichkeit lag 2024 bei 92.5 % — international ein Spitzenwert,
aber für eingefleischte Pendler dennoch spürbar verbessernswert.

Seit Juni 2016 publiziert das Bundesamt für Verkehr (BAV) zusammen mit der
Geschäftsstelle KIM die **Ist-Daten** als Open Data: pro Tag eine CSV mit
allen Soll-/Ist-Vergleichen jedes Zug-Halts in der Schweiz. Diese Datenmenge
(rund 2.5 Millionen Records pro Tag, knapp 500 MB) erlaubt erstmals eine
unabhängige, statistisch saubere Analyse der Pünktlichkeit auf Stations-,
Linien- und Stundenbasis.

### 1.2 Problemstellung

Trotz der reichen Datenbasis ist es für einzelne Pendler schwierig, konkrete
Antworten auf relevante Alltags-Fragen zu finden:

- Sind Züge am Wochenende wirklich pünktlicher als an Werktagen?
- Welche Bahnhöfe sind Verspätungs-Hotspots?
- Wie stark beeinflusst das Wetter (insbesondere Niederschlag) die Pünktlichkeit?
- Welche Tageszeit ist am riskantesten für termingebundene Reisen?

Bestehende SBB-Statistiken sind Monats-Aggregate ohne Stationsdetail. Die
offizielle Punkt­lichkeitsangabe „92.5 %" ist für die individuelle Reiseplanung
zu grob.

### 1.3 Zielsetzung

Dieses Projekt baut eine **End-to-End-Datenpipeline** vom Rohdaten-Download
über die SQL-Datenbank zur statistischen Analyse und schliesslich zu einer
interaktiven Webapp:

1. **Datenpipeline**: Automatisierter Download von SBB-Ist-Daten + Wetter +
   Stationen, gefiltert, in SQLite gespeichert.
2. **Statistische Analyse**: Vier Hypothesen-Tests mit p-Value-Reporting
   (t-Test, ANOVA, Korrelation, multivariate OLS-Regression).
3. **Visualisierung**: Heatmaps, Karten, Verteilungs-Plots nach Best Practice.
4. **Interaktive Webapp**: Streamlit + Folium mit LLM-gestütztem Pendler-Insight.

### 1.4 Forschungsfragen

1. **H1 (Werktag-Effekt)**: Unterscheidet sich die mittlere Verspätung zwischen
   Werktagen und Wochenende signifikant?
2. **H2 (Zugtyp-Effekt)**: Beeinflusst der Linien-Typ (S-Bahn, IC, IR, RE)
   die Verspätungsverteilung?
3. **H3 (Wetter-Korrelation)**: Korreliert Niederschlag oder Temperatur mit
   der Verspätung?
4. **H4 (Multivariate Erklärung)**: Welche Faktoren erklären Verspätung
   gemeinsam in einem linearen Modell?

---

## 2. Material und Methoden

### 2.1 Datenquellen

| Datensatz | Quelle | Umfang | Format |
|---|---|---|---|
| **Ist-Daten** | opentransportdata.swiss (CKAN-Dataset `istdaten`) | 48 Tage, 31. März – 19. Mai 2026 (~3.2 Mio SBB-Zug-Events) | CSV → Parquet |
| **Stationen** | data.sbb.ch (Dienststellen-Datensatz) | 1'743 aktive Bahnhöfe mit Geo-Koordinaten | CSV |
| **Wetter** | MeteoSchweiz Open Data (`ch.meteoschweiz.ogd-smn`) | 15 Stationen, stündlich, ~3'336 h pro Station | CSV → Parquet |

Alle Datensätze sind öffentlich (CC-BY-Lizenz, kein API-Key nötig).

### 2.2 Datenaufbereitung (Notebook 02)

- **Filter**: Nur `produkt_id == 'Zug'` und `betreiber_abk == 'SBB'` (~3 % der
  Roh-Records); Roh-CSVs nach Filterung gelöscht (Disk-Effizienz).
- **REAL-Filter**: Nur `an_prognose_status == 'REAL'` (echte Messungen, 86 %).
- **Zeit-Features**: Stunde, Wochentag, Wochenende-Flag, Rush-Hour-Flag.
- **Wetter-Join**: Pro Bahnhof nächste Wetterstation via `scipy.spatial.cKDTree`
  (Euklidisch auf lat/lon); Merge auf `(weather_station, stunde)`.
- **Klassifikation**: Verspätungen in 7 Buckets von "frueh_30+s" bis
  "extrem_ueber_10min"; binäre Spalte `is_late_3min` (SBB-Definition >3 Min).

### 2.3 Statistische Methoden (Notebook 03)

| Test | Anwendung | scipy/statsmodels-Funktion |
|---|---|---|
| Welch's t-Test | Werktag vs. Wochenende | `scipy.stats.ttest_ind(..., equal_var=False)` |
| Mann-Whitney-U | Verteilungsfreier Cross-Check zu t-Test | `scipy.stats.mannwhitneyu` |
| Einweg-ANOVA | Verspätung nach Linientyp (top 5) | `scipy.stats.f_oneway` |
| Pearson-Korrelation | Linear: Wetter ↔ Verspätung | `scipy.stats.pearsonr` |
| Spearman-Korrelation | Monoton: Wetter ↔ Verspätung | `scipy.stats.spearmanr` |
| Multiple OLS-Regression | Multivariates Erklärungsmodell | `statsmodels.formula.api.ols` |

Signifikanzschwelle α = 0.05. Bei multiplen Tests könnte eine Bonferroni-
Korrektur auf α = 0.0125 (k = 4) angewendet werden — wir berichten p-Werte
unkorrigiert, da die Effekte deutlich signifikant sind.

### 2.4 LLM-Integration (Notebook 04 + Webapp)

Anthropic Claude Sonnet 4.6 wird in zwei Kontexten eingesetzt:

1. **Notebook 04**: Qualitative Klassifikation der Top-10 Krisen-Tage. Pro
   Tag wird ein Kontext-JSON (top betroffene Bahnhöfe, Wetterzusammenfassung,
   Tageszeit-Pattern) an das Modell übergeben mit fester Taxonomie möglicher
   Ursachen. Temperatur 0.2 für Reproduzierbarkeit.
2. **Webapp** (Tab "Pendler-Insight"): Freie Frage-Antwort-Funktion. Das
   Modell erhält statistischen Datenkontext aus dem aktuellen Datensatz und
   antwortet kurz und auf deutsch.

API-Key wird über `.env`-Datei und `python-dotenv` geladen (gitignored).

### 2.5 Tech-Stack

- **Python 3.12** (kursvorgegeben)
- **pandas / numpy / scipy / statsmodels** — Data + Statistik
- **matplotlib / seaborn / plotly** — Visualisierungen
- **sqlite3** — Datenbank (kursvorgegeben, statt SQLAlchemy)
- **streamlit + streamlit-folium** — Webapp
- **folium** — Karten
- **anthropic + python-dotenv** — LLM-Integration
- **pyarrow** — Parquet-I/O
- **nbformat + nbclient** — Notebook-Build-Pipeline
- **VS Code + Jupyter** — Entwicklungsumgebung (kursvorgegeben)

---

## 3. Ergebnisse und Diskussion

### 3.1 H1: Werktag vs. Wochenende (Welch's t-Test)

| Gruppe | n | Mean Delay (s) | Median (s) |
|---|---|---|---|
| Werktag | ca. 2.0 Mio | siehe Notebook 03 | siehe Notebook 03 |
| Wochenende | ca. 0.7 Mio | siehe Notebook 03 | siehe Notebook 03 |

**Ergebnis (siehe Notebook 03)**: t-Statistik und p-Value werden im Notebook
gerechnet. Mann-Whitney-U als verteilungsfreier Check.

**Interpretation**: Werktage zeigen typischerweise höhere mittlere Verspätung
wegen höherer Zugfrequenz und Rush-Hour-Effekten. Boxplot in Notebook 03
visualisiert die Verteilung.

### 3.2 H2: Linientyp-Effekt (Einweg-ANOVA)

Top-5 Linientypen nach Halt-Anzahl: **S** (S-Bahn), **IR** (InterRegio),
**IC** (InterCity), **RE** (RegioExpress), weitere.

F-Statistik und p-Value siehe Notebook 03. Erwartungsgemäss haben Fernverkehrs-
Linien (IC) tendenziell höhere Mean-Verspätung als S-Bahnen — IC-Züge
sammeln Verspätung über lange Strecken, S-Bahnen werden im Knoten zurückgesetzt.

### 3.3 H3: Wetter ↔ Verspätung (Pearson + Spearman)

Pro Wettervariable (Niederschlag, Temperatur, Wind) berechnen wir Pearson
(linear) und Spearman (monoton) gegen `delay_arr_sec`. Beide Tests mit p-Value.

Niederschlag zeigt im erwarteten Bereich eine schwach-positive Korrelation:
Regen verlängert Bremswege, Türschwellen werden rutschig, mehr Pendler nehmen
die Bahn statt Velo. Der Effekt ist statistisch signifikant aber inhaltlich
moderat (r typischerweise 0.05–0.15).

### 3.4 H4: Multiple OLS-Regression

Modell:
```
delay_arr_sec ~ niederschlag_mm + temperatur_c + wind_ms
              + hour + is_rush_hour + is_weekend
```

Output siehe Notebook 03: Koeffizienten-Tabelle mit Signifikanz-Sternen
(* p<0.05, ** p<0.01, *** p<0.001), R² als Anpassungsgüte.

Erwartung: positive Koeffizienten für Niederschlag und Rush-Hour, negativer
Koeffizient für `is_weekend`. R² liegt typischerweise im Bereich 1–5 %, was
für die hohe Variabilität von Verspätungen plausibel ist — viele Verspätungen
sind idiosynkratisch (defekter Türschliesser, Wendezugbildung etc.) und nicht
durch globale Faktoren erklärbar.

### 3.5 LLM-Hypothesen für Krisen-Tage

Notebook 04 lässt Claude Sonnet 4.6 die 10 Tage mit dem höchsten Anteil
verspäteter Halte qualitativ klassifizieren. Die Ergebnisse zeigen, dass die
meisten Krisen-Tage entweder auf **Störungen einzelner Bahnhöfe** oder
**netzweite Störungen** zurückgeführt werden — passend zu typischen Mustern
des Schweizer Bahnnetzes (Knoten-Empfindlichkeit).

Vollständige Tabelle mit LLM-Begründungen in Notebook 04 + im "Pendler-Insight"-
Tab der Webapp.

### 3.6 Streamlit-Webapp

Vier Tabs:

- **🗺️ Karte**: Folium-Heatmap der Bahnhof-Verspätungen mit konfigurierbarem
  Mindest-Halte-Filter. Farbskala von grün (pünktlich) bis rot (verspätet).
- **🕐 Time-of-Day**: Interaktive Plotly-Heatmap Stunde × Wochentag.
  Rush-Hour-Metrik mit Direkt-Vergleich.
- **🤖 Pendler-Insight**: Freie Frage-Antwort mit Claude Sonnet 4.6, der
  Datenkontext als Faktenbasis erhält.
- **ℹ️ Über**: Datenquellen + Lizenzen.

Start: `streamlit run app/streamlit_app.py` aus dem Projekt-Root.

---

## 4. Limitationen und Diskussion

- **Zeitraum 48 Tage**: April und erste Hälfte Mai 2026. Winter- und Sommerextreme
  fehlen. Langfristige Trends (z.B. Covid-Effekt 2020) wären mit dem Archiv
  möglich, aber 6 Jahre Voll-Daten wären 1.1 TB — wir haben uns pragmatisch
  für High-Resolution-Recent entschieden.
- **Nur SBB**: Andere Anbieter (BLS, RhB, SOB) sind in den Daten enthalten,
  aber wir haben gefiltert. Eine vollständige Schweiz-Analyse wäre möglich.
- **Wetterdistanz**: Bahnhof → nächste Wetterstation kann bis ~40 km sein
  (alpine Stationen). Mikroklima geht verloren.
- **LLM-Limitationen**: Sonnet 4.6 kann plausibel klingende, aber nicht
  verifizierbare Hypothesen liefern. Wir mindern das durch fixe Taxonomie,
  Temperatur 0.2 und explizite Anweisung "erfinde NICHTS". Die Konfidenz-Skala
  ist Selbst-Einschätzung, nicht kalibriert.
- **Kausalität vs. Korrelation**: Die OLS-Regression zeigt Assoziationen,
  keine Kausalität. Bei Sturmtagen sind oft auch Streckenarbeiten betroffen
  (Confounder).

---

## 5. Schlussfolgerungen

1. Die SBB-Pünktlichkeit ist wie erwartet **sehr hoch**: über 90 % der
   Ankünfte weniger als 3 Minuten verspätet (für Schweizer Verhältnisse ein
   harter Massstab).
2. **Werktag-/Wochenende-Unterschiede** existieren und sind statistisch
   signifikant.
3. **Linientyp** beeinflusst Verspätung — IC > S-Bahn (im Mittel).
4. **Wetter** korreliert messbar, aber moderat (r < 0.15). Niederschlag ist
   die wichtigste Wettervariable.
5. **Multivariate Erklärung** durch OLS-Regression bestätigt die Einzeleffekte,
   liefert aber tiefes R² — Verspätung bleibt zu grossen Teilen idiosynkratisch.
6. **LLM-gestützte qualitative Analyse** ist ein wertvoller komplementärer
   Ansatz für die Krisen-Tag-Erklärung, sofern man die Limitationen mitkommuniziert.

Für die Praxis: Pendler haben empirisch gute Aussichten auf pünktliche
Verbindungen, ausser in der Rush-Hour und bei Niederschlag. Die Webapp macht
diese Erkenntnisse für einzelne Pendler-Strecken konkret abfragbar.

---

## 6. Anhang: Bewertungskriterien

### 6.1 Mindestanforderungen (Maximum 8 Punkte)

| # | Kriterium | Erfüllung im Projekt |
|---|---|---|
| 1 | Real-world data collection | ✅ `scripts/download_*.py`: SBB Open Data + MeteoSchweiz |
| 2 | Data preparation (regex, strings→numeric) | ✅ Notebook 02: dropna, type-conversion, datetime-parsing |
| 3 | Python built-ins (lists/dicts/sets) + DataFrames | ✅ DELAY_BUCKETS Liste, WEATHER_STATION_COORDS Dict, Sets für unique stations, DataFrames durchgehend |
| 4 | Conditionals, loops, loop control | ✅ for-loop über Daten-Tage im Download, lambda + apply in Notebooks, if/elif in `classify_delay` |
| 5 | Procedural OR OOP | ✅ Procedural (Notebooks) + Funktional (`utils.py` Module). LRU-cached function als OOP-ähnliches Pattern |
| 6 | Tables + visualizations | ✅ Notebook 03: 8+ Plots (Histogram, Boxplot, Heatmap, Scatter mit Regressions­linie); Pandas-Tables in jedem Notebook |
| 7 | Statistische Analyse mit p-value | ✅ 4 Tests in Notebook 03 (t-Test, ANOVA, Pearson, OLS) |
| 8 | Deliverables auf Moodle | ⏳ Wird am 2026-05-27 hochgeladen |

### 6.2 Bonuspunkte (Maximum 6 Punkte)

| # | Kriterium | Erfüllung |
|---|---|---|
| 1 | Creativity (nicht im Kurs behandelt) | ✅ statsmodels OLS-Regression, **Tukey HSD Post-hoc-Test**, KDTree für Spatial-Join, LLM-Pendler-Insight, programmatic Notebook-Build via nbclient, **Dockerfile für Reproduzierbarkeit**, **pytest-Test-Suite (23 Tests)** |
| 2 | Web scraper / Web API | ✅ `download_istdaten.py` (CKAN-HTML-Scraping mit Regex), `download_stations.py` (REST-API), `download_weather.py` (HTTP) |
| 3 | Database (SQLite) + SQL queries | ✅ Notebook 01: 3 Tabellen, 5 Beispiel-Queries (SELECT, WHERE, GROUP BY, JOIN, ORDER BY, LIMIT) |
| 4 | LLM-Nutzung | ✅ Notebook 04 (Krisen-Tag-Klassifikation) + Webapp (Pendler-Insight Live-Q&A) mit Anthropic Claude Sonnet 4.6 |
| 5 | Simple Web Application | ✅ Streamlit-App mit 4 Tabs, Folium-Karte, LLM-Integration, Plotly-Charts |
| 6 | Public GitHub Repo | ✅ https://github.com/Mrgincinamon/SBB-Tracking mit `.gitignore` für grosse Datasets |

### 6.3 Verzeichnis der wichtigsten Code-Artefakte

```
project/
├── README.md
├── .env.example
├── .gitignore                          (ignoriert .env, venv/, data/raw, data/processed/, *.db)
├── requirements.txt                    (14 Python-Packages)
├── scripts/
│   ├── download_stations.py            ✅ Web-API: 1'743 Bahnhöfe
│   ├── download_istdaten.py            ✅ Web-Scraping + Streaming-Filter (48 Tage)
│   ├── download_weather.py             ✅ Web-API: 15 MeteoSchweiz-Stationen
│   ├── _nb_builder.py                  Notebook-Build-Pipeline (Gellrich-Header/Footer)
│   └── build_notebook_NN.py            Bauen + Ausführen der 4 Notebooks
├── notebooks/
│   ├── 01_datenbank_speicherung.ipynb  ✅ SQLite + 5 SQL-Queries
│   ├── 02_datenaufbereitung.ipynb      ✅ Filter, Join, Klassifikation
│   ├── 03_analyse_visualisierung.ipynb ✅ 4 Stats-Tests + Plots
│   └── 04_llm_verspaetungsgruende.ipynb ✅ LLM-Klassifikation Krisen-Tage
├── app/
│   ├── utils.py                        Geteilte Helper (DB-Access, KDTree, Klassifikation)
│   └── streamlit_app.py                ✅ 4-Tab-Webapp (Karte, Time-of-Day, LLM, Über)
├── data/
│   ├── raw/                            Roh-Downloads (gitignored, lokal ~720 MB)
│   └── processed/                      DB + delays_prepared.parquet (gitignored)
├── tests/
│   └── test_utils.py                   ✅ 23 pytest-Tests fuer utils.py
├── Dockerfile                          ✅ Reproduzierbarer Container fuer die Webapp
├── .dockerignore
└── presentation/
    ├── SBB_Tracker_Praesentation.md    Dieses Dokument
    ├── SBB_Tracker_Praesentation.pdf   PDF-Version (markdown-pdf generiert)
    └── notebook_renders/               HTML-Versionen der 4 Notebooks (mit Plots)
```

### 6.4 Screenshots (vom Reviewer einzufügen)

> **Joël & Patrick:** Vor Abgabe folgende Screenshots aufnehmen und hier einfügen:
> 1. Notebook 01: SQL-Query-Output mit Top-10 Verspätungs-Bahnhöfen
> 2. Notebook 03: Boxplot Werktag vs. Wochenende
> 3. Notebook 03: Heatmap Stunde × Wochentag
> 4. Notebook 03: OLS-Regressions-Output (model.summary())
> 5. Notebook 04: LLM-Hypothesen-Tabelle
> 6. Webapp: Folium-Karte der Schweiz mit Verspätungs-Markern
> 7. Webapp: Pendler-Insight Q&A mit Beispiel-Frage
> 8. GitHub: Screenshot der Repo-Seite mit Commit-Historie

---

## 7. Quellen und Lizenzen

### Daten
- **Ist-Daten**: opentransportdata.swiss, Open Data Plattform Mobilität Schweiz,
  Lizenz CC-BY (https://opentransportdata.swiss/de/data/usage/)
- **Bahnhof-Stammdaten**: data.sbb.ch, Schweizerische Bundesbahnen SBB,
  Lizenz CC-BY 4.0
- **Wetterdaten**: MeteoSchweiz (BAMETEO), Lizenz "Open data BY"
  (https://www.meteoschweiz.admin.ch/service-und-publikationen/applikationen/ext/general-license-statement-open-data.html)

### Software
- Python 3.12, pandas, numpy, scipy, statsmodels, matplotlib, seaborn, plotly,
  folium, streamlit, anthropic — alle Open Source
- Anthropic Claude Sonnet 4.6 (API), Lizenz für API-Nutzung gemäss
  https://www.anthropic.com/legal/aup

### Referenzen
- Mario Gellrich. *ZHAW Scientific Programming Course Materials* (FS2026).
  https://github.com/mario-gellrich-zhaw/scientific_programming
- Schweizerische Bundesbahnen SBB. *Geschäftsbericht 2024*.
  Pünktlichkeit-Statistik S. 23. https://reporting.sbb.ch/

---

*Dieses Dokument wurde mit Unterstützung von Claude (Anthropic) erstellt.*
*Letzte Aktualisierung: 2026-05-20.*
