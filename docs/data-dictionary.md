# Data Dictionary

## Cities (`cities`)

| Field | Type | Description |
|---|---|---|
| `id` | int | PK |
| `name` | str | City name, e.g. "Mysore" |
| `state` | str | State, e.g. "Karnataka" |
| `lat` / `lon` | float | City reference coordinates (weather fetch point) |
| `timezone` | str | IANA tz, "Asia/Kolkata" |

## Wards (`wards`) — 15 demo wards

| Field | Type | Description |
|---|---|---|
| `id` | int | PK |
| `city_id` | int | FK → cities |
| `code` | str | e.g. "W-01" (unique) |
| `name` | str | Representative HDMC-area name |
| `population` | int | Total ward population (9k–46k) |
| `elderly_pct` | float | % aged 60+ (7–19.5) |
| `outdoor_worker_density` | float | Outdoor workers per km² (600–4600) |
| `informal_housing_pct` | float | Informal-settlement proxy % (4–38) |
| `hospital_access_score` | float | 0–100; higher = better access (22–96) |
| `population_density` | float | People per km² (derived = population / area) |
| `green_cover_pct` | float | Tree/green cover % (7–46) |
| `chronic_disease_pct` | float | Chronic-disease prevalence proxy % (3–15) |
| `elevation_m` | float | 620–685 |
| `area_km2` | float | Hexagon area (≈0.42–2.6) |
| `centroid_lat` / `centroid_lon` | float | Ward centre |
| `geojson` | JSON | Feature with Polygon geometry (demo boundaries — replaceable) |

## Hospitals (`hospitals`) — 4

| Field | Description |
|---|---|
| `name`, `htype` | e.g. Mysore Medical College & KR Hospital · District / Primary Health Centre / Private |
| `lat`, `lon` | Location |
| `beds`, `emergency_beds` | Total / emergency beds |
| `occupancy_pct` | Simulated baseline occupancy (55–82 %) |
| `has_icu` | bool |
| `ors_units`, `iv_fluids_units` | Simulated stock |

## Cooling centres (`cooling_centres`) — 6

| Field | Description |
|---|---|
| `name`, `lat`, `lon` | e.g. "Government School - Vidyanagar" |
| `capacity`, `current_occupancy` | Seats / people |
| `water_stock_l`, `ors_units` | Simulated stock |
| `opens`, `closes` | "10:00" / "18:00" |

## Water points (`water_points`) — 10

| Field | Description |
|---|---|
| `name`, `lat`, `lon` | e.g. "Gokul Road Community Tap" |
| `wptype` | Standpost / Tanker point / Community tap |
| `status` | "Operational" |

## Weather hours (computed, cached)

Raw provider variables per hour: `t, rh, wind, wind_dir, solar, cloud, precip_prob` plus derived
`apparent, hi, tw, tnwb, tg, wbgt, utci_proxy` (see methodology.md). Hour dicts carry
`ts, date, hour`.

## Historical daily (`historical_daily`) — 730 days (synthetic)

| Field | Description |
|---|---|
| `d` | date |
| `tmax`, `tmin` | Daily extremes |
| `rh`, `wind`, `radiation` | Daily values |
| `wbgt_max`, `hi_max`, `utci_max` | Derived maxima |
| `night_recovery` | Night-recovery score 0–100 |
| `consecutive_days` | Running count of WBGT ≥ 30 days |
| `hospital_load_increase_pct` | **Target variable** for the ML model |
| `heat_admissions` | Derived daily heat-related admissions |

## Alerts (`alerts`)

| Field | Description |
|---|---|
| `ward_id` | FK → wards |
| `ts` | Created at |
| `severity` | heat alert / dangerous heat / extreme heat |
| `title`, `body_en`, `body_kn` | Bilingual content |
| `channels` | ["dashboard","sms","whatsapp","webhook"] |
| `status` | "Draft" → "Sent (simulated)" |
| `sent_via` | Per-channel simulated delivery stamps |
| `delivered_at` | UTC timestamp |

## Action items (`action_items`)

`ward_id` (null ⇒ city-level), `risk_level`, `category`, `title`, `department`,
`priority` (Immediate/Today/Monitor), `reason`, `status` (Pending/In Progress/Completed), `ts`.

## Heat action plans (`heat_action_plans`)

`city_id`, `triggered_at`, `triggered_by`, `status` (Active), `summary` (one-line recap).

## Settings (`settings`)

Key–value JSON rows: `risk_thresholds`, `htsi_weights`, `vuln_weights`, `final_weights`,
`escalate_vulnerability_threshold`, `escalate_consecutive_days`, `weather_provider`,
`demo_scenario`, `city_id`. Defaults live in `backend/app/config.py`.

## Model metadata (`model_metadata`)

`trained_at`, `model_type` (RandomForestRegressor or rule-based fallback), `n_samples`,
`metrics` (r2, mae, rmse), `feature_importance`, `fallback_used`.

---

## Computed payload fields (API)

| Payload field | Derivation |
|---|---|
| `htsi` | `0.35·wbgt + 0.20·hi + 0.15·utci + 0.15·night + 0.15·consecutive` (normalised, 0–100) |
| `vulnerability.contributions` | `weight × component_score` per factor |
| `health.hospitalization_risk` | band of health score (<25/45/65/80) |
| `health.demand_increase_pct` | ML-blended or rule-based estimate, shown as min–max range |
| `health.confidence` | High (ML) / Medium (fallback) |
| `final.level` | threshold map of `0.55·HTSI + 0.30·Vuln + 0.15·Health` + escalations |
| `final.explanation` | generated text listing WBGT, HI, humidity, consecutive days, night relief, outdoor workers, green cover, hospital access |
| `severe_window` | first forecast day with hourly WBGT ≥ 30 °C (start/end hours) |
| `expected_heat_admissions_3_5d` | simulated surge per hospital from nearby ward risk/population |

## Units

Temperature °C · humidity % · wind m/s · radiation W/m² · distances km · areas km² ·
density people/km² · scores 0–100.