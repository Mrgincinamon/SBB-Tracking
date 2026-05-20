"""Quick verification: load the pilot Parquet files and print summary stats."""

import pandas as pd
from pathlib import Path

PARQUET_DIR = Path(__file__).parent.parent / "data" / "raw" / "istdaten"
files = sorted(PARQUET_DIR.glob("*_sbb.parquet"))

print(f"Pilot-Files: {len(files)}")
dfs = [pd.read_parquet(f) for f in files]
df = pd.concat(dfs, ignore_index=True)
print(f"Total Records: {len(df):,}")
print(f"\nColumns ({len(df.columns)}): {list(df.columns)}")

print("\n--- Sample (3 rows) ---")
print(df.sample(3, random_state=42).to_string())

print("\n--- Delay-Statistik (Ankunft, sek) ---")
mask = df["an_prognose_status"] == "REAL"
real = df.loc[mask, "delay_arr_sec"]
print(f"  REAL-Status-Anteil: {mask.mean():.1%} ({mask.sum():,}/{len(df):,})")
print(f"  Anzahl gueltig: {real.notna().sum():,}")
print(f"  Median:  {real.median():>8.0f} s")
print(f"  Mittel:  {real.mean():>8.0f} s")
print(f"  P95:     {real.quantile(0.95):>8.0f} s")
print(f"  Max:     {real.max():>8.0f} s")
print(f"  Anteil > 180s (klassische Versp.): {(real > 180).mean():.1%}")

print("\n--- Top 10 Bahnhoefe nach Halt-Anzahl ---")
print(df["haltestellen_name"].value_counts().head(10).to_string())

print("\n--- Liniencodes (top 10) ---")
print(df["linien_text"].value_counts().head(10).to_string())
