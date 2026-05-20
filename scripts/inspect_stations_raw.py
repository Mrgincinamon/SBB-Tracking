"""Debug: inspect the raw stations CSV to see actual column names and values."""

import pandas as pd

URL = (
    "https://data.sbb.ch/api/explore/v2.1/catalog/datasets/"
    "dienststellen-gemass-opentransportdataswiss/exports/csv"
)

df = pd.read_csv(URL, sep=";", low_memory=False)
print(f"Shape: {df.shape}")
print(f"\nColumns ({len(df.columns)}):")
for c in df.columns:
    print(f"  {c}")

print("\n--- meansoftransport: unique sample ---")
print(df["meansoftransport"].value_counts(dropna=False).head(15))

print("\n--- hasgeolocation: unique values ---")
print(df["hasgeolocation"].value_counts(dropna=False))

print("\n--- validto: NA-Anteil ---")
print(f"NaN: {df['validto'].isna().sum()}  /  total {len(df)}")

print("\n--- First row (transposed) ---")
print(df.iloc[0].to_string())
