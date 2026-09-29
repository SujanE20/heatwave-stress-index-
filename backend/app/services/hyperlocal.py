"""Hyperlocal risk zones inside each demo ward.

In real Mysore the air temperature on one day barely changes ward-to-ward
(or street-to-street), so every pocket inside a ward shares the SAME
thermal stress. What differs pocket-to-pocket is *exposure*: street
vendors and market crowds, tree shade, informal housing, daytime elderly
presence, and how far the nearest cooling centre / water point is.

Risk levels follow the temperature bands used everywhere else (Low 25-30 °C,
Moderate 30-35, High 35-40, Very High 40-44, Extreme >= 45) so the hyperlocal
map is consistent with the ward and city maps. Because air temperature is
city-wide, every pocket starts at the SAME temperature category as its ward
- the heat floor. A pocket's local exposure (market crowds, tree shade,
informal housing, daytime elderly presence, shelter distance) can only push
it ABOVE that floor:

    zone_effective_tmax = max(city tmax, city tmax + 0.2 * (exposure - 50))
    zone_level = temperature_level(zone_effective_tmax)

So in a 37 °C day (High city-wide) a shaded residential block stays High
while a packed market pocket with no shelter climbs to Very High (and in a
heatwave an extreme-exposure pocket can reach Extreme) - the map never
invents temperature differences that don't exist.

Zones and their micro-factors are generated deterministically from the
ward id + zone index (same principle as the demo weather generator), so
the hyperlocal map is stable across requests and needs no extra tables.
Boundaries are demonstration subdivisions of the demo ward polygons.
"""
import math
import random

from sqlalchemy.orm import Session

from .. import models
from ..config import RISK_LEVELS, RISK_ORDER, temperature_level, temperature_score
from . import geo, thermal
from .risk_pipeline import city_context, ward_current

# One central core + 6 outer blocks per ward.
CORE_SCALE = 0.5  # inner-core polygon scale factor relative to the ward ring

EXPOSURE_LABELS = {
    "activity": "Street activity / vendors",
    "no_shade": "Low tree shade",
    "informal": "Informal housing",
    "elderly_day": "Daytime elderly presence",
    "shelter_gap": "Distance to shelter / water",
}
EXPOSURE_WEIGHTS = {
    "activity": 0.28,
    "no_shade": 0.22,
    "informal": 0.15,
    "elderly_day": 0.15,
    "shelter_gap": 0.20,
}

# Zone archetypes: (label, base factor ranges, selection weight). The actual
# factor is drawn inside the range and blended with the ward's own profile.
CORE_KINDS = [
    ("Market / bazaar core", {
        "activity": (70, 95), "shade": (8, 30), "informal": (25, 55),
        "elderly_day": (25, 50), "weight": 4,
    }),
    ("Central residential core", {
        "activity": (30, 55), "shade": (35, 60), "informal": (10, 35),
        "elderly_day": (35, 65), "weight": 3,
    }),
    ("Informal dense core", {
        "activity": (55, 75), "shade": (20, 45), "informal": (70, 95),
        "elderly_day": (20, 45), "weight": 2,
    }),
]
OUTER_KINDS = [
    ("tree-lined residential block", {
        "activity": (25, 45), "shade": (45, 75), "informal": (5, 25),
        "elderly_day": (35, 65), "weight": 3,
    }),
    ("market street / vendor stretch", {
        "activity": (70, 95), "shade": (10, 30), "informal": (20, 50),
        "elderly_day": (25, 55), "weight": 3,
    }),
    ("informal settlement pocket", {
        "activity": (55, 80), "shade": (15, 40), "informal": (70, 95),
        "elderly_day": (15, 40), "weight": 2,
    }),
    ("institutional block (schools / offices)", {
        "activity": (45, 65), "shade": (35, 60), "informal": (8, 25),
        "elderly_day": (15, 35), "weight": 2,
    }),
]


# ---------------------------------------------------------------------------
# Geometry (pure python - no shapely / PostGIS dependency)
# ---------------------------------------------------------------------------
def _ring(geojson) -> list:
    """Outer ring of the ward polygon as a closed list of [lon, lat]."""
    coords = (geojson or {}).get("geometry", {}).get("coordinates")
    if not coords:
        raise ValueError("ward polygon geometry missing")
    return list(coords[0])


def _centroid(pts) -> tuple:
    n = len(pts)
    return sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n


def _polygon_feature(ring: list, properties: dict) -> dict:
    """Closed ring of [lon, lat] -> GeoJSON Feature with a Polygon geometry."""
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": {"type": "Polygon", "coordinates": [ring + [ring[0]]]},
    }


def split_ward_polygon(ward) -> list:
    """Subdivide one ward into (core, outer_blocks) zone polygons.

    Returns dicts {index, role, direction, centroid_lat, centroid_lon,
    geojson}. The zone polygons exactly tile the ward: a centre polygon
    scaled towards the centroid plus 6 quads between the scaled ring and
    the ward boundary.
    """
    ring = _ring(ward.geojson)
    pts = ring[:-1]  # drop the closing point -> the 6 hexagon vertices
    c_lon, c_lat = _centroid(ring)
    core = [
        (c_lon + (p[0] - c_lon) * CORE_SCALE, c_lat + (p[1] - c_lat) * CORE_SCALE)
        for p in pts
    ]
    zones = []
    cc_lon, cc_lat = _centroid(core)
    zones.append({
        "index": 0, "role": "core", "direction": "C",
        "centroid_lon": cc_lon, "centroid_lat": cc_lat,
        "geojson": _polygon_feature(core, {"zone": "C"}),
    })
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        quad = [tuple(pts[i]), tuple(pts[j]), core[j], core[i]]
        qc_lon, qc_lat = _centroid(quad)
        mid = ((pts[i][0] + pts[j][0]) / 2.0, (pts[i][1] + pts[j][1]) / 2.0)
        bearing = math.degrees(math.atan2(mid[0] - c_lon, mid[1] - c_lat)) % 360.0
        compass = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][round(bearing / 45.0) % 8]
        zones.append({
            "index": i + 1, "role": "outer", "direction": compass,
            "centroid_lon": qc_lon, "centroid_lat": qc_lat,
            "geojson": _polygon_feature(quad, {"zone": str(i + 1)}),
        })
    return zones


# ---------------------------------------------------------------------------
# Deterministic zone modelling + exposure scoring
# ---------------------------------------------------------------------------
def _draw(rng, lo: float, hi: float, ward_val: float, mix: float = 0.35) -> float:
    """Factor = uniform draw in [lo, hi], blended with the ward's own value."""
    val = rng.uniform(lo, hi) * (1.0 - mix) + ward_val * mix
    return round(max(0.0, min(100.0, val)), 1)


def _pick_kind(rng, role: str):
    table = CORE_KINDS if role == "core" else OUTER_KINDS
    weights = [k[1]["weight"] for k in table]
    return rng.choices(table, weights=weights, k=1)[0]


def zone_exposure(ward, zone: dict, cooling: list, water: list, kind) -> dict:
    """Exposure profile (0-100 components) of one pocket."""
    rng = random.Random(f"heatshield-hl:{ward.id}:{zone['index']}")
    factors = kind[1]
    # ward-level norms so a pocket inherits its ward's real character
    elderly_n = thermal.norm(ward.elderly_pct, 5.0, 20.0)
    outdoor_n = thermal.norm(ward.outdoor_worker_density, 300.0, 4500.0)
    informal_n = thermal.norm(ward.informal_housing_pct, 0.0, 35.0)
    green_n = 100.0 - thermal.norm(100.0 - ward.green_cover_pct, 30.0, 100.0)

    activity = _draw(rng, *factors["activity"], outdoor_n, 0.45)
    shade = _draw(rng, *factors["shade"], green_n, 0.30)
    informal = _draw(rng, *factors["informal"], informal_n, 0.30)
    elderly_day = _draw(rng, *factors["elderly_day"], elderly_n, 0.40)

    n_c, d_c = geo.nearest(cooling, zone["centroid_lat"], zone["centroid_lon"])
    n_w, d_w = geo.nearest(water, zone["centroid_lat"], zone["centroid_lon"])
    shelter_gap = round(0.65 * thermal.norm(d_c, 0.0, 3.0) + 0.35 * thermal.norm(d_w, 0.0, 2.0), 1)

    comps = {
        "activity": round(activity, 1),
        "no_shade": round(100.0 - shade, 1),
        "informal": round(informal, 1),
        "elderly_day": round(elderly_day, 1),
        "shelter_gap": shelter_gap,
    }
    contributions = {k: round(EXPOSURE_WEIGHTS[k] * comps[k], 1) for k in comps}
    score = round(sum(contributions.values()), 1)
    return {
        "score": score,
        "components": comps,
        "contributions": contributions,
        "weights": dict(EXPOSURE_WEIGHTS),
        "labels": dict(EXPOSURE_LABELS),
        "kind": kind[0],
        "nearest": {
            "cooling_centre": {"name": n_c["name"], "distance_km": round(d_c, 1)},
            "water_point": {"name": n_w["name"], "distance_km": round(d_w, 1)},
        },
    }


def _pocket_reasons(exp: dict) -> str:
    bits = []
    c = exp["components"]
    if c["activity"] >= 60:
        bits.append("concentrated street activity and crowds")
    if c["no_shade"] >= 60:
        bits.append("little tree shade")
    if c["informal"] >= 60:
        bits.append("dense informal housing")
    if c["elderly_day"] >= 60:
        bits.append("many elderly residents active by day")
    if c["shelter_gap"] >= 55:
        bits.append(f"the nearest cooling centre is {exp['nearest']['cooling_centre']['distance_km']} km away")
    if not bits:
        bits.append("exposure is comparatively low")
    return "; ".join(bits)


def hyperlocal_map(db: Session, settings: dict, ward_id: int | None = None) -> dict:
    """Compute the hyperlocal zone map for the demo city.

    Returns city metadata, ward outlines (context) and every zone with its
    geometry, exposure profile and risk level. `ward_id` optionally limits
    the result to a single ward.
    """
    ctx = city_context(db, settings)
    city, weather = ctx["city"], ctx["weather"]
    wards = ctx["wards"]
    if ward_id is not None:
        wards = [w for w in wards if w.id == ward_id]

    hospitals = [{"id": h.id, "name": h.name, "lat": h.lat, "lon": h.lon} for h in db.query(models.Hospital).all()]
    cooling = [{"id": c.id, "name": c.name, "lat": c.lat, "lon": c.lon} for c in db.query(models.CoolingCentre).all()]
    water = [{"id": p.id, "name": p.name, "lat": p.lat, "lon": p.lon} for p in db.query(models.WaterPoint).all()]

    wbgt_note = (
        f"(estimated WBGT up to ~{weather['daily'][0]['wbgt_max']:.0f} °C city-wide)"
        if weather.get("daily") else "(city-wide heat)"
    )

    # City-wide heat floor: every pocket starts at the same temperature
    # category as its ward (Mysore's air temperature does not vary ward to
    # ward). Exposure may only push a pocket above this floor.
    heat_tmax = float(weather["daily"][0]["tmax"]) if weather.get("daily") else 30.0
    heat_level = temperature_level(heat_tmax)
    heat_idx = RISK_ORDER.index(heat_level["key"])

    ward_outlines, zones = [], []
    for ward in wards:
        result = ward_current(ward, weather, settings)  # htsi / health / final risk
        htsi_score = result["htsi"]["score"]
        ward_level_label = result["final"]["label"]
        ward_parts = split_ward_polygon(ward)

        # deterministic population shares (core bigger, outer roughly even)
        rng_share = random.Random(f"heatshield-hl-pop:{ward.id}")
        core_share = rng_share.uniform(0.16, 0.26)
        outer_shares = [rng_share.random() for _ in range(6)]
        s_total = sum(outer_shares)
        outer_shares = [s / s_total * (1.0 - core_share) for s in outer_shares]

        ward_outlines.append({
            "id": ward.id, "code": ward.code, "name": ward.name,
            "level": result["final"]["level"], "label": result["final"]["label"],
            "score": result["final"]["score"], "htsi": htsi_score,
            "vulnerability": result["vulnerability"]["score"],
            "population": ward.population,
            "centroid_lat": ward.centroid_lat, "centroid_lon": ward.centroid_lon,
            "geojson": ward.geojson,
        })

        for idx, part in enumerate(ward_parts):
            rng = random.Random(f"heatshield-hl-kind:{ward.id}:{part['index']}")
            kind = _pick_kind(rng, part["role"])
            if part["role"] == "core":
                name = f"{ward.name} · core pocket"
            else:
                name = f"{ward.name} · {part['direction']} side block"
            share = core_share if part["role"] == "core" else outer_shares[idx - 1]

            exp = zone_exposure(ward, part, cooling, water, kind)

            # Hyperlocal risk: start from the city-wide heat category (same
            # for every pocket), then let local exposure lift a pocket's
            # effective heat above that floor. Exposure never takes a pocket
            # below the city's heat category.
            zone_tmax = max(heat_tmax, heat_tmax + 0.2 * (exp["score"] - 50.0))
            zone_level = temperature_level(zone_tmax)
            zone_score = round(temperature_score(zone_tmax), 1)
            escalations = []
            if RISK_ORDER.index(zone_level["key"]) > heat_idx:
                escalations.append(
                    f"Local exposure ({exp['score']:.0f}/100) pushes this pocket "
                    f"above the city-wide {heat_level['label']} heat category"
                )

            explanation = (
                f"{name} ({exp['kind']}). The whole ward shares the same city heat today "
                f"{wbgt_note} ({heat_level['label']} city-wide), and this pocket adds "
                f"{_pocket_reasons(exp)}."
                f" Hyperlocal risk: {zone_level['label']} ({zone_score:.0f}/100) "
                f"vs ward {ward_level_label}."
            )
            if escalations:
                explanation += " Escalated because: " + "; ".join(escalations) + "."
            explanation += " [Decision-support estimate]"

            zones.append({
                "id": f"{ward.code}-{part['direction']}",
                "zone_index": part["index"],
                "role": part["role"],
                "ward_id": ward.id, "ward_code": ward.code, "ward_name": ward.name,
                "name": name,
                "kind": exp["kind"],
                "level": zone_level["key"], "label": zone_level["label"],
                "score": zone_score, "base_score": zone_score,
                "escalations": escalations,
                "exposure": exp,
                "htsi": htsi_score,
                "ward_level": result["final"]["level"], "ward_label": ward_level_label,
                "ward_score": result["final"]["score"],
                "population": round(ward.population * share),
                "population_share": round(share, 3),
                "centroid_lat": part["centroid_lat"], "centroid_lon": part["centroid_lon"],
                "nearest": exp["nearest"],
                "explanation": explanation,
                "geojson": part["geojson"],
            })

    return {
        "city": {"id": city.id, "name": city.name, "state": city.state, "lat": city.lat, "lon": city.lon},
        "weather": {
            "provider": weather["provider"], "scenario": weather["scenario"],
            "is_demo": weather["is_demo"], "fallback": weather["fallback"],
        },
        "shared_heat_note": (
            "Air temperature and thermal stress are city-wide on a given day in Mysore; "
            "wards and pockets differ by exposure and vulnerability, not by temperature."
        ),
        "generated_note": "Zone boundaries and micro-factors are demonstration subdivisions of the demo ward polygons.",
        "wards": ward_outlines,
        "zones": zones,
    }
