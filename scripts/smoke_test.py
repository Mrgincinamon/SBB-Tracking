"""Quick smoke test: verify all key packages import and .env loads correctly."""
import pandas, numpy, scipy, statsmodels, matplotlib, seaborn
import streamlit, folium, plotly, requests, anthropic
from dotenv import load_dotenv
import os

print("OK: alle 12 Imports laufen")

load_dotenv()
key = os.getenv("ANTHROPIC_API_KEY")
ok = bool(key) and key.startswith("sk-ant-api03-")
print(f"API-Key sichtbar aus .env: {ok}")
if ok:
    print(f"  Länge: {len(key)} Zeichen, endet auf ...{key[-4:]}")

model = os.getenv("ANTHROPIC_MODEL", "(default)")
print(f"Model-Setting: {model}")
