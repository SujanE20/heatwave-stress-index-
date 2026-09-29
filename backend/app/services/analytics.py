"""Analytics / trends assembly for the Forecast & Analytics page."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .. import models
from ..config import temperature_level
from . import thermal
from .risk_pipeline import city_context, ward_days, compute_ward_day

IST = ZoneInfo("Asia/Kolkata")


def get_trends(db, settings: dict) -> dict:
    ctx = city_context(db, settings)
    city, wards, weather = ctx["city"], ctx["wards"], ctx["weather"]
    today = datetime.now(IST).date()

    # --- five-day city forecast chart ---------------------------------------
    forecast = []
    for d in weather["daily"]:
        night = thermal.night_recovery_score(d["tmin"], d["night_hi"], d["hot_nights"], d["consecutive_warm_nights"])
        consec = thermal.consecutive_exposure_score(d["consecutive_hi_hours"], d["consecutive_high_days"], d["exposure_hours"])
        htsi = thermal.htsi_index(d["wbgt_max"], d["hi_max"], d["utci_max"], night["score"], consec["score"], settings.get("htsi_weights"))
        # risk level follows the day's max air temperature (city-wide)
        level = temperature_level(d["tmax"])
        forecast.append({
            "date": str(d["date"]),
            "tmax": d["tmax"], "tmin": d["tmin"],
            "hi_max": d["hi_max"], "wbgt_max": d["wbgt_max"],
            "utci_max": d["utci_max"], "htsi": htsi["score"],
            "risk_level": level["key"], "risk_label": level["label"],
        })

    # --- hourly forecast series for charts -----------------------------------
    hourly = [
        {
            "ts": h["ts"].isoformat(),
            "hour": f"{h['hour']:02d}:00",
            "t": h["t"], "apparent": h.get("apparent", h["hi"]),
            "hi": h["hi"], "wbgt": h["wbgt"], "utci_proxy": h["utci_proxy"],
        }
        for h in weather["hours"]
    ]

    # --- ward comparison (current risk, sorted worst first) ------------------
    ward_rows = []
    for w in wards:
        days = ward_days(w, weather["hours"])
        day0 = days[0] if days else None
        if day0 is None:
            continue
        res = compute_ward_day(w, day0, settings)
        ward_rows.append({
            "id": w.id, "code": w.code, "name": w.name,
            "population": w.population,
            "risk_level": res["final"]["level"], "risk_label": res["final"]["label"],
            "risk_score": res["final"]["score"],
            "htsi": res["htsi"]["score"],
            "vulnerability": res["vulnerability"]["score"],
            "health_score": res["health"]["score"],
            "wbgt_max": day0["wbgt_max"],
            "consecutive_days": day0["consecutive_high_days"],
        })
    ward_rows.sort(key=lambda r: r["risk_score"], reverse=True)

    # --- vulnerability vs thermal scatter ------------------------------------
    scatter = [
        {"ward": r["name"], "x": r["vulnerability"], "y": r["htsi"], "risk": r["risk_level"]}
        for r in ward_rows
    ]

    # --- historical hospital load (last 120 days, weekly average) ------------
    history_rows = (
        db.query(models.HistoricalDaily)
        .filter(models.HistoricalDaily.city_id == city.id, models.HistoricalDaily.d >= today - timedelta(days=120))
        .order_by(models.HistoricalDaily.d)
        .all()
    )
    history = [
        {
            "date": str(r.d), "load_increase_pct": r.hospital_load_increase_pct,
            "heat_admissions": r.heat_admissions, "wbgt_max": r.wbgt_max, "tmax": r.tmax,
        }
        for r in history_rows
    ]

    # --- alert history --------------------------------------------------------
    alerts = db.query(models.Alert).order_by(models.Alert.ts.desc()).limit(50).all()
    alert_history = [
        {
            "id": a.id, "ts": a.ts.isoformat(), "ward_id": a.ward_id,
            "severity": a.severity, "title": a.title, "status": a.status,
            "channels": a.channels,
        }
        for a in alerts
    ]

    # --- intervention effectiveness (demo placeholder) ------------------------
    intervention = {
        "note": "Placeholder derived from demo data - to be replaced with real HAP evaluation metrics.",
        "series": [
            {"day": "Day -3", "excess_health_demand_pct": 6},
            {"day": "Day -2", "excess_health_demand_pct": 11},
            {"day": "Day -1", "excess_health_demand_pct": 18},
            {"day": "Day 0 (HAP active)", "excess_health_demand_pct": 24},
            {"day": "Day +1", "excess_health_demand_pct": 21},
            {"day": "Day +2", "excess_health_demand_pct": 15},
            {"day": "Day +3", "excess_health_demand_pct": 9},
        ],
        "estimated_effect": "Hypothetical model: alerts + cooling centres reduce peak demand growth by ~25% after 48h.",
    }

    return {
        "forecast": forecast,
        "hourly": hourly,
        "ward_comparison": ward_rows,
        "scatter": scatter,
        "hospital_load_history": history,
        "alert_history": alert_history,
        "intervention_effectiveness": intervention,
        "weather": {"provider": weather["provider"], "is_demo": weather["is_demo"], "fallback": weather["fallback"]},
    }