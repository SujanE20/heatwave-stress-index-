"""Geographic helpers: distances, nearest resources, ward microclimate offsets."""
import math


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest(items: list, lat: float, lon: float, key: str = "name"):
    """Return (item, distance_km) for the nearest item in a list of dicts."""
    best, best_d = None, None
    for it in items:
        d = haversine_km(lat, lon, it["lat"], it["lon"])
        if best is None or d < best_d:
            best, best_d = it, d
    return best, round(best_d, 1)


def ward_weather_offsets(ward) -> dict:
    """Per-ward weather offsets applied to the city forecast.

    Mysore's weather is city-wide: on one day the air temperature barely
    changes from ward to ward (real differences are a fraction of a °C).
    Offsets are therefore zero - every ward sees exactly the same forecast
    and derives the same heat category. Ward differentiation is the AI risk
    pipeline's job (vulnerability, exposure, resources), never weather.
    """
    return {
        "temp_offset": 0.0,
        "rh_offset": 0.0,
        "wind_factor": 1.0,
        "label": "City-wide weather - no ward-to-ward variation (Mysore)",
    }