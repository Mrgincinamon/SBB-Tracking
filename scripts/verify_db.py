"""Quick DB sanity check after notebooks 01-02 ran."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
import utils

tables = utils.query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print("Tabellen in DB:")
print(tables.to_string(index=False))

for t in tables["name"]:
    n = utils.query(f"SELECT COUNT(*) AS n FROM {t}").iloc[0, 0]
    print(f"  {t}: {n:,} Records")

# DB-Groesse
db = utils.db_path()
print(f"\nDB-Datei: {db}")
print(f"Groesse:  {db.stat().st_size / 1024**2:.1f} MB")

# Prepared parquet
import pandas as pd
p = utils.project_root() / "data" / "processed" / "delays_prepared.parquet"
if p.exists():
    df = pd.read_parquet(p)
    print(f"\ndelays_prepared.parquet: {len(df):,} Zeilen, {p.stat().st_size / 1024**2:.1f} MB")
    print(f"Zeitraum: {df['betriebstag'].min()}  bis  {df['betriebstag'].max()}")
    print(f"Mit Wetter: {df['temperatur_c'].notna().sum():,}")

# LLM Output
p2 = utils.project_root() / "data" / "processed" / "llm_delay_reasons.parquet"
if p2.exists():
    df2 = pd.read_parquet(p2)
    print(f"\nllm_delay_reasons.parquet: {len(df2)} Tage analysiert")
    print(df2["llm_ursache"].value_counts().to_string())
