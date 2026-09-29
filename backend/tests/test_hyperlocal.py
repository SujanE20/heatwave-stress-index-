"""Tests for the hyperlocal risk zone engine + API endpoint."""
import math

import pytest

from app.config import RISK_ORDER, temperature_level
from app.services import hyperlocal
from app.services.settings_svc import load_settings

ALL_LEVELS = set(RISK_ORDER)


def _polygon_area_deg(ring) -> float:
    """Shoelace area of a [lon, lat] ring (in degree^2, for relative checks)."""
    return abs(sum(
        ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
        for i in range(len(ring) - 1)
    )) / 2.0


def test_split_produces_seven_zones_per_ward(db):
    wards = db.query(hyperlocal.models.Ward).all()
    assert len(wards) == 15
    for ward in wards:
        parts = hyperlocal.split_ward_polygon(ward)
        assert len(parts) == 7
        roles = [p["role"] for p in parts]
        assert roles.count("core") == 1 and roles.count("outer") == 6


def test_zone_geometry_tiles_ward(db):
    """Zone polygon areas should sum to (about) the ward polygon area."""
    ward = db.query(hyperlocal.models.Ward).order_by(hyperlocal.models.Ward.id).first()
    outer = hyperlocal._ring(ward.geojson)
    total = _polygon_area_deg(outer)
    zones = hyperlocal.split_ward_polygon(ward)
    zone_area = 0.0
    for z in zones:
        ring = z["geojson"]["geometry"]["coordinates"][0]
        assert ring[0] == ring[-1]  # closed ring
        zone_area += _polygon_area_deg(ring)
    assert zone_area == pytest.approx(total, rel=0.01)


def test_zone_centroids_inside_ward_bounds(db):
    ward = db.query(hyperlocal.models.Ward).first()
    ring = hyperlocal._ring(ward.geojson)
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    for z in hyperlocal.split_ward_polygon(ward):
        assert min(lons) - 1e-9 <= z["centroid_lon"] <= max(lons) + 1e-9
        assert min(lats) - 1e-9 <= z["centroid_lat"] <= max(lats) + 1e-9


def test_hyperlocal_map_deterministic_and_scored(db):
    settings = load_settings(db)
    out1 = hyperlocal.hyperlocal_map(db, settings)
    out2 = hyperlocal.hyperlocal_map(db, settings)
    assert len(out1["zones"]) == 15 * 7 == 105
    assert len(out1["wards"]) == 15
    assert out1["zones"][0]["id"] == out2["zones"][0]["id"]
    assert out1["zones"][0]["score"] == out2["zones"][0]["score"]

    for z in out1["zones"]:
        assert 0.0 <= z["score"] <= 100.0
        assert 0.0 <= z["exposure"]["score"] <= 100.0
        assert z["level"] in ALL_LEVELS
        assert z["exposure"]["components"].keys() == {
            "activity", "no_shade", "informal", "elderly_day", "shelter_gap",
        }
        assert sum(z["exposure"]["weights"].values()) == pytest.approx(1.0)
        # population shares should add up to the ward population
        assert z["population"] > 0

    # per ward, zone populations must sum to (about) the ward population
    by_ward: dict = {}
    for z in out1["zones"]:
        by_ward.setdefault(z["ward_code"], 0)
        by_ward[z["ward_code"]] += z["population"]
    ward_pop = {w.code: w.population for w in db.query(hyperlocal.models.Ward).all()}
    for code, pop in by_ward.items():
        assert pop == pytest.approx(ward_pop[code], rel=0.05)


def test_zone_levels_follow_city_heat_floor(db):
    """Every pocket sits at or above the city-wide temperature category;
    extreme local exposure can push pockets above it (never below)."""
    settings = load_settings(db)
    ctx = hyperlocal.city_context(db, settings)
    tmax = float(ctx["weather"]["daily"][0]["tmax"])
    heat_idx = RISK_ORDER.index(temperature_level(tmax)["key"])

    out = hyperlocal.hyperlocal_map(db, settings)
    idxs = [RISK_ORDER.index(z["level"]) for z in out["zones"]]
    # heat is city-wide: no pocket may claim a LOWER risk than the city heat
    assert all(i >= heat_idx for i in idxs)
    # but exposure differentiates pockets: at least one climbs above the floor
    assert max(idxs) > heat_idx
    assert len({z["level"] for z in out["zones"]}) >= 2


def test_hyperlocal_single_ward_filter(db):
    settings = load_settings(db)
    out = hyperlocal.hyperlocal_map(db, settings, ward_id=3)
    assert len(out["zones"]) == 7
    assert all(z["ward_id"] == 3 for z in out["zones"])
    assert len(out["wards"]) == 1


def test_hyperlocal_api(client):
    res = client.get("/api/v1/map/hyperlocal")
    assert res.status_code == 200
    data = res.json()
    assert data["city"]["name"] == "Mysore"
    assert len(data["zones"]) == 105
    sample = data["zones"][0]
    for key in ("id", "name", "level", "label", "score", "exposure", "explanation", "geojson"):
        assert key in sample
    assert sample["geojson"]["geometry"]["type"] == "Polygon"

    one = client.get("/api/v1/map/hyperlocal", params={"ward_id": 1})
    assert one.status_code == 200
    assert len(one.json()["zones"]) == 7
