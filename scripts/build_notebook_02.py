"""Build notebook 02: Datenaufbereitung (Feature-Engineering, Wetter-Join, Klassifikation).

Reads from the SQLite DB built in notebook 01, derives time/weather features,
classifies delays, and persists a 'prepared' dataset for notebook 03.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _nb_builder import md, code, header_cell, footer_cell, build_notebook, save_and_run


NB_PATH = Path(__file__).parent.parent / "notebooks" / "02_datenaufbereitung.ipynb"


def build_cells() -> list:
    cells = []

    cells.append(md("""
        # Notebook 02 — Datenaufbereitung

        **SBB Tracker · ZHAW Scientific Programming FS2026**
        Joël Hasler & Patrick Ferreira

        Aufbauend auf der Datenbank aus Notebook 01 bereiten wir die Rohdaten
        für die statistische Analyse vor. Konkret:

        1. **Datenqualität checken** — Missings, Duplikate, Outlier
        2. **Filter auf saubere Daten** — nur `an_prognose_status == 'REAL'`
        3. **Zeit-Features ableiten** — Stunde, Wochentag, Rush-Hour-Flag
        4. **Stationen mit Wetterstationen verknüpfen** — via KDTree-Nearest
        5. **Wetterdaten joinen** — pro Verspätungs-Event Temperatur, Regen, Wind
        6. **Verspätungen klassifizieren** — kategoriale Buckets (pünktlich,
           leicht, klassisch, stark, extrem)
        7. **Speichern** als Parquet für Notebook 03

        Hilfsfunktionen sind in `app/utils.py` ausgelagert (OOP-Bonus + Wiederverwendung
        in der Streamlit-Webapp).
    """))

    cells.append(md("## Bibliotheken und Einstellungen"))
    cells.append(header_cell())

    cells.append(code("""
        # Utility-Modul aus app/ einbinden
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "app"))
        import utils
        print("utils.py geladen aus:", PROJECT_ROOT / "app" / "utils.py")
        print("DB-Pfad:", utils.db_path())
    """))

    # Load all 3 tables
    cells.append(md("""
        ## Daten aus der Datenbank laden

        Wir lesen die in Notebook 01 erstellten Tabellen direkt mit
        `pd.read_sql(...)`. Indizes auf `bpuic` und `betriebstag` (in NB01
        angelegt) beschleunigen die Joins.
    """))
    cells.append(code("""
        df_stations = utils.query("SELECT * FROM stations")
        df_weather = utils.query("SELECT * FROM weather_hourly")
        df_delays = utils.query("SELECT * FROM delays")
        print(f"Stationen:  {len(df_stations):>9,} Zeilen")
        print(f"Wetter:     {len(df_weather):>9,} Zeilen")
        print(f"Verspaetung:{len(df_delays):>9,} Zeilen")
    """))

    # Data quality
    cells.append(md("""
        ## Datenqualitäts-Check

        Erst pro Tabelle: wie viele Missing-Werte? Gibt es Duplikate? Wie
        verteilen sich die Zeitstempel? Das ist Standard-EDA, gibt aber
        Hinweise auf Cleaning-Bedarf bevor wir Statistik darauf rechnen.
    """))
    cells.append(code("""
        def quality_report(name, df):
            print(f"=== {name} ({len(df):,} Zeilen) ===")
            missing = df.isna().sum()
            missing_pct = (100 * missing / len(df)).round(2)
            report = pd.DataFrame({"missing": missing, "pct": missing_pct})
            report = report[report["missing"] > 0].sort_values("missing", ascending=False)
            if len(report) == 0:
                print("  Keine Missings.")
            else:
                print(report.head(10).to_string())
            print(f"  Duplikate (exakt): {df.duplicated().sum():,}")
            print()

        quality_report("Stationen", df_stations)
        quality_report("Wetter", df_weather)
        quality_report("Verspaetungen", df_delays)
    """))

    # Filter to REAL only
    cells.append(md("""
        ## Auf saubere Messungen filtern (`AN_PROGNOSE_STATUS == 'REAL'`)

        Die Spalte `an_prognose_status` unterscheidet zwischen `REAL` (echte
        gemessene Ankunftszeit) und `PROGNOSE` (geschätzt — z.B. weil der Zug
        noch nicht angekommen ist oder die Messung nicht funktionierte). Für
        seriöse Statistik verwenden wir nur `REAL`.
    """))
    cells.append(code("""
        n_before = len(df_delays)
        df = df_delays.loc[df_delays["an_prognose_status"] == "REAL"].copy()
        df = df.loc[df["delay_arr_sec"].notna()].copy()
        n_after = len(df)
        print(f"Vorher:  {n_before:,} Records")
        print(f"Nachher: {n_after:,} Records  ({100*n_after/n_before:.1f}%)")
    """))

    # Plausibilitäts-Filter für korrupte Soll-Zeitstempel
    cells.append(md("""
        ## Plausibilitäts-Filter: physikalisch unmögliche Negativ-Verspätungen

        Eine Stichprobe der extremsten Negativwerte zeigt ein Datenqualitäts-
        Problem im **Quell-Feed**: Einzelne Records haben ein **Soll-Datum
        mehrere Tage nach dem Betriebstag**, wodurch sich rechnerisch
        Verspätungen von z.B. **−48 Stunden** ergeben. Betroffen sind v.a.
        Nacht- und Auslandszüge (NJ, EC).

        An getakteten SBB-Halten kann ein Zug nicht mehr als wenige Minuten
        *vor* Fahrplan ankommen — Werte unter **−10 Minuten** sind daher keine
        echten Frühankünfte, sondern fehlerhafte Zeitstempel. Wir entfernen sie
        (Schwelle `MIN_PLAUSIBLE_DELAY_SEC = −600 s`, ausgelagert in `utils.py`).

        **Wichtig:** Grosse *positive* Verspätungen bleiben erhalten — sie sind
        reale Störungen (Auslandszüge akkumulieren im Ausland Verspätung) und
        gehören zum Untersuchungsgegenstand.
    """))
    cells.append(code("""
        # Vor dem Filter: extremste Negativwerte als Beleg fuer das Quell-Feed-Problem
        worst = df.nsmallest(3, "delay_arr_sec")[
            ["betriebstag", "haltestellen_name", "ankunftszeit", "an_prognose",
             "delay_arr_sec", "linien_text"]]
        print("Extremste Negativ-Verspaetungen VOR Filter (korrupte Soll-Zeitstempel):")
        print(worst.to_string(index=False))

        n_pre = len(df)
        df = utils.filter_implausible_delays(df, col="delay_arr_sec")
        n_removed = n_pre - len(df)
        print(f"\\nEntfernt: {n_removed:,} Records mit Ankunft > 10 Min vor Fahrplan "
              f"({100*n_removed/n_pre:.4f}%)")
        print(f"Verbleibend: {len(df):,} Records")
        print(f"Neuer Minimal-/Maximalwert: {df['delay_arr_sec'].min():.0f}s / "
              f"{df['delay_arr_sec'].max():.0f}s")
    """))

    # Outlier handling
    cells.append(md("""
        ### Positive Ausreisser inspizieren

        Verspätungen mit > 30 Minuten sind ungewöhnlich — meist Folge von
        Notfällen, Streckensperrungen oder Auslandszügen. Im Gegensatz zu den
        unmöglichen Negativwerten sind das **plausible reale Störungen**, die
        wir behalten, aber explizit ausweisen.
    """))
    cells.append(code("""
        print("Verteilung Ankunftsverspaetung (Sekunden):")
        print(df["delay_arr_sec"].describe(percentiles=[.5, .9, .95, .99, .999]).to_string())
        n_extreme = (df["delay_arr_sec"] > 1800).sum()
        print(f"\\nExtreme Verspaetungen (>30 Min): {n_extreme:,} "
              f"({100*n_extreme/len(df):.3f}% aller Faelle)")
    """))

    # Time features
    cells.append(md("""
        ## Zeit-Features ableiten

        Aus dem Zeitstempel `ankunftszeit` extrahieren wir Stunde, Wochentag,
        Wochenende-Flag und Rush-Hour-Flag. Diese Features werden in den
        Stats-Tests von Notebook 03 als Gruppierungs-Variablen benutzt
        (Werktag vs. Wochenende, Stunde vs. Verspätung).
    """))
    cells.append(code("""
        df = utils.add_time_features(df, ts_col="ankunftszeit")
        cols_to_show = ["betriebstag", "haltestellen_name", "ankunftszeit",
                        "delay_arr_sec", "hour", "weekday", "is_weekend", "is_rush_hour"]
        df[cols_to_show].head(5)
    """))
    cells.append(code("""
        # Verteilung der Faelle ueber Stunde + Wochentag
        crosstab = pd.crosstab(df["weekday"], df["hour"])
        crosstab = crosstab.reindex(["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"])
        crosstab
    """))

    # Stations to weather mapping
    cells.append(md("""
        ## Bahnhöfe ↔ Wetterstationen mappen

        Pro Bahnhof finden wir die geografisch nächste MeteoSchweiz-Station
        (von 15 Stationen) via scipy KDTree (Euklidische Distanz auf lat/lon).
        Das ist deutlich schneller als ein Haversine-Loop und für die Schweiz
        ausreichend präzise.
    """))
    cells.append(code("""
        df_stations_mapped = utils.map_stations_to_weather(df_stations)
        print("Beispiel-Mapping (10 Bahnhoefe):")
        print(df_stations_mapped[["designationofficial", "cantonabbreviation",
                                  "nearest_weather_abbr", "weather_distance_km"]]
              .sample(10, random_state=42).to_string(index=False))
    """))
    cells.append(code("""
        # Verteilung: wie viele Bahnhoefe pro Wetterstation?
        mapping_dist = (df_stations_mapped["nearest_weather_abbr"]
                        .value_counts()
                        .sort_values(ascending=False))
        print("Bahnhoefe pro Wetterstation:")
        print(mapping_dist.to_string())
    """))

    # Weather join
    cells.append(md("""
        ## Wetterdaten an Verspätungs-Events joinen

        Für jeden Verspätungs-Event holen wir die Wetterdaten der nächsten
        Wetterstation zur passenden Stunde. Strategie:

        1. Verspätungs-DF mit `nearest_weather_abbr` per BPUIC-Join anreichern
        2. Wetter-Zeitstempel auf Stunde runden (stündliche Wetterdaten)
        3. Merge auf `(weather_abbr, weather_hour)`

        Das ergibt für jeden Halt: Temperatur, Niederschlag, Wind, Feuchtigkeit
        in der Stunde des Halts.
    """))
    cells.append(code("""
        # Schritt 1: nearest_weather_abbr an delays anhaengen
        station_lookup = df_stations_mapped.set_index("number")["nearest_weather_abbr"]
        df["weather_abbr"] = df["bpuic"].map(station_lookup)
        n_matched = df["weather_abbr"].notna().sum()
        print(f"Verspaetungen mit Wetter-Mapping: {n_matched:,}/{len(df):,} "
              f"({100*n_matched/len(df):.1f}%)")
    """))
    cells.append(code("""
        # Schritt 2: Wetter-Zeitstempel auf Stunde runden + delay-Zeitstempel auch
        df_weather["weather_ts_hour"] = (pd.to_datetime(df_weather["reference_timestamp"])
                                         .dt.floor("h"))
        df["delay_ts_hour"] = pd.to_datetime(df["ankunftszeit"]).dt.floor("h")

        # Schritt 3: Merge
        df_with_weather = df.merge(
            df_weather[["station_abbr", "weather_ts_hour",
                        "tre200h0", "rre150h0", "fkl010h0", "ure200h0", "sre000h0"]],
            left_on=["weather_abbr", "delay_ts_hour"],
            right_on=["station_abbr", "weather_ts_hour"],
            how="left",
        )

        # Aufraeumen: Hilfs-Spalten droppen, sinnvolle Namen vergeben
        df_with_weather = df_with_weather.drop(columns=["station_abbr", "weather_ts_hour"])
        df_with_weather = df_with_weather.rename(columns={
            "tre200h0": "temperatur_c",
            "rre150h0": "niederschlag_mm",
            "fkl010h0": "wind_ms",
            "ure200h0": "feuchte_pct",
            "sre000h0": "sonne_min",
        })
        n_weather = df_with_weather["temperatur_c"].notna().sum()
        print(f"Records mit Wetterdaten: {n_weather:,}/{len(df_with_weather):,} "
              f"({100*n_weather/len(df_with_weather):.1f}%)")
        df_with_weather[["haltestellen_name", "ankunftszeit", "delay_arr_sec",
                         "temperatur_c", "niederschlag_mm", "wind_ms"]].head(5)
    """))

    # Delay classification
    cells.append(md("""
        ## Verspätungs-Klassifikation

        Aus der Sekunden-Spalte `delay_arr_sec` leiten wir eine kategoriale
        Spalte `delay_class` ab — von "frueh_30+s" bis "extrem_ueber_10min".
        Das gibt uns gleichzeitig die "klassische Verspätung" (>3 Min, SBB-
        offizielle Definition) als binäres Feature.
    """))
    cells.append(code("""
        df_final = utils.add_delay_class(df_with_weather, col="delay_arr_sec")
        df_final["is_late_3min"] = df_final["delay_arr_sec"] > 180

        # Verteilung der Klassen
        class_dist = df_final["delay_class"].value_counts().sort_index()
        print("Verspaetungs-Klassen:")
        print(class_dist.to_string())
        print(f"\\nKlassisch verspaetet (>3 Min): {df_final['is_late_3min'].sum():,} "
              f"({100*df_final['is_late_3min'].mean():.2f}%)")
    """))

    # Save prepared dataset
    cells.append(md("""
        ## Speichern als `delays_prepared.parquet`

        Notebook 03 nimmt diese Datei als Input. Wir speichern als Parquet
        (komprimiert, typisiert) statt CSV — pandas liest's 10× schneller.
    """))
    cells.append(code("""
        OUT = DATA_PROCESSED / "delays_prepared.parquet"
        df_final.to_parquet(OUT, compression="snappy", index=False)
        print(f"Gespeichert: {OUT}")
        print(f"Groesse:     {OUT.stat().st_size / 1024**2:.1f} MB")
        print(f"Zeilen:      {len(df_final):,}")
        print(f"Spalten:     {df_final.shape[1]}")
    """))

    cells.append(md("""
        ## Zusammenfassung Notebook 02

        Aus den drei Rohtabellen ist nun ein einziger angereicherter Datensatz
        entstanden. Pro Verspätungs-Event haben wir:
        - **Zeitliche Features**: Stunde, Wochentag, Rush-Hour-Flag
        - **Wetter-Features**: Temperatur, Regen, Wind, Feuchtigkeit, Sonne
        - **Geografisches**: Kanton, lat/lon (über Stations-JOIN)
        - **Klassifikation**: Bucket-Label + binäres `is_late_3min`

        Notebook 03 testet damit vier Hypothesen:
        1. Werktag vs. Wochenende (t-Test / Mann-Whitney)
        2. Zugtyp (S-Bahn vs. IC) — ANOVA
        3. Wetter ↔ Verspätung — Pearson/Spearman-Korrelation mit p-value
        4. Multivariate OLS-Regression als Krönung
    """))

    cells.append(footer_cell())
    return cells


def main() -> int:
    cells = build_cells()
    nb = build_notebook(cells, title="02 — Datenaufbereitung")
    ok = save_and_run(nb, NB_PATH, run=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
