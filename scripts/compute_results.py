"""Berechnet alle Stats-Resultate aus delays_prepared.parquet und schreibt
sie als results.json und als markdown-fertige Snippets nach
presentation/computed_results/.

Idee: Praesentations-PDF kann die Zahlen direkt aus dem JSON ziehen
(oder wir bauen sie per Find&Replace in den Markdown).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf


PARQUET = Path(__file__).parent.parent / "data" / "processed" / "delays_prepared.parquet"
OUT_DIR = Path(__file__).parent.parent / "presentation" / "computed_results"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Lade {PARQUET.name} ...")
    df = pd.read_parquet(PARQUET)
    print(f"  {len(df):,} Zeilen")

    valid = df[df["delay_arr_sec"].notna()].copy()
    n_valid = len(valid)

    r: dict[str, object] = {}
    r["n_total_events"] = int(len(df))
    r["n_valid_arrival"] = int(n_valid)
    r["mean_delay_sec"] = float(valid["delay_arr_sec"].mean())
    r["median_delay_sec"] = float(valid["delay_arr_sec"].median())
    r["p95_delay_sec"] = float(valid["delay_arr_sec"].quantile(0.95))
    r["pct_classically_delayed"] = float((valid["delay_arr_sec"] > 180).mean() * 100)
    r["pct_early_or_punctual"] = float((valid["delay_arr_sec"] <= 0).mean() * 100)

    # Test 1: Welch's t-test Werktag vs Wochenende
    wt = valid.loc[~valid["is_weekend"].astype(bool), "delay_arr_sec"]
    we = valid.loc[valid["is_weekend"].astype(bool), "delay_arr_sec"]
    t_stat, t_p = stats.ttest_ind(wt, we, equal_var=False)
    r["test_welch_ttest"] = {
        "name": "Welch's t-Test Werktag vs Wochenende",
        "t_statistic": float(t_stat),
        "p_value": float(t_p),
        "mean_werktag_sec": float(wt.mean()),
        "mean_wochenende_sec": float(we.mean()),
        "n_werktag": int(len(wt)),
        "n_wochenende": int(len(we)),
        "significant_at_005": bool(t_p < 0.05),
    }

    # Test 2: ANOVA Linientyp
    line_groups = [g["delay_arr_sec"].values for _, g in valid.groupby("verkehrsmittel_text")
                   if len(g) > 100]
    line_names = [name for name, g in valid.groupby("verkehrsmittel_text") if len(g) > 100]
    f_stat, f_p = stats.f_oneway(*line_groups)
    means_by_line = valid.groupby("verkehrsmittel_text")["delay_arr_sec"].agg(["mean", "count"])
    r["test_anova_linientyp"] = {
        "name": "One-Way ANOVA: Verspaetung nach Linien-Typ",
        "f_statistic": float(f_stat),
        "p_value": float(f_p),
        "groups": line_names,
        "n_groups": len(line_names),
        "means_per_group": {k: float(v) for k, v in means_by_line["mean"].items()},
        "n_per_group": {k: int(v) for k, v in means_by_line["count"].items()},
        "significant_at_005": bool(f_p < 0.05),
    }

    # Test 3: Pearson r — Niederschlag vs Verspaetung
    weather_cols = [c for c in ["temperatur_c", "niederschlag_mm", "wind_ms",
                                "feuchte_pct", "sonne_min"] if c in valid.columns]
    r["weather_columns_found"] = weather_cols
    pearson = {}
    for col in weather_cols:
        sub = valid[[col, "delay_arr_sec"]].dropna()
        if len(sub) < 1000:
            continue
        pr, pp = stats.pearsonr(sub[col], sub["delay_arr_sec"])
        sp, spp = stats.spearmanr(sub[col], sub["delay_arr_sec"])
        pearson[col] = {
            "n": int(len(sub)),
            "pearson_r": float(pr),
            "pearson_p": float(pp),
            "spearman_rho": float(sp),
            "spearman_p": float(spp),
        }
    r["test_correlation"] = pearson

    # Test 4: Multiple OLS-Regression
    # delay ~ rush_hour + weekend + verkehrsmittel_text + precipitation + temperature
    cols_needed = ["delay_arr_sec", "is_rush_hour", "is_weekend",
                   "verkehrsmittel_text", "niederschlag_mm",
                   "temperatur_c", "hour"]
    avail = [c for c in cols_needed if c in valid.columns]
    if {"delay_arr_sec", "is_rush_hour", "is_weekend"}.issubset(set(avail)):
        # Vollständiger Wetter-valider Datensatz (kein Subsample): macht die
        # Koeffizienten deterministisch und stabil. Seltene Linientypen (z.B.
        # NJ, n<1000) wären in einem 200k-Subsample stark untererfasst und
        # lieferten schwankende Schätzer.
        sub = valid[avail].dropna()
        formula_parts = []
        if "is_rush_hour" in avail:
            formula_parts.append("C(is_rush_hour)")
        if "is_weekend" in avail:
            formula_parts.append("C(is_weekend)")
        if "verkehrsmittel_text" in avail:
            formula_parts.append("C(verkehrsmittel_text)")
        if "niederschlag_mm" in avail:
            formula_parts.append("niederschlag_mm")
        if "temperatur_c" in avail:
            formula_parts.append("temperatur_c")
        formula = "delay_arr_sec ~ " + " + ".join(formula_parts)
        try:
            model = smf.ols(formula, data=sub).fit()
            r["test_ols"] = {
                "name": "Multiple OLS-Regression",
                "formula": formula,
                "n_observations": int(model.nobs),
                "r_squared": float(model.rsquared),
                "adj_r_squared": float(model.rsquared_adj),
                "f_statistic": float(model.fvalue),
                "f_p_value": float(model.f_pvalue),
                "coefficients": {k: {"value": float(v), "p": float(model.pvalues[k])}
                                 for k, v in model.params.items()},
            }
        except Exception as e:
            r["test_ols"] = {"error": str(e), "formula": formula}

    # Top-Stationen
    if "haltestellen_name" in valid.columns:
        top_delay = (valid.groupby("haltestellen_name")
                     .agg(n=("delay_arr_sec", "count"),
                          mean=("delay_arr_sec", "mean"))
                     .query("n >= 1000")
                     .nlargest(10, "mean"))
        r["top_10_stations_highest_mean_delay"] = [
            {"station": name, "n": int(row["n"]), "mean_sec": float(row["mean"])}
            for name, row in top_delay.iterrows()
        ]

    # Linien-Typ Counts (fuer Methods-Sektion)
    if "verkehrsmittel_text" in valid.columns:
        r["verkehrsmittel_text_distribution"] = {
            k: int(v) for k, v in valid["verkehrsmittel_text"].value_counts().items()
        }

    # Datum-Range — auf Basis BETRIEBSTAG (operativer Tag), nicht ankunftszeit.
    # ankunftszeit kann nach Mitternacht auf den Folgetag fallen (Nachtzüge),
    # was die Kalenderspanne künstlich aufbläht. Die echte Datenbasis ist die
    # Anzahl distinct Betriebstage (= was App und Präsentation ausweisen).
    if "betriebstag" in valid.columns:
        bt = pd.to_datetime(valid["betriebstag"], errors="coerce").dropna()
        r["data_range"] = {
            "start": str(bt.min().date()),
            "end": str(bt.max().date()),
            "n_days": int(bt.dt.normalize().nunique()),
            "n_calendar_span": int((bt.max() - bt.min()).days + 1),
        }

    out_json = OUT_DIR / "results.json"
    out_json.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSchrieb {out_json}")

    # Pretty-Print das wichtigste
    print("\n=== KEY RESULTS ===")
    print(f"Events: {r['n_total_events']:,}")
    print(f"Mittlere Verspaetung: {r['mean_delay_sec']:.1f}s")
    print(f"Median: {r['median_delay_sec']:.1f}s")
    print(f"P95: {r['p95_delay_sec']:.1f}s")
    print(f"Klassisch verspaetet (>3min): {r['pct_classically_delayed']:.2f}%")
    print()
    print(f"Welch t: t={r['test_welch_ttest']['t_statistic']:.2f}, "
          f"p={r['test_welch_ttest']['p_value']:.2e}")
    print(f"  Werktag mean: {r['test_welch_ttest']['mean_werktag_sec']:.1f}s")
    print(f"  Wochenende mean: {r['test_welch_ttest']['mean_wochenende_sec']:.1f}s")
    print()
    print(f"ANOVA F: F={r['test_anova_linientyp']['f_statistic']:.1f}, "
          f"p={r['test_anova_linientyp']['p_value']:.2e}")
    print(f"  Gruppen: {r['test_anova_linientyp']['groups']}")
    print()
    if "test_ols" in r and "r_squared" in r["test_ols"]:
        print(f"OLS R^2: {r['test_ols']['r_squared']:.4f}, "
              f"adj_R^2: {r['test_ols']['adj_r_squared']:.4f}")
        print(f"  N: {r['test_ols']['n_observations']:,}")
    print()
    if "test_correlation" in r:
        for col, st in r["test_correlation"].items():
            print(f"Pearson {col}: r={st['pearson_r']:.3f}, p={st['pearson_p']:.2e} "
                  f"(n={st['n']:,})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
