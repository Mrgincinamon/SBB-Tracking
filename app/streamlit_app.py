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

# Streamlit-Standard "Running"-Icon (Schwimmer) oben rechts ausblenden —
# wir nutzen stattdessen die eigene SBB-Zug-Animation als Loading-Indikator.
st.markdown(
    "<style>[data-testid='stStatusWidget']{display:none;}</style>",
    unsafe_allow_html=True,
)


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
with st.spinner("Lade Verspätungs-Datensatz (2.7 Mio Events)..."):
    df_delays = load_delays()
if df_delays.empty:
    st.error("❌ Keine Daten gefunden. Bitte erst Notebook 01 und 02 ausführen, "
             "um die Datenbank und das Prepared-Parquet zu erstellen.")
    st.info("ℹ️ Anleitung: Aus dem Projekt-Root die Notebooks `01_datenbank_speicherung.ipynb` "
            "und `02_datenaufbereitung.ipynb` ausführen (z.B. via `jupyter nbconvert --execute`).")
    st.stop()

# KPI-Zeile mit Schluessel-Metriken (sofort sichtbar ohne Tab-Wechsel)
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
_n_total = len(df_delays)
_mean_delay = df_delays["delay_arr_sec"].mean()
_pct_late = df_delays["is_late_3min"].mean() * 100
_n_days = df_delays["betriebstag"].nunique()
kpi1.metric("Analysierte Halte", f"{_n_total/1e6:.2f} M",
            help="Zug-Halte mit gültiger Ankunftszeit (Status REAL)")
kpi2.metric("Ø Verspätung", f"{_mean_delay:.1f} s",
            help="Mittlere Ankunftsverspätung über alle Halte")
kpi3.metric("Klassisch verspätet", f"{_pct_late:.2f} %",
            help="Anteil Halte mit >3 Minuten Verspätung (SBB-Standard)")
kpi4.metric("Tage Datenbasis", _n_days,
            help="48 Tage Apr–Mai 2026, hochaufgelöst pro Zug-Halt")

st.markdown("---")

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

    # Drill-Down: Wochentag + Stunde auswählen → Kennzahlen passen sich an
    st.markdown("#### Kennzahlen — wähle Tag und/oder Stunde für Details")
    fcol1, fcol2 = st.columns(2)
    day_opt = fcol1.selectbox(
        "Wochentag", ["Alle Tage"] + ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
        key="tod_day",
    )
    hour_opt = fcol2.selectbox(
        "Stunde", ["Alle Stunden"] + list(range(24)),
        key="tod_hour",
    )

    overall_mean = df["delay_arr_sec"].mean()
    sub = df
    label_parts = []
    if day_opt != "Alle Tage":
        sub = sub[sub["weekday"] == day_opt]
        label_parts.append(day_opt)
    if hour_opt != "Alle Stunden":
        sub = sub[sub["hour"] == int(hour_opt)]
        label_parts.append(f"{int(hour_opt):02d}:00 Uhr")

    if label_parts:
        # Spezifische Auswahl (Tag und/oder Stunde)
        st.subheader(f"📍 Auswahl: {' · '.join(label_parts)}")
        c1, c2, c3 = st.columns(3)
        if len(sub) > 0:
            c1.metric(
                "Mean Delay", f"{sub['delay_arr_sec'].mean():.1f} s",
                f"{sub['delay_arr_sec'].mean() - overall_mean:+.1f} s vs Ø "
                f"{overall_mean:.1f} s",
            )
            c2.metric("Halte in Auswahl", f"{len(sub):,}")
            c3.metric("Abweichung vom Schnitt",
                      f"{(sub['delay_arr_sec'].mean() / overall_mean - 1) * 100:+.1f} %")
        else:
            c1.info("Keine Daten für diese Auswahl.")
    else:
        # Default: Rush-Hour vs Off-Peak
        st.subheader("Rush-Hour vs. Off-Peak")
        rush = df.loc[df["is_rush_hour"], "delay_arr_sec"]
        off = df.loc[~df["is_rush_hour"], "delay_arr_sec"]
        col1, col2, col3 = st.columns(3)
        col1.metric("Rush-Hour: Mean Delay", f"{rush.mean():.1f} s",
                    f"{rush.mean() - off.mean():+.1f} s vs Off-Peak")
        col2.metric("Off-Peak: Mean Delay", f"{off.mean():.1f} s")
        col3.metric("Differenz", f"{(rush.mean() / off.mean() - 1) * 100:+.1f}%")


# === TAB 3: Pendler-Insight (LLM) ===
import random

# Allgemeine (städteunabhängige) Beispiel-Fragen
_GENERIC_QUESTIONS = [
    "Zu welcher Tageszeit sind Züge am pünktlichsten?",
    "Welcher Zugtyp ist am zuverlässigsten — S-Bahn, IC oder IR?",
    "Sind Wochenenden wirklich pünktlicher als Werktage?",
    "Welche Bahnhöfe haben die grössten Verspätungen?",
    "Lohnt es sich, die Rush-Hour zu meiden?",
    "Sind internationale Züge unpünktlicher als Schweizer Züge?",
    "Wie stark beeinflusst Regen die Verspätungen?",
    "Welcher Wochentag ist am schlimmsten?",
    "Ist der Abendverkehr schlimmer als der Morgenverkehr?",
    "Wann ist die schlechteste Zeit zum Reisen?",
    "Sind Nachtzüge besonders unpünktlich?",
    "Wie pünktlich sind die Züge am frühen Morgen?",
]

# Städte für template-generierte Fragen (alle mit Daten im Datensatz)
_CITIES = [
    "Zürich", "Bern", "Basel", "Genève", "Lausanne", "Luzern", "Winterthur",
    "St. Gallen", "Lugano", "Olten", "Biel", "Chur", "Fribourg", "Zug",
    "Thun", "Neuchâtel", "Schaffhausen", "Aarau", "Baden", "Wil",
]

# Templates mit {c}-Platzhalter für die Stadt
_CITY_TEMPLATES = [
    "Wie pünktlich ist der Bahnhof {c}?",
    "Ist {c} ein Verspätungs-Hotspot?",
    "Lohnt sich die Fahrt ab {c} morgens?",
    "Wie zuverlässig sind die Züge in {c}?",
]


def question_pool() -> list[str]:
    """Erzeugt den vollständigen Fragen-Pool (generisch + Stadt × Template)."""
    pool = list(_GENERIC_QUESTIONS)
    for c in _CITIES:
        for t in _CITY_TEMPLATES:
            pool.append(t.format(c=c))
    return pool


N_PILLS = 6  # Anzahl gleichzeitig angezeigter Bubble-Fragen
DEFAULT_Q = ""  # Feld startet leer, Placeholder lädt zum Fragen ein

# SBB-Zug-Loading-Animation: handgezeichneter SVG-Zug (kein Emoji) faehrt auf
# Gleisen in SBB-Rot. CSS-Animation laeuft browserseitig waehrend des API-Calls.
# Hinweis: Eigene SVG-Grafik im SBB-Farbstil (#EB0000), KEIN offizielles SBB-Asset.
_TRAIN_SVG = """
<svg width="475" height="50" viewBox="0 0 475 50" xmlns="http://www.w3.org/2000/svg">
  <rect x="108" y="26" width="7" height="3" fill="#555"/>
  <rect x="219" y="26" width="7" height="3" fill="#555"/>
  <rect x="330" y="26" width="7" height="3" fill="#555"/>
  <rect x="4" y="13" width="104" height="23" rx="3" fill="#f6f6f6" stroke="#cfcfcf" stroke-width="1"/><rect x="4" y="13" width="104" height="4" rx="2" fill="#dcdcdc"/><rect x="12" y="18" width="88" height="10" fill="#23262b"/><rect x="22" y="18" width="3" height="10" fill="#f6f6f6"/><rect x="42" y="18" width="3" height="10" fill="#f6f6f6"/><rect x="62" y="18" width="3" height="10" fill="#f6f6f6"/><rect x="82" y="18" width="3" height="10" fill="#f6f6f6"/><rect x="14" y="14" width="10" height="22" fill="#EB0000"/><rect x="86" y="14" width="10" height="22" fill="#EB0000"/><rect x="4" y="31" width="104" height="3" fill="#EB0000"/><rect x="4" y="34" width="104" height="4" fill="#4a4a4a"/><circle cx="26" cy="42" r="6" fill="#111" stroke="#888" stroke-width="1.5"/><circle cx="86" cy="42" r="6" fill="#111" stroke="#888" stroke-width="1.5"/>
  <rect x="115" y="13" width="104" height="23" rx="3" fill="#f6f6f6" stroke="#cfcfcf" stroke-width="1"/><rect x="115" y="13" width="104" height="4" rx="2" fill="#dcdcdc"/><rect x="123" y="18" width="88" height="10" fill="#23262b"/><rect x="133" y="18" width="3" height="10" fill="#f6f6f6"/><rect x="153" y="18" width="3" height="10" fill="#f6f6f6"/><rect x="173" y="18" width="3" height="10" fill="#f6f6f6"/><rect x="193" y="18" width="3" height="10" fill="#f6f6f6"/><rect x="125" y="14" width="10" height="22" fill="#EB0000"/><rect x="197" y="14" width="10" height="22" fill="#EB0000"/><rect x="115" y="31" width="104" height="3" fill="#EB0000"/><rect x="115" y="34" width="104" height="4" fill="#4a4a4a"/><circle cx="137" cy="42" r="6" fill="#111" stroke="#888" stroke-width="1.5"/><circle cx="197" cy="42" r="6" fill="#111" stroke="#888" stroke-width="1.5"/>
  <rect x="226" y="13" width="104" height="23" rx="3" fill="#f6f6f6" stroke="#cfcfcf" stroke-width="1"/><rect x="226" y="13" width="104" height="4" rx="2" fill="#dcdcdc"/><rect x="234" y="18" width="88" height="10" fill="#23262b"/><rect x="244" y="18" width="3" height="10" fill="#f6f6f6"/><rect x="264" y="18" width="3" height="10" fill="#f6f6f6"/><rect x="284" y="18" width="3" height="10" fill="#f6f6f6"/><rect x="304" y="18" width="3" height="10" fill="#f6f6f6"/><rect x="236" y="14" width="10" height="22" fill="#EB0000"/><rect x="308" y="14" width="10" height="22" fill="#EB0000"/><rect x="226" y="31" width="104" height="3" fill="#EB0000"/><rect x="226" y="34" width="104" height="4" fill="#4a4a4a"/><circle cx="248" cy="42" r="6" fill="#111" stroke="#888" stroke-width="1.5"/><circle cx="308" cy="42" r="6" fill="#111" stroke="#888" stroke-width="1.5"/>
  <rect x="337" y="13" width="104" height="23" rx="3" fill="#f6f6f6" stroke="#cfcfcf" stroke-width="1"/><rect x="337" y="13" width="104" height="4" rx="2" fill="#dcdcdc"/><rect x="345" y="18" width="88" height="10" fill="#23262b"/><rect x="355" y="18" width="3" height="10" fill="#f6f6f6"/><rect x="375" y="18" width="3" height="10" fill="#f6f6f6"/><rect x="395" y="18" width="3" height="10" fill="#f6f6f6"/><rect x="415" y="18" width="3" height="10" fill="#f6f6f6"/><rect x="347" y="14" width="10" height="22" fill="#EB0000"/><rect x="419" y="14" width="10" height="22" fill="#EB0000"/><rect x="337" y="31" width="104" height="3" fill="#EB0000"/><rect x="337" y="34" width="104" height="4" fill="#4a4a4a"/><circle cx="359" cy="42" r="6" fill="#111" stroke="#888" stroke-width="1.5"/><circle cx="419" cy="42" r="6" fill="#111" stroke="#888" stroke-width="1.5"/>
  <path d="M441 13 q22 0 34 12 q2 4 1 11 H455 q-14 0 -14 -12 Z" fill="#EB0000"/>
  <path d="M444 17 q15 1 23 9 H444 Z" fill="#15171a"/>
  <circle cx="471" cy="31" r="2.4" fill="#fff4b0"/>
</svg>
"""

def train_loader_html(text: str = "deine Anfrage wird ausgewertet") -> str:
    """SBB-Zug-Loading-Animation. animation-delay negativ -> Zug ist sofort
    sichtbar (startet mitten im Lauf), kein Warten bis er ins Bild faehrt."""
    return f"""
<style>
@keyframes sbb-train-move {{
  0%   {{ left: -490px; }}      /* Zug (~475px) startet komplett links ausserhalb */
  100% {{ left: 100%; }}        /* linke Kante an rechtem Rand -> faehrt ganz raus */
}}
.sbb-loader-wrap {{ margin: 0.6rem 0 0.4rem 0; }}
.sbb-track {{
  position: relative;
  height: 58px;
  overflow: hidden;
  border-bottom: 4px solid #9a9a9a;
  background:
    repeating-linear-gradient(90deg,#9a9a9a 0 5px,transparent 5px 24px)
      bottom 0 left 0 / 100% 10px no-repeat,
    linear-gradient(#bbbbbb,#bbbbbb)
      bottom 4px left 0 / 100% 2px no-repeat;
}}
.sbb-train {{
  position: absolute;
  bottom: 8px;
  left: -490px;
  animation: sbb-train-move 4.5s linear infinite;
  animation-delay: -1.8s;   /* startet mitten im Lauf -> sofort sichtbar */
  will-change: left;
}}
.sbb-loader-text {{
  text-align: center;
  color: #EB0000;          /* SBB-Rot */
  font-weight: 600;
  margin-top: 8px;
  letter-spacing: 0.3px;
}}
</style>
<div class="sbb-loader-wrap">
  <div class="sbb-track"><div class="sbb-train">{_TRAIN_SVG}</div></div>
  <div class="sbb-loader-text">{text}</div>
</div>
"""

# Deutsche Stoppwörter, die bei der Bahnhof-Keyword-Suche ignoriert werden
_STOPWORDS = {
    "wie", "welche", "welcher", "welches", "sind", "wirklich", "haben", "fahren",
    "lohnt", "vermeiden", "meiden", "zwischen", "morgens", "abends", "mittags",
    "nachts", "puenktlich", "pünktlich", "zuverlaessig", "zuverlässig", "tageszeit",
    "zugtyp", "bahn", "bahnhof", "bahnhoefe", "bahnhöfe", "groessten", "grössten",
    "verspaetung", "verspätung", "verspaetungen", "verspätungen", "wochenende",
    "wochenenden", "werktage", "werktag", "rush", "hour", "zuege", "züge", "zug",
    "der", "die", "das", "und", "oder", "als", "wenn", "denn", "auch", "noch",
}


def _apply_example():
    """Pill-Klick: Frage übernehmen UND direkt absenden (1-Klick-UX)."""
    picked = st.session_state.get("example_pills")
    if picked:
        st.session_state.q_text = picked
        st.session_state.auto_generate = True


def build_llm_context(df: pd.DataFrame, question: str) -> str:
    """Reichhaltiger Datenkontext: gesamt + stündlich + pro Zugtyp + Frage-relevante Bahnhöfe."""
    import re

    n_total = len(df)
    mean_delay = df["delay_arr_sec"].mean()
    pct_late = df["is_late_3min"].mean() * 100
    rush_mean = df.loc[df["is_rush_hour"], "delay_arr_sec"].mean()
    off_mean = df.loc[~df["is_rush_hour"], "delay_arr_sec"].mean()
    we_mean = df.loc[df["is_weekend"].astype(bool), "delay_arr_sec"].mean()
    wt_mean = df.loc[~df["is_weekend"].astype(bool), "delay_arr_sec"].mean()

    # Stündliche Verspätung (alle 24 Stunden)
    hourly = df.groupby("hour")["delay_arr_sec"].mean().round(0)
    hourly_str = ", ".join(f"{int(h)}h={int(v)}s" for h, v in hourly.items())

    # Pro Verkehrsmittel-Typ (sortiert, nur mit genug Daten)
    by_type = (df.groupby("verkehrsmittel_text")["delay_arr_sec"]
               .agg(["mean", "count"]).query("count >= 100")
               .sort_values("mean").round(1))
    type_str = "\n".join(
        f"  {typ}: {row['mean']:.1f}s (n={int(row['count']):,})"
        for typ, row in by_type.iterrows()
    )

    # Top-5 schlimmste Bahnhöfe gesamt
    top5_late = (df.groupby("haltestellen_name")["delay_arr_sec"]
                 .agg(["mean", "count"]).query("count >= 500")
                 .sort_values("mean", ascending=False).head(5).round(1))
    top5_str = "\n".join(
        f"  {name}: {row['mean']:.1f}s (n={int(row['count']):,})"
        for name, row in top5_late.iterrows()
    )

    # Frage-relevante Bahnhöfe via Keyword-Match
    keywords = [w for w in re.findall(r"[a-zäöüA-ZÄÖÜ]{4,}", question.lower())
                if w not in _STOPWORDS]
    station_block = ""
    if keywords:
        pattern = "|".join(re.escape(k) for k in keywords)
        matched = df[df["haltestellen_name"].str.lower()
                     .str.contains(pattern, na=False, regex=True)]
        if len(matched) > 0:
            matched_agg = (matched.groupby("haltestellen_name")["delay_arr_sec"]
                           .agg(["mean", "count"]).query("count >= 30")
                           .sort_values("count", ascending=False).head(8).round(1))
            if len(matched_agg) > 0:
                station_block = "\n\nZur Frage passende Bahnhöfe (Keyword-Match):\n" + "\n".join(
                    f"  {name}: {row['mean']:.1f}s (n={int(row['count']):,})"
                    for name, row in matched_agg.iterrows()
                )

    llm_reasons = load_llm_reasons()
    worst_days = ""
    if not llm_reasons.empty:
        worst_days = "\n\nTop-5 Krisen-Tage (LLM-Hypothese):\n" + llm_reasons[
            ["datum", "wochentag", "pct_late_3min", "llm_ursache"]
        ].head(5).to_string(index=False)

    return f"""Datenbasis SBB-Verspätungen {df['betriebstag'].min()} bis {df['betriebstag'].max()} ({df['betriebstag'].nunique()} Tage):
- {n_total:,} Halte (Zug + SBB-only, Status REAL)
- Mittlere Ankunftsverspätung gesamt: {mean_delay:.1f}s
- Anteil >3 Min verspätet: {pct_late:.2f}%
- Werktag {wt_mean:.1f}s vs Wochenende {we_mean:.1f}s
- Rush-Hour {rush_mean:.1f}s vs Off-Peak {off_mean:.1f}s

Mittlere Verspätung pro Stunde (0-23h):
  {hourly_str}

Mittlere Verspätung pro Zugtyp (aufsteigend):
{type_str}

Top-5 unpünktlichste Bahnhöfe gesamt:
{top5_str}{station_block}{worst_days}"""


with tab_insight:
    st.header("Wie pendelst du am Besten..? Frag mich :)")

    if "q_text" not in st.session_state:
        st.session_state.q_text = DEFAULT_Q

    # Zufällige Bubble-Auswahl, stabil innerhalb der Session, neu bei Refresh
    if "pill_choices" not in st.session_state:
        st.session_state.pill_choices = random.sample(question_pool(), N_PILLS)

    st.pills(
        "💡 Was möchtest du über die Verspätungen der SBB wissen?",
        st.session_state.pill_choices,
        selection_mode="single",
        key="example_pills",
        on_change=_apply_example,
    )
    if st.button("🎲 Andere Fragen", key="shuffle_pills"):
        st.session_state.pill_choices = random.sample(question_pool(), N_PILLS)
        st.rerun()

    st.markdown("### Stell deine Frage zu Strecke, Zugtyp oder Tageszeit")
    insight_q = st.text_area(
        "Frage-Eingabe",
        key="q_text",
        height=80,
        label_visibility="collapsed",
        placeholder="Frag mich :)",
    )
    st.markdown(
        f"<span style='font-size:0.72em; color:#888;'>Powered by Anthropic "
        f"{MODEL_NAME} · Antwort basiert ausschliesslich auf den Projektdaten</span>",
        unsafe_allow_html=True,
    )

    # Generieren wenn Button geklickt ODER eine Beispiel-Pill gewählt wurde
    generate = st.button("Antwort generieren", type="primary")
    if st.session_state.get("auto_generate"):
        generate = True
        st.session_state.auto_generate = False

    if generate and not insight_q.strip():
        st.warning("Bitte gib zuerst eine Frage ein oder klick eine Beispiel-Frage an.")
    elif generate:
        from anthropic import Anthropic
        client = Anthropic()

        context = build_llm_context(df, insight_q)

        # SBB-Zug-Loading-Animation (CSS läuft browserseitig während des API-Calls)
        loader = st.empty()
        loader.markdown(train_loader_html(), unsafe_allow_html=True)
        try:
            msg = client.messages.create(
                model=MODEL_NAME,
                max_tokens=600,
                temperature=0.3,
                system=(
                    "Du bist ein freundlicher Pendler-Berater für den öffentlichen Verkehr "
                    "in der Schweiz. Du antwortest immer auf Deutsch, kompakt (max 4 Sätze) "
                    "und stützt dich AUSSCHLIESSLICH auf die unten gelieferten statistischen "
                    "Daten. Nenne konkrete Zahlen aus den Daten. Wenn die Daten die Frage nicht "
                    "exakt beantworten (z.B. eine spezifische Linie fehlt), sag ehrlich was du "
                    "aus den vorhandenen Daten ableiten kannst und was nicht. Du erfindest NIEMALS "
                    "Zahlen, Linien oder Bahnhöfe, die nicht im Kontext stehen."
                ),
                messages=[{
                    "role": "user",
                    "content": f"Frage: {insight_q}\n\n--- Datenkontext ---\n{context}",
                }],
            )
            answer = msg.content[0].text
            cost = (msg.usage.input_tokens / 1e6 * 3.0
                    + msg.usage.output_tokens / 1e6 * 15.0)
        finally:
            loader.empty()  # Animation entfernen sobald Antwort da ist

        st.success(answer)
        st.caption(f"Tokens: {msg.usage.input_tokens} input / {msg.usage.output_tokens} output  "
                   f"· Kosten: ${cost:.4f}")

        with st.expander("🔍 Welche Daten hat Claude gesehen? (Transparenz)"):
            st.code(context, language="text")

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
