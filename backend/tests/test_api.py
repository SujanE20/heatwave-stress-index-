"""API integration tests (FastAPI TestClient against seeded in-memory DB)."""
import json


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "up"


def test_cities(client):
    r = client.get("/api/v1/cities")
    assert r.status_code == 200
    cities = r.json()
    assert any(c["name"] == "Mysore" for c in cities)


def test_wards_list(client):
    r = client.get("/api/v1/wards")
    assert r.status_code == 200
    wards = r.json()
    assert len(wards) == 15
    assert all(w["code"].startswith("W-") for w in wards)
    assert all("risk" in w for w in wards)


def test_ward_detail(client):
    r = client.get("/api/v1/wards/1")
    assert r.status_code == 200
    w = r.json()
    for key in ("htsi", "vulnerability", "health", "final", "current", "actions", "nearest"):
        assert key in w
    assert w["final"]["explanation"]
    assert w["nearest"]["hospital"]["distance_km"] > 0


def test_ward_404(client):
    r = client.get("/api/v1/wards/9999")
    assert r.status_code == 404


def test_ward_forecast(client):
    r = client.get("/api/v1/wards/1/forecast")
    assert r.status_code == 200
    body = r.json()
    assert len(body["daily"]) == 5  # five forecast days
    for d in body["daily"]:
        assert d["risk_level"] in ("green", "yellow", "orange", "red", "maroon")


def test_dashboard_summary(client):
    r = client.get("/api/v1/dashboard/summary")
    assert r.status_code == 200
    s = r.json()
    assert s["city"]["name"] == "Mysore"
    assert s["risk"]["city_level"] in ("green", "yellow", "orange", "red", "maroon")
    assert s["risk"]["ward_counts"]["red"] >= 0
    assert s["current_conditions"]["wbgt"] > 0
    assert len(s["disclaimers"]) >= 4
    assert s["health"]["label"].startswith("Predicted increase")
    assert len(s["wards"]) == 15


def test_severe_scenario_is_high_everywhere(client):
    """Default demo scenario (~37 °C max) classifies every ward High (35-40 °C),
    because Mysore weather is city-wide: no ward gets a different temperature."""
    s = client.get("/api/v1/dashboard/summary").json()
    tmaxs = [w["score"] for w in s["wards"]]  # scores derive from tmax
    counts = s["risk"]["ward_counts"]
    # all 15 wards share the same daily max temperature -> same level
    assert counts["orange"] == 15
    assert s["risk"]["city_level"] == "orange"
    levels = {w["level"] for w in s["wards"]}
    assert levels == {"orange"}
    # temperature-derived scores are (nearly) identical city-wide
    assert max(tmaxs) - min(tmaxs) < 0.5


def test_weather_endpoints(client):
    cur = client.get("/api/v1/weather/current")
    assert cur.status_code == 200
    c = cur.json()
    assert c["is_demo"] is True
    assert c["temperature_2m"] > 20
    assert c["estimated_wbgt"] > 0
    fc = client.get("/api/v1/weather/forecast")
    assert fc.status_code == 200
    assert len(fc.json()["daily"]) == 5


def test_risk_endpoints(client):
    r = client.get("/api/v1/risk/ward/1")
    assert r.status_code == 200
    assert r.json()["final"]["score"] > 0
    s = client.get("/api/v1/risk/city-summary")
    assert s.status_code == 200
    assert s.json()["city_risk_level"] in ("green", "yellow", "orange", "red", "maroon")


def test_actions_and_trigger_plan(client):
    r = client.get("/api/v1/actions/recommendations")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    r = client.post("/api/v1/actions/trigger-heat-action-plan", json={"triggered_by": "Test Officer"})
    assert r.status_code == 200
    assert r.json()["detail"]["plan_id"] > 0


def test_resources(client):
    h = client.get("/api/v1/resources/hospitals").json()
    assert len(h) == 4
    assert all(x["expected_heat_admissions_3_5d"] >= 0 for x in h)
    cc = client.get("/api/v1/resources/cooling-centres").json()
    assert len(cc) == 6
    cov = client.get("/api/v1/resources/ward-coverage").json()
    assert len(cov) == 15
    assert all("recommendation" in x for x in cov)


def test_analytics_trends(client):
    r = client.get("/api/v1/analytics/trends")
    assert r.status_code == 200
    t = r.json()
    assert len(t["forecast"]) == 5
    assert len(t["ward_comparison"]) == 15
    assert len(t["scatter"]) == 15
    assert len(t["hospital_load_history"]) >= 100
    assert "intervention_effectiveness" in t


def test_alerts_generate_and_send(client):
    r = client.post("/api/v1/alerts/generate", json={"min_level": "orange"})
    assert r.status_code == 200
    body = r.json()
    assert body["generated"] >= 1
    first = body["alerts"][0]
    assert "ಬಿಸಿ" in first["body_kn"]  # Kannada content present
    assert "HEAT ALERT" in first["body_en"]
    alert_id = first["id"]
    r = client.post("/api/v1/alerts/send", json={"alert_ids": [alert_id], "channels": ["sms", "whatsapp"]})
    assert r.status_code == 200
    assert r.json()["sent"] == 1
    # verify status updated
    alerts = client.get("/api/v1/alerts").json()
    assert any(a["id"] == alert_id and a["status"] == "Sent (simulated)" for a in alerts)


def test_alert_list_has_sms_whatsapp_previews(client):
    r = client.post("/api/v1/alerts/generate", json={"min_level": "orange"})
    first_id = r.json()["alerts"][0]["id"]
    alerts = client.get("/api/v1/alerts").json()
    a = next(x for x in alerts if x["id"] == first_id)
    assert a["sms"].startswith("HS-ALERT")
    assert a["whatsapp"].startswith("*")
    assert "HEAT" in a["whatsapp"]  # severity header preserved (DANGEROUS/EXTREME HEAT)


def test_send_is_drafts_only_and_idempotent(client):
    """Sending must only deliver Draft alerts, never re-send already-sent ones."""
    # other tests may leave drafts behind, so measure the delta relative to now
    drafts_before = [a["id"] for a in client.get("/api/v1/alerts").json() if a["status"] == "Draft"]
    body = client.post("/api/v1/alerts/generate", json={"min_level": "orange"}).json()
    ids = [a["id"] for a in body["alerts"] if a["id"] not in drafts_before]
    assert len(ids) >= 2
    total_drafts = len(drafts_before) + len(ids)

    # send exactly one alert; the rest must stay drafts
    r = client.post("/api/v1/alerts/send", json={"alert_ids": [ids[0]]})
    assert r.status_code == 200
    assert r.json()["sent"] == 1

    # sending without ids must deliver every remaining draft exactly once
    # (including older drafts) but never re-send ids[0]
    r = client.post("/api/v1/alerts/send", json={})
    assert r.status_code == 200
    assert r.json()["sent"] == total_drafts - 1

    # re-sending a specific already-sent alert is refused (no draft to send)
    r = client.post("/api/v1/alerts/send", json={"alert_ids": [ids[0]]})
    assert r.status_code == 404


def test_settings_roundtrip(client):
    r = client.get("/api/v1/settings")
    assert r.status_code == 200
    assert r.json()["settings"]["weather_provider"] == "demo"
    r = client.post("/api/v1/settings", json={"demo_scenario": "extreme_dry"})
    assert r.status_code == 200
    assert r.json()["settings"]["demo_scenario"] == "extreme_dry"
    # restore
    client.post("/api/v1/settings", json={"demo_scenario": "severe_humid"})


def test_invalid_settings_rejected_and_sanitised(client):
    """Corrupt threshold/weight values must never break the risk engine."""
    # non-monotonic thresholds (drift bug) -> silently ignored, defaults kept
    r = client.post("/api/v1/settings", json={"risk_thresholds": [20, 17, 5, 5]})
    assert r.status_code == 200
    assert r.json()["settings"]["risk_thresholds"] == [20, 40, 60, 80]
    # partial weight map -> ignored, full defaults kept
    r = client.post("/api/v1/settings", json={"htsi_weights": {"wbgt": 5.0}})
    assert r.status_code == 200
    assert r.json()["settings"]["htsi_weights"]["wbgt"] == 0.35
    # dashboard still computes sensible ward levels
    s = client.get("/api/v1/dashboard/summary").json()
    assert sum(s["risk"]["ward_counts"].values()) == 15


def test_model_metadata_and_retrain(client):
    r = client.get("/api/v1/admin/model")
    assert r.status_code == 200
    meta = r.json()
    assert meta["n_samples"] >= 700
    r = client.post("/api/v1/admin/retrain-model")
    assert r.status_code == 200
    assert r.json()["metadata"]["n_samples"] >= 700


def test_sample_csv(client):
    r = client.get("/api/v1/admin/sample-csv")
    assert r.status_code == 200
    assert "ward_code" in r.json()["content"]


def test_data_sources(client):
    r = client.get("/api/v1/admin/data-sources")
    assert r.status_code == 200
    assert r.json()["counts"]["wards"] == 15
    assert r.json()["counts"]["historical_days"] >= 730


def test_openapi_docs(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    for p in [
        "/health", "/api/v1/cities", "/api/v1/wards", "/api/v1/wards/{ward_id}",
        "/api/v1/wards/{ward_id}/forecast", "/api/v1/dashboard/summary",
        "/api/v1/weather/current", "/api/v1/weather/forecast",
        "/api/v1/risk/ward/{ward_id}", "/api/v1/risk/city-summary",
        "/api/v1/actions/recommendations", "/api/v1/actions/trigger-heat-action-plan",
        "/api/v1/resources/hospitals", "/api/v1/resources/cooling-centres",
        "/api/v1/alerts", "/api/v1/alerts/generate", "/api/v1/alerts/send",
        "/api/v1/analytics/trends", "/api/v1/settings",
        "/api/v1/admin/retrain-model",
    ]:
        assert p in paths, f"missing endpoint {p}"