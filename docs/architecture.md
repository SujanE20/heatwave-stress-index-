# Architecture

## 1. Overview

HEATSHIELD INDIA is a three-service monorepo:

```
┌─────────────────────────┐         ┌──────────────────────────────┐
│  frontend (Next.js 14)  │  REST   │  backend (FastAPI)           │
│  App Router, client     │ ──────► │  routers → services → models │
│  components, Leaflet    │  JSON   │  thermal/vuln/health/risk    │
│  map, Recharts          │         │  ML model + weather providers│
└─────────────────────────┘         └──────────────┬───────────────┘
                                                   │ SQLAlchemy
                                                   ▼
                                    ┌──────────────────────────────┐
                                    │  db (PostgreSQL 16 + PostGIS)│
                                    │  fallback: SQLite (local)    │
                                    └──────────────────────────────┘
```

- **Frontend** never talks to the weather API or the ML model directly — everything is served by
  the backend through typed REST endpoints.
- **Backend** computes all derived values on the fly from raw weather hours + ward demographics.
  Nothing important is pre-baked into static JSON, so switching the demo scenario live changes
  the entire dashboard.
- **Database** is the single source of truth for wards, resources, history, alerts, settings and
  model metadata.

## 2. Backend layering

```
app/main.py            FastAPI app, CORS, lifespan (init tables → seed if empty)
app/routers/           thin HTTP layer: validation (Pydantic), error mapping, JSON shape
app/services/          pure computation (no FastAPI imports — unit-testable standalone)
app/models.py          SQLAlchemy ORM
app/database.py        engine/session (Postgres + PostGIS in Docker, SQLite locally/tests)
app/seed.py            idempotent demo seed + GeoJSON export
```

### Service responsibilities

| Service | Responsibility |
|---|---|
| `thermal.py` | Heat Index (NOAA/NWS Rothfusz + fallbacks), Stull wet-bulb, estimated natural wet-bulb, estimated globe temperature, estimated outdoor WBGT, UTCI Proxy, night-recovery score, consecutive-exposure score, HTSI (0–100) with component explainability. Pure Python (math only). |
| `weather.py` | Provider abstraction. `DemoWeatherProvider` (deterministic, offline, 4 scenarios) and `OpenMeteoProvider` (live, 30-min in-memory cache). Returns hour dicts; `summarize_days()` derives per-day metrics including night values and running counts. |
| `geo.py` | Haversine distance, nearest-resource lookup, per-ward microclimate offsets (UHI). |
| `vulnerability.py` | Weighted 0–100 vulnerability score with per-factor contributions. |
| `health_risk.py` | Hospitalization band, demand-increase % (ML-blended or rule-based), mortality band, confidence, drivers, mandatory safety notes. |
| `final_risk.py` | `0.55·HTSI + 0.30·Vulnerability + 0.15·HealthLoad`, threshold mapping, escalation rules, plain-language explanation. |
| `actions.py` | Rule-based action library by risk level with department / priority / reason / status. |
| `alerts.py` | English + Kannada templates, SMS/WhatsApp previews, simulated delivery. |
| `demo_ml.py` | 730-day synthetic history generator, RandomForestRegressor training/prediction, rule-based fallback, model metadata + feature importance. |
| `analytics.py` | Trends payload for charts/tables (forecast, ward comparison, scatter, history, alerts, intervention placeholder). |
| `risk_pipeline.py` | Orchestration: city hours → ward hours (offsets) → day metrics → HTSI → vulnerability → health → final risk; city summary aggregation. |

## 3. Data flow for one ward risk value

```
1. get_city_weather(settings, city)  → hourly forecast (demo or Open-Meteo), enriched with
                                       HI / Tw / Tnwb / Tg / WBGT / UTCI proxy per hour
2. ward_hours(ward, city_hours)      → apply microclimate offsets
                                       (UHI temp offset, humidity offset, wind reduction)
3. summarize_days(ward_hours)        → per-day: tmax, tmin, peak RH/wind/solar, HI/WBGT/UTCI
                                       maxima, exposure hours, night metrics, running counts
4. compute_ward_day(ward, day)       →
     night = night_recovery_score(tmin, night_hi, hot_nights, consec_warm_nights)
     consec = consecutive_exposure_score(hours, days, exposure)
     htsi = 0.35·WBGT + 0.20·HI + 0.15·UTCI + 0.15·night + 0.15·consec
     vuln = vulnerability_score(ward, weights)
     ml    = RandomForest.predict(features)   [or None → rule-based fallback]
     health = compute_health_risk(...)        [bands, demand %, confidence, drivers]
     final  = final_risk(...)                 [base score + escalations + explanation]
5. city_summary(db, settings)         → aggregate all wards: city level = max, counts,
                                       exposed populations, demand-weighted hospital load,
                                       severe-risk window, recommended actions
```

## 4. Frontend structure

```
src/app/
  page.tsx              Landing / role selection
  dashboard/page.tsx    Command Centre dashboard
  map/page.tsx          GIS risk map + side panel
  ward/[id]/page.tsx    Ward details
  analytics/page.tsx    Forecast & analytics
  alerts/page.tsx       Alerts centre
  resources/page.tsx    Resources management
  admin/page.tsx        Admin settings
  citizen/page.tsx      Citizen mobile view
src/components/
  ui/index.tsx          shadcn-style kit (no Radix runtime dependency — offline-friendly)
  RiskMap.tsx           SSR-safe dynamic import of RiskMapInner (Leaflet)
  RiskMapInner.tsx      Leaflet map: GeoJSON polygons, layer groups, legend, popups
  WardPanel.tsx         Selected-ward side panel
  charts.tsx            Recharts wrappers (multi-line, scatter, bars, risk bars)
  NavBar.tsx            Role selector + demo badge + nav
  RiskBadge.tsx         Labelled risk badges (never colour-only)
src/lib/
  api.ts                typed API client (fetch, error handling)
  types.ts              payload types mirroring the backend
  useApi.ts             loading/error/refresh hook
  utils.ts              classnames, risk metadata, formatting
```

### Why Leaflet is dynamically imported
Leaflet accesses `window` at module load, which breaks Next.js server-side prerendering. The map
page imports `RiskMap` via `next/dynamic(..., { ssr: false })`; everything else is a normal client
component. The remaining pages are statically prerendered, so they load instantly and show a
spinner while data streams in.

## 5. Database & PostGIS strategy

- Docker Compose runs `postgis/postgis:16-3.4`; `database/init.sql` enables `postgis`,
  `postgis_topology` and `fuzzystrmatch` on first boot.
- Ward boundaries are stored as **GeoJSON (JSONB)** — the exact format Leaflet renders — so there
  is no serialization mismatch between store, API and map.
- **Migration path to native geometry:** add a `geometry(Geometry,4326)` column and populate it
  with `ST_GeomFromGeoJSON(geojson)`, then use `ST_DWithin` for nearest-resource queries. The
  current implementation computes haversine distances in Python, which is deterministic and
  identical on SQLite/Postgres.
- Local development and tests use SQLite (in-memory for tests) so `pytest` needs no database
  server. `DATABASE_URL` selects the backend at startup.

## 6. Concurrency & caching

- Open-Meteo responses are cached in memory with a 30-minute TTL (module-level dict, keyed by
  lat/lon/days). Demo data is deterministic and regenerated per request — no cache needed.
- The trained model artifact is cached in memory and reloaded when the file changes.
- SQLite is safe for demo concurrency; use the Postgres profile for multi-user deployments.

## 7. Security & safety constraints

- CORS is configured via `CORS_ORIGINS` (default `*` for the demo).
- No API keys are hardcoded; Open-Meteo needs none.
- Alerts never send real messages — delivery is simulated and clearly labelled.
- Health outputs are banded estimates with mandatory disclaimers; no individual-level data exists
  in the schema.