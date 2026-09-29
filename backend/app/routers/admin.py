"""Admin: settings CRUD, model retraining, GeoJSON/CSV uploads, data-source status."""
import csv
import io
import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import DEFAULT_SETTINGS
from ..database import get_db
from ..services import demo_ml
from ..services.settings_svc import load_settings, save_settings

router = APIRouter(prefix="/api/v1", tags=["admin"])

METHODOLOGY = {
    "htsi": (
        "HTSI = 0.35*normalised WBGT + 0.20*normalised Heat Index + 0.15*normalised UTCI Proxy "
        "+ 0.15*night-time recovery + 0.15*consecutive exposure. All component scores are stored "
        "for explainability. WBGT is estimated from routine weather data (Stull wet-bulb + "
        "documented radiation boost; globe temperature from a documented solar/wind model)."
    ),
    "vulnerability": (
        "Vulnerability = 25% elderly + 20% outdoor workers + 15% poor housing + 15% poor hospital "
        "access + 10% population density + 10% low green cover + 5% chronic disease. Each factor "
        "is normalised 0-100 then weighted."
    ),
    "final_risk": (
        "Final Risk = 55% HTSI + 30% Vulnerability + 15% Health-System Load. Thresholds "
        "0-20 Green, 21-40 Yellow, 41-60 Orange, 61-80 Red, 81-100 Maroon. Escalations: "
        "very-high vulnerability, 3+ consecutive dangerous days, very-high predicted hospital load."
    ),
    "safety": [
        "HeatShield is a decision-support prototype. Heat-stress and health-risk estimates must be "
        "calibrated and validated using local meteorological and public-health data before "
        "operational deployment.",
        "Estimated WBGT is not a replacement for a calibrated onsite WBGT instrument.",
        "UTCI Proxy is not official UTCI if a validated UTCI implementation is not used.",
        "No individual health data must be publicly displayed - only ward-level aggregated estimates.",
    ],
}


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    s = load_settings(db)
    return {
        "settings": s,
        "methodology": METHODOLOGY,
        "defaults": DEFAULT_SETTINGS,
        "scenarios": {
            "normal_summer": "Normal Summer Day",
            "moderate_heatwave": "Moderate Heatwave",
            "severe_humid": "Severe Humid Heatwave",
            "extreme_dry": "Extreme Dry Heatwave",
        },
    }


@router.post("/settings")
def update_settings(payload: schemas.SettingsUpdateIn, db: Session = Depends(get_db)):
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No valid settings provided.")
    s = save_settings(db, updates)
    return {"message": "Settings updated", "settings": s}


@router.post("/admin/retrain-model")
def retrain_model(db: Session = Depends(get_db)):
    try:
        meta = demo_ml.train_demo_model(db)
        return {"message": "Demo model retrained", "metadata": meta}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/admin/model")
def model_metadata(db: Session = Depends(get_db)):
    meta = demo_ml.get_model_metadata(db)
    if meta is None:
        raise HTTPException(status_code=404, detail="Model not trained yet. POST /api/v1/admin/retrain-model")
    return meta


@router.get("/admin/data-sources")
def data_source_status(db: Session = Depends(get_db)):
    settings = load_settings(db)
    counts = {
        "wards": db.query(models.Ward).count(),
        "hospitals": db.query(models.Hospital).count(),
        "cooling_centres": db.query(models.CoolingCentre).count(),
        "water_points": db.query(models.WaterPoint).count(),
        "historical_days": db.query(models.HistoricalDaily).count(),
        "alerts": db.query(models.Alert).count(),
    }
    model = demo_ml.get_model_metadata(db)
    return {
        "weather_provider": settings.get("weather_provider"),
        "is_demo": settings.get("weather_provider") == "demo",
        "scenario": settings.get("demo_scenario"),
        "counts": counts,
        "model": model,
        "postgis": "Provisioned in Docker (postgis/postgis image); ward geometry stored as GeoJSON. "
                   "Migration to native geometry columns documented in docs/architecture.md.",
        "health_data_policy": "Only ward-level aggregated estimates are used. No individual health data.",
    }


@router.post("/admin/wards/geojson")
async def upload_wards_geojson(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = await file.read()
    try:
        fc = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON.")
    feats = fc.get("features", [])
    if not feats:
        raise HTTPException(status_code=400, detail="GeoJSON must be a FeatureCollection with at least one feature.")
    updated = 0
    for f in feats:
        props = f.get("properties", {})
        code = props.get("code")
        if not code:
            continue
        ward = db.query(models.Ward).filter_by(code=str(code)).first()
        if ward is None:
            ward = models.Ward(code=str(code), city_id=1)
            db.add(ward)
        ward.name = props.get("name", ward.name or code)
        ward.geojson = f
        geom = f.get("geometry", {})
        if geom.get("type") == "Polygon":
            coords = geom["coordinates"][0]
            lats = [c[1] for c in coords]
            lons = [c[0] for c in coords]
            ward.centroid_lat = round(sum(lats) / len(lats), 6)
            ward.centroid_lon = round(sum(lons) / len(lons), 6)
        for field in ("population", "elderly_pct", "outdoor_worker_density", "informal_housing_pct",
                      "hospital_access_score", "population_density", "green_cover_pct",
                      "chronic_disease_pct", "elevation_m", "area_km2"):
            if field in props:
                setattr(ward, field, float(props[field]))
        updated += 1
    db.commit()
    return {"message": f"Updated {updated} ward geometries/demographics."}


@router.post("/admin/wards/demographics")
async def upload_wards_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))
    fields = {"population", "elderly_pct", "outdoor_worker_density", "informal_housing_pct",
              "hospital_access_score", "population_density", "green_cover_pct",
              "chronic_disease_pct", "elevation_m", "area_km2"}
    updated = 0
    for row in reader:
        code = (row.get("ward_code") or "").strip()
        if not code:
            continue
        ward = db.query(models.Ward).filter_by(code=code).first()
        if ward is None:
            continue
        if row.get("ward_name"):
            ward.name = row["ward_name"].strip()
        for f in fields:
            val = row.get(f)
            if val is not None and str(val).strip() != "":
                setattr(ward, f, float(val))
        updated += 1
    db.commit()
    if updated == 0:
        raise HTTPException(status_code=400, detail="No matching ward codes found in CSV.")
    return {"message": f"Updated demographics for {updated} wards."}