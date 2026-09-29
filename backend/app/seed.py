"""Seed the demo database: 15 wards, hospitals, cooling centres, water points,
settings, 730 days of synthetic history, and the demo ML model.

Default demo city: Mysore, Karnataka. Ward boundaries are demonstration
polygons (irregular hexagons around the city centre) that can later be
replaced with official municipal GIS data.
"""
import json
import math
import os
import random
from pathlib import Path

from . import models
from .config import DEFAULT_SETTINGS

SEED_DIR = Path(__file__).resolve().parent.parent.parent / "database" / "seed_data"

CITY = {"name": "Mysore", "state": "Karnataka", "lat": 12.2958, "lon": 76.6394, "timezone": "Asia/Kolkata"}

# Representative ward names (Mysuru city area). Boundaries are demonstration polygons.
WARD_NAMES = [
    "Vidyaranyapuram", "Kuvempunagar", "Jayalakshmipuram", "Hebbal", "Yadavagiri",
    "Krishnamurthypuram", "Gokulam", "Saraswathipuram", "Udayagiri", "K. R. Mohalla",
    "Chamrajpura", "Bannimantap", "Lakshmipuram", "Mandi Mohalla", "Nazarbad",
]

# Resources are defined as (name, dlat, dlon) offsets from the city centre so
# they stay inside the ward ring for ANY demo city.
HOSPITALS = [
    {"name": "Mysore Medical College & KR Hospital", "htype": "District", "dlat": 0.015, "dlon": 0.018,
     "beds": 800, "emergency_beds": 100, "occupancy_pct": 79, "has_icu": True, "ors_units": 4800, "iv_fluids_units": 2000},
    {"name": "Cheluvamba Hospital", "htype": "District", "dlat": -0.018, "dlon": -0.020,
     "beds": 350, "emergency_beds": 50, "occupancy_pct": 83, "has_icu": True, "ors_units": 2900, "iv_fluids_units": 1200},
    {"name": "Hebbal PHC", "htype": "Primary Health Centre", "dlat": -0.010, "dlon": -0.006,
     "beds": 30, "emergency_beds": 8, "occupancy_pct": 56, "has_icu": False, "ors_units": 950, "iv_fluids_units": 320},
    {"name": "Apollo BGS Hospitals, Mysore", "htype": "Private", "dlat": 0.020, "dlon": 0.002,
     "beds": 150, "emergency_beds": 20, "occupancy_pct": 71, "has_icu": True, "ors_units": 1600, "iv_fluids_units": 650},
]

COOLING_CENTRES = [
    {"name": "Government School - Vidyaranyapuram", "dlat": 0.014, "dlon": 0.016, "capacity": 400, "water_stock_l": 2400, "ors_units": 600},
    {"name": "Community Hall - Kuvempunagar", "dlat": 0.004, "dlon": -0.020, "capacity": 300, "water_stock_l": 1800, "ors_units": 450},
    {"name": "Public Library - Jayalakshmipuram", "dlat": 0.000, "dlon": 0.012, "capacity": 250, "water_stock_l": 1500, "ors_units": 350},
    {"name": "Anganwadi Centre - Gokulam", "dlat": 0.016, "dlon": 0.004, "capacity": 200, "water_stock_l": 1200, "ors_units": 300},
    {"name": "Municipal Building - K. R. Mohalla", "dlat": 0.006, "dlon": 0.001, "capacity": 500, "water_stock_l": 3000, "ors_units": 800},
    {"name": "Temple Hall - Nazarbad", "dlat": -0.011, "dlon": -0.020, "capacity": 180, "water_stock_l": 1000, "ors_units": 250},
]

WATER_POINTS = [
    ("Gokulam Community Tap", 0.016, 0.005, "Community tap"),
    ("Kukkarahalli Lake Tanker Point", -0.004, 0.006, "Tanker point"),
    ("Kuvempunagar Standpost", 0.004, -0.021, "Standpost"),
    ("K. R. Mohalla Bazaar Tap", 0.006, 0.002, "Community tap"),
    ("Hebbal Tanker", -0.011, -0.006, "Tanker point"),
    ("Yadavagiri Standpost", 0.012, 0.012, "Standpost"),
    ("Nazarbad Well Point", -0.012, -0.019, "Community tap"),
    ("Saraswathipuram Tap", -0.006, 0.010, "Community tap"),
    ("Bannimantap Tanker", -0.015, -0.012, "Tanker point"),
    ("Vidyaranyapuram Standpost", 0.014, 0.018, "Standpost"),
]


def _hexagon(lat_c: float, lon_c: float, radius_deg: float, rng: random.Random) -> list:
    """Irregular hexagon around (lat_c, lon_c). Returns [lon, lat] pairs (GeoJSON order)."""
    pts = []
    for i in range(6):
        ang = math.radians(60 * i + rng.uniform(-8, 8))
        r = radius_deg * rng.uniform(0.82, 1.15)
        pts.append([round(lon_c + r * math.sin(ang), 6), round(lat_c + r * math.cos(ang), 6)])
    pts.append(pts[0])
    return pts


def _ward_features(rng: random.Random, radius_km: float) -> dict:
    area = 2.598 * radius_km * radius_km  # hexagon area
    population = rng.randint(9000, 46000)
    return {
        "population": population,
        "elderly_pct": round(rng.uniform(7.0, 19.5), 1),
        "outdoor_worker_density": round(rng.uniform(600, 4600), 0),
        "informal_housing_pct": round(rng.uniform(4.0, 38.0), 1),
        "hospital_access_score": round(rng.uniform(22, 96), 1),
        "population_density": round(population / area, 0),
        "green_cover_pct": round(rng.uniform(7.0, 46.0), 1),
        "chronic_disease_pct": round(rng.uniform(3.0, 15.0), 1),
        "elevation_m": round(rng.uniform(700, 780), 0),
        "area_km2": round(area, 2),
    }


def seed_all(db) -> dict:
    """Idempotent seed. Returns a summary dict."""
    if db.query(models.City).count() > 0:
        return {"seeded": False, "message": "Database already seeded"}

    rng = random.Random(42)
    city = models.City(**CITY)
    db.add(city)
    db.flush()
    lat_c, lon_c = city.lat, city.lon

    # --- wards: 5 inner + 10 outer ring --------------------------------------
    wards = []
    for i, name in enumerate(WARD_NAMES):
        ring = 0 if i < 5 else 1
        angle = math.radians(72 * i) if ring == 0 else math.radians(36 * (i - 5) + 18)
        r = 0.021 if ring == 0 else 0.052
        cx = lat_c + r * math.cos(angle) * 0.9 + rng.uniform(-0.001, 0.001)
        cy = lon_c + r * math.sin(angle) + rng.uniform(-0.001, 0.001)
        radius_km = rng.uniform(0.42, 1.05)
        radius_deg = radius_km / 111.0
        poly = _hexagon(cx, cy, radius_deg, rng)
        feats = _ward_features(rng, radius_km)
        ward = models.Ward(
            city_id=city.id, code=f"W-{i + 1:02d}", name=name,
            centroid_lat=round(cx, 6), centroid_lon=round(cy, 6),
            geojson={"type": "Feature", "properties": {"code": f"W-{i + 1:02d}", "name": name},
                     "geometry": {"type": "Polygon", "coordinates": [poly]}},
            **feats,
        )
        db.add(ward)
        wards.append(ward)
    db.flush()

    for h in HOSPITALS:
        db.add(models.Hospital(
            city_id=city.id, name=h["name"], htype=h["htype"],
            lat=round(lat_c + h["dlat"], 6), lon=round(lon_c + h["dlon"], 6),
            beds=h["beds"], emergency_beds=h["emergency_beds"], occupancy_pct=h["occupancy_pct"],
            has_icu=h["has_icu"], ors_units=h["ors_units"], iv_fluids_units=h["iv_fluids_units"],
        ))
    for cc in COOLING_CENTRES:
        db.add(models.CoolingCentre(
            city_id=city.id, name=cc["name"], lat=round(lat_c + cc["dlat"], 6),
            lon=round(lon_c + cc["dlon"], 6), capacity=cc["capacity"],
            water_stock_l=cc["water_stock_l"], ors_units=cc["ors_units"],
        ))
    for name, dlat, dlon, wtype in WATER_POINTS:
        db.add(models.WaterPoint(
            city_id=city.id, name=name, lat=round(lat_c + dlat, 6), lon=round(lon_c + dlon, 6),
            wptype=wtype,
        ))

    for key, value in DEFAULT_SETTINGS.items():
        db.add(models.Setting(key=key, value=value))

    # --- synthetic history + ML model -----------------------------------------
    from .services.demo_ml import build_synthetic_history, train_demo_model

    n = build_synthetic_history(db, city.id, days=730)
    model_meta = None
    try:
        model_meta = train_demo_model(db)
    except Exception as exc:
        model_meta = {"error": str(exc), "fallback_used": True}

    db.commit()

    if os.getenv("HEATSHIELD_EXPORT_SEED", "0") == "1":
        export_seed_files(db)

    return {
        "seeded": True,
        "wards": len(wards),
        "hospitals": len(HOSPITALS),
        "cooling_centres": len(COOLING_CENTRES),
        "water_points": len(WATER_POINTS),
        "historical_days": n,
        "model": model_meta,
    }


def export_seed_files(db) -> dict:
    """Write static GeoJSON + sample CSV into database/seed_data for the repo."""
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    out = {}

    wards = db.query(models.Ward).order_by(models.Ward.code).all()
    fc = {"type": "FeatureCollection", "features": []}
    for w in wards:
        props = {
            "code": w.code, "name": w.name, "population": w.population,
            "elderly_pct": w.elderly_pct, "outdoor_worker_density": w.outdoor_worker_density,
            "informal_housing_pct": w.informal_housing_pct,
            "hospital_access_score": w.hospital_access_score,
            "population_density": w.population_density, "green_cover_pct": w.green_cover_pct,
            "chronic_disease_pct": w.chronic_disease_pct, "elevation_m": w.elevation_m,
            "area_km2": w.area_km2,
        }
        fc["features"].append({"type": "Feature", "properties": props, "geometry": w.geojson["geometry"]})
    out["wards.geojson"] = fc

    def points(model, fields):
        rows = db.query(model).all()
        return {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {f: getattr(r, f) for f in fields},
                 "geometry": {"type": "Point", "coordinates": [r.lon, r.lat]}}
                for r in rows
            ],
        }

    out["hospitals.geojson"] = points(models.Hospital, ["name", "htype", "beds", "emergency_beds", "occupancy_pct"])
    out["cooling_centres.geojson"] = points(models.CoolingCentre, ["name", "capacity", "water_stock_l", "ors_units"])
    out["water_points.geojson"] = points(models.WaterPoint, ["name", "wptype", "status"])

    for fname, payload in out.items():
        (SEED_DIR / fname).write_text(json.dumps(payload, indent=1), encoding="utf-8")

    csv_header = ("ward_code,ward_name,population,elderly_pct,outdoor_worker_density,"
                  "informal_housing_pct,hospital_access_score,population_density,"
                  "green_cover_pct,chronic_disease_pct,elevation_m,area_km2\n")
    rows = []
    for w in wards:
        rows.append(",".join(str(getattr(w, f)) for f in
                             ["code", "name", "population", "elderly_pct", "outdoor_worker_density",
                              "informal_housing_pct", "hospital_access_score", "population_density",
                              "green_cover_pct", "chronic_disease_pct", "elevation_m", "area_km2"]))
    (SEED_DIR / "sample_demographics.csv").write_text(csv_header + "\n".join(rows), encoding="utf-8")
    return out