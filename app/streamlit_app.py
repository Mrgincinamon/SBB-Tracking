"""SBB Tracker — Streamlit Webapp.

Drei Sektionen:
1. Karte — Folium-Heatmap der Bahnhof-Verspätungen
2. Time-of-Day — interaktiver Plotly-Chart Stunde × Wochentag
3. Pendler-Insight — LLM-gestützter Berater für deine Strecke

Start: streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# utils.py liegt im gleichen Ordner
sys.path.insert(0, str(Path(__file__).parent))
import utils

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from streamlit_folium import st_folium

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="SBB Tracker — Verspätungsanalyse",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv(utils.project_root() / ".env")
MODEL_NAME = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")


# ---------------------------------------------------------------------------
# Daten cachen
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_delays() -> pd.DataFrame:
    """Lade das vorbereitete Verspätungs-Dataset."""
    p = utils.project_root() / "data" / "processed" / "delays_prepared.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


@st.cache_data(ttl=3600)
def load_stations() -> pd.DataFrame:
    return utils.query("SELECT * FROM stations")


@st.cache_data(ttl=3600)
def load_llm_reasons() -> pd.DataFrame:
    p = utils.project_root() / "data" / "processed" / "llm_delay_reasons.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("🚂 SBB Tracker — Verspätungsanalyse")
st.caption("ZHAW Scientific Programming · FS2026 · Joël Hasler & Patrick Ferreira")

# Datenverfügbarkeit prüfen
df_delays = load_delays()
if df_delays.empty:
    st.error("❌ Keine Daten gefunden. Bitte erst Notebook 01 und 02 ausführen, "
             "um die Datenbank und das Prepared-Parquet zu erstellen.")
    st.stop()

# Sidebar-Filter
st.sidebar.header("Filter")
date_min, date_max = df_delays["betriebstag"].min(), df_delays["betriebstag"].max()
st.sidebar.info(f"Datenbestand: **{date_min}** bis **{date_max}** "
                f"({df_delays['betriebstag'].nunique()} Tage)")

cantons = sorted([c for c in load_stations()["cantonabbreviation"].unique()
                  if pd.notna(c)])
selected_cantons = st.sidebar.multiselect(
    "Kantone (leer = alle)", options=cantons, default=[]
)

# Daten filtern
df = df_delays.copy()
if selected_cantons:
    canton_stations = load_stations().query("cantonabbreviation in @selected_cantons")["number"].tolist()
    df = df.loc[df["bpuic"].isin(canton_stations)]

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_karte, tab_tod, tab_insight, tab_about = st.tabs([
    "🗺️ Karte", "🕐 Time-of-Day", "🤖 Pendler-Insight (LLM)", "ℹ️ Über"
])


# === TAB 1: Karte ===
with tab_karte:
    st.header("Verspätungs-Hotspots auf der Schweizer Karte")
    st.caption("Pro Bahnhof: durchschnittliche Ankunftsverspätung (Sekunden). "
               "Rot = hohe Verspätung, Grün = pünktlich.")

    min_halte = st.slider("Mindestanzahl Halte pro Bahnhof (Filter Rauschen)",
                          min_value=50, max_value=2000, value=200, step=50)

    # Aggregat pro Station
    stations = load_stations()
    by_station = (df.groupby("bpuic")
                  .agg(n_halte=("delay_arr_sec", "size"),
                       mean_delay=("delay_arr_sec", "mean"),
                       pct_late=("is_late_3min", "mean"))
                  .query("n_halte >= @min_halte")
                  .reset_index())
    by_station = by_station.merge(
        stations[["number", "designationofficial", "lat", "lon", "cantonabbreviation"]],
        left_on="bpuic", right_on="number", how="inner"
    )
    by_station["pct_late"] = (by_station["pct_late"] * 100).round(1)
    by_station["mean_delay"] = by_station["mean_delay"].round(1)

    st.metric("Anzahl Bahnhöfe (gefiltert)", len(by_station))

    # Folium-Karte
    if len(by_station) > 0:
        m = folium.Map(location=[46.85, 8.2], zoom_start=8, tiles="cartodbpositron")

        # Farbskala definieren
        def delay_color(sec):
            if sec < 20: return "#1a9850"
            elif sec < 40: return "#66bd63"
            elif sec < 60: return "#fdae61"
            elif sec < 90: return "#f46d43"
            else: return "#d73027"

        for _, r in by_station.iterrows():
            folium.CircleMarker(
                location=[r["lat"], r["lon"]],
                radius=4 + min(r["n_halte"] / 500, 10),
                color=delay_color(r["mean_delay"]),
                fill=True,
                fill_opacity=0.7,
                popup=folium.Popup(
                    f"<b>{r['designationofficial']}</b> ({r['cantonabbreviation']})<br>"
                    f"Mean Delay: {r['mean_delay']} s<br>"
                    f"Klassisch verspätet: {r['pct_late']}%<br>"
                    f"Halte (Stichprobe): {r['n_halte']:,}",
                    max_width=300
                ),
            ).add_to(m)
        st_folium(m, width=None, height=550, returned_objects=[])

    st.subheader("Top-20 Bahnhöfe nach mittlerer Verspätung")
    top20 = (by_station.sort_values("mean_delay", ascending=False)
             .head(20)[["designationofficial", "cantonabbreviation", "n_halte",
                        "mean_delay", "pct_late"]])
    top20.columns = ["Bahnhof", "Kanton", "Halte", "Mean Delay [s]", "% Verspaetet"]
    st.dataframe(top20, use_container_width=True, hide_index=True)


# === TAB 2: Time-of-Day ===
with tab_tod:
    st.header("Verspätung nach Tageszeit und Wochentag")
    st.caption("Wann fährt man am sichersten? Heatmap zeigt mittlere Verspätung "
               "in Sekunden.")

    pivot = (df.groupby(["weekday", "hour"])["delay_arr_sec"]
             .mean()
             .reset_index()
             .pivot(index="weekday", columns="hour", values="delay_arr_sec"))
    pivot = pivot.reindex(["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"])

    fig = px.imshow(
        pivot,
        labels=dict(x="Stunde", y="Wochentag", color="Mean Delay [s]"),
        color_continuous_scale="YlOrRd",
        aspect="auto",
        text_auto=".0f",
    )
    fig.update_layout(height=400, margin=dict(l=40, r=20, t=30, b=40))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Rush-Hour vs. Off-Peak")
    rush = df.loc[df["is_rush_hour"], "delay_arr_sec"]
    off = df.loc[~df["is_rush_hour"], "delay_arr_sec"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Rush-Hour: Mean Delay", f"{rush.mean():.1f} s",
                f"{rush.mean() - off.mean():+.1f} s vs Off-Peak")
    col2.metric("Off-Peak: Mean Delay", f"{off.mean():.1f} s")
    col3.metric("Differenz", f"{(rush.mean() / off.mean() - 1) * 100:+.1f}%")


# === TAB 3: Pendler-Insight (LLM) ===
with tab_insight:
    st.header("🤖 Pendler-Insight — LLM-Beratung")
    st.caption(f"Powered by Anthropic {MODEL_NAME}")

    insight_q = st.text_area(
        "Stell deine Frage zu einer Strecke oder Tageszeit:",
        value="Wie zuverlaessig ist die S-Bahn Zuerich morgens zwischen 7 und 9 Uhr?",
        height=80,
    )

    if st.button("Antwort generieren", type="primary"):
        from anthropic import Anthropic
        client = Anthropic()

        # Kontext aus den Daten erstellen
        n_total = len(df)
        mean_delay = df["delay_arr_sec"].mean()
        pct_late = df["is_late_3min"].mean() * 100
        rush_mean = df.loc[df["is_rush_hour"], "delay_arr_sec"].mean()
        off_mean = df.loc[~df["is_rush_hour"], "delay_arr_sec"].mean()

        top5_late = (df.groupby("haltestellen_name")["delay_arr_sec"]
                     .agg(["mean", "count"])
                     .query("count >= 500")
                     .sort_values("mean", ascending=False)
                     .head(5))

        llm_reasons = load_llm_reasons()
        worst_days_summary = ""
        if not llm_reasons.empty:
            worst_days_summary = llm_reasons[["datum", "wochentag",
                                              "pct_late_3min", "llm_ursache"]].head(5).to_string(index=False)

        context = f"""Datenbasis SBB-Verspaetungen vom {df['betriebstag'].min()} bis {df['betriebstag'].max()}:
- {n_total:,} Verspaetungs-Events (Zug + SBB-only, Status REAL)
- Mean Ankunftsverspaetung: {mean_delay:.1f} s
- Anteil klassisch verspaetet (>3 Min): {pct_late:.2f}%
- Rush-Hour Mean Delay: {rush_mean:.1f} s
- Off-Peak Mean Delay: {off_mean:.1f} s

Top-5 Bahnhoefe mit hoechster mittlerer Verspaetung:
{top5_late.to_string()}

Top-5 schlimmste Tage mit LLM-hypothetisierter Ursache:
{worst_days_summary if worst_days_summary else "(keine LLM-Analyse vorhanden)"}"""

        with st.spinner("Claude denkt nach..."):
            msg = client.messages.create(
                model=MODEL_NAME,
                max_tokens=600,
                temperature=0.3,
                system=(
                    "Du bist ein freundlicher Pendler-Berater fuer den oeffentlichen Verkehr in der Schweiz. "
                    "Du antwortest immer in deutscher Sprache, kompakt (max 4 Saetze) und basiert AUSSCHLIESSLICH "
                    "auf den unten gelieferten statistischen Daten. Wenn die Daten die Frage nicht beantworten "
                    "koennen, sag das ehrlich. Du erfindest KEINE Zahlen oder Linien."
                ),
                messages=[{
                    "role": "user",
                    "content": f"Frage: {insight_q}\n\n--- Datenkontext ---\n{context}",
                }],
            )
            answer = msg.content[0].text
            cost = (msg.usage.input_tokens / 1e6 * 3.0
                    + msg.usage.output_tokens / 1e6 * 15.0)

        st.success(answer)
        st.caption(f"Tokens: {msg.usage.input_tokens} input / {msg.usage.output_tokens} output  "
                   f"· Kosten: ${cost:.4f}")

    # Anzeige der vorab analysierten Krisen-Tage
    if not load_llm_reasons().empty:
        st.subheader("Vorab analysierte Krisen-Tage (Notebook 04)")
        reasons = load_llm_reasons()[["datum", "wochentag", "pct_late_3min",
                                       "llm_ursache", "llm_konfidenz", "llm_begruendung"]]
        reasons.columns = ["Datum", "Tag", "% Verspaetet", "LLM-Ursache",
                           "Konfidenz", "Begruendung"]
        st.dataframe(reasons, use_container_width=True, hide_index=True)


# === TAB 4: Über ===
with tab_about:
    st.header("Über dieses Projekt")
    st.markdown("""
        **SBB Tracker** analysiert die Pünktlichkeit der Schweizerischen
        Bundesbahnen auf Basis offizieller Open-Data-Quellen.

        ### Datenquellen
        - **Ist-Daten** (`opentransportdata.swiss`) — tägliche Soll-/Ist-Vergleiche
          aller SBB-Zug-Halte
        - **Stationen** (`data.sbb.ch`) — Bahnhof-Stammdaten mit Geo-Koordinaten
        - **Wetter** (`MeteoSchweiz`) — stündliche Messdaten von 15 Stationen
        - **LLM** (Anthropic Claude Sonnet 4.6) — qualitative Ursachen-Hypothesen

        ### Methodik
        Notebooks 01-04 bauen die Datenpipeline und führen vier statistische
        Tests (Welch's t-Test, ANOVA, Pearson/Spearman, OLS-Regression) mit
        p-Value-Reporting durch.

        ### Code
        - GitHub: [Mrgincinamon/SBB-Tracking](https://github.com/Mrgincinamon/SBB-Tracking)
        - Lizenz: MIT
        - Daten: CC-BY (SBB, MeteoSchweiz)

        ### Modul-Kontext
        ZHAW Scientific Programming FS2026  ·  Dozent: Mario Gellrich
    """)
