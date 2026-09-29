"""Tests for final-risk (temperature bands), health risk and actions."""
from app.config import DEFAULT_SETTINGS
from app.models import Ward
from app.services.actions import generate_ward_actions
from app.services.final_risk import final_risk
from app.services.health_risk import compute_health_risk
from app.services.risk_pipeline import pseudo_defaults


def make_ward(**over):
    base = dict(
        id=2, city_id=1, code="W-02", name="Test Ward", population=25000,
        elderly_pct=12.0, outdoor_worker_density=2000.0, informal_housing_pct=15.0,
        hospital_access_score=70.0, population_density=12000.0, green_cover_pct=25.0,
        chronic_disease_pct=8.0, elevation_m=650.0, area_km2=1.5,
        centroid_lat=15.36, centroid_lon=75.12, geojson={},
    )
    base.update(over)
    return Ward(**base)


def vuln(score):
    return {
        "score": score,
        "components": {"elderly": 50, "outdoor_workers": 50, "poor_housing": 50,
                        "hospital_access": 50, "population_density": 50,
                        "low_green_cover": 50, "chronic_disease": 50},
        "contributions": {},
    }


def htsi(score):
    return {"score": score, "components": {}}


def health(score, band="Low"):
    return {"score": score, "hospitalization_risk": band, "demand_increase_pct": {"predicted": 5},
            "mortality_risk_band": "Low", "confidence": "High", "drivers": [], "inputs": {}}


def day(tmax: float = 38.0, consecutive=0):
    d = pseudo_defaults()
    d.update({
        "tmax": tmax, "tmin": 27.0, "rh": 60.0, "wind": 2.0, "solar": 800.0, "cloud": 20.0,
        "hi_max": 48.0, "wbgt_max": 31.0, "utci_max": 45.0,
        "consecutive_high_days": consecutive, "hot_night": True,
    })
    return d


def test_temperature_bands_drive_level():
    """Low 25-30 | Moderate 30-35 | High 35-40 | Very High 40-44 | Extreme 45+."""
    cases = [
        (28.0, "green"), (30.0, "green"), (32.0, "yellow"), (35.0, "yellow"),
        (37.0, "orange"), (40.0, "orange"), (42.0, "red"), (44.9, "red"),
        (45.0, "maroon"), (47.0, "maroon"),
    ]
    for tmax, expected in cases:
        r = final_risk(make_ward(), day(tmax=tmax), htsi(50), vuln(50), health(50), DEFAULT_SETTINGS)
        assert r["level"] == expected, f"tmax {tmax} -> {r['level']}, expected {expected}"


def test_level_does_not_vary_with_vulnerability():
    """All wards share the same city temperature, so the displayed level is
    identical regardless of ward demographics; vulnerability stays a detail."""
    low = final_risk(make_ward(), day(tmax=37.0), htsi(70), vuln(20), health(30), DEFAULT_SETTINGS)
    high = final_risk(make_ward(), day(tmax=37.0), htsi(70), vuln(95), health(90), DEFAULT_SETTINGS)
    assert low["level"] == high["level"] == "orange"
    assert low["escalations"] == high["escalations"] == []


def test_temperature_score_moves_with_tmax():
    assert final_risk(make_ward(), day(tmax=25.0), htsi(0), vuln(0), health(0), DEFAULT_SETTINGS)["score"] == 0.0
    assert final_risk(make_ward(), day(tmax=35.0), htsi(0), vuln(0), health(0), DEFAULT_SETTINGS)["score"] == 50.0
    assert final_risk(make_ward(), day(tmax=45.0), htsi(0), vuln(0), health(0), DEFAULT_SETTINGS)["score"] == 100.0


def test_explanation_present_and_temperature_aware():
    r = final_risk(make_ward(), day(tmax=42.0), htsi(70), vuln(70), health(60), DEFAULT_SETTINGS)
    assert r["level"] == "red"
    assert "because" in r["explanation"]
    assert "42" in r["explanation"]
    assert "Very High" in r["explanation"]
    assert "Decision-support estimate" in r["explanation"]


def test_health_risk_bands_and_safety():
    ward = make_ward()
    d = day(consecutive=2)
    d["night_score"] = {"score": 80}
    d["consec_score"] = {"score": 80}
    res = compute_health_risk(ward, d, htsi(80), vuln(80), DEFAULT_SETTINGS, ml_prediction=None)
    assert res["hospitalization_risk"] in ("High", "Very High", "Extreme")
    assert res["confidence"] == "Medium"
    assert "decision-support" in " ".join(res["safety_notes"]).lower() or "calibration" in " ".join(res["safety_notes"]).lower()
    assert res["demand_increase_pct"]["predicted"] >= 10
    assert res["demand_increase_pct"]["max"] > res["demand_increase_pct"]["min"]
    assert len(res["drivers"]) >= 3
    total = sum(d["contribution_pct"] for d in res["drivers"])
    assert 99.0 <= total <= 101.0


def test_health_risk_ml_blend_raises_confidence():
    ward = make_ward()
    d = day()
    d["night_score"] = {"score": 40}
    d["consec_score"] = {"score": 40}
    rule = compute_health_risk(ward, d, htsi(50), vuln(50), DEFAULT_SETTINGS, ml_prediction=None)
    ml = compute_health_risk(ward, d, htsi(50), vuln(50), DEFAULT_SETTINGS, ml_prediction=30.0)
    assert ml["confidence"] == "High"
    assert ml["demand_increase_pct"]["source"].startswith("RandomForest")


def test_actions_by_level():
    ward = make_ward()
    yellow = generate_ward_actions(ward, "yellow")
    red = generate_ward_actions(ward, "red")
    assert all(a["status"] == "Pending" for a in red)
    assert all(a["department"] for a in red)
    assert all(a["priority"] in ("Immediate", "Today", "Monitor") for a in red)
    titles_red = {a["title"] for a in red}
    assert "Open cooling centres" in titles_red
    assert "Shift outdoor work to 6 AM-10 AM and after 4 PM" in titles_red
    assert len(red) > len(yellow)
