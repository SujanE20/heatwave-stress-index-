"""Application configuration and defaults for HEATSHIELD INDIA."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/

# Local (no-Docker) default is SQLite so the demo runs with zero setup.
# Docker Compose overrides this with PostgreSQL + PostGIS.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'data' / 'heatshield.db'}",
)

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

# ---------------------------------------------------------------------------
# Default settings (persisted in the `settings` table; Admin panel can edit)
# ---------------------------------------------------------------------------
DEFAULT_SETTINGS = {
    # 0-20 Green/Low, 21-40 Yellow/Moderate, 41-60 Orange/High,
    # 61-80 Red/Very High, 81-100 Maroon/Extreme
    "risk_thresholds": [20, 40, 60, 80],
    "htsi_weights": {
        "wbgt": 0.35,
        "heat_index": 0.20,
        "utci": 0.15,
        "night_recovery": 0.15,
        "consecutive_exposure": 0.15,
    },
    "vuln_weights": {
        "elderly": 0.25,
        "outdoor_workers": 0.20,
        "poor_housing": 0.15,
        "hospital_access": 0.15,
        "population_density": 0.10,
        "low_green_cover": 0.10,
        "chronic_disease": 0.05,
    },
    "final_weights": {
        "htsi": 0.55,
        "vulnerability": 0.30,
        "health_load": 0.15,
    },
    "escalate_vulnerability_threshold": 80.0,
    "escalate_consecutive_days": 3,
    "weather_provider": os.getenv("WEATHER_PROVIDER", "demo"),
    "demo_scenario": os.getenv("DEMO_SCENARIO", "severe_humid"),
    "city_id": 1,
    "default_city_lat": 12.2958,
    "default_city_lon": 76.6394,
}

RISK_LEVELS = [
    {"key": "green", "label": "Low", "min": 0, "max": 20},
    {"key": "yellow", "label": "Moderate", "min": 21, "max": 40},
    {"key": "orange", "label": "High", "min": 41, "max": 60},
    {"key": "red", "label": "Very High", "min": 61, "max": 80},
    {"key": "maroon", "label": "Extreme", "min": 81, "max": 100},
]

RISK_ORDER = ["green", "yellow", "orange", "red", "maroon"]


def risk_level_for(score: float, thresholds=None) -> dict:
    """Map a 0-100 score to a risk level dict using configured thresholds.

    Thresholds are the upper bounds of the first four levels, e.g.
    [20, 40, 60, 80] => 0-20 Green, 21-40 Yellow, 41-60 Orange,
    61-80 Red, 81-100 Maroon. Ranges are contiguous so decimal scores
    like 40.2 map to Orange (not a gap).
    """
    t = list(thresholds or DEFAULT_SETTINGS["risk_thresholds"])
    for i, level in enumerate(RISK_LEVELS):
        hi = t[i] if i < len(t) else 100.0
        if score <= hi:
            return level
    return RISK_LEVELS[-1]


# ---------------------------------------------------------------------------
# Temperature-based risk categories (daily maximum air temperature, °C)
# ---------------------------------------------------------------------------
# Low 25-30 °C | Moderate 30-35 | High 35-40 | Very High 40-44 | Extreme 45+
# The displayed ward / city risk level follows these bands: weather across
# Mysore wards is city-wide, so every ward shares the same category.
def temperature_level(tmax_c: float) -> dict:
    """Map a daily maximum air temperature (°C) to a risk level dict.

    Bands (per product spec): Low <= 30, Moderate 30-35, High 35-40,
    Very High 40-44, Extreme >= 45 °C.
    """
    t = float(tmax_c)
    if t <= 30.0:
        return RISK_LEVELS[0]   # green / Low
    if t <= 35.0:
        return RISK_LEVELS[1]   # yellow / Moderate
    if t <= 40.0:
        return RISK_LEVELS[2]   # orange / High
    if t < 45.0:
        return RISK_LEVELS[3]   # red / Very High
    return RISK_LEVELS[4]       # maroon / Extreme


def temperature_score(tmax_c: float) -> float:
    """0-100 strength indicator derived from the max temperature.

    Maps 25 -> 0 ... 45+ -> 100 so numeric scores move with the displayed
    temperature category (25-30 Low ... 45+ Extreme).
    """
    return round(min(100.0, max(0.0, (float(tmax_c) - 25.0) / 20.0 * 100.0)), 1)