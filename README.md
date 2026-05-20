# SBB Tracker — Verspätungsanalyse Schweizer Bahnverbindungen

ZHAW Scientific Programming Projekt (FS2026), Gruppenarbeit.

## Forschungsfrage

Wie hängen Verspätungen auf den Hauptlinien der SBB von Faktoren wie **Wetter, Wochentag, Tageszeit und Zugtyp** ab — und hat sich die Pünktlichkeit über die Jahre (inkl. Covid-Bruch) signifikant verändert?

## Datenquellen

- **opentransportdata.swiss** — historische Ist-Daten (SBB) als CSV-Downloads
- **transport.opendata.ch** — Live-Verbindungs- und Verspätungs-API
- **MeteoSchweiz / Open-Meteo** — historische Wetterdaten

## Projektstruktur

```
project/
├── notebooks/        Jupyter Notebooks (numeriert: 01_…, 02_…, …)
├── scripts/          Python-Skripte (z.B. Daten-Download)
├── data/
│   ├── raw/          (gitignored — große Roh-CSVs)
│   └── processed/    (committed — schlanke aufbereitete Daten)
├── app/              Streamlit Web App
└── presentation/     Folien + Video
```

## Tech-Stack

Python 3.12 · pandas · scipy · statsmodels · sqlite3 · matplotlib · plotly · folium · Streamlit · Anthropic Claude API

## Setup

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Dann .env öffnen und ANTHROPIC_API_KEY eintragen
```

## Gruppe

- Joël Hasler
- _(Partner-Name folgt)_
