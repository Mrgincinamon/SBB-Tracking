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

import branca.colormap as cm
import folium
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

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


# Streamlit-Standard "Running"-Icon (Schwimmer) oben rechts ausblenden —
# wir nutzen stattdessen die eigene SBB-Zug-Animation als Loading-Indikator.
st.markdown(
    """
    <style>
    /* Standard-Streamlit-"Running"-Schwimmer oben rechts ausblenden */
    [data-testid='stStatusWidget'] { display: none; }

    /* Pills (Beispiel-Fragen) im SBB-Stil: luftig, abgerundet, rot */
    [data-testid='stButtonGroup'] {
        gap: 10px !important;
        flex-wrap: wrap !important;
    }
    [data-testid='stBaseButton-pills'] {
        border-radius: 18px !important;
        border: 1.5px solid #EB0000 !important;
        color: #EB0000 !important;
        background: #ffffff !important;
        padding: 6px 16px !important;
        margin: 4px 4px !important;
        font-weight: 500 !important;
        transition: all 0.15s ease !important;
    }
    [data-testid='stBaseButton-pills']:hover {
        background: #EB0000 !important;
        color: #ffffff !important;
        box-shadow: 0 2px 8px rgba(235,0,0,0.25) !important;
    }
    </style>
    """,
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

# Daten filtern (gecacht pro Kantons-Auswahl -> schnelle Reruns)
@st.cache_data(show_spinner=False)
def get_filtered_df(cantons_key: tuple) -> pd.DataFrame:
    d = load_delays()
    if cantons_key:
        nums = load_stations().query(
            "cantonabbreviation in @cantons_key")["number"].tolist()
        d = d.loc[d["bpuic"].isin(nums)]
    return d


df = get_filtered_df(tuple(selected_cantons))

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
               "Farbskala von hellrot (pünktlich) bis dunkelrot (stark verspätet). "
               "Mit dem Hotspot-Regler rechts lassen sich gezielt die "
               "verspätungs­anfälligsten Bahnhöfe isolieren.")

    slider_col1, slider_col2 = st.columns(2)
    with slider_col1:
        min_halte = st.slider(
            "Mindestanzahl Halte pro Bahnhof (Filter gegen Rauschen)",
            min_value=50, max_value=1500, value=200, step=50,
            help="Gesamtzahl der Zug-Halte an diesem Bahnhof über den ganzen "
                 "48-Tage-Zeitraum (nicht pro Tag). Bahnhöfe mit weniger Halten "
                 "werden ausgeblendet, da ihr Mittelwert statistisch unzuverlässig "
                 "ist. Ab ~500 Halten ist die Schätzung stabil (95%-CI ±11 s).",
        )
    with slider_col2:
        min_delay = st.slider(
            "Nur Hotspots: Mindest-Ø-Verspätung [s]",
            min_value=0, max_value=200, value=0, step=10,
            help="Zeigt nur Bahnhöfe, deren mittlere Ankunftsverspätung mindestens "
                 "diesen Wert erreicht. 0 = alle anzeigen. Höhere Werte isolieren "
                 "die Verspätungs-Hotspots (v.a. Grenzbahnhöfe).",
        )

    # Aggregat pro Station (gecacht pro Kantons-Auswahl + Schwellwert)
    @st.cache_data(show_spinner=False)
    def aggregate_stations(cantons_key: tuple, min_n: int) -> pd.DataFrame:
        d = get_filtered_df(cantons_key)
        agg = (d.groupby("bpuic")
               .agg(n_halte=("delay_arr_sec", "size"),
                    mean_delay=("delay_arr_sec", "mean"),
                    pct_late=("is_late_3min", "mean"))
               .query("n_halte >= @min_n")
               .reset_index())
        agg = agg.merge(
            load_stations()[["number", "designationofficial", "lat", "lon",
                             "cantonabbreviation"]],
            left_on="bpuic", right_on="number", how="inner")
        agg["pct_late"] = (agg["pct_late"] * 100).round(1)
        agg["mean_delay"] = agg["mean_delay"].round(1)
        return agg

    def apply_hotspot(agg: pd.DataFrame, min_d: int) -> pd.DataFrame:
        """Billiger Nachfilter auf das (kleine) Aggregat: nur Bahnhöfe mit
        mittlerer Verspätung >= min_d. min_d == 0 -> keine Filterung."""
        return agg[agg["mean_delay"] >= min_d] if min_d > 0 else agg

    by_station = apply_hotspot(
        aggregate_stations(tuple(selected_cantons), min_halte), min_delay)

    kpi_left, kpi_right = st.columns(2)
    kpi_left.metric("Sichtbare Bahnhöfe", len(by_station))
    if min_delay > 0:
        kpi_right.metric("Hotspot-Schwelle", f"≥ {min_delay} s")

    # Folium-Karte als STATISCHES HTML rendern (components.html) — viel schneller
    # als st_folium (kein bidirektionaler Roundtrip), gecacht pro Auswahl.
    @st.cache_data(show_spinner=False)
    def build_map_html(cantons_key: tuple, min_n: int, min_d: int) -> str:
        full = aggregate_stations(cantons_key, min_n)
        if len(full) == 0:
            return ""
        m = folium.Map(location=[46.85, 8.2], zoom_start=8, tiles="cartodbpositron")

        # Kontinuierliche Rot-Gradient-Skala (hellrot -> dunkelrot), wie Covid-Projekt.
        # vmin/vmax robust auf 5./95. Perzentil der VOLLEN Population (vor Hotspot-
        # Filter), damit die Farben absolute Verspätungsniveaus zeigen und beim
        # Verschieben des Hotspot-Reglers nicht "zurücksetzen".
        vmin = float(full["mean_delay"].quantile(0.05))
        vmax = float(full["mean_delay"].quantile(0.95))
        if vmax <= vmin:
            vmax = vmin + 1

        # Nur die Hotspot-Teilmenge zeichnen (Farbskala bleibt absolut)
        agg = apply_hotspot(full, min_d)
        if len(agg) == 0:
            return ""
        colormap = cm.LinearColormap(
            colors=["#fee0d2", "#fc9272", "#fb6a4a", "#de2d26", "#a50f15"],
            vmin=vmin, vmax=vmax,
            caption="Mittlere Ankunftsverspätung [s]")

        for _, r in agg.iterrows():
            folium.CircleMarker(
                location=[r["lat"], r["lon"]],
                radius=4 + min(r["n_halte"] / 500, 9),
                color="#555555", weight=0.6,
                fill=True, fill_color=colormap(r["mean_delay"]), fill_opacity=0.85,
                popup=folium.Popup(
                    f"<b>{r['designationofficial']}</b> ({r['cantonabbreviation']})<br>"
                    f"Mean Delay: {r['mean_delay']} s<br>"
                    f"Klassisch verspätet: {r['pct_late']}%<br>"
                    f"Halte (Stichprobe): {r['n_halte']:,}",
                    max_width=300),
            ).add_to(m)
        colormap.add_to(m)  # Legende
        return m.get_root().render()

    # Zug-Loader waehrend des (auf Cache-Miss langsamen) Karten-Builds
    map_ph = st.empty()
    map_ph.markdown(train_loader_html("Karte wird geladen …"), unsafe_allow_html=True)
    map_html = build_map_html(tuple(selected_cantons), min_halte, min_delay)
    map_ph.empty()
    if map_html:
        components.html(map_html, height=550)
    else:
        st.info("Keine Bahnhöfe für diese Filter-Einstellung.")

    st.subheader(f"Top-20 Bahnhöfe nach mittlerer Verspätung "
                 f"(von {len(by_station)} gefilterten Bahnhöfen)")
    st.caption("Passt sich automatisch dem Regler oben an.")
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

# Allgemeine (städteunabhängige) Beispiel-Fragen — bewusst über verschiedene
# Analyse-Blickwinkel gestreut (Tageszeit, Zugtyp, Wetter, Pendeln, Kuriosa),
# damit die Vorschläge nicht monoton wirken.
_GENERIC_QUESTIONS = [
    "Wann erwische ich am ehesten einen pünktlichen Zug?",
    "Wie viele Minuten kostet mich die Rush-Hour wirklich?",
    "Komme ich mit dem IC oder dem IR zuverlässiger ans Ziel?",
    "Stimmt es, dass Auslandszüge die Statistik verderben?",
    "Warum sind ausgerechnet Grenzbahnhöfe so verspätungsanfällig?",
    "Macht schlechtes Wetter die Züge spürbar langsamer?",
    "Ich pendle täglich — wann sollte ich am besten losfahren?",
    "Reise ich am Wochenende wirklich entspannter?",
    "Was waren die schlimmsten Tage im Datensatz — und warum?",
    "Ist die S-Bahn im Berufsverkehr verlässlich?",
    "Welche Stunde des Tages ist die unberechenbarste?",
    "Hat die SBB ihren Ruf als Pünktlichkeits-Weltmeister verdient?",
    "Soll ich abends lieber einen früheren Zug nehmen?",
    "Wie gross ist der Unterschied zwischen bestem und schlechtestem Bahnhof?",
]

# Städte für template-generierte Fragen (alle mit Daten im Datensatz)
_CITIES = [
    "Zürich", "Bern", "Basel", "Genève", "Lausanne", "Luzern", "Winterthur",
    "St. Gallen", "Lugano", "Olten", "Biel", "Chur", "Fribourg", "Zug",
    "Thun", "Neuchâtel", "Schaffhausen", "Aarau", "Baden", "Wil",
]

# Templates mit {c}-Platzhalter für die Stadt — verschiedene Blickwinkel statt
# vier Varianten derselben "Wie pünktlich ist X?"-Frage. Alle aus den
# Bahnhof-Mittelwerten im LLM-Kontext beantwortbar.
_CITY_TEMPLATES = [
    "Wie schlägt sich {c} im Schweizer Vergleich?",
    "Sollte ich ab {c} einen Zeitpuffer einplanen?",
    "Ist {c} ein Verspätungs-Hotspot oder eher harmlos?",
    "Wie zuverlässig komme ich in {c} an?",
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

    # Wetter-Effekt: Regenstunden vs. trockene Stunden (aus MeteoSchweiz-Join)
    weather_str = ""
    if "niederschlag_mm" in df.columns:
        w = df[df["niederschlag_mm"].notna()]
        if len(w) > 1000:
            rain = w.loc[w["niederschlag_mm"] > 0, "delay_arr_sec"].mean()
            dry = w.loc[w["niederschlag_mm"] == 0, "delay_arr_sec"].mean()
            weather_str = (
                f"\n\nWetter (n={len(w):,} Halte mit MeteoSchweiz-Daten):\n"
                f"  Regenstunden: {rain:.1f}s vs. trockene Stunden: {dry:.1f}s "
                f"(Effekt klein, vgl. Notebook 03: |r| < 0.06)"
            )

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
{top5_str}{weather_str}{station_block}{worst_days}"""


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

    # Button in Platzhalter -> kann waehrend Loading durch die Zug-Animation
    # ersetzt werden (Button "verschwindet" waehrend der Generierung).
    if "gen_key" not in st.session_state:
        st.session_state.gen_key = 0
    action = st.empty()
    generate = action.button("Antwort generieren", type="primary",
                             key=f"gen_btn_{st.session_state.gen_key}")
    if st.session_state.get("auto_generate"):
        generate = True
        st.session_state.auto_generate = False

    if generate and not insight_q.strip():
        st.warning("Bitte gib zuerst eine Frage ein oder klick eine Beispiel-Frage an.")
    elif generate:
        from anthropic import Anthropic
        client = Anthropic()

        context = build_llm_context(df, insight_q)

        # Button durch SBB-Zug-Animation ersetzen (Button weg waehrend Loading)
        action.markdown(train_loader_html(), unsafe_allow_html=True)
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
            action.empty()  # Animation entfernen sobald Antwort da ist

        # Button wieder einblenden (neuer key, da alter in diesem Run verbraucht)
        st.session_state.gen_key += 1
        action.button("Antwort generieren", type="primary",
                      key=f"gen_btn_{st.session_state.gen_key}")

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
