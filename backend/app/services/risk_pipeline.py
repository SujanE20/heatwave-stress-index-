"""Central risk pipeline: turns weather hours + wards into full risk results.

Pipeline per ward per day:
  city weather (same for every ward) -> day metrics
  -> HTSI -> vulnerability -> health risk (ML or fallback) -> final risk
  (final risk level = daily max air temperature category - see final_risk.py)
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from .. import models
from ..config import RISK_ORDER
from . import demo_ml, geo, thermal, weather as weather_svc
from .actions import generate_city_actions, generate_ward_actions
from .final_risk import final_risk
from .health_risk import compute_health_risk
from .vulnerability import vulnerability_score

IST = ZoneInfo("Asia/Kolkata")


# ---------------------------------------------------------------------------
# Ward-level day metrics
# ---------------------------------------------------------------------------
def ward_hours(ward: models.Ward, city_hours: list) -> list:
    """Ward hours = city hours (weather is city-wide in Mysore, offsets are zero)."""
    off = geo.ward_weather_offsets(ward)
    out = []
    for h in city_hours:
        w = dict(h)
        w["t"] = round(h["t"] + off["temp_offset"], 1)
        w["rh"] = round(min(98.0, max(5.0, h["rh"] + off["rh_offset"])), 1)
        w["wind"] = round(h["wind"] * off["wind_factor"], 1)
        d = thermal.derived_metrics(w["t"], w["rh"], w["wind"], h["solar"], h["cloud"])
        w.update(d)
        w["apparent"] = round(d["hi"], 1)
        out.append(w)
    return out


def ward_days(ward: models.Ward, city_hours: list) -> list:
    """Per-day summaries for one ward (offsets applied), forecast days only."""
    wh = ward_hours(ward, city_hours)
    today = datetime.now(IST).date()
    wh = [h for h in wh if h["date"] >= today]
    return weather_svc.summarize_days(wh)


def compute_ward_day(ward: models.Ward, day: dict, settings: dict) -> dict:
    """Full risk computation for one ward on one forecast day."""
    night = thermal.night_recovery_score(
        day["tmin"], day["night_hi"], day["hot_nights"], day["consecutive_warm_nights"]
    )
    consec = thermal.consecutive_exposure_score(
        day["consecutive_hi_hours"], day["consecutive_high_days"], day["exposure_hours"]
    )
    day = {**day, "night_score": night, "consec_score": consec}

    htsi = thermal.htsi_index(
        day["wbgt_max"], day["hi_max"], day["utci_max"],
        night["score"], consec["score"], settings.get("htsi_weights"),
    )
    vuln = vulnerability_score(ward, settings.get("vuln_weights"))
    ml = demo_ml.predict_from_day(day)
    ml_pred = ml[0] if ml else None  # predict_from_day returns (pct, source) or None
    health = compute_health_risk(ward, day, htsi, vuln, settings, ml_pred)
    final = final_risk(ward, day, htsi, vuln, health, settings)
    return {
        "date": day["date"],
        "day": day,
        "htsi": htsi,
        "vulnerability": vuln,
        "health": health,
        "final": final,
    }


def ward_current(ward: models.Ward, city_weather: dict, settings: dict) -> dict:
    """Current-risk state for a ward: current-hour thermal values + rolling
    night/consecutive context from today's day metrics."""
    days = ward_days(ward, city_weather["hours"])
    day0 = days[0] if days else None
    cur = city_weather["current"]
    off = geo.ward_weather_offsets(ward)
    w = dict(cur)
    w["t"] = round(cur["t"] + off["temp_offset"], 1)
    w["rh"] = round(min(98.0, max(5.0, cur["rh"] + off["rh_offset"])), 1)
    w["wind"] = round(cur["wind"] * off["wind_factor"], 1)
    w.update(thermal.derived_metrics(w["t"], w["rh"], w["wind"], cur["solar"], cur["cloud"]))

    if day0:
        # Risk is a DAY-level statement: use today's full forecast (peak hours
        # included) so the ward risk level is stable across the day instead of
        # swinging with the current clock hour. `current` below still reports
        # the live hourly conditions.
        result = compute_ward_day(ward, day0, settings)
    else:
        night = thermal.night_recovery_score(w["t"] - 8.0, w["hi"], 0, 0)
        consec = thermal.consecutive_exposure_score(0, 0, 0)
        htsi = thermal.htsi_index(w["wbgt"], w["hi"], w["utci_proxy"], night["score"], consec["score"], settings.get("htsi_weights"))
        vuln = vulnerability_score(ward, settings.get("vuln_weights"))
        health = compute_health_risk(ward, {**pseudo_defaults(), "wbgt_max": w["wbgt"], "hi_max": w["hi"], "utci_max": w["utci_proxy"], "rh": w["rh"], "wind": w["wind"], "night_score": night, "consec_score": consec}, htsi, vuln, settings, None)
        final = final_risk(ward, {**pseudo_defaults(), "wbgt_max": w["wbgt"], "hi_max": w["hi"], "utci_max": w["utci_proxy"], "consecutive_high_days": 0}, htsi, vuln, health, settings)
        result = {"date": datetime.now(IST).date(), "day": {"wbgt_max": w["wbgt"], "hi_max": w["hi"], "utci_max": w["utci_proxy"], "rh": w["rh"], "wind": w["wind"], "night_score": night, "consec_score": consec}, "htsi": htsi, "vulnerability": vuln, "health": health, "final": final}

    result["current"] = {
        "t": w["t"], "rh": w["rh"], "wind": w["wind"], "wind_dir": w.get("wind_dir", 0),
        "solar": w["solar"], "cloud": w["cloud"], "precip_prob": w.get("precip_prob", 0),
        "hi": w["hi"], "wbgt": w["wbgt"], "utci_proxy": w["utci_proxy"],
        "apparent": w.get("apparent", w["hi"]),
    }
    result["offsets"] = off
    return result


def pseudo_defaults() -> dict:
    return {
        "tmin": 24.0, "night_hi": 26.0, "hot_nights": 0, "consecutive_warm_nights": 0,
        "exposure_hours": 0, "consecutive_hi_hours": 0, "consecutive_high_days": 0,
        "solar": 0, "cloud": 0, "night_score": {"score": 0}, "consec_score": {"score": 0},
    }


# ---------------------------------------------------------------------------
# City-level aggregation
# ---------------------------------------------------------------------------
def city_context(db, settings: dict) -> dict:
    """Load city + wards + weather once for all endpoints."""
    city = db.query(models.City).get(settings.get("city_id", 1)) or db.query(models.City).first()
    wards = db.query(models.Ward).filter_by(city_id=city.id).order_by(models.Ward.code).all()
    weather = weather_svc.get_city_weather(settings, city.lat, city.lon)
    return {"city": city, "wards": wards, "weather": weather}


def ward_risk_rows(wards: list, weather: dict, settings: dict) -> list:
    """Current-risk state for every ward (all share the same city weather)."""
    return [{"ward": w, "result": ward_current(w, weather, settings)} for w in wards]


def city_summary(db, settings: dict) -> dict:
    ctx = city_context(db, settings)
    city, weather = ctx["city"], ctx["weather"]
    rows = ward_risk_rows(ctx["wards"], weather, settings)

    level_idx = lambda lvl: RISK_ORDER.index(lvl)
    city_idx = max(level_idx(r["result"]["final"]["level"]) for r in rows)
    city_level = RISK_ORDER[city_idx]
    counts = {lvl: 0 for lvl in RISK_ORDER}
    for r in rows:
        counts[r["result"]["final"]["level"]] += 1

    high_risk = [r for r in rows if level_idx(r["result"]["final"]["level"]) >= 3]  # red + maroon
    exposed = [r for r in rows if level_idx(r["result"]["final"]["level"]) >= 2]   # orange+
    people_exposed = sum(r["ward"].population for r in exposed)
    vuln_exposed = sum(
        int(r["ward"].population * (r["ward"].elderly_pct + 8.0) / 100.0)
        for r in exposed
    )  # elderly + outdoor-worker share estimate

    # population-weighted health-demand increase
    total_pop = sum(r["ward"].population for r in rows) or 1
    demand = sum(r["result"]["health"]["demand_increase_pct"]["predicted"] * r["ward"].population for r in rows) / total_pop
    demand_min = sum(r["result"]["health"]["demand_increase_pct"]["min"] * r["ward"].population for r in rows) / total_pop
    demand_max = sum(r["result"]["health"]["demand_increase_pct"]["max"] * r["ward"].population for r in rows) / total_pop

    cur = weather["current"]
    night0 = thermal.night_recovery_score(weather["daily"][0]["tmin"], weather["daily"][0]["night_hi"], weather["daily"][0]["hot_nights"], weather["daily"][0]["consecutive_warm_nights"]) if weather["daily"] else {"score": 0}
    consec0 = thermal.consecutive_exposure_score(weather["daily"][0]["consecutive_hi_hours"], weather["daily"][0]["consecutive_high_days"], weather["daily"][0]["exposure_hours"]) if weather["daily"] else {"score": 0}
    htsi_city = thermal.htsi_index(cur["wbgt"], cur["hi"], cur["utci_proxy"], night0["score"], consec0["score"], settings.get("htsi_weights"))

    active_alerts = db.query(models.Alert).filter(models.Alert.status == "Draft").count()
    plan = db.query(models.HeatActionPlan).order_by(models.HeatActionPlan.triggered_at.desc()).first()

    # upcoming severe window (next day with WBGT >= 30)
    severe_window = None
    if len(weather["daily"]) >= 2:
        for d in weather["daily"][1:]:
            hours = [h for h in weather["hours"] if h["date"] == d["date"]]
            hot = [h for h in hours if h["wbgt"] >= 30.0]
            if hot:
                severe_window = {
                    "date": str(d["date"]),
                    "start": f"{min(h['hour'] for h in hot):02d}:00",
                    "end": f"{max(h['hour'] for h in hot) + 1:02d}:00",
                    "peak_wbgt": d["wbgt_max"],
                }
                break

    return {
        "city": {"id": city.id, "name": city.name, "state": city.state, "lat": city.lat, "lon": city.lon},
        "weather": {"provider": weather["provider"], "scenario": weather["scenario"], "is_demo": weather["is_demo"], "fallback": weather["fallback"]},
        "current_conditions": {
            "t": cur["t"], "rh": cur["rh"], "wind": cur["wind"], "wind_dir": cur.get("wind_dir", 0),
            "solar": cur["solar"], "cloud": cur["cloud"], "precip_prob": cur.get("precip_prob", 0),
            "hi": cur["hi"], "wbgt": cur["wbgt"], "utci_proxy": cur["utci_proxy"],
            "apparent": cur.get("apparent", cur["hi"]),
            "htsi": htsi_city["score"],
            "htsi_components": htsi_city["components"],
            "observed_at": cur["ts"].isoformat(),
        },
        "risk": {
            "city_level": city_level,
            "city_label": {"green": "Low", "yellow": "Moderate", "orange": "High", "red": "Very High", "maroon": "Extreme"}[city_level],
            "ward_counts": counts,
            "high_risk_wards": len(high_risk),
            "people_exposed": people_exposed,
            "vulnerable_exposed": vuln_exposed,
            "high_risk_ward_names": [r["ward"].name for r in high_risk],
        },
        "health": {
            "demand_increase_pct": round(demand, 1),
            "demand_range_pct": f"{demand_min:.0f}-{demand_max:.0f}",
            "label": "Predicted increase in health demand (decision-support estimate)",
        },
        "alerts": {"active": active_alerts},
        "severe_window": severe_window,
        "action_plan": None if plan is None else {
            "id": plan.id, "status": plan.status, "triggered_at": plan.triggered_at.isoformat(),
            "summary": plan.summary,
        },
        "recommended_actions": generate_city_actions(city_level, {}),
        "wards": [
            {
                "id": r["ward"].id, "code": r["ward"].code, "name": r["ward"].name,
                "level": r["result"]["final"]["level"], "label": r["result"]["final"]["label"],
                "score": r["result"]["final"]["score"], "htsi": r["result"]["htsi"]["score"],
                "vulnerability": r["result"]["vulnerability"]["score"],
                "population": r["ward"].population,
                "centroid_lat": r["ward"].centroid_lat, "centroid_lon": r["ward"].centroid_lon,
            }
            for r in rows
        ],
        "disclaimers": [
            "HeatShield is a decision-support prototype. Heat-stress and health-risk estimates must be calibrated and validated using local meteorological and public-health data before operational deployment.",
            "Estimated WBGT is not a replacement for a calibrated onsite WBGT instrument.",
            "UTCI Proxy is not official UTCI if a validated UTCI implementation is not used.",
            "No individual health data is displayed; only ward-level aggregated estimates are used.",
        ],
    }