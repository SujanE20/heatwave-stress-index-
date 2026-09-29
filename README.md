# HEATSHIELD INDIA 🔥🛡️

**“Predicting what heat will do to people, not just what the weather will be.”**

A localized heat-health early warning system for Indian cities. HEATSHIELD transforms a
5-day weather forecast into **ward-level human thermal stress → vulnerability →
hospitalization / mortality-risk estimates → recommended municipal action → bilingual citizen alerts**,
displayed on an interactive GIS map.

**Demo city:** Mysore, Karnataka (configurable — any Indian city can be added).
**Runs fully offline** in Demo Mode (no internet required) with four realistic weather scenarios.

---

## Problem statement

Traditional heatwave alerts report dry-bulb temperature. But human danger depends on far more:

| Weather & exposure | People & place |
|---|---|
| Air temperature | Elderly population |
| Relative humidity | Outdoor-worker density |
| Wind speed | Poor housing / informal settlements |
| Solar radiation | Low tree cover / urban heat island |
| Cloud cover | Hospital access |
| Consecutive hot days | Population density |
| High night-time temperature | Chronic-disease burden |

> A 38 °C day at 20% humidity feels very different from a 38 °C day at 70% humidity —
> and it is *far* more dangerous for an elderly outdoor worker in a dense ward with no
> hospital nearby. HEATSHIELD models exactly this difference.

## Solution

```
Weather forecast            (dry-bulb T, RH, wind, radiation, cloud)
        ↓
Human Thermal Stress Index  (HTSI 0–100: WBGT + Heat Index + UTCI Proxy + night recovery + cumulative exposure)
        ↓
Ward Vulnerability Score    (0–100: elderly, outdoor workers, housing, hospital access, density, green cover, chronic disease)
        ↓
Health-risk estimate        (hospitalization band, demand increase %, mortality band, confidence, drivers)
        ↓
Final risk (Green → Maroon) with escalation rules and full explanations
        ↓
Role-specific actions       (department, priority, reason, status) + bilingual EN/KN alerts
```

## Key innovation

1. **Human-centred thermal engine** — estimated outdoor WBGT (0.7·Tnwb + 0.2·Tg + 0.1·Tdb),
   NOAA/NWS Heat Index, a documented **UTCI Proxy**, night-time recovery and consecutive-exposure
   scores. Every formula is documented; every estimate is labelled as an estimate.
2. **Temperature-first, honest risk bands** — the displayed risk level follows the daily
   MAXIMUM air temperature (Low 25-30 °C · Moderate 30-35 · High 35-40 · Very High 40-44 ·
   Extreme ≥ 45 °C). Weather is city-wide in Mysore, so every ward shares the same heat
   category — the AI never invents ward-to-ward temperature differences. Vulnerability,
   thermal stress and health-load analysis are still computed per ward as detail and drive
   actions and shelter planning.
3. **ML with an honest fallback** — a RandomForestRegressor trained on 730+ days of synthetic
   history predicts hospital-load increase, with a documented rule-based fallback if training
   fails. Feature importance and model metadata are exposed in the Admin panel.
4. **Offline demo-ready** — 15 demo wards, 4 hospitals, 6 cooling centres, 10 water points and a
   deterministic scenario generator make the full product demoable on a single laptop with no internet.
5. **Safety by design** — no exact death counts, no individual health data, WBGT/UTCI clearly
   labelled as estimates, and a mandatory disclaimer in the footer of every page.

## Features

- **Role-based views** (Municipal Command Centre Officer, Hospital Administrator, Labour Department
  Officer, Citizen) via a role selector in the top navigation.
- **Temperature-based risk levels** — Low 25-30 °C · Moderate 30-35 · High 35-40 · Very High 40-44 ·
  Extreme ≥ 45 °C, applied uniformly across Mysore's wards (weather is city-wide; no manual
  overrides).
- **Command Centre dashboard** — city risk, live conditions (T, RH, wind, solar, Heat Index,
  estimated WBGT, UTCI Proxy, HTSI), high-risk ward counts, people exposed, hospital-load estimate,
  severe-risk window, Trigger Heat Action Plan + Generate Alerts buttons.
- **Interactive GIS map** — 15 ward polygons coloured by risk (never colour-only: labels + icons),
  click popups + detailed side panel, and layer toggles (Combined Risk / Thermal Stress /
  Vulnerability / Hospitals / Cooling Centres / Water Points / Green Cover–UHI).
- **Hyperlocal risk map** — every ward subdivided into 7 pockets (105 total) that tile the ward
  polygons exactly. All pockets share the same city heat; pocket colours differ only by local
  exposure (market crowds, tree shade, informal housing, daytime elderly presence, shelter
  distance), which can push a pocket above — never below — the city's temperature category.
  Full-screen map with focus-ward zoom, risk legend and a per-pocket detail panel.
- **Ward details** — full demographics, thermal metrics, vulnerability contributions,
  hospitalization/mortality bands, confidence, risk drivers, nearest resources, recommended actions.
- **Forecast & Analytics** — 5-day and hourly charts (T, apparent T, Heat Index, WBGT, UTCI Proxy,
  HTSI), risk-forecast bars, ward comparison table, vulnerability-vs-thermal scatter, historical
  hospital-load trend, alert history, intervention-effectiveness placeholder.
- **Alerts Centre** — bilingual English + Kannada generation, SMS / WhatsApp / webhook previews,
  simulated delivery (no real messages by default), alert history.
- **Resource management** — hospital surge estimates, cooling-centre occupancy & stock, water
  points, ward coverage-gap recommendations (e.g. *"Ward W-05 has 16,000 vulnerable residents
  exposed to Very High risk and the nearest cooling centre is 3.2 km away. Recommend opening a
  temporary cooling centre at Ward Community Hall."*).
- **Admin settings** — risk thresholds, HTSI/vulnerability weights, weather provider + demo
  scenario, GeoJSON + demographic CSV uploads, sample CSV download, methodology reference,
  ML model metadata + retrain, data-source status.

## Architecture

```mermaid
flowchart LR
    subgraph Browser
        NEXT[Next.js 14 + Tailwind + Leaflet + Recharts]
    end
    subgraph Backend
        API[FastAPI - routers]
        ENG[Thermal / Vulnerability / Health / Risk / Actions engines]
        ML[Hospital-load ML model + rule fallback]
        WX[Weather providers: Demo / Open-Meteo]
    end
    DB[(PostgreSQL + PostGIS)]
    NEXT -->|REST JSON| API
    API --> ENG
    ENG --> ML
    ENG --> WX
    WX -.->|live forecast| OM[Open-Meteo API]
    API <--> DB
    ENG <--> DB
```

## Technology stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn-style UI kit, React Leaflet, Recharts, Lucide icons |
| Backend | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2, Pandas, NumPy, scikit-learn (RandomForest), optional XGBoost |
| Database | PostgreSQL 16 + PostGIS 3.4 (Docker) · SQLite fallback for local demo/tests |
| DevOps | Docker Compose, `.env.example`, OpenAPI docs (`/docs`) |

## Repository structure

```
heatshield-india/
├── README.md
├── docker-compose.yml
├── .env.example
├── docs/
│   ├── architecture.md
│   ├── methodology.md
│   ├── api-spec.md
│   ├── demo-script.md
│   └── data-dictionary.md
├── frontend/                 # Next.js 14 app (9 pages)
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app, CORS, lifespan seed
│   │   ├── config.py         # defaults, risk levels
│   │   ├── database.py       # engine/session (Postgres or SQLite)
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── seed.py           # demo seed + GeoJSON export
│   │   ├── services/
│   │   │   ├── thermal.py        # HI, wet-bulb, globe, WBGT, UTCI proxy, HTSI
│   │   │   ├── weather.py        # provider abstraction + demo generator
│   │   │   ├── vulnerability.py  # weighted vulnerability score
│   │   │   ├── health_risk.py    # hospitalization/mortality estimates
│   │   │   ├── final_risk.py     # combined risk + escalations
│   │   │   ├── actions.py        # role-based action engine
│   │   │   ├── alerts.py         # bilingual templates + simulated delivery
│   │   │   ├── demo_ml.py        # synthetic history + RandomForest + fallback
│   │   │   ├── analytics.py      # trends assembly
│   │   │   └── risk_pipeline.py  # end-to-end computation
│   │   └── routers/          # health / core / alerts / admin
│   └── tests/                # pytest suite (51 tests)
├── database/
│   ├── init.sql              # PostGIS extension setup
│   └── seed_data/            # exported GeoJSON + sample CSV
└── scripts/
    ├── seed.py               # standalone seeding + export
    ├── dev.sh                # docker compose up
    └── test.sh               # full test suite
```

## Setup

### Option A — Docker Compose (recommended, everything included)

```bash
git clone <repo> heatshield-india && cd heatshield-india
cp .env.example .env          # defaults already work offline
./scripts/dev.sh              # = docker compose up --build
```

Then open:
- **Dashboard** → http://localhost:3000
- **API docs (OpenAPI)** → http://localhost:8000/docs
- **Health check** → http://localhost:8000/health

The database container provisions **PostgreSQL + PostGIS** and the backend auto-seeds the
Mysore demo (15 wards, resources, 730 days of history, demo ML model) on first start.

### Option B — Local development (no Docker)

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Uses SQLite by default (`backend/data/heatshield.db`, auto-created and seeded on start).

**Frontend:**
```bash
cd frontend
npm install
npm run dev                  # http://localhost:3000
```

### Option D — VS Code (recommended for development)

Open this folder in VS Code — the repo ships `.vscode/` configs, so everything works out of
the box once dependencies are installed (Option B):

- **Run & debug (F5)** — three launch configurations:
  - `Backend (uvicorn :8000)` — FastAPI with the debugger attached (uses the repo `.venv`).
  - `Frontend (Next.js :3000)` — `next dev -p 3000` with Node debugging attached.
  - `Full stack (backend + frontend)` — both at once (compound config, stops both).
- **Tasks: Run Task** — `install: backend deps`, `install: frontend deps`,
  `run: backend (hot reload)` (uvicorn `--reload`), `run: frontend (dev server)`,
  `test: backend (pytest)`, `typecheck: frontend (tsc --noEmit)`.
- **Recommended extensions** (`.vscode/extensions.json`) — Python, Pylance, ESLint,
  Tailwind CSS, Prettier, TypeScript; VS Code offers to install them on first open.
- Ports are pinned (`8000` backend / `3000` frontend) so the dev servers always land where
  the app expects them. The frontend calls the backend at `http://localhost:8000` via
  `NEXT_PUBLIC_API_URL` (no proxy needed).

### Option C — PostgreSQL locally (no Docker, with PostGIS installed)
```bash
export DATABASE_URL=postgresql+psycopg2://heatshield:heatshield@localhost:5432/heatshield
python scripts/seed.py       # seeds the DB and exports GeoJSON into database/seed_data/
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///…/heatshield.db` | SQLAlchemy URL (Postgres in Docker) |
| `WEATHER_PROVIDER` | `demo` | `demo` (offline) or `openmeteo` (live) |
| `DEMO_SCENARIO` | `severe_humid` | `normal_summer` \| `moderate_heatwave` \| `severe_humid` \| `extreme_dry` |
| `OPEN_METEO_BASE_URL` | `https://api.open-meteo.com/v1` | Open-Meteo endpoint |
| `CORS_ORIGINS` | `*` | Comma-separated CORS origins |
| `POSTGRES_USER/PASSWORD/DB/PORT` | `heatshield` | DB container credentials |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL as seen by the browser |

## Demo mode

Demo Mode is the default and needs **no internet**. A deterministic weather generator produces
hourly data (temperature, humidity, wind, radiation, cloud, precipitation probability) for four
scenarios:

1. **Normal Summer Day** — daily max ~33 °C → Moderate (yellow) city-wide.
2. **Moderate Heatwave** — daily max ~38 °C → High (orange) city-wide.
3. **Severe Humid Heatwave** *(default)* — daily max ~37 °C, Heat Index ~44–46 °C, estimated
   WBGT ~30–32 °C → High (orange) city-wide; hyperlocal pockets with extreme exposure climb to
   Very High.
4. **Extreme Dry Heatwave** — daily max ~44 °C, very high UTCI Proxy → Very High (red) city-wide.

Switch scenarios live in **Admin Settings → Weather provider**. A **"Demo Data"** badge appears in
the navbar whenever demo mode is active. If Open-Meteo is selected but unreachable, the app
automatically falls back to demo data.

## API

Interactive docs at `http://localhost:8000/docs` (OpenAPI). Endpoints:

```
GET  /health
GET  /api/v1/cities
GET  /api/v1/wards                       ?include_geometry=true
GET  /api/v1/wards/{ward_id}
GET  /api/v1/wards/{ward_id}/forecast
GET  /api/v1/dashboard/summary
GET  /api/v1/map/hyperlocal             ?ward_id=1 (optional single ward)
GET  /api/v1/weather/current
GET  /api/v1/weather/forecast
GET  /api/v1/risk/ward/{ward_id}
GET  /api/v1/risk/city-summary
GET  /api/v1/actions/recommendations
POST /api/v1/actions/trigger-heat-action-plan
GET  /api/v1/resources/hospitals
GET  /api/v1/resources/cooling-centres
GET  /api/v1/resources/water-points
GET  /api/v1/resources/ward-coverage
GET  /api/v1/analytics/trends
GET  /api/v1/alerts
POST /api/v1/alerts/generate
POST /api/v1/alerts/send
GET  /api/v1/settings
POST /api/v1/settings
GET  /api/v1/admin/model
POST /api/v1/admin/retrain-model
GET  /api/v1/admin/data-sources
POST /api/v1/admin/wards/geojson
POST /api/v1/admin/wards/demographics
GET  /api/v1/admin/sample-csv
```

See `docs/api-spec.md` for schemas and examples.

## Testing

```bash
./scripts/test.sh      # backend pytest + frontend typecheck/build
# or separately:
cd backend && python -m pytest tests/ -q     # 55 tests
cd frontend && npx tsc --noEmit               # frontend typecheck
```

Coverage: Heat Index (Rothfusz + fallbacks), Stull wet-bulb, globe temperature bounds,
WBGT formula, UTCI proxy bounds, night-recovery & consecutive-exposure scores, HTSI weights,
vulnerability directions & contributions, risk thresholds & escalations, health-risk bands &
safety notes, action rules, and full API integration (seed → dashboard → alerts → settings →
model → OpenAPI routes).

## Limitations

- **Decision-support prototype** — must be calibrated with local meteorological and public-health
  data before operational deployment.
- **Estimated WBGT / UTCI Proxy** — derived from routine weather data; not replacements for a
  calibrated onsite WBGT instrument or official UTCI.
- **Demo ward boundaries** — demonstration polygons; replace with official municipal GIS data
  (Admin → upload GeoJSON).
- **Synthetic history & ML** — the 730-day history and hospital-load model are synthetic;
  retrain on real local data.
- **Alerts are simulated** — no real SMS/WhatsApp; integrate approved gateways for production.
- **Aggregated data only** — no individual health records are stored or displayed.

## Future scope

- Live ingestion of IMD / NDMA gridded forecasts and warnings.
- Official UTCI implementation (e.g. the UTCI-Fiala model) behind the proxy.
- PostGIS-native geometry columns + spatial nearest-neighbour queries.
- Real hospital admissions / emergency attendance feeds for model calibration.
- WhatsApp Business / SMS gateway integration with opt-in citizen subscriptions.
- Kannada + Hindi TTS voice alerts and IVR for low-literacy users.
- Impact-based forecasting for agriculture and school/workplace closures.
- Scale-out: multi-city onboarding (add a `cities` row + ward GeoJSON and the whole pipeline follows).

## License

Demo prototype for the Smart India Hackathon — educational use.