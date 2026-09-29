# Methodology

This document describes every calculation in HEATSHIELD. All thermal values derived from routine
weather data are **estimates** and are labelled as such in the UI.

## 1. Inputs

Per hour, per city (from the demo generator or Open-Meteo):

- `temperature_2m` (°C), `relative_humidity_2m` (%), `wind_speed_10m` (m/s),
  `wind_direction_10m` (°), `cloud_cover` (%), `shortwave_radiation` (W/m²),
  `precipitation_probability` (%).
- Daily: `temperature_2m_max`, `temperature_2m_min`.

Per ward (seeded demographics, replaceable via Admin uploads):

- population, area (km²), population density, elderly %, outdoor-worker density,
  informal-housing %, hospital-access score, green-cover %, chronic-disease proxy, elevation.

## 2. Heat Index (NOAA/NWS Rothfusz)

Valid range: T ≥ 26.7 °C (80 °F), RH ≥ 40 %.

```
HI°F = -42.379 + 2.04901523·T + 10.14333127·RH - 0.22475541·T·RH
       - 0.00683783·T² - 0.05481717·RH² + 0.00122874·T²·RH
       + 0.00085282·T·RH² - 0.00000199·T²·RH²
```

Adjustments (per NWS):
- RH < 13 % and 80 ≤ T ≤ 112 °F: `HI -= ((13-RH)/4)·sqrt((17-|T-95|)/17)`
- RH > 85 % and 80 ≤ T ≤ 87 °F: `HI += ((RH-85)/10)·((87-T)/5)`
- The regression is averaged with the air temperature (Rothfusz, NWS SR 90-23) to match the
  published NWS chart.

**Fallbacks** (safe, documented): outside the valid range, the NWS simple approximation is used:
`HI = 0.5·(T + 61 + (T-68)·1.2 + RH·0.094)` (°F). The result is never below the air temperature.

## 3. Wet-bulb temperature (Stull, 2011)

Psychrometric wet-bulb from T (°C) and RH (%):

```
Tw = T·atan(0.151977·sqrt(RH+8.313659)) + atan(T+RH) - atan(RH-1.676331)
     + 0.00391838·RH^1.5·atan(0.023101·RH) - 4.686035
```

## 4. Estimated natural wet-bulb (Tnwb)

A natural (unaspirated) wet bulb absorbs solar radiation and reads warmer than the psychrometric
Tw (physical basis: Liljegren et al. 2008). HEATSHIELD applies a documented boost:

```
Tnwb ≈ Tw + 1.8 · min(SR/800, 1) · (1 - cloud/100) · (1 - 0.4·min(v/6, 1))   [cap +3 °C]
```

This is an **estimate**, not a measured Tnwb.

## 5. Estimated globe temperature (Tg)

Black-globe temperature from routine weather (documented solar/wind model):

```
SR_eff = SR · (1 - 0.75·cloud/100)
Tg = T + 0.010 · SR_eff / sqrt(max(v, 0.5))     [cap T + 15 °C]
```

Units: SR in W/m², v in m/s. This is an **estimate**; a physical globe thermometer is the reference.

## 6. Estimated outdoor WBGT

```
WBGT = 0.7·Tnwb + 0.2·Tg + 0.1·Tdb
```

Displayed as **“Estimated Outdoor WBGT”**. Not a replacement for a calibrated onsite WBGT instrument.

## 7. UTCI Proxy

Official UTCI requires a validated implementation of the Fiala thermophysiological model, which is
not bundled. HEATSHIELD therefore exposes a clearly-labelled **UTCI Proxy**:

```
Tg        = estimated globe temperature
rad_effect = 0.6·(Tg - T)
hum_effect = 0.02·max(RH-40, 0) if T ≥ 30 °C else 0
wind_effect = 0.2·v
UTCI_proxy = T + rad_effect + hum_effect - wind_effect
clamped to [T-5, T+15] °C
```

The proxy is never presented as official UTCI.

## 8. Night-time recovery score (0–100, higher = worse)

| Component | 0 → 100 mapping | Weight |
|---|---|---|
| Minimum temperature | 22 °C → 29 °C | 0.40 |
| Night-time Heat Index | 26 °C → 36 °C | 0.30 |
| Hot nights (Tmin ≥ 26 °C) in the run | 0 → 4 nights | 0.20 |
| Consecutive warm nights | 0 → 4 nights | 0.10 |

## 9. Consecutive exposure score (0–100, higher = worse)

| Component | 0 → 100 mapping | Weight |
|---|---|---|
| Consecutive high-WBGT hours (≥ 26 °C) | 2 h → 14 h | 0.50 |
| Consecutive high-risk days (max WBGT ≥ 30 °C) | 0 → 4 days | 0.30 |
| Daily exposure hours (≥ WBGT 26 °C) | 2 h → 10 h | 0.20 |

## 10. Human Thermal Stress Index (HTSI, 0–100)

```
HTSI = 0.35·WBGT_score + 0.20·HI_score + 0.15·UTCI_score + 0.15·Night + 0.15·Consecutive
```

Normalisation: WBGT 18–34 °C → 0–100; Heat Index 27–55 °C → 0–100; UTCI Proxy 22–50 °C → 0–100.
Every component score is stored and shown for explainability. **Weights are configurable** in
Admin Settings.

## 11. Vulnerability score (0–100)

| Factor | Normalisation | Weight |
|---|---|---|
| Elderly population % | 5 % → 20 % | 25 % |
| Outdoor-worker density (/km²) | 300 → 4500 | 20 % |
| Poor housing / informal-settlement % | 0 % → 35 % | 15 % |
| Poor hospital access (100 − access score) | 0 → 75 | 15 % |
| Population density (/km²) | 2000 → 40000 | 10 % |
| Low green cover (100 − green %) | 30 → 100 | 10 % |
| Chronic-disease proxy % | 2 % → 15 % | 5 % |

Each factor normalises to 0–100, is multiplied by its weight, and all contributions are shown
(e.g. *Elderly population contribution: +19*). **Weights are editable in Admin Settings.**

## 12. Health-risk engine (decision support)

```
score = 0.40·HTSI + 0.20·Vulnerability + 0.15·Night + 0.15·Consecutive + 0.10·(100 − hospital access)
```

- **Hospitalization risk:** <25 Low · <45 Moderate · <65 High · <80 Very High · ≥80 Extreme
- **Excess mortality-risk band:** <30 Low · <50 Moderate · <70 High · <85 Very High · ≥85 Extreme
- **Health-demand increase above baseline:** rule-based `4 + 0.55·score` (%); when the ML model is
  available, blended 50/50 with the RandomForest prediction. Shown as a range
  (e.g. *25–40 %*).
- **Confidence:** High (ML available) / Medium (rule-based fallback) / Low (missing inputs).
- **Drivers:** normalised contribution percentages of HTSI, vulnerability, night recovery,
  cumulative exposure and poor hospital access.

**Safety rules (hard-coded):**
- Never claim an exact number of deaths — only an *excess mortality-risk band*.
- Outputs labelled *decision-support estimate* and *requires calibration using local
  public-health data*.

## 13. Final ward risk

```
Final Risk = 0.55·HTSI + 0.30·Vulnerability + 0.15·Health-System Load
```

| Score | Level | Key |
|---|---|---|
| 0–20 | Low | green |
| 21–40 | Moderate | yellow |
| 41–60 | High | orange |
| 61–80 | Very High | red |
| 81–100 | Extreme | maroon |

**Escalation rules** (each +1 category, only when heat is dangerous, i.e. ward max WBGT ≥ 28 °C;
never above Extreme):
- vulnerability ≥ 80 → +1
- dangerous heat for ≥ 3 consecutive days → +1
- predicted hospital load Very High/Extreme → +1

Every result includes `explanation` — a generated sentence like:
> *“Ward W-09 is classified as Extreme because estimated WBGT is 31.9 °C, Heat Index reaches
> 46.6 °C, nights give little relief, outdoor-worker density is high, and green cover is low.”*

## 14. Demo weather scenarios

Hourly diurnal cycle `f(h) = max(0, cos(π·(h−14.5)/12.5))`, deterministic noise seeded by
scenario+date+hour. Heatwave scenarios build up day over day (capped) and their humidity eases as
temperature rises, mirroring real Indian heatwaves.

| Scenario | Tmax day 0 | RH | Wind | Solar | Effect |
|---|---|---|---|---|---|
| Normal Summer Day | 35.2 °C | 40–64 % | 5 m/s | 820 W/m² | yellow/orange wards |
| Moderate Heatwave | 39.6 °C | 24–52 % | 3 m/s | 930 W/m² | orange, a few red |
| Severe Humid Heatwave (default) | 38.6 °C | 48–76 % | 2.4 m/s | 730 W/m² | HI ~50 °C, WBGT 32–35 °C, multiple red + extreme wards |
| Extreme Dry Heatwave | 45.3 °C | 7–29 % | 4.2 m/s | 1020 W/m² | Tmax to ~48 °C, very high UTCI Proxy |

## 15. Synthetic history & ML model

- 730 days generated with a seasonal temperature cycle (peak mid-April), random heatwave events,
  and a physically-consistent hospital-load response (quadratic in WBGT + night recovery +
  consecutive days + mild winter flu bump + noise). The final 5 days are hot to connect to the
  active scenario.
- A `RandomForestRegressor` (150 trees, max depth 9) predicts daily hospital-load increase from
  [tmax, tmin, rh, wind, radiation, wbgt_max, hi_max, utci_max, night_recovery,
  consecutive_days, month_sin, month_cos, weekday].
- If scikit-learn is unavailable or training fails, the **rule-based fallback** (`4 + 0.55·score`)
  is used and the model metadata records `fallback_used: true`.
- Model metadata (R², MAE, RMSE, feature importance, sample count, timestamp) is stored in the DB
  and shown in Admin → ML model. `POST /api/v1/admin/retrain-model` retrains.

## 16. Action engine

Actions are assigned by risk level per the specification (yellow → hydration awareness; orange →
PHC hours, ORS/IV, outdoor-worker checks, precautionary SMS; red → cooling centres, shifted work
hours, surge planning, mobile water/ORS units, elderly-care volunteers, ambulance staffing,
multilingual alerts; extreme → city heat-emergency protocol, extended cooling-centre hours,
suspended outdoor work, informal-settlement outreach, electricity/water to cooling centres,
repeated multilingual alerts, bed/ambulance/supply coordination). Each action carries a
department, priority (Immediate/Today/Monitor), reason and status (Pending/In Progress/Completed).

## 17. Bilingual alerts

Alerts are generated in English and Kannada using ward-specific windows (derived from forecast
hours with WBGT ≥ 30 °C) and the nearest cooling centre with its distance. Delivery is always
simulated unless a real gateway is integrated.