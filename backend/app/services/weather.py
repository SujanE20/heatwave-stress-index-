"""Weather provider abstraction.

Two providers:

1. DemoWeatherProvider - deterministic, offline, 4 realistic scenarios.
   Scenarios drive hourly temperature / humidity / wind / radiation / cloud
   so that the derived thermal metrics (Heat Index, WBGT, UTCI proxy) behave
   like a real Indian summer.

2. OpenMeteoProvider - live hourly forecast from Open-Meteo (needs internet).
   Responses are cached in memory (TTL 30 min).

Both return the same hour-dict schema:
  ts, date, hour, t, rh, wind, wind_dir, solar, cloud, precip_prob,
  apparent, hi, tw, tnwb, tg, wbgt, utci_proxy, hi_method

If the live provider fails, the router layer falls back to the demo
generator so the app never breaks offline.
"""
import math
import random
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import thermal

IST = ZoneInfo("Asia/Kolkata")
OPEN_METEO_CACHE: dict = {}  # key -> (fetched_at, data)
CACHE_TTL_SECONDS = 30 * 60

# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------
SCENARIOS = {
    "normal_summer": {
        "label": "Normal Summer Day",
        "description": "Typical pre-monsoon summer day in North Karnataka.",
        # day-level calibration: mostly Moderate (yellow) with some High (orange)
        "tmin": 22.4, "tmax": 33.2, "rh_base": 46.0, "wind_base": 5.2,
        "radiation": 750.0, "cloud": 34.0, "precip_prob": 12.0,
        "trend": 0.0, "trend_cap": 0.0, "pre_days": 0,
    },
    "moderate_heatwave": {
        "label": "Moderate Heatwave",
        "description": "A 3-4 day heatwave with strong daytime heating and warm nights.",
        # day-level calibration: High (orange) majority as the wave builds
        "tmin": 25.2, "tmax": 37.8, "rh_base": 36.0, "wind_base": 3.4,
        "radiation": 900.0, "cloud": 12.0, "precip_prob": 3.0,
        "trend": 0.6, "trend_cap": 1.6, "pre_days": 1,
    },
    "severe_humid": {
        "label": "Severe Humid Heatwave",
        "description": "Hot AND humid - drives Heat Index and WBGT into the danger zone.",
        # tuned so the demo peak shows a differentiated city (orange/red/maroon)
        # instead of every ward saturating to the same level
        "tmin": 26.8, "tmax": 36.4, "rh_base": 57.0, "wind_base": 3.0,
        "radiation": 730.0, "cloud": 44.0, "precip_prob": 24.0,
        "trend": 0.7, "trend_cap": 2.0, "pre_days": 2,
    },
    "extreme_dry": {
        "label": "Extreme Dry Heatwave",
        "description": "Very high dry-bulb temperatures, intense sun, dust haze.",
        # day-level calibration: Very High/Extreme across the city
        "tmin": 28.6, "tmax": 43.6, "rh_base": 16.0, "wind_base": 4.4,
        "radiation": 1000.0, "cloud": 5.0, "precip_prob": 1.0,
        "trend": 1.0, "trend_cap": 2.0, "pre_days": 2,
    },
}


def _diurnal_factor(hour: int) -> float:
    """0..1 shape of the diurnal cycle; peak ~14:30 IST."""
    return max(0.0, math.cos(math.pi * (hour - 14.5) / 12.5))


class DemoWeatherProvider:
    """Deterministic offline weather generator. Same scenario + clock -> same data."""

    name = "demo"

    def __init__(self, lat: float, lon: float, scenario: str = "severe_humid"):
        self.lat, self.lon = lat, lon
        self.scenario = scenario if scenario in SCENARIOS else "severe_humid"

    def _params(self, day_idx: int) -> dict:
        s = SCENARIOS[self.scenario]
        # cap the multi-day build-up so values stay physically plausible
        tmax = s["tmax"] + min(s["trend"] * day_idx, s["trend_cap"])
        tmin = s["tmin"] + min(0.6 * s["trend"] * day_idx, 0.6 * s["trend_cap"])
        # humidity eases as the heatwave matures (drier air at higher temperatures)
        rh_base = max(8.0, s["rh_base"] - 1.2 * min(day_idx, 4))
        return {**s, "tmax": tmax, "tmin": tmin, "rh_base": rh_base}

    def _hour_raw(self, dt: datetime, day_idx: int) -> dict:
        s = self._params(day_idx)
        hour = dt.hour
        seed = random.Random(f"{self.scenario}:{dt.strftime('%Y-%m-%d')}:{hour}")
        f = _diurnal_factor(hour)

        t = s["tmin"] + (s["tmax"] - s["tmin"]) * f + seed.uniform(-0.6, 0.6)
        rh_max = min(97.0, s["rh_base"] + 14.0)
        rh_min = max(6.0, s["rh_base"] - 8.0)
        rh = rh_max - (rh_max - rh_min) * f + seed.uniform(-4.0, 4.0)
        rh = max(5.0, min(98.0, rh))
        wind = s["wind_base"] * (1.0 + 0.35 * f) + seed.uniform(-0.5, 0.5)
        wind = max(0.4, wind)
        cloud = max(0.0, min(100.0, s["cloud"] + seed.uniform(-10.0, 10.0)))
        if 6.5 <= hour <= 17.5:
            solar = s["radiation"] * (1.0 - 0.8 * cloud / 100.0) * math.sin(math.pi * (hour - 6.5) / 11.0)
        else:
            solar = 0.0
        precip = max(0.0, min(100.0, s["precip_prob"] + seed.uniform(-5.0, 8.0)))
        return {
            "ts": dt, "date": dt.date(), "hour": hour,
            "t": round(t, 1), "rh": round(rh, 1), "wind": round(wind, 1),
            "wind_dir": round(seed.uniform(180, 320), 0),
            "solar": round(max(0.0, solar), 0),
            "cloud": round(cloud, 1), "precip_prob": round(precip, 1),
        }

    def get_hours(self, days: int = 6) -> list:
        """Generate `days` days of hourly data starting from yesterday 00:00 IST
        (the extra day lets night-recovery metrics look back correctly)."""
        now = datetime.now(IST).replace(minute=0, second=0, microsecond=0)
        start = (now - timedelta(days=1)).replace(hour=0)
        hours = []
        for i in range(days * 24):
            dt = start + timedelta(hours=i)
            day_idx = max(0, (dt.date() - start.date()).days)
            hours.append(self._hour_raw(dt, day_idx))
        return hours

    def get_current(self) -> dict:
        now = datetime.now(IST).replace(minute=0, second=0, microsecond=0)
        hours = self.get_hours(1)
        current = min(hours, key=lambda h: abs((h["ts"] - now).total_seconds()))
        return current


class OpenMeteoProvider:
    """Live hourly forecast from Open-Meteo (https://open-meteo.com)."""

    name = "openmeteo"

    def __init__(self, lat: float, lon: float, base_url: str = "https://api.open-meteo.com/v1"):
        self.lat, self.lon = lat, lon
        self.base_url = base_url.rstrip("/")

    def _fetch(self, days: int) -> list:
        key = f"{self.lat:.4f},{self.lon:.4f},{days}"
        cached = OPEN_METEO_CACHE.get(key)
        if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]

        import httpx

        params = {
            "latitude": self.lat, "longitude": self.lon,
            "hourly": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "wind_speed_10m,wind_direction_10m,cloud_cover,"
                "shortwave_radiation,precipitation_probability"
            ),
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "Asia/Kolkata",
            "forecast_days": days,
        }
        resp = httpx.get(f"{self.base_url}/forecast", params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        hours = []
        hourly = data["hourly"]
        n = len(hourly["time"])
        for i in range(n):
            solar = hourly.get("shortwave_radiation", [0] * n)[i] or 0.0
            hours.append({
                "ts": datetime.fromisoformat(hourly["time"][i]),
                "date": datetime.fromisoformat(hourly["time"][i]).date(),
                "hour": datetime.fromisoformat(hourly["time"][i]).hour,
                "t": hourly["temperature_2m"][i],
                "rh": hourly["relative_humidity_2m"][i],
                "wind": round((hourly["wind_speed_10m"][i] or 0.0) / 3.6, 1),  # km/h -> m/s
                "wind_dir": hourly.get("wind_direction_10m", [0] * n)[i] or 0.0,
                "solar": solar,
                "cloud": hourly.get("cloud_cover", [0] * n)[i] or 0.0,
                "precip_prob": hourly.get("precipitation_probability", [0] * n)[i] or 0.0,
                "apparent": hourly.get("apparent_temperature", [0] * n)[i],
            })
        OPEN_METEO_CACHE[key] = (time.time(), hours)
        return hours

    def get_hours(self, days: int = 6) -> list:
        return self._fetch(days)

    def get_current(self) -> dict:
        now = datetime.now(IST).replace(minute=0, second=0, microsecond=0)
        hours = self.get_hours(1)
        current = min(hours, key=lambda h: abs((h["ts"] - now).total_seconds()))
        return current


class WeatherProviderError(Exception):
    pass


def get_provider(settings: dict, lat: float, lon: float):
    """Build the provider selected in settings."""
    provider = settings.get("weather_provider", "demo")
    if provider == "openmeteo":
        return OpenMeteoProvider(lat, lon)
    return DemoWeatherProvider(lat, lon, settings.get("demo_scenario", "severe_humid"))


# ---------------------------------------------------------------------------
# Derived metrics + daily summaries
# ---------------------------------------------------------------------------
def enrich_hours(hours: list) -> list:
    """Attach derived thermal metrics to every hour dict."""
    for h in hours:
        d = thermal.derived_metrics(h["t"], h["rh"], h["wind"], h["solar"], h["cloud"])
        h.update(d)
        if "apparent" not in h or h.get("apparent") is None:
            h["apparent"] = round(d["hi"], 1)
    return hours


def get_city_weather(settings: dict, lat: float, lon: float, days: int = 5) -> dict:
    """Return {provider, scenario, is_demo, fallback, hours, daily, current}.

    `hours` covers the previous day + the next `days` days; `daily` summarises
    only the `days` forecast days; `current` is the nearest hour to now.
    """
    try:
        provider = get_provider(settings, lat, lon)
        hours = enrich_hours(provider.get_hours(days + 1))
        is_demo = provider.name == "demo"
        fallback = False
    except Exception as exc:  # live provider failed (e.g., offline) -> demo fallback
        demo = DemoWeatherProvider(lat, lon, settings.get("demo_scenario", "severe_humid"))
        hours = enrich_hours(demo.get_hours(days + 1))
        is_demo, fallback = True, True

    # keep only the last `days` days for display
    dates = sorted({h["date"] for h in hours})
    display = [d for d in dates if d >= datetime.now(IST).date()]
    hours = [h for h in hours if h["date"] in display]
    daily = summarize_days(hours)
    current = min(hours, key=lambda h: abs((h["ts"] - datetime.now(IST).replace(minute=0, second=0, microsecond=0)).total_seconds()))
    scenario = settings.get("demo_scenario", "severe_humid")
    return {
        "provider": "demo" if is_demo else "openmeteo",
        "scenario": scenario if is_demo else "",
        "is_demo": is_demo,
        "fallback": fallback,
        "hours": hours,
        "daily": daily,
        "current": current,
    }


def summarize_days(hours: list) -> list:
    """Per-day summary used by the risk pipeline.

    Night metrics for day d use the night before d (hours 21-23 of day d-1
    plus hours 0-6 of day d) so values are physically coherent.
    """
    by_day: dict = {}
    for h in hours:
        by_day.setdefault(h["date"], []).append(h)

    dates = sorted(by_day)
    daily = []
    for i, d in enumerate(dates):
        hs = by_day[d]
        day_hs = [h for h in hs if h["hour"] >= 7 and h["hour"] <= 20]
        peak = max(day_hs, key=lambda h: h["t"]) if day_hs else hs[0]
        prev_night = []
        if i > 0:
            prev_night = [h for h in by_day[dates[i - 1]] if h["hour"] >= 21]
        this_night = [h for h in hs if h["hour"] <= 6]
        night_hs = prev_night + this_night
        night_hi = max((h["hi"] for h in night_hs), default=peak["hi"])
        tmin = min(h["t"] for h in hs)
        exposure_hours = sum(1 for h in hs if h["wbgt"] >= 26.0)
        # longest run of consecutive high-WBGT hours within this day
        run = 0
        for h in sorted(hs, key=lambda x: x["hour"]):
            run = run + 1 if h["wbgt"] >= 26.0 else 0
        daily.append({
            "date": d,
            "tmax": round(peak["t"], 1),
            "tmin": round(tmin, 1),
            "rh": peak["rh"],
            "wind": peak["wind"],
            "solar": max(h["solar"] for h in hs),
            "cloud": peak["cloud"],
            "hi_max": max(h["hi"] for h in hs),
            "wbgt_max": max(h["wbgt"] for h in hs),
            "utci_max": max(h["utci_proxy"] for h in hs),
            "wbgt_max_hour": max(hs, key=lambda h: h["wbgt"])["hour"],
            "exposure_hours": exposure_hours,
            "night_hi": round(night_hi, 1),
            "hot_night": tmin >= 26.0,
        })
    # running counts across days
    hot_run = consec_run = 0
    for i, d in enumerate(daily):
        hot_run = hot_run + 1 if d["hot_night"] else 0
        hot_days = sum(1 for x in daily[: i + 1] if x["hot_night"])
        consec_run = consec_run + 1 if d["wbgt_max"] >= 30.0 else 0
        d["hot_nights"] = hot_days
        d["consecutive_warm_nights"] = hot_run
        d["consecutive_high_days"] = consec_run
        d["consecutive_hi_hours"] = min(14, max(run, consec_hi_hours_of(daily[: i + 1])))
    return daily


def consec_hi_hours_of(days: list) -> int:
    """Approximate running exposure: exposure hours of the hottest day +
    continuity bonus from consecutive hot days."""
    if not days:
        return 0
    top = max(d["exposure_hours"] for d in days)
    if len(days) >= 3 and all(d["wbgt_max"] >= 30.0 for d in days[-3:]):
        top += 3
    return top