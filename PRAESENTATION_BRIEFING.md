# Präsentations-Briefing — alles, was ihr wissen müsst

Lest das einmal vor der Video-Aufnahme durch. Die PowerPoint hat zusätzlich
pro Slide Sprechernotizen; dieses Dokument ist der grosse Überblick.

---

## 1. Das Projekt in 30 Sekunden (Elevator Pitch)

Wir analysieren die Pünktlichkeit der SBB nicht über die offizielle
Sammelzahl (92.5 %), sondern hochaufgelöst: **2.74 Millionen einzelne Zug-Halte**
über **48 Betriebstage** (31.03.–19.05.2026), aus drei offenen Datenquellen.
Wir beantworten vier Fragen mit Statistik, machen die Daten in einer Webapp
interaktiv zugänglich und lassen ein Sprachmodell die schlimmsten Tage einordnen.

**Die wichtigste Erkenntnis:** Bei so vielen Daten ist statistisch fast alles
„signifikant" — aber die **Effektstärken sind klein**. Verspätung ist
grösstenteils Zufall im Einzelfall. Und die unpünktlichsten Bahnhöfe liegen an
der Grenze (importierte Verspätung internationaler Züge).

---

## 2. Die Daten

- **Was ist ein „Halt"?** Ein einzelner Stopp eines Zuges an einem Bahnhof. Ein
  Zug erzeugt auf seiner Fahrt viele Halte. Wir haben 2.74 Mio davon.
- **Quellen (alle offen, CC-BY):**
  - opentransportdata.swiss → Ist-Daten (Soll- vs. tatsächliche Zeiten)
  - data.sbb.ch → Bahnhof-Stammdaten (Koordinaten, Kanton)
  - MeteoSchweiz → stündliches Wetter (15 Stationen)
- **Verspätung** = tatsächliche Ankunft − Fahrplan-Ankunft, in Sekunden. Wir
  nutzen nur **gemessene** Ankünfte (Status REAL), keine Prognosen.
- **„Verspätet"** = mehr als **3 Minuten** zu spät (offizielle SBB-Definition).
- **Design-Entscheidung:** lieber 48 Tage in voller Auflösung als Jahre an groben
  Summen. Nur so kann man nach Stunde, Bahnhof und Wetter auswerten. (Die ganze
  Historie 2019–2025 wären ~1.1 Terabyte.)
- **Bereinigung:** 70 physikalisch unmögliche Werte (fehlerhafte Zeitstempel im
  Quell-Feed, z. B. „−48 h") entfernt.

**Kernzahlen:** Ø Verspätung **45.6 s**, Median **28 s**, 95 %-Perzentil **181 s**,
Anteil > 3 min verspätet **5.03 %** (also ~95 % pünktlich).

---

## 3. Die vier Analysen + Ergebnisse

| Frage | Test | Ergebnis | Effektstärke |
|---|---|---|---|
| Werktag vs. Wochenende | Welch-t-Test | 50.1 s vs. 34.6 s, t = 95, p < 10⁻³⁰⁰ | **Cohen's d = 0.12 → klein** |
| Linientyp | ANOVA + Tukey | F = 8'450, p < 10⁻³⁰⁰ | **η² = 0.039 → klein** |
| Wetter ↔ Verspätung | Pearson/Spearman | alle signifikant | **\|r\| < 0.04 → trivial** |
| Alle Faktoren zusammen | OLS-Regression | R² = 0.043 | erklärt nur **~4 %** |

**Was man dazu sagt:**
- Werktage sind ~15 s unpünktlicher — real, aber im Alltag kaum spürbar.
- Internationale Züge (TGV, EC, RailJet, Nightjet) sind am unpünktlichsten — sie
  bringen Verspätung aus dem Ausland mit. Inländische IC/IR sind sehr pünktlich (~30 s).
- Wetter wirkt in die erwartete Richtung (mehr Regen → minim mehr Verspätung),
  aber praktisch vernachlässigbar.
- Das Gesamtmodell erklärt nur ~4 % → der Rest ist idiosynkratisch (Einzelfälle:
  Defekte, Störungen).
- **Hotspots = Grenzbahnhöfe:** Buchs SG (196 s), St. Margrethen (169 s),
  Basel St. Johann (127 s).

---

## 4. Die Kernbotschaft (euer roter Faden)

> „Statistisch signifikant ist nicht dasselbe wie praktisch relevant. Bei 2.7
> Millionen Beobachtungen wird jeder winzige Unterschied signifikant — deshalb
> berichten wir konsequent **Effektstärken**. Und die sind klein. Die SBB ist
> sehr pünktlich; Verspätung entsteht überwiegend zufällig im Einzelfall."

Genau dieser **ehrliche Umgang mit kleinen Effekten** ist die methodische Stärke
der Arbeit. Das nicht verstecken, sondern selbstbewusst betonen.

---

## 5. Die Webapp (Tab für Tab)

App starten: `streamlit run app/streamlit_app.py` → http://localhost:8501

- **Karte:** Schweizer Karte, jeder Punkt ein Bahnhof, Farbe = Ø-Verspätung.
  Zwei Regler: links blendet Bahnhöfe mit zu wenig Daten aus (Verlässlichkeit),
  rechts „Nur Hotspots" zeigt nur die rotesten Bahnhöfe.
- **Tageszeit:** Heatmap Stunde × Wochentag (dunkler = verspäteter). Darunter
  Drilldown: Tag/Stunde wählen, Kennzahlen passen sich an. Default zeigt
  Rush-Hour vs. Off-Peak.
- **Pendler-Insight:** Frage stellen (oder Beispiel-Bubble klicken). Ein
  Sprachmodell (Claude) antwortet **nur** auf Basis unserer Statistik-Daten
  (erfindet nichts). Aufklapper zeigt transparent, welche Daten es gesehen hat.
- **Über:** Datenquellen + Lizenzen.

**Demo-Tipps fürs Video (der visuelle Höhepunkt):**
1. Karte zeigen, dann den **Hotspot-Regler hochziehen** → es bleiben die
   Grenzbahnhöfe übrig. Das ist euer „Aha"-Moment.
2. Im Pendler-Tab eine Frage stellen, z. B. „Wann erwische ich am ehesten einen
   pünktlichen Zug?" → live die Antwort generieren lassen.
3. Kurz den Transparenz-Aufklapper zeigen („nur diese Daten hat das Modell gesehen").

---

## 6. Begriffe einfach erklärt (falls gefragt)

- **p-Wert:** Wahrscheinlichkeit, dieses Ergebnis zu sehen, wenn es in Wirklichkeit
  KEINEN Unterschied gäbe. Klein (< 0.05) = „wahrscheinlich kein Zufall" =
  signifikant. **Aber:** bei riesigem n wird fast alles signifikant.
- **Effektstärke:** misst, wie GROSS ein Unterschied praktisch ist (unabhängig von n).
- **Cohen's d:** Effektstärke für Mittelwert-Vergleiche. 0.2 klein, 0.5 mittel,
  0.8 gross. Unser 0.12 = sehr klein.
- **η² (eta-Quadrat):** Effektstärke der ANOVA = Anteil der Schwankung, den der
  Linientyp erklärt. 0.039 = ~4 %.
- **Korrelation r:** Zusammenhang zweier Grössen, −1…+1. Unsere ~0.02–0.04 ≈ null.
- **Pearson** = linearer Zusammenhang, **Spearman** = monoton (über Ränge).
- **Welch-t-Test:** vergleicht zwei Mittelwerte, verträgt ungleiche Streuung.
- **ANOVA:** vergleicht Mittelwerte von > 2 Gruppen. **Tukey-HSD:** sagt, welche
  Paare sich konkret unterscheiden.
- **OLS-Regression:** Modell, das Verspätung gleichzeitig durch mehrere Faktoren
  erklärt. **R²** = wie viel % der Schwankung erklärt werden.
- **Heteroskedastizität (Breusch-Pagan):** die Streuung der Fehler ist nicht
  konstant. Haben wir, benennen wir offen.
- **Pseudoreplikation:** unsere Halte sind nicht unabhängig (gleicher Zug/Bahnhof/
  Tag). Deshalb der **Tagesmittel-Gegencheck** (Test auf 48 Tagesmitteln — Effekt
  überlebt).
- **idiosynkratisch:** durch viele unvorhersehbare Einzelereignisse bestimmt.
- **LLM-„Temperatur":** Kreativitäts-Regler 0–1. Wir nutzen 0.2 = faktentreu.

---

## 7. Mögliche Fragen + kurze Antworten

- **„Warum nur 48 Tage?"** → Auflösung vor Zeitspanne; ganze Historie wären 1.1 TB.
  48 Tage hochaufgelöst sind für unsere Fragen aussagekräftiger.
- **„R² ist doch sehr tief?"** → Genau, und das ist eine ehrliche Erkenntnis:
  Verspätung ist überwiegend zufällig. Wir verschönern nichts.
- **„Ist der LLM-Teil wissenschaftlich?"** → Als qualitative Ergänzung, klar als
  Hypothese gekennzeichnet, mit niedriger Temperatur und fester Kategorienliste.
- **„Halluziniert das Modell in der App?"** → Wir geben ihm nur unsere Zahlen mit
  und weisen es an, nichts zu erfinden; die Datenbasis ist transparent einsehbar.
- **„Wetter sollte doch wichtig sein?"** → Es wirkt richtungstechnisch wie erwartet,
  aber der Effekt ist winzig — Signifikanz wegen n, nicht wegen Relevanz.

---

## 8. Was Punkte bringt (Rubrik-Abdeckung)

**Minimum (8/8):** reale Daten · Regex + Typkonvertierung · Built-ins
(dict/list/set/tuple) + DataFrames · Loops/Conditionals/Control · prozedural (+OOP) ·
Tabellen + 7 Plots · 4 Statistik-Tests mit p-Wert · Abgabe auf Moodle.

**Bonus (6/6):** Kreativität (OLS+Diagnostik, Tukey, Effektstärken, KDTree,
Performance-Fragmente, Docker, 27 Tests) · Web-API/Scraper · SQLite + 5 SQL-Queries ·
LLM · Streamlit-Webapp · öffentliches GitHub-Repo.

Konkrete Code-Beweise stehen im PDF-Anhang (Sektion 6.5) — genau das, was der
Dozent verlangt.

---

## 9. Praktisch

- **App starten:** `& venv\Scripts\streamlit.exe run app\streamlit_app.py`
- **Wichtige Dateien:** `notebooks/01–04`, `app/streamlit_app.py`, `app/utils.py`,
  `presentation/SBB_Tracker_Praesentation.pdf` (Abgabe-Dokument),
  `..._solo.pptx` / `....pptx` (Foliendecks fürs Video).
- **Abgabe (Moodle, Frist 27.05.2026 23:59):** ZIP
  `projectwork_SP_FS2026_group_11.zip` mit dem PDF + `videopresentation_group_11.mp4`.
- **Video-Länge:** Anzahl Studierende × 5 Min (2er-Gruppe → ~10 Min).

---

## 10. Noch offen (eure Handlungen)

- [ ] Video aufnehmen (Foliendeck + Sprechernotizen bereit; Solo-Variant vorhanden).
- [x] Gruppennummer = 11 → ZIP-Name `projectwork_SP_FS2026_group_11.zip`.
- [ ] KI-Deklaration im README ausfüllen (Eigenleistung + Aufteilung) — Pflicht!
- [ ] Optional: ZHAW-Recherche (Statista/Factiva/Scopus).
- [ ] ZIP packen + auf Moodle hochladen.
