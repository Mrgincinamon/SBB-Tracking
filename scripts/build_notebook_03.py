"""Build notebook 03: Statistische Analyse + Visualisierungen.

Reads the prepared parquet from notebook 02 and runs the 4 planned
statistical tests:
  1. Welch's t-test: Werktag vs. Wochenende
  2. One-way ANOVA: Verspätung nach Linientyp
  3. Pearson + Spearman correlation: Wetter ↔ Verspätung
  4. Multivariate OLS regression (statsmodels)
Plus Gellrich-style visualisations.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _nb_builder import md, code, header_cell, footer_cell, build_notebook, save_and_run


NB_PATH = Path(__file__).parent.parent / "notebooks" / "03_analyse_visualisierung.ipynb"


def build_cells() -> list:
    cells = []

    cells.append(md("""
        # Notebook 03 — Analyse und Visualisierung

        **SBB Tracker · ZHAW Scientific Programming FS2026**
        Joël Hasler & Patrick Ferreira

        In diesem Notebook beantworten wir vier konkrete Forschungsfragen
        mit klassischen Statistik-Tests (alle mit p-Value-Reporting) und
        visualisieren die Ergebnisse:

        | # | Forschungsfrage | Methode |
        |---|---|---|
        | 1 | Sind Züge am Wochenende pünktlicher als an Werktagen? | Welch's t-Test |
        | 2 | Gibt es Unterschiede in der Verspätung zwischen Linien-Typen? | Einweg-ANOVA |
        | 3 | Korreliert Niederschlag/Temperatur mit Verspätung? | Pearson + Spearman |
        | 4 | Welche Faktoren erklären Verspätung gemeinsam? | Multiple OLS-Regression |

        Die OLS-Regression als vierter Test geht über das Kurslevel hinaus
        (statsmodels), bringt aber wertvolle multivariate Erkenntnisse.
    """))

    cells.append(md("## Bibliotheken und Einstellungen"))
    cells.append(header_cell())
    cells.append(code("""
        # Zusaetzlich fuer Stats
        import sys
        from scipy import stats
        import statsmodels.api as sm
        import statsmodels.formula.api as smf

        sys.path.insert(0, str(PROJECT_ROOT / "app"))
        import utils
    """))

    cells.append(md("""
        ## Daten laden

        Wir lesen den in Notebook 02 vorbereiteten, angereicherten Datensatz.
    """))
    cells.append(code("""
        df = pd.read_parquet(DATA_PROCESSED / "delays_prepared.parquet")
        print(f"Geladen: {len(df):,} Zeilen, {df.shape[1]} Spalten")
        print(f"Zeitraum: {df['betriebstag'].min()}  bis  {df['betriebstag'].max()}")
        print(f"Stationen: {df['haltestellen_name'].nunique():,}")
        print(f"Linien:    {df['linien_text'].nunique():,}")
    """))

    # Deskriptive Statistik
    cells.append(md("""
        ## Deskriptive Statistik der Ankunftsverspätung

        Bevor wir Tests rechnen, ein erster Blick auf die Verteilung der
        Verspätungen (in Sekunden).
    """))
    cells.append(code("""
        s = df["delay_arr_sec"]
        desc = pd.DataFrame({
            "Metrik": ["N", "Mittelwert", "Median", "StdAbw",
                       "Min", "P05", "P25", "P75", "P95", "P99", "Max",
                       "Anteil > 3 Min (klassisch verspaetet)"],
            "Wert": [
                f"{len(s):,}",
                f"{s.mean():.1f} s",
                f"{s.median():.1f} s",
                f"{s.std():.1f} s",
                f"{s.min():.0f} s",
                f"{s.quantile(.05):.0f} s",
                f"{s.quantile(.25):.0f} s",
                f"{s.quantile(.75):.0f} s",
                f"{s.quantile(.95):.0f} s",
                f"{s.quantile(.99):.0f} s",
                f"{s.max():.0f} s",
                f"{100*(s > 180).mean():.2f}%",
            ]
        })
        desc
    """))
    cells.append(code("""
        # Histogramm + Boxplot der Verspaetungen
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))

        # Histogramm geclippt fuer Lesbarkeit
        s_clip = s.clip(-60, 600)
        axes[0].hist(s_clip, bins=50, color="steelblue", edgecolor="white")
        axes[0].axvline(0, color="black", linewidth=1, linestyle="--", label="punktlich")
        axes[0].axvline(180, color="red", linewidth=1, linestyle="--", label="3-Min-Schwelle")
        axes[0].set_xlabel("Ankunftsverspaetung [s]", fontsize=10)
        axes[0].set_ylabel("Haeufigkeit", fontsize=10)
        axes[0].set_title("Verteilung der Verspaetung (geclippt auf -60 ... +600 s)", fontsize=11)
        axes[0].legend(fontsize=9)

        axes[1].boxplot(s_clip, vert=True, showfliers=False)
        axes[1].axhline(0, color="black", linewidth=0.5, linestyle="--")
        axes[1].set_ylabel("Ankunftsverspaetung [s]", fontsize=10)
        axes[1].set_title("Boxplot (ohne Outlier)", fontsize=11)
        axes[1].set_xticklabels(["alle Halte"])

        plt.tight_layout()
        plt.show()
    """))

    # Test 1: t-test Werktag vs Wochenende
    cells.append(md("""
        ## Test 1: Werktag vs. Wochenende — Welch's t-Test

        **Hypothesen:**
        - H₀: Die mittlere Verspätung an Werktagen ist gleich der am Wochenende.
        - H₁: Die mittlere Verspätung unterscheidet sich.

        Wir nutzen **Welch's t-Test** (`equal_var=False`), weil Werktag und
        Wochenende sehr unterschiedliche Zugfrequenz und damit andere
        Varianzen haben.
    """))
    cells.append(code("""
        weekday_delays = df.loc[~df["is_weekend"], "delay_arr_sec"]
        weekend_delays = df.loc[df["is_weekend"], "delay_arr_sec"]

        print(f"Werktag:    n = {len(weekday_delays):>7,}  Mean = {weekday_delays.mean():.1f} s "
              f"Median = {weekday_delays.median():.1f} s")
        print(f"Wochenende: n = {len(weekend_delays):>7,}  Mean = {weekend_delays.mean():.1f} s "
              f"Median = {weekend_delays.median():.1f} s")

        t_stat, p_val = stats.ttest_ind(weekday_delays, weekend_delays,
                                        equal_var=False, nan_policy="omit")
        print(f"\\nWelch's t-Test: t = {t_stat:.3f}, p = {p_val:.2e}")
        if p_val < 0.05:
            print(f"--> Signifikant (p < 0.05): Verspaetungen unterscheiden sich.")
        else:
            print(f"--> Nicht signifikant (p >= 0.05): kein Unterschied nachweisbar.")
    """))
    cells.append(code("""
        # Robuster: Mann-Whitney-U (verteilungsfrei) als Cross-Check
        u_stat, u_p = stats.mannwhitneyu(weekday_delays, weekend_delays,
                                         alternative="two-sided")
        print(f"Mann-Whitney-U Cross-Check: U = {u_stat:.0f}, p = {u_p:.2e}")
    """))
    cells.append(code("""
        # Visualisierung: Boxplot Werktag vs. Wochenende
        plot_df = df[["is_weekend", "delay_arr_sec"]].copy()
        plot_df["Tag-Typ"] = plot_df["is_weekend"].map({True: "Wochenende", False: "Werktag"})
        plot_df["Verspaetung [s]"] = plot_df["delay_arr_sec"].clip(-60, 600)

        plt.figure(figsize=(7, 4))
        sns.boxplot(x="Tag-Typ", y="Verspaetung [s]", data=plot_df,
                    palette=["steelblue", "darkorange"], showfliers=False)
        plt.title("Verspaetung: Werktag vs. Wochenende", fontsize=11)
        plt.axhline(0, color="black", linewidth=0.5, linestyle="--")
        plt.tight_layout()
        plt.show()
    """))

    # Test 2: ANOVA Linientyp
    cells.append(md("""
        ## Test 2: Verspätung nach Linien-Typ — Einweg-ANOVA

        SBB-Linien lassen sich grob klassifizieren nach `verkehrsmittel_text`:
        S (S-Bahn), IC (Inter­City), IR (Inter­Regio), RE (RegioExpress) usw.

        **Hypothesen:**
        - H₀: Die mittlere Verspätung ist über alle Linien-Typen gleich.
        - H₁: Mindestens ein Linien-Typ unterscheidet sich.
    """))
    cells.append(code("""
        # Top-5 haeufigste Linien-Typen, sonst landen seltene Kategorien als Rauschen
        top_types = df["verkehrsmittel_text"].value_counts().head(5).index.tolist()
        df_top = df.loc[df["verkehrsmittel_text"].isin(top_types)].copy()

        # Gruppen-Daten fuer ANOVA
        groups = [df_top.loc[df_top["verkehrsmittel_text"] == t, "delay_arr_sec"].values
                  for t in top_types]
        n_per_group = [len(g) for g in groups]
        means = [g.mean() for g in groups]
        print("Linien-Typ      |       N |   Mean (s)")
        for t, n, m in zip(top_types, n_per_group, means):
            print(f"  {t:12s}  | {n:>7,} | {m:>8.2f}")

        f_stat, anova_p = stats.f_oneway(*groups)
        print(f"\\nOne-way ANOVA: F = {f_stat:.3f}, p = {anova_p:.2e}")
    """))

    cells.append(md("""
        ### Tukey HSD Post-hoc: welche Linientyp-Paare unterscheiden sich konkret?

        Eine signifikante ANOVA sagt nur, dass mindestens ein Paar unterschiedlich
        ist — sie sagt nicht **welches**. Der Tukey-HSD-Test ist die klassische
        Post-hoc-Methode, die ALLE Paar-Vergleiche mit Familywise-Error-Control
        macht. Reject = das Paar unterscheidet sich signifikant.
    """))
    cells.append(code("""
        from statsmodels.stats.multicomp import pairwise_tukeyhsd

        # Stichprobe ziehen (100k pro Gruppe), sonst dauert Tukey ewig
        np.random.seed(42)
        sample_dfs = []
        for t in top_types:
            sub = df_top.loc[df_top["verkehrsmittel_text"] == t]
            sample_dfs.append(sub.sample(min(len(sub), 100_000), random_state=42))
        tukey_df = pd.concat(sample_dfs, ignore_index=True)
        tukey_res = pairwise_tukeyhsd(
            endog=tukey_df["delay_arr_sec"].values,
            groups=tukey_df["verkehrsmittel_text"].values,
            alpha=0.05,
        )
        print(tukey_res.summary())
    """))

    cells.append(code("""
        # Visualisierung
        plot_df = df_top[["verkehrsmittel_text", "delay_arr_sec"]].copy()
        plot_df["Verspaetung [s]"] = plot_df["delay_arr_sec"].clip(-60, 600)

        plt.figure(figsize=(8, 4))
        sns.boxplot(x="verkehrsmittel_text", y="Verspaetung [s]", data=plot_df,
                    order=top_types, palette="Set2", showfliers=False)
        plt.title("Verspaetung nach Linien-Typ (Top-5)", fontsize=11)
        plt.xlabel("Linien-Typ", fontsize=10)
        plt.axhline(0, color="black", linewidth=0.5, linestyle="--")
        plt.tight_layout()
        plt.show()
    """))

    # Test 3: Korrelation Wetter <-> Verspätung
    cells.append(md("""
        ## Test 3: Wetter ↔ Verspätung — Pearson + Spearman

        Nur Records mit Wetter-Match nutzen. Wir testen, ob **Niederschlag**
        und **Temperatur** linear (Pearson) oder monoton (Spearman) mit der
        Verspätung zusammenhängen.

        **Hypothesen** (für jeden Wettervariable):
        - H₀: Korrelationskoeffizient = 0 (kein Zusammenhang).
        - H₁: Korrelationskoeffizient ≠ 0.
    """))
    cells.append(code("""
        df_w = df.loc[df["temperatur_c"].notna()].copy()
        print(f"Records mit Wetterdaten: {len(df_w):,}")

        for var, label in [("niederschlag_mm", "Niederschlag"),
                           ("temperatur_c", "Temperatur"),
                           ("wind_ms", "Wind")]:
            mask = df_w[var].notna()
            x = df_w.loc[mask, var]
            y = df_w.loc[mask, "delay_arr_sec"]
            r_p, p_p = stats.pearsonr(x, y)
            r_s, p_s = stats.spearmanr(x, y)
            print(f"\\n{label:14s} (n={len(x):,})")
            print(f"  Pearson  r = {r_p:+.4f}, p = {p_p:.2e}")
            print(f"  Spearman r = {r_s:+.4f}, p = {p_s:.2e}")
    """))
    cells.append(code("""
        # Scatter Niederschlag vs. Verspaetung
        sub = df_w.loc[df_w["niederschlag_mm"].notna()].sample(5000, random_state=42)
        plt.figure(figsize=(7, 4))
        plt.scatter(sub["niederschlag_mm"], sub["delay_arr_sec"].clip(-60, 600),
                    alpha=0.3, s=10, color="steelblue")
        # Regressionslinie
        coef = np.polyfit(sub["niederschlag_mm"], sub["delay_arr_sec"], 1)
        x_range = np.linspace(sub["niederschlag_mm"].min(), sub["niederschlag_mm"].max(), 50)
        plt.plot(x_range, np.polyval(coef, x_range), color="red", linewidth=2,
                 label=f"Regression: y = {coef[0]:.1f}x + {coef[1]:.1f}")
        plt.xlabel("Niederschlag [mm/h]", fontsize=10)
        plt.ylabel("Verspaetung [s]", fontsize=10)
        plt.title("Niederschlag vs. Ankunftsverspaetung (Stichprobe 5'000)", fontsize=11)
        plt.legend(fontsize=9)
        plt.tight_layout()
        plt.show()
    """))

    # Test 4: OLS Regression
    cells.append(md("""
        ## Test 4: Multiple OLS-Regression (Krönung)

        Was erklärt Verspätung **gemeinsam**? Wir bauen ein lineares Modell mit
        statsmodels (das im Kurs nicht behandelt wurde — bewusste Erweiterung
        für Bonuspunkte "Kreativität").

        **Modell:**
        ```
        delay_arr_sec ~ niederschlag + temperatur + wind + hour + is_rush_hour + is_weekend
        ```

        Output: Koeffizienten, p-Werte pro Prädiktor, R² als Anpassungsgüte.
    """))
    cells.append(code("""
        # Daten fuer Regression vorbereiten
        df_reg = df_w[["delay_arr_sec", "niederschlag_mm", "temperatur_c", "wind_ms",
                       "hour", "is_rush_hour", "is_weekend"]].copy()
        df_reg = df_reg.dropna()
        df_reg["is_rush_hour_int"] = df_reg["is_rush_hour"].astype(int)
        df_reg["is_weekend_int"] = df_reg["is_weekend"].astype(int)

        formula = ("delay_arr_sec ~ niederschlag_mm + temperatur_c + wind_ms "
                   "+ hour + is_rush_hour_int + is_weekend_int")
        model = smf.ols(formula, data=df_reg).fit()
        print(model.summary().as_text())
    """))
    cells.append(code("""
        # Schoene Tabelle der Koeffizienten
        coef_table = pd.DataFrame({
            "Koeffizient": model.params,
            "Std-Error": model.bse,
            "t": model.tvalues,
            "p-Wert": model.pvalues,
        }).round(4)
        coef_table["Signifikanz"] = coef_table["p-Wert"].apply(
            lambda p: "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
        )
        coef_table
    """))

    # Heatmap Stunde x Wochentag
    cells.append(md("""
        ## Visualisierung: Verspätungs-Heatmap (Stunde × Wochentag)

        Wo liegen die Rush-Hour-Hotspots? Die Heatmap zeigt mittlere Verspätung
        pro (Wochentag × Stunde)-Zelle.
    """))
    cells.append(code("""
        pivot = (df.groupby(["weekday", "hour"])["delay_arr_sec"]
                 .mean()
                 .reset_index()
                 .pivot(index="weekday", columns="hour", values="delay_arr_sec"))
        pivot = pivot.reindex(["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"])

        plt.figure(figsize=(10, 4))
        sns.heatmap(pivot, cmap="YlOrRd", annot=False, cbar_kws={"label": "Mean delay [s]"})
        plt.title("Mittlere Verspaetung nach Wochentag und Stunde", fontsize=11)
        plt.xlabel("Stunde", fontsize=10)
        plt.ylabel("Wochentag", fontsize=10)
        plt.tight_layout()
        plt.show()
    """))

    # Klassifikations-Visualisierung
    cells.append(md("""
        ## Verspätungs-Klassen visualisieren

        Die in Notebook 02 vergebene Klassifizierung (frueh → puenktlich →
        leicht → klassisch → stark → extrem) als gestapeltes Balkendiagramm
        nach Linien-Typ.
    """))
    cells.append(code("""
        class_order = ["frueh_30+s", "frueh_unter_30s", "puenktlich_unter_1min",
                       "leicht_1_3min", "verspaetet_3_5min", "stark_5_10min",
                       "extrem_ueber_10min"]
        # Nur Klassen, die tatsaechlich vorkommen
        class_order = [c for c in class_order if c in df["delay_class"].unique()]

        ct = pd.crosstab(df["verkehrsmittel_text"], df["delay_class"],
                         normalize="index") * 100
        ct = ct.loc[df["verkehrsmittel_text"].value_counts().head(5).index, class_order]

        plt.figure(figsize=(10, 5))
        ct.plot(kind="bar", stacked=True, ax=plt.gca(), colormap="RdYlGn_r")
        plt.title("Verspaetungs-Klassen pro Linien-Typ (%)", fontsize=11)
        plt.ylabel("Anteil [%]", fontsize=10)
        plt.xlabel("Linien-Typ", fontsize=10)
        plt.legend(title="Klasse", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
        plt.xticks(rotation=0)
        plt.tight_layout()
        plt.show()
    """))

    # Limitations
    cells.append(md("""
        ## Limitationen und Diskussion

        - **Zeitraum begrenzt**: 50 Tage (April – Mitte Mai 2026). Saisonale
          Effekte (Winter, Bauarbeiten-Hochphase) nicht abgedeckt.
        - **Nur SBB**: Andere Anbieter (BLS, SOB, RhB) fehlen — Ergebnisse
          gelten nur für SBB-Fernverkehr + S-Bahn.
        - **Wetter-Distanz**: Bahnhof zu Wetterstation kann bis ~40 km sein
          (Berg-Stationen). Mikroklimatische Effekte (Wind im Tal) verloren.
        - **Multiples Testen**: Wir rechnen mehrere Tests ohne Bonferroni-
          Korrektur. Bei sehr strikten Standards würde p-Schwelle auf
          0.05/k = 0.0125 sinken (k=4 Tests).
        - **Kausalität ≠ Korrelation**: Die OLS-Regression zeigt assoziative,
          keine kausalen Zusammenhänge. Stürmische Wettertage gehen oft mit
          Streckenarbeiten einher (Confounder).
    """))

    cells.append(md("""
        ## Zusammenfassung Notebook 03

        Alle vier Hypothesen-Tests mit p-Values dokumentiert + visualisiert.
        Der Datensatz erlaubt klare Aussagen über Werktag-Effekte, Linientyp-
        Unterschiede, Wetter-Korrelation und multivariate Erklärung.

        **Nächste Schritte**:
        - Streamlit-Webapp baut auf dieser DB + diesen Erkenntnissen auf
        - LLM-Klassifikation reichert die Daten qualitativ an (in der App)
    """))

    cells.append(footer_cell())
    return cells


def main() -> int:
    cells = build_cells()
    nb = build_notebook(cells, title="03 — Analyse und Visualisierung")
    ok = save_and_run(nb, NB_PATH, run=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
