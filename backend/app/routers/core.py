"""Core API: cities, wards, dashboard, weather, risk, actions, resources, analytics."""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services import demo_ml, geo, weather as weather_svc
from ..services.actions import generate_city_actions, generate_ward_actions
from ..services.risk_pipeline import (
    city_context, city_summary, compute_ward_day, ward_current, ward_days,
)
from ..services.settings_svc import load_settings

router = APIRouter(prefix="/api/v1", tags=["core"])


def _get_ward(db: Session, ward_id: int) -> models.Ward:
    ward = db.get(models.Ward, ward_id)
    if ward is None:
        raise HTTPException(status_code=404, detail=f"Ward {ward_id} not found")
    return ward


# ---------------------------------------------------------------------------
# Cities / wards
# ---------------------------------------------------------------------------
@router.get("/cities", response_model=list[schemas.CityOut])
def list_cities(db: Session = Depends(get_db)):
    return db.query(models.City).all()


@router.get("/wards")
def list_wards(include_geometry: bool = Query(False), db: Session = Depends(get_db)):
    settings = load_settings(db)
    ctx = city_context(db, settings)
    out = []
    for w in ctx["wards"]:
        cur = ward_current(w, ctx["weather"], settings)
        item = {
            "id": w.id, "city_id": w.city_id, "code": w.code, "name": w.name,
            "population": w.population, "centroid_lat": w.centroid_lat, "centroid_lon": w.centroid_lon,
            "elderly_pct": w.elderly_pct, "outdoor_worker_density": w.outdoor_worker_density,
            "informal_housing_pct": w.informal_housing_pct,
            "hospital_access_score": w.hospital_access_score,
            "population_density": w.population_density, "green_cover_pct": w.green_cover_pct,
            "chronic_disease_pct": w.chronic_disease_pct, "elevation_m": w.elevation_m,
            "area_km2": w.area_km2,
            "risk": cur["final"],
        }
        if include_geometry:
            item["geojson"] = w.geojson
        out.append(item)
    return out


@router.get("/wards/{ward_id}", response_model=schemas.WardRiskOut)
def ward_detail(ward_id: int, db: Session = Depends(get_db)):
    settings = load_settings(db)
    ward = _get_ward(db, ward_id)
    ctx = city_context(db, settings)
    result = ward_current(ward, ctx["weather"], settings)

    hospitals = [{"id": h.id, "name": h.name, "htype": h.htype, "lat": h.lat, "lon": h.lon,
                  "beds": h.beds, "emergency_beds": h.emergency_beds, "occupancy_pct": h.occupancy_pct}
                 for h in db.query(models.Hospital).all()]
    cooling = [{"id": c.id, "name": c.name, "lat": c.lat, "lon": c.lon, "capacity": c.capacity,
                "current_occupancy": c.current_occupancy}
               for c in db.query(models.CoolingCentre).all()]
    water = [{"id": p.id, "name": p.name, "lat": p.lat, "lon": p.lon, "wptype": p.wptype}
             for p in db.query(models.WaterPoint).all()]

    n_h, d_h = geo.nearest(hospitals, ward.centroid_lat, ward.centroid_lon)
    n_c, d_c = geo.nearest(cooling, ward.centroid_lat, ward.centroid_lon)
    n_w, d_w = geo.nearest(water, ward.centroid_lat, ward.centroid_lon)

    actions = generate_ward_actions(ward, result["final"]["level"], {"vulnerability": result["vulnerability"]})

    return {
        "ward_id": ward.id, "ward_code": ward.code, "ward_name": ward.name,
        "date": str(result["date"]),
        "current": result["current"],
        "htsi": result["htsi"],
        "vulnerability": result["vulnerability"],
        "health": result["health"],
        "final": result["final"],
        "day": result["day"],
        "actions": actions,
        "nearest": {
            "hospital": {**n_h, "distance_km": d_h},
            "cooling_centre": {**n_c, "distance_km": d_c},
            "water_point": {**n_w, "distance_km": d_w},
        },
    }


@router.get("/wards/{ward_id}/forecast")
def ward_forecast(ward_id: int, db: Session = Depends(get_db)):
    settings = load_settings(db)
    ward = _get_ward(db, ward_id)
    ctx = city_context(db, settings)
    days = ward_days(ward, ctx["weather"]["hours"])
    daily = []
    for d in days:
        res = compute_ward_day(ward, d, settings)
        daily.append({
            "date": str(d["date"]),
            "tmax": d["tmax"], "tmin": d["tmin"], "rh": d["rh"], "wind": d["wind"],
            "hi_max": d["hi_max"], "wbgt_max": d["wbgt_max"], "utci_max": d["utci_max"],
            "exposure_hours": d["exposure_hours"], "consecutive_days": d["consecutive_high_days"],
            "htsi": res["htsi"]["score"],
            "risk_level": res["final"]["level"], "risk_label": res["final"]["label"],
            "health_demand": res["health"]["demand_increase_pct"],
            "mortality_band": res["health"]["mortality_risk_band"],
            "confidence": res["health"]["confidence"],
        })
    hourly = [
        {"ts": h["ts"].isoformat(), "hour": h["hour"], "t": h["t"], "rh": h["rh"], "wind": h["wind"],
         "solar": h["solar"], "hi": h["hi"], "wbgt": h["wbgt"], "utci_proxy": h["utci_proxy"]}
        for h in ctx["weather"]["hours"][:120]
    ]
    return {"ward_id": ward.id, "ward_code": ward.code, "ward_name": ward.name,
            "daily": daily, "hourly": hourly}


# ---------------------------------------------------------------------------
# Dashboard / weather / risk
# ---------------------------------------------------------------------------
@router.get("/dashboard/summary", response_model=schemas.CitySummaryOut)
def dashboard_summary(db: Session = Depends(get_db)):
    settings = load_settings(db)
    return city_summary(db, settings)


@router.get("/weather/current")
def weather_current(db: Session = Depends(get_db)):
    settings = load_settings(db)
    ctx = city_context(db, settings)
    cur = ctx["weather"]["current"]
    return {
        "provider": ctx["weather"]["provider"],
        "is_demo": ctx["weather"]["is_demo"],
        "fallback": ctx["weather"]["fallback"],
        "scenario": ctx["weather"]["scenario"],
        "observed_at": cur["ts"].isoformat(),
        "temperature_2m": cur["t"],
        "relative_humidity_2m": cur["rh"],
        "wind_speed_10m": cur["wind"],
        "shortwave_radiation": cur["solar"],
        "cloud_cover": cur["cloud"],
        "precipitation_probability": cur.get("precip_prob", 0),
        "heat_index": cur["hi"],
        "estimated_wbgt": cur["wbgt"],
        "utci_proxy": cur["utci_proxy"],
        "apparent_temperature": cur.get("apparent", cur["hi"]),
    }


@router.get("/weather/forecast", response_model=schemas.WeatherResponseOut)
def weather_forecast(db: Session = Depends(get_db)):
    settings = load_settings(db)
    ctx = city_context(db, settings)
    return {
        "provider": ctx["weather"]["provider"],
        "is_demo": ctx["weather"]["is_demo"],
        "fallback": ctx["weather"]["fallback"],
        "scenario": ctx["weather"]["scenario"],
        "current": ctx["weather"]["current"],
        "daily": ctx["weather"]["daily"],
        "hours": [
            {"ts": h["ts"].isoformat(), "hour": f"{h['hour']:02d}:00", "t": h["t"], "rh": h["rh"],
             "wind": h["wind"], "solar": h["solar"], "cloud": h["cloud"],
             "hi": h["hi"], "wbgt": h["wbgt"], "utci_proxy": h["utci_proxy"]}
            for h in ctx["weather"]["hours"]
        ],
    }


@router.get("/risk/ward/{ward_id}", response_model=schemas.WardRiskOut)
def risk_ward(ward_id: int, db: Session = Depends(get_db)):
    settings = load_settings(db)
    ward = _get_ward(db, ward_id)
    ctx = city_context(db, settings)
    result = ward_current(ward, ctx["weather"], settings)
    actions = generate_ward_actions(ward, result["final"]["level"], {"vulnerability": result["vulnerability"]})
    return {
        "ward_id": ward.id, "ward_code": ward.code, "ward_name": ward.name,
        "date": str(result["date"]),
        "current": result["current"],
        "htsi": result["htsi"],
        "vulnerability": result["vulnerability"],
        "health": result["health"],
        "final": result["final"],
        "day": result["day"],
        "actions": actions,
        "nearest": {},
    }


@router.get("/risk/city-summary")
def risk_city_summary(db: Session = Depends(get_db)):
    settings = load_settings(db)
    summary = city_summary(db, settings)
    return {
        "city_risk_level": summary["risk"]["city_level"],
        "city_risk_label": summary["risk"]["city_label"],
        "ward_counts": summary["risk"]["ward_counts"],
        "high_risk_wards": summary["risk"]["high_risk_wards"],
        "people_exposed": summary["risk"]["people_exposed"],
        "vulnerable_exposed": summary["risk"]["vulnerable_exposed"],
        "demand_increase_pct": summary["health"]["demand_increase_pct"],
        "disclaimers": summary["disclaimers"],
    }


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
@router.get("/actions/recommendations")
def action_recommendations(
    ward_id: int | None = Query(None),
    level: str | None = Query(None),
    db: Session = Depends(get_db),
):
    settings = load_settings(db)
    if ward_id is not None:
        ward = _get_ward(db, ward_id)
        ctx = city_context(db, settings)
        result = ward_current(ward, ctx["weather"], settings)
        return generate_ward_actions(ward, result["final"]["level"], {"vulnerability": result["vulnerability"]})
    if level:
        wards = db.query(models.Ward).all()
        return [a for w in wards for a in generate_ward_actions(w, level)]
    summary = city_summary(db, settings)
    return summary["recommended_actions"]


@router.post("/actions/trigger-heat-action-plan", response_model=schemas.MessageOut)
def trigger_heat_action_plan(payload: schemas.TriggerPlanIn, db: Session = Depends(get_db)):
    settings = load_settings(db)
    summary = city_summary(db, settings)
    city_id = summary["city"]["id"]
    level = summary["risk"]["city_level"]
    plan = models.HeatActionPlan(
        city_id=city_id,
        triggered_by=payload.triggered_by,
        status="Active",
        summary=(
            f"Heat Action Plan triggered. City risk: {summary['risk']['city_label']} "
            f"({summary['risk']['high_risk_wards']} high-risk wards, "
            f"{summary['risk']['people_exposed']:,} people exposed). "
            f"Estimated demand increase: {summary['health']['demand_increase_pct']}%."
        ),
    )
    db.add(plan)
    # mark matching city actions In Progress
    for a in summary["recommended_actions"]:
        item = models.ActionItem(
            ward_id=None, risk_level=level, category=a["title"],
            title=a["title"], department=a["department"], priority=a["priority"],
            reason="Triggered via Heat Action Plan", status="In Progress",
        )
        db.add(item)
    db.commit()
    return {"message": "Heat Action Plan triggered", "detail": {"plan_id": plan.id, "summary": plan.summary}}


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------
@router.get("/resources/hospitals")
def resources_hospitals(db: Session = Depends(get_db)):
    settings = load_settings(db)
    ctx = city_context(db, settings)
    summary = city_summary(db, settings)
    hospitals = db.query(models.Hospital).all()
    wards = ctx["wards"]
    out = []
    for h in hospitals:
        # expected heat admissions next 3-5 days from nearby exposed wards
        near = []
        for w in wards:
            d = geo.haversine_km(h.lat, h.lon, w.centroid_lat, w.centroid_lon)
            if d <= 6.0:
                near.append((w, d))
        heat_admissions = 0
        for w, d in near:
            ward_rows = [r for r in summary["wards"] if r["id"] == w.id]
            if not ward_rows:
                continue
            rl = ward_rows[0]["level"]
            weight = 1.0 if rl in ("red", "maroon") else (0.5 if rl == "orange" else 0.1)
            heat_admissions += int(w.population * 0.0008 * weight * (1.1 - min(0.6, d / 10.0)))
        out.append({
            "id": h.id, "name": h.name, "type": h.htype, "lat": h.lat, "lon": h.lon,
            "beds": h.beds, "emergency_beds": h.emergency_beds,
            "available_emergency_beds": max(0, h.emergency_beds - int(h.emergency_beds * h.occupancy_pct / 100)),
            "occupancy_pct": h.occupancy_pct, "has_icu": h.has_icu,
            "ors_units": h.ors_units, "iv_fluids_units": h.iv_fluids_units,
            "expected_heat_admissions_3_5d": heat_admissions,
            "note": "Simulated capacity and expected admissions - decision-support estimate.",
        })
    return out


@router.get("/resources/cooling-centres")
def resources_cooling_centres(db: Session = Depends(get_db)):
    centres = db.query(models.CoolingCentre).all()
    out = []
    for c in centres:
        occupancy_pct = round(c.current_occupancy / max(1, c.capacity) * 100, 1)
        out.append({
            "id": c.id, "name": c.name, "lat": c.lat, "lon": c.lon,
            "capacity": c.capacity, "current_occupancy": c.current_occupancy,
            "occupancy_pct": occupancy_pct, "water_stock_l": c.water_stock_l,
            "ors_units": c.ors_units, "opens": c.opens, "closes": c.closes,
            "hours_remaining_today": "Until " + c.closes,
            "note": "Simulated occupancy and stock levels for demo.",
        })
    return out


@router.get("/resources/water-points")
def resources_water_points(db: Session = Depends(get_db)):
    return [
        {"id": p.id, "name": p.name, "lat": p.lat, "lon": p.lon, "type": p.wptype, "status": p.status}
        for p in db.query(models.WaterPoint).all()
    ]


@router.get("/resources/ward-coverage")
def resources_ward_coverage(db: Session = Depends(get_db)):
    """Transparent rule: vulnerable residents exposed + distance to cooling centre
    => recommendation to open a temporary cooling centre."""
    settings = load_settings(db)
    ctx = city_context(db, settings)
    hospitals = [{"id": h.id, "name": h.name, "lat": h.lat, "lon": h.lon} for h in db.query(models.Hospital).all()]
    cooling = [{"id": c.id, "name": c.name, "lat": c.lat, "lon": c.lon, "capacity": c.capacity} for c in db.query(models.CoolingCentre).all()]
    out = []
    for w in ctx["wards"]:
        result = ward_current(w, ctx["weather"], settings)
        n_c, d_c = geo.nearest(cooling, w.centroid_lat, w.centroid_lon)
        vulnerable = int(w.population * (w.elderly_pct + 8.0) / 100.0)
        lvl = result["final"]["level"]
        needs_cc = lvl in ("red", "maroon") and d_c > 2.0
        out.append({
            "ward_id": w.id, "ward_code": w.code, "ward_name": w.name,
            "vulnerable_exposed": vulnerable,
            "risk_level": lvl, "risk_label": result["final"]["label"],
            "nearest_cooling_centre": n_c["name"], "distance_km": d_c,
            "recommendation": (
                f"Ward {w.code} has {vulnerable:,} vulnerable residents exposed to "
                f"{result['final']['label']} risk and the nearest cooling centre is {d_c} km away. "
                f"Recommend opening a temporary cooling centre at Ward Community Hall."
                if needs_cc else
                "Existing cooling centre coverage is adequate."
            ),
        })
    return out


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
@router.get("/analytics/trends")
def analytics_trends(db: Session = Depends(get_db)):
    from ..services.analytics import get_trends

    settings = load_settings(db)
    return get_trends(db, settings)


# ---------------------------------------------------------------------------
# Sample CSV template (admin helper)
# ---------------------------------------------------------------------------
@router.get("/admin/sample-csv")
def sample_csv():
    header = ("ward_code,ward_name,population,elderly_pct,outdoor_worker_density,"
              "informal_housing_pct,hospital_access_score,population_density,"
              "green_cover_pct,chronic_disease_pct,elevation_m,area_km2\n")
    sample = ("W-01,Vidyanagar,28500,12.4,1800,18.5,72,12400,22.1,7.8,655,2.30\n"
              "W-02,Keshwapur,31200,15.1,2400,26.0,55,15600,14.5,9.2,642,2.00\n")
    return {
        "filename": "sample_demographics.csv",
        "content": header + sample,
        "columns": [c.strip() for c in header.split(",")],
    }