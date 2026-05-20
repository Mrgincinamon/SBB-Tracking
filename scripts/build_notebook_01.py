"""Build notebook 01: Datenbank-Speicherung der SBB-Verspätungsdaten.

Loads stations.csv, weather parquets, and ist-daten parquets into a SQLite DB,
then demonstrates SQL queries (the 'DB+SQL' bonus criterion).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make _nb_builder importable when run from project root or scripts/
sys.path.insert(0, str(Path(__file__).parent))
from _nb_builder import md, code, header_cell, footer_cell, build_notebook, save_and_run


NB_PATH = Path(__file__).parent.parent / "notebooks" / "01_datenbank_speicherung.ipynb"


def build_cells() -> list:
    cells = []

    # Title + Intro
    cells.append(md("""
        # Notebook 01 — Datenbank-Speicherung

        **SBB Tracker · ZHAW Scientific Programming FS2026**
        Joël Hasler & Patrick Ferreira

        In diesem ersten Notebook werden die rohen Datensätze (Bahnhöfe,
        Wetterdaten, Ist-Daten = Soll-/Ist-Vergleich der SBB) in eine
        **SQLite-Datenbank** überführt. Diese DB dient als zentraler
        Datenspeicher für die nachfolgenden Notebooks und ermöglicht
        SQL-Queries als Bonus-Kriterium (Datenbank + SQL).

        ## Datenquellen

        1. **Stationen** — `data/raw/stations.csv` (1'743 aktive Schweizer Bahnhöfe
           mit Geo-Koordinaten, SBB Open Data)
        2. **Wetter** — `data/raw/weather/*_hourly_recent.parquet` (15 MeteoSchweiz-
           Stationen nahe der wichtigsten Bahnhöfe, stündlich)
        3. **Ist-Daten** — `data/raw/istdaten/*_sbb.parquet` (gefilterte SBB-Zug-
           Events: geplante vs. tatsächliche An-/Abfahrtszeiten, 50 Tage)

        Die Roh-Downloads selbst werden in `scripts/download_*.py` durchgeführt
        und sind als reine Python-Scripts implementiert (Web-Scraper / API-Calls
        als zweites Bonus-Kriterium).
    """))

    # Setup
    cells.append(md("## Bibliotheken und Einstellungen"))
    cells.append(header_cell())

    # DB Path + Schema
    cells.append(md("""
        ## Datenbank initialisieren

        Wir nutzen `sqlite3` direkt (keine ORM-Schicht wie SQLAlchemy), gemäss
        Dozenten-Konvention. Die DB liegt unter `data/processed/sbb_tracker.db`
        und enthält drei Tabellen:

        - `stations` — Stamm­daten der Bahnhöfe (BPUIC, Name, lat/lon, Kanton)
        - `weather_hourly` — Stündliche Wetterdaten pro MeteoSchweiz-Station
        - `delays` — Verspätungs-Events pro Zug-Halt mit `delay_arr_sec` /
          `delay_dep_sec`

        Existierende Tabellen werden überschrieben (`if_exists='replace'`),
        damit das Notebook idempotent ist.
    """))
    cells.append(code("""
        DB_PATH = DATA_PROCESSED / "sbb_tracker.db"
        if DB_PATH.exists():
            DB_PATH.unlink()
        print(f"DB-Pfad: {DB_PATH}")
    """))

    # Stations table
    cells.append(md("""
        ## Tabelle 1: Bahnhof-Stammdaten

        Die Stations-CSV wurde von `data.sbb.ch` heruntergeladen
        (Web-API → CSV-Export). Wir filtern auf aktive Bahn-Stationen mit
        Geo-Koordinaten und speichern die wichtigsten Spalten.
    """))
    cells.append(code("""
        df_stations = pd.read_csv(DATA_RAW / "stations.csv", sep=";")
        df_stations.columns = df_stations.columns.str.lower()
        print(f"Geladen: {len(df_stations):,} Bahnhoefe, {df_stations.shape[1]} Spalten")
        df_stations.head(3)
    """))
    cells.append(code("""
        conn = sqlite3.connect(DB_PATH)
        df_stations.to_sql("stations", conn, if_exists="replace", index=False)
        # Verifikation
        check = pd.read_sql("SELECT COUNT(*) AS n FROM stations", conn)
        print(f"In DB gespeichert: {check.iloc[0]['n']:,} Stationen")
        conn.close()
    """))

    # Weather table
    cells.append(md("""
        ## Tabelle 2: Wetterdaten

        15 MeteoSchweiz-Stationen (SMA Zürich, BER Bern, GVE Genève, BAS Basel,
        LUG Lugano, …) wurden mit stündlicher Auflösung heruntergeladen. Jede
        Station ist ein separates Parquet — wir concat'en sie und ergänzen
        eine `station_abbr`-Spalte.
    """))
    cells.append(code("""
        weather_files = sorted((DATA_RAW / "weather").glob("*_hourly_recent.parquet"))
        print(f"Wetter-Parquets: {len(weather_files)}")
        for f in weather_files[:3]:
            print(" ", f.name)
        print(" ...")
    """))
    cells.append(code("""
        weather_dfs = []
        for f in weather_files:
            abbr = f.stem.split("_")[0]
            df = pd.read_parquet(f)
            df["station_abbr"] = abbr
            weather_dfs.append(df)
        df_weather = pd.concat(weather_dfs, ignore_index=True)
        df_weather.columns = df_weather.columns.str.lower()
        # Wichtigste Spalten herausgreifen
        keep_cols = ["station_abbr", "reference_timestamp",
                     "tre200h0",   # Temperatur 2m (°C)
                     "rre150h0",   # Niederschlag Stundensumme (mm)
                     "fkl010h0",   # Windgeschwindigkeit (m/s)
                     "ure200h0",   # Relative Feuchtigkeit (%)
                     "sre000h0"]   # Sonnenscheindauer (Min)
        keep_cols = [c for c in keep_cols if c in df_weather.columns]
        df_weather_slim = df_weather[keep_cols].copy()
        print(f"Wetterdaten gesamt: {len(df_weather_slim):,} Zeilen, "
              f"{df_weather_slim['station_abbr'].nunique()} Stationen")
    """))
    cells.append(code("""
        conn = sqlite3.connect(DB_PATH)
        df_weather_slim.to_sql("weather_hourly", conn, if_exists="replace", index=False)
        check = pd.read_sql("SELECT COUNT(*) AS n FROM weather_hourly", conn)
        print(f"In DB gespeichert: {check.iloc[0]['n']:,} Wetter-Records")
        conn.close()
    """))

    # Delays table
    cells.append(md("""
        ## Tabelle 3: Verspätungsdaten (Ist-Daten)

        Pro Tag eine Parquet-Datei mit den SBB-Zug-Events. Die Daten wurden
        bereits beim Download auf `PRODUKT_ID == 'Zug'` und `BETREIBER_ABK == 'SBB'`
        gefiltert (statt 2.5 Mio Roh-Events pro Tag bleiben ~65k SBB-relevante).

        Wir speichern alle Tage zusammen, behalten aber nur die für die Analyse
        wesentlichen Spalten, um die DB-Grösse moderat zu halten.
    """))
    cells.append(code("""
        delay_files = sorted((DATA_RAW / "istdaten").glob("*_sbb.parquet"))
        print(f"Tages-Parquets: {len(delay_files)}")
        print(f"Zeitraum: {delay_files[0].stem[:10]}  bis  {delay_files[-1].stem[:10]}")
    """))
    cells.append(code("""
        delay_cols = [
            "betriebstag", "fahrt_bezeichner", "linien_text", "verkehrsmittel_text",
            "bpuic", "haltestellen_name", "sloid",
            "ankunftszeit", "an_prognose", "an_prognose_status",
            "abfahrtszeit", "ab_prognose", "ab_prognose_status",
            "delay_arr_sec", "delay_dep_sec",
            "faellt_aus_tf", "durchfahrt_tf",
        ]
        delay_dfs = []
        for f in delay_files:
            df = pd.read_parquet(f, columns=[c for c in delay_cols if True])
            df_slim = df[[c for c in delay_cols if c in df.columns]].copy()
            delay_dfs.append(df_slim)
        df_delays = pd.concat(delay_dfs, ignore_index=True)
        print(f"Total Records: {len(df_delays):,}  ({len(df_delays)/1e6:.2f} Mio)")
    """))
    cells.append(code("""
        conn = sqlite3.connect(DB_PATH)
        df_delays.to_sql("delays", conn, if_exists="replace", index=False)
        # Indizes auf Join-Keys fuer schnellere Queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_delays_bpuic ON delays(bpuic)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_delays_betriebstag ON delays(betriebstag)")
        conn.commit()
        check = pd.read_sql("SELECT COUNT(*) AS n FROM delays", conn)
        print(f"In DB gespeichert: {check.iloc[0]['n']:,} Verspaetungs-Records")
        print(f"DB-Groesse: {DB_PATH.stat().st_size / 1024**2:.1f} MB")
        conn.close()
    """))

    # SQL Queries section
    cells.append(md("""
        ## SQL-Queries: Erste Erkundung

        Nun demonstrieren wir die wichtigsten SQL-Patterns auf der Datenbank.
        Die folgenden Queries decken `SELECT`, `WHERE`, `GROUP BY`, `JOIN`,
        `ORDER BY` und `LIMIT` ab — exakt die Spannweite, die für das
        DB+SQL-Bonuskriterium erwartet wird.
    """))

    cells.append(md("### Query 1 — Schema-Überblick"))
    cells.append(code("""
        conn = sqlite3.connect(DB_PATH)
        schema = pd.read_sql(
            "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'index') "
            "ORDER BY type, name", conn)
        print(schema.to_string(index=False))
        conn.close()
    """))

    cells.append(md("### Query 2 — Verspätungs-Hotspots: Top-10 Bahnhöfe nach durchschnittlicher Ankunftsverspätung"))
    cells.append(code("""
        conn = sqlite3.connect(DB_PATH)
        q = '''
            SELECT haltestellen_name,
                   COUNT(*) AS n_halte,
                   ROUND(AVG(delay_arr_sec), 1) AS avg_delay_sec,
                   ROUND(AVG(delay_arr_sec) / 60.0, 2) AS avg_delay_min
              FROM delays
             WHERE an_prognose_status = 'REAL'
               AND delay_arr_sec IS NOT NULL
             GROUP BY haltestellen_name
            HAVING COUNT(*) >= 1000
             ORDER BY avg_delay_sec DESC
             LIMIT 10
        '''
        top_late = pd.read_sql(q, conn)
        conn.close()
        top_late
    """))

    cells.append(md("### Query 3 — Verspätungs-Verteilung nach Wochentag (für späteren t-Test)"))
    cells.append(code("""
        conn = sqlite3.connect(DB_PATH)
        q = '''
            SELECT strftime('%w', betriebstag) AS weekday_num,
                   COUNT(*) AS n_events,
                   ROUND(AVG(delay_arr_sec), 1) AS avg_delay_sec,
                   ROUND(100.0 * SUM(CASE WHEN delay_arr_sec > 180 THEN 1 ELSE 0 END)
                         / COUNT(*), 2) AS pct_late_over_3min
              FROM delays
             WHERE an_prognose_status = 'REAL'
               AND delay_arr_sec IS NOT NULL
             GROUP BY weekday_num
             ORDER BY weekday_num
        '''
        by_dow = pd.read_sql(q, conn)
        # 0=Sonntag in SQLite, mappen auf deutsche Namen
        dow_names = {"0": "So", "1": "Mo", "2": "Di", "3": "Mi", "4": "Do", "5": "Fr", "6": "Sa"}
        by_dow["weekday"] = by_dow["weekday_num"].map(dow_names)
        conn.close()
        by_dow[["weekday", "n_events", "avg_delay_sec", "pct_late_over_3min"]]
    """))

    cells.append(md("### Query 4 — JOIN von Verspätungen mit Stationen-Stammdaten (zeigt Kanton + Geo-Koords)"))
    cells.append(code("""
        conn = sqlite3.connect(DB_PATH)
        q = '''
            SELECT s.cantonabbreviation AS kanton,
                   COUNT(*) AS n_events,
                   ROUND(AVG(d.delay_arr_sec), 1) AS avg_delay_sec
              FROM delays d
              JOIN stations s ON d.bpuic = s.number
             WHERE d.an_prognose_status = 'REAL'
               AND d.delay_arr_sec IS NOT NULL
             GROUP BY s.cantonabbreviation
            HAVING n_events >= 500
             ORDER BY avg_delay_sec DESC
        '''
        by_canton = pd.read_sql(q, conn)
        conn.close()
        by_canton
    """))

    cells.append(md("### Query 5 — Liniencodes mit den meisten Halten (Top-10 SBB-S-Bahn-/Fernverkehr-Linien)"))
    cells.append(code("""
        conn = sqlite3.connect(DB_PATH)
        q = '''
            SELECT linien_text, COUNT(*) AS n_halte
              FROM delays
             WHERE linien_text IS NOT NULL
             GROUP BY linien_text
             ORDER BY n_halte DESC
             LIMIT 10
        '''
        top_lines = pd.read_sql(q, conn)
        conn.close()
        top_lines
    """))

    # Summary
    cells.append(md("""
        ## Zusammenfassung

        Drei Tabellen sind erstellt, indiziert und mit SQL erkundet:
        - **`stations`** — Stamm­daten für JOIN per BPUIC
        - **`weather_hourly`** — Stündliche Wetter-Messpunkte für Wetter-Korrelation
        - **`delays`** — Verspätungs-Events als Hauptanalyse-Datensatz

        Die nächsten Notebooks setzen darauf auf:
        - `02_datenaufbereitung.ipynb` — Cleaning, Merges, Feature-Engineering
        - `03_analyse_visualisierung.ipynb` — 4 Statistik-Tests + Visualisierungen
    """))

    cells.append(footer_cell())
    return cells


def main() -> int:
    cells = build_cells()
    nb = build_notebook(cells, title="01 — Datenbank-Speicherung")
    ok = save_and_run(nb, NB_PATH, run=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
