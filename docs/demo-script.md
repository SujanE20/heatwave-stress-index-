# Demo Script — HEATSHIELD INDIA (4–5 minutes for the SIH jury)

**Setup before the demo** (do this before the jury arrives):
```bash
docker compose up --build          # or: backend via uvicorn + frontend via npm run dev
# Open http://localhost:3000 and http://localhost:8000/docs in two tabs
```
No internet is required — Demo Mode is the default (a **"Demo Data"** badge appears in the navbar).

---

## 0:00–0:20 — Landing & problem framing

**Click:** landing page → choose **Municipal Command Centre Officer**.

**Say:** *"Every summer, Indian cities issue temperature warnings. But a 38 °C day at 20%
humidity and a 38 °C day at 70% humidity feel completely different — and both are far more
dangerous for an elderly outdoor worker in a dense ward with no hospital nearby. HEATSHIELD
predicts what heat will do to people, not just what the weather will be. Our demo city is
Mysore."*

---

## 0:20–1:20 — Command Centre dashboard

**Click:** **Command Centre** in the top nav.

**Say (pointing as you go):**
- *"The city is at **Extreme** risk — 2 wards High, 4 Very High, 9 Extreme."*
- *"This is why: 33 °C, 66% humidity → Heat Index 38 °C, **estimated WBGT 30.4 °C**, UTCI
  Proxy 34.4, and the **Human Thermal Stress Index is 62/100**."*
- *"The system shows what weather alone can't: **5,45,000 people exposed**, of whom ~1,07,000 are
  elderly or outdoor workers; **hospital demand is expected to rise 31–55%** above baseline."*
- *"Tomorrow's severe-risk window is **10:00–19:00** with peak WBGT 35 °C — the dashboard turns
  that straight into recommended city actions with departments and priorities."*

**Click:** **Trigger Heat Action Plan** → shows the Active plan banner with a summary.
**Say:** *"One click activates the municipal Heat Action Plan and marks the coordinating actions
in progress."*

---

## 1:20–2:10 — GIS risk map (the wow moment)

**Click:** **GIS Risk Map**.

**Say:** *"15 wards, each coloured by risk — but never colour alone: every polygon is labelled."*

**Click:** a Red/Extreme ward polygon → side panel opens.

**Say:** *"Ward W-09, Railway Colony, is classified **Extreme** — the explanation is generated,
not hardcoded: estimated WBGT 31.9 °C, Heat Index 46.6 °C, nights give little relief,
outdoor-worker density is high, green cover is low."*

**Scroll the panel** — HTSI components, vulnerability contributions with point values
(e.g. *"elderly contribution +19"*), hospitalization risk, mortality band, confidence,
nearest hospital/cooling centre/water point with distances, and role-specific actions with
departments and priorities.

**Click layer toggles:** Hospitals → cooling-centre markers; Thermal Stress → recolours wards by
thermal stress only; Vulnerability → recolours by vulnerability.
**Say:** *"Layer toggles separate thermal stress from vulnerability — so you can see that the
hottest ward is not always the most dangerous one."*

---

## 2:10–3:00 — Forecast, analytics & the ML model

**Click:** **Forecast & Analytics**.

**Say:** *"The 5-day forecast compares dry-bulb temperature, Heat Index, estimated WBGT and the
UTCI Proxy — this gap is the entire point of the product."*

**Point to:** the risk-bars chart (HTSI mapped to Green→Maroon bands), the ward comparison table
sorted by risk, and the vulnerability-vs-thermal scatter.

**Click:** **Admin Settings → ML model** → **Retrain Demo Model**.
**Say:** *"The hospital-load model is a RandomForest trained on 730 days of synthetic history —
R² 0.97, and the top feature is WBGT, which is exactly what we'd expect. If ML is unavailable it
falls back to a documented rule-based estimate, and the metadata says so."*

---

## 3:00–3:40 — Bilingual alerts

**Click:** **Alerts Centre** → **Generate draft alerts**.

**Say:** *"Alerts are generated per ward in English and Kannada, with the severe window and the
nearest cooling centre baked in."* (Read the Kannada line aloud — the jury loves this.)

**Click:** **Simulate send**.
**Say:** *"Delivery is simulated — no real messages are sent. The gateway integration point is
documented for production."*

---

## 3:40–4:10 — Citizen view & role switch

**Click the role selector → Citizen**, or open **Citizen View**.

**Say:** *"The same engine, reframed for a citizen on a phone — current conditions, plain-language
guidance, their ward's alert in English or Kannada, and the nearest cooling centre."*

**Switch back** to Municipal Command Centre Officer via the role selector.

---

## 4:10–4:45 — Scenario switching (flexibility) & close

**Click:** **Admin Settings → Weather provider** → change scenario to **Normal Summer Day** →
open the dashboard.
**Say:** *"The entire platform recomputes instantly — on a normal day the same wards drop to
yellow and orange, and escalations switch off. The severe humid heatwave is our demo default
because it shows exactly the Red/Extreme cascade Indian cities need to prepare for."*

**Switch back** to **Severe Humid Heatwave**.

**Close with:**
*"Weather forecast → human thermal stress → ward vulnerability → health-risk estimate →
recommended action → citizen alert. Every number is explainable, every estimate is labelled as
an estimate, and the disclaimer on every page says it must be calibrated with local data before
operational use. HEATSHIELD turns a weather forecast into a people plan."*

---

## Failure fallbacks (be prepared)

| If… | Then… |
|---|---|
| Backend not running | Check `docker compose ps`; backend logs in `docker compose logs backend` |
| Map tiles don't load (offline) | Polygons still render on the grid background; a badge says tiles are unavailable |
| Demo scenario feels too extreme | Switch to `moderate_heatwave` in Admin → Weather provider |
| Ports busy | Change `BACKEND_PORT` / `FRONTEND_PORT` in `.env` |

## Judge Q&A cheat sheet

- **Why WBGT and not temperature?** Dry-bulb ignores humidity, wind and radiation — WBGT folds
  in all three and is the international standard for occupational heat stress (ISO 7243).
- **Is this real data?** Wards, resources and the 730-day history are realistic synthetic demo
  data. Live mode uses Open-Meteo forecasts; official municipal GIS and IMD data plug in via the
  admin uploads.
- **Is UTCI official?** We clearly label it *UTCI Proxy*; swapping in a validated UTCI
  implementation is a documented integration point.
- **How do you handle health data privacy?** No individual health data exists or is displayed —
  only ward-level aggregated estimates.
- **How is it scalable?** Add a city row + ward GeoJSON; the whole pipeline follows. PostGIS is
  provisioned for spatial queries at scale.