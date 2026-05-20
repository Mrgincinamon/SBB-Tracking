"""Build notebook 04: LLM-basierte Verspätungsgrund-Hypothesen (Bonus #4).

Identifies the worst delay days, gathers contextual signals (top stations,
weather, time-of-day), then asks Claude Sonnet 4.6 to hypothesize the cause
from a fixed taxonomy.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _nb_builder import md, code, header_cell, footer_cell, build_notebook, save_and_run


NB_PATH = Path(__file__).parent.parent / "notebooks" / "04_llm_verspaetungsgruende.ipynb"


def build_cells() -> list:
    cells = []

    cells.append(md("""
        # Notebook 04 — LLM-basierte Verspätungsgrund-Hypothesen

        **SBB Tracker · ZHAW Scientific Programming FS2026**
        Joël Hasler & Patrick Ferreira

        Die offiziellen SBB-Daten enthalten **keine** Verspätungs-Gründe — nur
        Soll- und Ist-Zeiten. Trotzdem wäre es wertvoll, die "schlimmsten Tage"
        qualitativ erklären zu können ("War das Wetter? Streckenarbeiten? Ein
        Unfall?").

        Hier nutzen wir ein **Large Language Model (Anthropic Claude Sonnet 4.6)**
        als qualitativen Klassifikator: Wir geben ihm pro Tag den verfügbaren
        Kontext (top betroffene Bahnhöfe, Wetter, Wochentag, Uhrzeit-Pattern)
        und lassen es aus einer fixen Taxonomie eine Hypothese ableiten.

        **Wichtig**: Das Modell kennt die Realität nicht — es **hypothetisiert**
        plausible Ursachen aus dem Kontext. Limitations am Ende ausführlich
        diskutiert.

        Dieses Notebook deckt Bonus #4 (LLM-Nutzung) der Bewertungsrubrik ab.
    """))

    cells.append(md("## Bibliotheken und Einstellungen"))
    cells.append(header_cell())
    cells.append(code("""
        import json
        from dotenv import load_dotenv
        from anthropic import Anthropic

        load_dotenv(PROJECT_ROOT / ".env")
        api_key = os.getenv("ANTHROPIC_API_KEY")
        model_name = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        if not api_key:
            raise ValueError("Missing ANTHROPIC_API_KEY in .env")
        print(f"LLM-Modell: {model_name}")
        print(f"API-Key sichtbar: True (endet auf ...{api_key[-4:]})")

        client = Anthropic()  # liest ANTHROPIC_API_KEY automatisch
    """))

    cells.append(md("""
        ## Datensatz laden
    """))
    cells.append(code("""
        df = pd.read_parquet(DATA_PROCESSED / "delays_prepared.parquet")
        print(f"Geladen: {len(df):,} Verspaetungs-Events")
        print(f"Zeitraum: {df['betriebstag'].min()}  bis  {df['betriebstag'].max()}")
    """))

    cells.append(md("""
        ## Schritt 1 — Top-10 Verspätungs-Tage identifizieren

        Pro Tag berechnen wir die mittlere Ankunftsverspätung und den
        Anteil klassisch verspäteter Halte (>3 Min). Die Tage mit dem
        höchsten %-Wert sind die "Krisen-Tage" — vermutlich mit Wetter
        oder Störungen verbunden.
    """))
    cells.append(code("""
        daily = (df.groupby("betriebstag")
                 .agg(n_halte=("delay_arr_sec", "size"),
                      mean_delay=("delay_arr_sec", "mean"),
                      pct_late_3min=("is_late_3min", "mean"))
                 .assign(pct_late_3min=lambda d: 100 * d["pct_late_3min"])
                 .sort_values("pct_late_3min", ascending=False))
        top10 = daily.head(10).reset_index()
        print(f"Top-10 Tage nach %-verspaetet:")
        print(top10.to_string(index=False))
    """))

    cells.append(md("""
        ## Schritt 2 — Kontext pro Tag sammeln

        Für jeden Top-10-Tag holen wir vier Kontext-Signale:
        - Top-5 am stärksten betroffene Bahnhöfe (mit deren mittlerer Verspätung)
        - Wetter-Mittelwert über alle Wetterstationen
        - Wochentag
        - Tageszeit-Pattern (Vormittag/Nachmittag/Abend-Vergleich)
    """))
    cells.append(code("""
        def gather_context(date_str: str) -> dict:
            day = df.loc[df["betriebstag"] == date_str]
            top_stations = (day.groupby("haltestellen_name")["delay_arr_sec"]
                            .agg(["mean", "count"])
                            .query("count >= 50")
                            .sort_values("mean", ascending=False)
                            .head(5))
            weather_mean = {
                "temperatur_c": day["temperatur_c"].mean(),
                "niederschlag_mm": day["niederschlag_mm"].mean(),
                "wind_ms": day["wind_ms"].mean(),
                "niederschlag_max": day["niederschlag_mm"].max(),
            }
            by_hour = day.groupby(pd.cut(day["hour"], [0, 6, 12, 18, 24],
                                          labels=["Nacht", "Vormittag", "Nachmittag", "Abend"]),
                                   observed=True)["delay_arr_sec"].mean()
            weekday = day["weekday"].iloc[0] if len(day) > 0 else "?"
            return {
                "date": date_str,
                "weekday": weekday,
                "n_halte": len(day),
                "mean_delay": float(day["delay_arr_sec"].mean()),
                "pct_late_3min": float(100 * day["is_late_3min"].mean()),
                "top_stations": [
                    {"name": n, "mean_delay_sec": round(r["mean"], 0), "n_halte": int(r["count"])}
                    for n, r in top_stations.iterrows()
                ],
                "weather": {k: round(v, 1) if pd.notna(v) else None for k, v in weather_mean.items()},
                "by_daytime": {str(k): round(v, 0) if pd.notna(v) else None for k, v in by_hour.items()},
            }

        # Test: Kontext fuer den schlimmsten Tag
        worst_day = top10.iloc[0]["betriebstag"]
        ctx = gather_context(worst_day)
        print(json.dumps(ctx, indent=2, ensure_ascii=False)[:1200])
    """))

    cells.append(md("""
        ## Schritt 3 — LLM-Prompt-Template

        Wir bauen einen strukturierten Prompt mit:
        - System-Message: Rolle (Daten-Analyst, Schweizer ÖV-Experte)
        - Fixe Taxonomie der möglichen Ursachen
        - JSON-Output-Format
        - Kontext als JSON

        Niedrige Temperatur (0.2) für reproduzierbare Ergebnisse.
    """))
    cells.append(code("""
        TAXONOMY = [
            "wetter_regen", "wetter_schnee_kalt", "wetter_sturm",
            "rush_hour_ueberlastung", "wochenende_baustelle",
            "stoerung_einzelner_bahnhof", "stoerung_netzweit",
            "saisonaler_betrieb", "unbestimmbar",
        ]

        SYSTEM_PROMPT = '''Du bist ein erfahrener Daten-Analyst des oeffentlichen Verkehrs in der Schweiz. Deine Aufgabe: aus statistischen Kontext-Signalen eine plausible Hypothese ableiten, warum an einem bestimmten Tag die SBB-Zuege ueberdurchschnittlich verspaetet waren. Du erfindest NICHTS, was nicht im Kontext steht. Wenn der Kontext keine klare Ursache zulaesst, antwortest du "unbestimmbar".

Antworte AUSSCHLIESSLICH in folgendem JSON-Format:
{
  "primaere_ursache": "<eine Kategorie aus der Taxonomie>",
  "begruendung": "<2-3 Saetze, deutsch, ausschliesslich basierend auf den Kontext-Signalen>",
  "konfidenz": "hoch|mittel|niedrig"
}'''

        USER_TEMPLATE = '''Taxonomie der moeglichen Ursachen:
{taxonomy}

Kontext-Daten fuer den Tag {date} ({weekday}):
{context_json}

Welche Hypothese ist am plausibelsten?'''

        def build_user_prompt(ctx: dict) -> str:
            return USER_TEMPLATE.format(
                taxonomy="\\n".join(f"- {t}" for t in TAXONOMY),
                date=ctx["date"],
                weekday=ctx["weekday"],
                context_json=json.dumps(ctx, indent=2, ensure_ascii=False),
            )

        # Beispiel-Prompt fuer den schlimmsten Tag
        example_prompt = build_user_prompt(ctx)
        print(example_prompt[:800])
    """))

    cells.append(md("""
        ## Schritt 4 — LLM-Aufrufe für alle 10 Tage

        Pro Tag ein API-Call. Wir parsen die JSON-Antwort und sammeln die
        Ergebnisse. Kosten pro Call: ~0.001 USD (Sonnet 4.6).
    """))
    cells.append(code("""
        def classify_day(ctx: dict) -> dict:
            msg = client.messages.create(
                model=model_name,
                max_tokens=400,
                temperature=0.2,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_user_prompt(ctx)}],
            )
            response_text = msg.content[0].text.strip()
            # Robust JSON extrahieren (Modell kann text um JSON herumschreiben)
            try:
                start = response_text.index("{")
                end = response_text.rindex("}") + 1
                parsed = json.loads(response_text[start:end])
            except (ValueError, json.JSONDecodeError) as e:
                parsed = {"primaere_ursache": "parse_error",
                          "begruendung": f"JSON-Parse-Fehler: {e}",
                          "konfidenz": "niedrig",
                          "raw": response_text}
            parsed["input_tokens"] = msg.usage.input_tokens
            parsed["output_tokens"] = msg.usage.output_tokens
            return parsed

        results = []
        total_cost = 0.0
        for i, row in top10.iterrows():
            date_str = row["betriebstag"]
            ctx = gather_context(date_str)
            print(f"[{i+1}/{len(top10)}] {date_str} ({ctx['weekday']}) ...", end=" ", flush=True)
            res = classify_day(ctx)
            cost = (res.get("input_tokens", 0) / 1e6 * 3.0
                    + res.get("output_tokens", 0) / 1e6 * 15.0)
            total_cost += cost
            print(f"{res.get('primaere_ursache', '?')} ({res.get('konfidenz', '?')}) ${cost:.4f}")
            results.append({
                "datum": date_str,
                "wochentag": ctx["weekday"],
                "pct_late_3min": round(row["pct_late_3min"], 1),
                "mean_delay_s": round(row["mean_delay"], 1),
                "llm_ursache": res.get("primaere_ursache", "fehler"),
                "llm_konfidenz": res.get("konfidenz", "niedrig"),
                "llm_begruendung": res.get("begruendung", ""),
            })
        print(f"\\nTotal Kosten: ${total_cost:.4f}")
    """))

    cells.append(md("""
        ## Schritt 5 — Ergebnis-Tabelle
    """))
    cells.append(code("""
        df_results = pd.DataFrame(results)
        # Speichern fuer Webapp
        df_results.to_parquet(DATA_PROCESSED / "llm_delay_reasons.parquet", index=False)
        df_results[["datum", "wochentag", "pct_late_3min", "llm_ursache", "llm_konfidenz"]]
    """))
    cells.append(code("""
        # Volle Begruendungen einzeln durchgehen
        for _, r in df_results.iterrows():
            print(f"\\n=== {r['datum']} ({r['wochentag']}) | {r['pct_late_3min']}% verspaetet ===")
            print(f"Ursache: {r['llm_ursache']} (Konfidenz: {r['llm_konfidenz']})")
            print(f"Begruendung: {r['llm_begruendung']}")
    """))

    cells.append(md("""
        ## Visualisierung — Verteilung der LLM-Hypothesen
    """))
    cells.append(code("""
        cause_counts = df_results["llm_ursache"].value_counts()
        plt.figure(figsize=(7, 4))
        cause_counts.plot(kind="barh", color="steelblue")
        plt.title("Verteilung der LLM-Hypothesen ueber Top-10 Krisentage", fontsize=11)
        plt.xlabel("Anzahl Tage", fontsize=10)
        plt.tight_layout()
        plt.show()
    """))

    cells.append(md("""
        ## Diskussion und Limitationen

        - **Keine Ground Truth**: Wir vergleichen die LLM-Hypothesen nicht mit
          tatsächlichen Vorfällen — das wäre nur mit Aufwand (Faktiva-News,
          SBB-Pressemitteilungen) möglich. In der Webapp ergänzen wir später
          News-Headlines aus Factiva als qualitative Validierung.
        - **Halluzinations-Risiko**: LLMs können plausibel klingende, aber
          erfundene Erklärungen produzieren. Wir mindern das durch:
          - Niedrige Temperatur (0.2) für Konsistenz
          - Fixe Taxonomie (keine freien Antworten)
          - Explizite Anweisung: "Du erfindest NICHTS"
        - **Konfidenz-Skala selbst-eingeschätzt**: "hoch/mittel/niedrig" ist
          die Selbst-Einschätzung des Modells, kein kalibriertes
          Wahrscheinlichkeits-Mass.
        - **Aggregations-Verlust**: Tages-Mittel überdeckt lokale Ereignisse
          (z.B. nur Zürich war betroffen). Eine feinere Analyse (pro Stunde,
          pro Region) wäre nächster Schritt.

        Trotz dieser Einschränkungen ist die LLM-Klassifikation wertvoll als
        **erste Heuristik**: ein Pendler kann den "schlimmsten Tag" verstehen,
        ohne 50'000 Datenpunkte zu durchforsten.
    """))

    cells.append(md("""
        ## Zusammenfassung Notebook 04

        Bonus #4 (LLM-Nutzung) ist erfüllt mit einer **inhaltlich
        sinnvollen** Anwendung: qualitative Ursachen-Hypothesen für die
        Krisen-Tage. Die Ergebnisse werden in der Streamlit-Webapp im
        "Pendler-Insight"-Feature wiederverwendet.
    """))

    cells.append(footer_cell())
    return cells


def main() -> int:
    cells = build_cells()
    nb = build_notebook(cells, title="04 — LLM Verspätungsgrund-Hypothesen")
    ok = save_and_run(nb, NB_PATH, run=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
