"""Synthetic historical data + baseline hospital-load model (Phase 4).

- Generates >= 730 days of synthetic daily weather and hospital-load data.
- Trains a RandomForestRegressor to predict the daily increase in hospital
  demand above baseline.
- Falls back to a documented rule-based estimate if ML is unavailable or
  training fails.
- Stores model metadata and feature importance; supports "Retrain Demo Model".
"""
import math
import os
import random
from datetime import date, datetime, timedelta
from pathlib import Path

from .. import models
from . import thermal

# backend/data/demo_model.joblib (backend/data is gitignored)
MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "data"
MODEL_PATH = MODEL_DIR / "demo_model.joblib"

try:
    import joblib
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, r2_score
    from sklearn.model_selection import train_test_split

    ML_AVAILABLE = True
except Exception:  # pragma: no cover - depends on environment
    joblib = None
    ML_AVAILABLE = False

FEATURES = [
    "tmax", "tmin", "rh", "wind", "radiation",
    "wbgt_max", "hi_max", "utci_max", "night_recovery",
    "consecutive_days", "month_sin", "month_cos", "weekday",
]

_model_cache = {"mtime": None, "model": None}


# ---------------------------------------------------------------------------
# Synthetic history
# ---------------------------------------------------------------------------
def build_synthetic_history(db, city_id: int, days: int = 730, seed: int = 2024) -> int:
    """Deterministic 730+ day history with seasonal cycle + random heatwaves.

    The final 5 days are forced hot so the analytics chart connects to the
    current forecast scenario. Returns number of rows inserted.
    """
    rng = random.Random(seed)
    today = date.today()
    start = today - timedelta(days=days - 1)
    scenario = "severe_humid"
    rows, heatwave_left, consec = [], 0, 0

    for i in range(days):
        d = start + timedelta(days=i)
        doy = d.timetuple().tm_yday
        seasonal = 25.5 + 7.5 * math.sin(2 * math.pi * (doy - 105) / 365.0)  # peak mid-April

        if rng.random() < 0.07:
            heatwave_left = rng.randint(2, 6)
        if heatwave_left > 0:
            heatwave_left -= 1
            boost = rng.uniform(3.0, 7.5)
        else:
            boost = 0.0

        if i >= days - 5:  # connect history tail to the demo heatwave
            boost = 6.0 + (i - (days - 5)) * 0.8

        tmax = seasonal + boost + rng.uniform(-2.5, 2.5)
        tmin = tmax - rng.uniform(7.0, 11.0)
        rh = max(8.0, min(95.0, 72.0 - (tmax - 25.0) * 1.2 + rng.uniform(-8.0, 8.0)))
        wind = max(0.5, min(8.0, 5.5 - boost * 0.35 + rng.uniform(-1.0, 1.0)))
        cloud = max(0.0, min(100.0, 32.0 - boost * 3.0 + rng.uniform(-12.0, 12.0)))
        radiation = max(0.0, 760.0 + rng.uniform(-160.0, 160.0))
        solar_eff = radiation * (1.0 - 0.8 * cloud / 100.0)

        wbgt = thermal.wbgt_outdoor(tmax, rh, solar_eff, wind, cloud)
        hi, _ = thermal.heat_index(tmax, rh)
        utci = thermal.utci_proxy(tmax, rh, wind, solar_eff, cloud)
        night = thermal.night_recovery_score(
            tmin, thermal.heat_index(min(98.0, tmin + 1.0), min(98.0, rh + 12.0))[0],
            0, 0,
        )["score"]
        consec = consec + 1 if wbgt >= 30.0 else 0

        # hospital-load response: quadratic in WBGT + night + cumulative days
        demand = (
            4.0
            + 0.38 * max(0.0, wbgt - 22.0) ** 2
            + 0.35 * night
            + 2.2 * consec
            + 4.0 * math.sin(2 * math.pi * (doy - 350) / 365.0)  # mild winter flu bump
            + rng.uniform(-4.0, 4.0)
        )
        demand = round(max(0.0, min(80.0, demand)), 1)
        heat_admissions = max(0, round(max(0.0, demand - 6.0) * 3.1 + rng.uniform(-15, 20)))

        rows.append(models.HistoricalDaily(
            city_id=city_id, d=d, tmax=round(tmax, 1), tmin=round(tmin, 1),
            rh=round(rh, 1), wind=round(wind, 1), radiation=round(radiation, 0),
            wbgt_max=wbgt, hi_max=hi, utci_max=utci, night_recovery=round(night, 1),
            consecutive_days=consec, hospital_load_increase_pct=demand,
            heat_admissions=heat_admissions,
        ))

    db.add_all(rows)
    db.commit()
    return len(rows)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
def _matrix(rows):
    X, y = [], []
    for r in rows:
        X.append([
            r.tmax, r.tmin, r.rh, r.wind, r.radiation,
            r.wbgt_max, r.hi_max, r.utci_max, r.night_recovery,
            r.consecutive_days,
            math.sin(2 * math.pi * r.d.timetuple().tm_yday / 365.0),
            math.cos(2 * math.pi * r.d.timetuple().tm_yday / 365.0),
            r.d.weekday(),
        ])
        y.append(r.hospital_load_increase_pct)
    return np.array(X, dtype=float), np.array(y, dtype=float)


def train_demo_model(db) -> dict:
    """Train/retrain the RandomForest model; fall back gracefully. Returns metadata."""
    rows = db.query(models.HistoricalDaily).order_by(models.HistoricalDaily.d).all()
    if len(rows) < 300:
        raise ValueError("Not enough historical data to train (need >= 300 days).")

    metadata = {
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "model_type": "RandomForestRegressor (fallback: rule-based)",
        "n_samples": len(rows),
        "fallback_used": not ML_AVAILABLE,
        "metrics": {},
        "feature_importance": {},
    }

    if ML_AVAILABLE:
        X, y = _matrix(rows)
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
        model = RandomForestRegressor(n_estimators=150, max_depth=9, random_state=42, n_jobs=-1)
        model.fit(X_tr, y_tr)
        pred = model.predict(X_te)
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        _model_cache.update({"mtime": MODEL_PATH.stat().st_mtime, "model": model})
        metadata.update({
            "model_type": "RandomForestRegressor",
            "metrics": {
                "r2": round(float(r2_score(y_te, pred)), 3),
                "mae": round(float(mean_absolute_error(y_te, pred)), 2),
                "rmse": round(float(np.sqrt(np.mean((pred - y_te) ** 2))), 2),
            },
            "feature_importance": {
                FEATURES[i]: round(float(imp), 4)
                for i, imp in enumerate(model.feature_importances_)
            },
        })
    else:
        metadata["model_type"] = "Rule-based fallback (scikit-learn unavailable)"
        metadata["metrics"] = {"note": "ML library unavailable in this environment"}

    # persist metadata row
    db.query(models.ModelMetadata).delete()
    db.add(models.ModelMetadata(
        trained_at=datetime.utcnow(),
        model_type=metadata["model_type"],
        n_samples=metadata["n_samples"],
        metrics=metadata["metrics"],
        feature_importance=metadata.get("feature_importance", {}),
        fallback_used=metadata["fallback_used"],
    ))
    db.commit()
    return metadata


def _load_model():
    if not ML_AVAILABLE or not MODEL_PATH.exists():
        return None
    mtime = MODEL_PATH.stat().st_mtime
    if _model_cache["mtime"] != mtime:
        _model_cache.update({"mtime": mtime, "model": joblib.load(MODEL_PATH)})
    return _model_cache["model"]


def predict_from_day(day: dict) -> tuple[float, str] | None:
    """Predict hospital-load increase (%) from a ward/day summary dict.

    Returns None when no trained model is available (caller uses the
    rule-based estimate instead).
    """
    model = _load_model()
    if model is None:
        return None
    d = day.get("date") or date.today()
    features = [
        day.get("tmax", 0), day.get("tmin", 0), day.get("rh", 50), day.get("wind", 3),
        day.get("solar", 700), day.get("wbgt_max", 0), day.get("hi_max", 0),
        day.get("utci_max", 0), day.get("night_score", {}).get("score", 0),
        day.get("consecutive_high_days", 0),
        math.sin(2 * math.pi * d.timetuple().tm_yday / 365.0),
        math.cos(2 * math.pi * d.timetuple().tm_yday / 365.0),
        d.weekday(),
    ]
    try:
        pred = float(model.predict(np.array([features]))[0])
        return round(max(0.0, pred), 1), "RandomForest (trained on 730-day synthetic history)"
    except Exception:
        return None


def get_model_metadata(db) -> dict | None:
    row = db.query(models.ModelMetadata).order_by(models.ModelMetadata.trained_at.desc()).first()
    if row is None:
        return None
    return {
        "trained_at": row.trained_at.isoformat() + "Z",
        "model_type": row.model_type,
        "n_samples": row.n_samples,
        "metrics": row.metrics,
        "feature_importance": row.feature_importance,
        "fallback_used": row.fallback_used,
    }