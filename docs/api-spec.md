# API Specification

Base URL: `http://localhost:8000` · Interactive docs: `/docs` (OpenAPI 3).

All endpoints return JSON. Errors use FastAPI's standard shape:
`{"detail": "..."}` with appropriate HTTP status codes (404 for unknown wards, 400 for invalid
payloads, 500 for engine failures). CORS is enabled (origins from `CORS_ORIGINS`).

## Health

### `GET /health`
```json
{
  "status": "ok",
  "service": "heatshield-backend",
  "version": "1.0.0",
  "database": "up",
  "demo_mode": true,
  "scenario": "severe_humid",
  "docs": "/docs"
}
```

## Cities & wards

### `GET /api/v1/cities`
```json
[{ "id": 1, "name": "Mysore", "state": "Karnataka", "lat": 12.2958, "lon": 76.6394, "timezone": "Asia/Kolkata" }]
```

### `GET /api/v1/wards?include_geometry=false`
List of 15 wards with demographics + current `risk` (final risk object). With
`include_geometry=true`, each item adds `geojson` (Feature with Polygon geometry).

### `GET /api/v1/wards/{ward_id}`
Full ward risk profile (see WardRisk schema below).

### `GET /api/v1/wards/{ward_id}/forecast`
```json
{
  "ward_id": 1, "ward_code": "W-01", "ward_name": "Vidyanagar",
  "daily": [
    {
      "date": "2026-09-07", "tmax": 37.3, "tmin": 26.8, "rh": 57.0, "wind": 3.0,
      "hi_max": 45.2, "wbgt_max": 31.8, "utci_max": 39.4,
      "exposure_hours": 9, "consecutive_days": 3,
      "htsi": 72.3, "risk_level": "orange", "risk_label": "High",
      "health_demand": { "predicted": 38.4, "range_pct": "30-50" },
      "mortality_band": "High", "confidence": "High"
    }
  ],
  "hourly": [ { "ts": "...", "hour": 10, "t": 33.1, "rh": 58.2, "wind": 2.1, "solar": 520,
                "hi": 40.1, "wbgt": 30.2, "utci_proxy": 36.4 } ]
}
```

## Dashboard & weather

### `GET /api/v1/dashboard/summary`
```json
{
  "city": { "id": 1, "name": "Mysore", "state": "Karnataka", "lat": 12.2958, "lon": 76.6394 },
  "weather": { "provider": "demo", "scenario": "severe_humid", "is_demo": true, "fallback": false },
  "current_conditions": {
    "t": 33.3, "rh": 66.2, "wind": 2.8, "wind_dir": 250, "solar": 440, "cloud": 35,
    "precip_prob": 24, "hi": 38.0, "wbgt": 30.4, "utci_proxy": 34.4, "apparent": 38.0,
    "htsi": 62.2, "htsi_components": { "wbgt": 77.5, "heat_index": 39.3, "utci": 44.3,
      "night_recovery": 79.4, "consecutive_exposure": 69.0 },
    "observed_at": "2026-09-06T10:00:00+05:30"
  },
  "risk": {
    "city_level": "orange", "city_label": "High",
    "ward_counts": { "green": 0, "yellow": 0, "orange": 15, "red": 0, "maroon": 0 },
    "high_risk_wards": 0, "people_exposed": 545026, "vulnerable_exposed": 106902,
    "high_risk_ward_names": []
  },
  "note": "Risk levels follow daily MAX air temperature (Low 25-30 °C · Moderate 30-35 · High 35-40 · Very High 40-44 · Extreme ≥ 45 °C). Weather is city-wide in Mysore, so all wards share the same category.",
  "health": { "demand_increase_pct": 45.2, "demand_range_pct": "31-55",
              "label": "Predicted increase in health demand (decision-support estimate)" },
  "alerts": { "active": 0 },
  "severe_window": { "date": "2026-09-07", "start": "10:00", "end": "19:00", "peak_wbgt": 35.0 },
  "action_plan": null,
  "recommended_actions": [ { "title": "...", "department": "...", "priority": "Immediate" } ],
  "wards": [ { "id": 1, "code": "W-01", "name": "Vidyanagar", "level": "red", "label": "Very High",
               "score": 61, "htsi": 66.4, "vulnerability": 58.3, "population": 31200,
               "centroid_lat": 15.3745, "centroid_lon": 75.1378 } ],
  "disclaimers": ["..."]
}
```

### `GET /api/v1/weather/current`
Raw provider variables + derived indices for the current hour.

### `GET /api/v1/weather/forecast`
`{ provider, is_demo, fallback, scenario, current, daily[], hours[] }` — five forecast days of
hourly data (each hour includes `t, rh, wind, solar, cloud, hi, wbgt, utci_proxy`).

## Risk

### `GET /api/v1/risk/ward/{ward_id}`
Same payload as `wards/{ward_id}` (WardRisk).

### `GET /api/v1/risk/city-summary`
`{ city_risk_level, city_risk_label, ward_counts, high_risk_wards, people_exposed,
   vulnerable_exposed, demand_increase_pct, disclaimers }`

### Hyperlocal map

### `GET /api/v1/map/hyperlocal?ward_id=1`
Sub-ward risk zones for the demo city: every ward is tiled into 7 pockets
(1 core + 6 side blocks; 105 total). All pockets share the city-wide heat
category; pocket levels differ only by local exposure (street activity,
tree shade, informal housing, daytime elderly presence, shelter distance),
which can push a pocket ABOVE — never below — the city's temperature category.

```json
{
  "city": { "id": 1, "name": "Mysore", "state": "Karnataka", "lat": 12.2958, "lon": 76.6394 },
  "weather": { "provider": "demo", "scenario": "severe_humid", "is_demo": true, "fallback": false },
  "shared_heat_note": "Air temperature and thermal stress are city-wide on a given day in Mysore; wards and pockets differ by exposure and vulnerability, not by temperature.",
  "wards": [ { "id": 1, "code": "W-01", "name": "Vidyaranyapuram", "level": "orange",
                "label": "High", "score": 62, "htsi": 69.5, "vulnerability": 54.3,
                "population": 31200, "centroid_lat": 12.30, "centroid_lon": 76.64, "geojson": {...} } ],
  "zones": [ {
    "id": "W-01-C", "zone_index": 0, "role": "core", "ward_id": 1,
    "ward_code": "W-01", "ward_name": "Vidyaranyapuram",
    "name": "Vidyaranyapuram · core pocket", "kind": "Market / bazaar core",
    "level": "red", "label": "Very High", "score": 77.7, "base_score": 77.7,
    "escalations": ["Local exposure (75.3/100) pushes this pocket above the city-wide High heat category"],
    "exposure": { "score": 75.3, "components": { "activity": 82.1, "no_shade": 74.0,
                  "informal": 44.2, "elderly_day": 38.9, "shelter_gap": 70.5 },
                  "contributions": {...}, "weights": {...}, "labels": {...},
                  "kind": "Market / bazaar core",
                  "nearest": { "cooling_centre": { "name": "...", "distance_km": 0.8 },
                                "water_point": { "name": "...", "distance_km": 0.5 } } },
    "htsi": 69.5, "ward_level": "orange", "ward_label": "High", "ward_score": 62,
    "population": 6400, "population_share": 0.205,
    "centroid_lat": 12.30, "centroid_lon": 76.64,
    "explanation": "Vidyaranyapuram · core pocket (Market / bazaar core). The whole ward shares the same city heat today (estimated WBGT up to ~32 °C city-wide) (High city-wide), and this pocket adds concentrated street activity and crowds; ... [Decision-support estimate]",
    "geojson": { "type": "Feature", "properties": { "zone": "C" },
                  "geometry": { "type": "Polygon", "coordinates": [...] } }
  } ]
}
```

### WardRisk schema (abridged)
```json
{
  "ward_id": 1, "ward_code": "W-01", "ward_name": "Vidyanagar", "date": "2026-09-06",
  "current": { "t": 33.1, "rh": 58.2, "wind": 2.1, "solar": 520, "cloud": 38,
               "hi": 40.1, "wbgt": 30.2, "utci_proxy": 36.4, "apparent": 40.1 },
  "htsi": { "score": 66.4, "components": { "wbgt": 76.2, "heat_index": 46.8, "utci": 51.4,
            "night_recovery": 79.4, "consecutive_exposure": 72.0 } },
  "vulnerability": { "score": 58.3, "components": {...}, "contributions": { "elderly": 10.2, ... },
                     "weights": {...}, "labels": {...} },
  "health": {
    "score": 61.2, "hospitalization_risk": "Very High",
    "mortality_risk_band": "High",
    "demand_increase_pct": { "predicted": 38.4, "range_pct": "30-50", "min": 30, "max": 50,
      "source": "RandomForest (trained on 730-day synthetic history)",
      "label": "Predicted increase in health demand (decision-support estimate)" },
    "confidence": "High",
    "drivers": [ { "name": "Thermal stress (HTSI)", "contribution_pct": 42.1 } ],
    "inputs": { "htsi": 66.4, "wbgt": 30.2, "heat_index": 40.1, "utci_proxy": 36.4,
                "relative_humidity": 58.2, "wind_speed": 2.1, "night_recovery": 79.4,
                "consecutive_exposure": 72.0, "vulnerability": 58.3, "hospital_access": 62.0 },
    "safety_notes": ["Decision-support estimate - requires calibration using local public-health data.",
                     "No exact number of deaths is claimed; only an excess mortality-risk band is provided.",
                     "Estimated WBGT is not a replacement for a calibrated onsite WBGT instrument."]
  },
  "final": {
    "score": 61.5, "base_score": 61.5, "level": "orange", "label": "High",
    "base_level": "orange", "base_label": "High",
    "escalations": [],
    "explanation": "Ward W-01 is classified High because today's forecast maximum air temperature is 37.3 °C (Low ≤ 30 °C · Moderate 30-35 · High 35-40 · Very High 40-44 · Extreme ≥ 45 °C). Temperature is city-wide in Mysore - all wards share this heat category. [Decision-support estimate]",
    "weights": { "htsi": 0.55, "vulnerability": 0.30, "health_load": 0.15 },
    "temperature_c": 37.3,
    "bands": { "Low": "≤ 30 °C", "Moderate": "30-35 °C", "High": "35-40 °C",
                "Very High": "40-44 °C", "Extreme": "≥ 45 °C" }
  },
  "actions": [ { "ward_id": 1, "ward_code": "W-01", "ward_name": "Vidyanagar",
                 "risk_level": "red", "category": "Infrastructure", "title": "Open cooling centres",
                 "department": "Municipal Corporation", "priority": "Immediate",
                 "reason": "...", "status": "Pending" } ],
  "nearest": { "hospital": { "name": "Mysore Medical College & KR Hospital", "distance_km": 1.2 },
               "cooling_centre": { "name": "Government School - Vidyanagar", "distance_km": 0.8 },
               "water_point": { "name": "...", "distance_km": 0.5 } }
}
```

## Actions

### `GET /api/v1/actions/recommendations?ward_id=1|level=red`
Returns action objects (see above). Without parameters: city-level recommendations.

### `POST /api/v1/actions/trigger-heat-action-plan`
Body: `{ "triggered_by": "Command Centre Officer" }`
Creates an `Active` Heat Action Plan and marks matching city actions `In Progress`.
```json
{ "message": "Heat Action Plan triggered",
  "detail": { "plan_id": 1, "summary": "Heat Action Plan triggered. City risk: High (0 high-risk wards, 545,026 people exposed). Estimated demand increase: 57.1%." } }
```

## Resources

### `GET /api/v1/resources/hospitals`
```json
[{ "id": 1, "name": "Mysore Medical College & KR Hospital", "type": "District", "lat": 12.3108, "lon": 76.6574,
   "beds": 750, "emergency_beds": 90, "available_emergency_beds": 20, "occupancy_pct": 78,
   "has_icu": true, "ors_units": 4200, "iv_fluids_units": 1800,
   "expected_heat_admissions_3_5d": 214, "note": "Simulated capacity and expected admissions - decision-support estimate." }]
```

### `GET /api/v1/resources/cooling-centres`
Capacity, current occupancy, occupancy %, water stock (L), ORS units, hours.

### `GET /api/v1/resources/water-points`
Name, location, type, status.

### `GET /api/v1/resources/ward-coverage`
```json
[{ "ward_id": 5, "ward_code": "W-05", "ward_name": "Unkal Lake", "vulnerable_exposed": 16200,
   "risk_level": "red", "risk_label": "Very High",
   "nearest_cooling_centre": "Government School - Vidyanagar", "distance_km": 3.2,
   "recommendation": "Ward W-05 has 16,200 vulnerable residents exposed to Very High risk and the nearest cooling centre is 3.2 km away. Recommend opening a temporary cooling centre at Ward Community Hall." }]
```

## Analytics

### `GET /api/v1/analytics/trends`
```json
{
  "forecast": [ { "date": "2026-09-06", "tmax": 37.3, "tmin": 26.8, "hi_max": 45.2,
                  "wbgt_max": 31.8, "utci_max": 39.4, "htsi": 71.4, "risk_level": "orange",
                  "risk_label": "High" } ],
  "hourly": [...48+ hourly points...],
  "ward_comparison": [ { "id": 1, "code": "W-01", "name": "Vidyaranyapuram", "population": 31200,
                         "risk_level": "orange", "risk_label": "High", "risk_score": 61.5,
                         "htsi": 69.5, "vulnerability": 54.3, "health_score": 61.2,
                         "wbgt_max": 31.8, "consecutive_days": 3 } ],
  "scatter": [ { "ward": "Vidyaranyapuram", "x": 54.3, "y": 69.5, "risk": "orange" } ],
  "hospital_load_history": [ { "date": "2026-05-01", "load_increase_pct": 24.5,
                               "heat_admissions": 68, "wbgt_max": 31.2, "tmax": 39.1 } ],
  "alert_history": [],
  "intervention_effectiveness": { "note": "...", "series": [...], "estimated_effect": "..." },
  "weather": { "provider": "demo", "is_demo": true, "fallback": false }
}
```

## Alerts

### `GET /api/v1/alerts?limit=50`
Alert list (id, ward_id, ts, severity, title, body_en, body_kn, channels, status, sent_via, delivered_at).

### `POST /api/v1/alerts/generate`
Body: `{ "min_level": "orange", "channels": ["dashboard", "sms", "whatsapp", "webhook"] }`
Creates **draft** bilingual alerts for wards at/above the level. Response includes each alert's
EN + KN body plus SMS and WhatsApp previews. Returns 400 if no ward qualifies.

### `POST /api/v1/alerts/send`
Body: `{ "alert_ids": [1,2], "channels": ["sms","whatsapp"] }` (either optional)
Marks alerts `Sent (simulated)` with per-channel delivery stamps. **No real messages are sent.**

## Settings & admin

### `GET /api/v1/settings`
`{ settings, methodology, defaults, scenarios }`

### `POST /api/v1/settings`
Partial update — only provided keys change. Allowed keys: `risk_thresholds`,
`htsi_weights`, `vuln_weights`, `final_weights`, `escalate_vulnerability_threshold`,
`escalate_consecutive_days`, `weather_provider`, `demo_scenario`, `city_id`.
Example: `{ "demo_scenario": "extreme_dry" }`.

### `GET /api/v1/admin/model` · `POST /api/v1/admin/retrain-model`
Model metadata (trained_at, model_type, n_samples, metrics {r2, mae, rmse},
feature_importance, fallback_used). Retrain returns the fresh metadata.

### `GET /api/v1/admin/data-sources`
Provider, scenario, entity counts, model metadata, PostGIS note, data policy.

### `POST /api/v1/admin/wards/geojson` (multipart `file`)
FeatureCollection; matches ward codes and updates geometry + demographics.

### `POST /api/v1/admin/wards/demographics` (multipart `file`)
CSV with the columns from `GET /api/v1/admin/sample-csv`.

### `GET /api/v1/admin/sample-csv`
`{ filename, content, columns }` — template for the demographics upload.

## Validation & errors

- Request bodies are validated with Pydantic v2 (`TriggerPlanIn`, `GenerateIn`, `SendIn`,
  `SettingsUpdateIn`) — invalid types/values return 422 with field errors.
- Unknown ward ids return `404 {"detail": "Ward {id} not found"}`.
- `POST /api/v1/alerts/send` with no alerts returns 404; `generate` with no qualifying wards
  returns 400.
- Retraining with < 300 history days returns 400.