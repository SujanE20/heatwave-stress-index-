"""Thermal stress calculation engine.

Pure-Python (math only) so it can be unit-tested without any framework
dependencies. Every formula is documented; every estimate is clearly labelled
as an estimate.

References
----------
- Heat Index: NOAA/NWS Rothfusz regression + NWS adjustments
  https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml
- Wet-bulb: Stull (2011), "Wet-bulb temperature from relative humidity and
  air temperature", J. Appl. Meteor. Climatol. 50, 2267-2269.
- Natural wet-bulb / WBGT: outdoor WBGT = 0.7*Tnwb + 0.2*Tg + 0.1*Tdb;
  Tnwb and Tg are ESTIMATES from routine weather data (Liljegren et al. 2008
  provide the physical basis; we use a documented simplification).
- UTCI: no official implementation is bundled; we expose a clearly-labelled
  "UTCI Proxy" - never present it as official UTCI.

All returned WBGT / globe / UTCI values are estimates unless a physical
sensor is used.
"""
import math


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# ---------------------------------------------------------------------------
# Heat Index (NOAA/NWS Rothfusz)
# ---------------------------------------------------------------------------
def heat_index(t_c: float, rh: float) -> tuple[float, str]:
    """Heat Index (°C) from air temperature (°C) and relative humidity (%).

    Uses the Rothfusz regression when inside its valid range; otherwise falls
    back to the NWS simple approximation. Never returns a value below the air
    temperature (physical sanity check).
    """
    rh = _clamp(rh, 0.0, 100.0)
    t_f = t_c * 9.0 / 5.0 + 32.0

    if t_c >= 26.7 and rh >= 40.0:
        hi_f = (
            -42.379
            + 2.04901523 * t_f
            + 10.14333127 * rh
            - 0.22475541 * t_f * rh
            - 0.00683783 * t_f * t_f
            - 0.05481717 * rh * rh
            + 0.00122874 * t_f * t_f * rh
            + 0.00085282 * t_f * rh * rh
            - 0.00000199 * t_f * t_f * rh * rh
        )
        # NWS adjustments
        if rh < 13.0 and 80.0 <= t_f <= 112.0:
            hi_f -= ((13.0 - rh) / 4.0) * math.sqrt(max(0.0, (17.0 - abs(t_f - 95.0)) / 17.0))
        elif rh > 85.0 and 80.0 <= t_f <= 87.0:
            hi_f += ((rh - 85.0) / 10.0) * ((87.0 - t_f) / 5.0)
        # Rothfusz (NWS SR 90-23) recommends averaging the regression with
        # the air temperature; this matches the published NWS heat-index chart.
        hi_f = (hi_f + t_f) / 2.0
        method = "NOAA/NWS Rothfusz regression (averaged with air temperature)"
    else:
        # NWS simple approximation - valid across a broad range
        hi_f = 0.5 * (t_f + 61.0 + ((t_f - 68.0) * 1.2) + (rh * 0.094))
        method = "NWS simple approximation (outside Rothfusz range)"

    hi_f = max(hi_f, t_f)
    return round((hi_f - 32.0) * 5.0 / 9.0, 1), method


# ---------------------------------------------------------------------------
# Wet-bulb temperature
# ---------------------------------------------------------------------------
def wet_bulb_stull(t_c: float, rh: float) -> float:
    """Psychrometric wet-bulb temperature (°C) - Stull (2011) approximation."""
    rh = _clamp(rh, 0.0, 100.0)
    tw = (
        t_c * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(t_c + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * rh ** 1.5 * math.atan(0.023101 * rh)
        - 4.686035
    )
    return _clamp(tw, t_c - 20.0, t_c)


def natural_wet_bulb(t_c: float, rh: float, solar_wm2: float, wind_ms: float, cloud_pct: float) -> float:
    """ESTIMATED natural wet-bulb temperature (°C).

    A natural (unaspirated) wet-bulb thermometer runs warmer than the
    psychrometric wet-bulb because of absorbed solar radiation. We start from
    the Stull psychrometric value and add a documented radiation boost,
    capped at +3 °C. This is an estimate, not a measured Tnwb.
    """
    tw = wet_bulb_stull(t_c, rh)
    solar_frac = _clamp(solar_wm2 / 800.0, 0.0, 1.0)
    cloud_factor = 1.0 - _clamp(cloud_pct, 0.0, 100.0) / 100.0
    wind_factor = 1.0 - 0.4 * _clamp(wind_ms / 6.0, 0.0, 1.0)
    boost = 1.8 * solar_frac * cloud_factor * wind_factor
    return tw + min(boost, 3.0)


def globe_temp(t_c: float, solar_wm2: float, wind_ms: float, cloud_pct: float) -> float:
    """ESTIMATED black-globe temperature (°C).

    Simple documented model: the globe exceeds air temperature in proportion
    to absorbed shortwave radiation and inversely with wind speed:
        Tg ~ T + k * SR_eff / sqrt(v),  k = 0.010 °C·m^0.5·s^0.5·m2/W
    SR_eff is solar radiation reduced by cloud cover. Cap at +15 °C above air
    temperature. NOT a substitute for a physical globe thermometer.
    """
    cloud = _clamp(cloud_pct, 0.0, 100.0)
    solar = max(0.0, solar_wm2) * (1.0 - 0.75 * cloud / 100.0)
    v = max(0.5, wind_ms)
    tg = t_c + 0.010 * solar / math.sqrt(v)
    return min(tg, t_c + 15.0)


def wbgt_outdoor(t_c: float, rh: float, solar_wm2: float, wind_ms: float, cloud_pct: float) -> float:
    """ESTIMATED outdoor Wet-Bulb Globe Temperature (°C).

        WBGT = 0.7 * Tnwb + 0.2 * Tg + 0.1 * Tdb

    Tnwb and Tg are estimates derived from routine weather data - label the
    result "Estimated Outdoor WBGT". A calibrated onsite WBGT instrument
    remains the reference.
    """
    tnwb = natural_wet_bulb(t_c, rh, solar_wm2, wind_ms, cloud_pct)
    tg = globe_temp(t_c, solar_wm2, wind_ms, cloud_pct)
    return round(0.7 * tnwb + 0.2 * tg + 0.1 * t_c, 1)


def utci_proxy(t_c: float, rh: float, wind_ms: float, solar_wm2: float, cloud_pct: float) -> float:
    """UTCI Proxy (°C) - a documented stand-in, NOT official UTCI.

    UTCI combines air temperature, radiation (via MRT), humidity and wind.
    We approximate:
        UTCI_proxy = T + 0.6*(Tg - T) + humidity_effect - wind_effect
    where Tg is our estimated globe temperature. The proxy never exceeds
    T + 15 °C and never drops more than 5 °C below T.
    """
    tg = globe_temp(t_c, solar_wm2, wind_ms, cloud_pct)
    radiation_effect = 0.6 * (tg - t_c)
    humidity_effect = 0.02 * max(0.0, rh - 40.0) if t_c >= 30.0 else 0.0
    wind_effect = 0.2 * max(0.0, wind_ms)
    u = t_c + radiation_effect + humidity_effect - wind_effect
    return round(_clamp(u, t_c - 5.0, t_c + 15.0), 1)


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
def norm(x: float, lo: float, hi: float) -> float:
    """Normalise x into 0-100, clamped. Used across all component scores."""
    if hi <= lo:
        return 0.0
    return round(_clamp((x - lo) / (hi - lo), 0.0, 1.0) * 100.0, 1)


def wbgt_score(wbgt: float) -> float:
    """WBGT 18-34 °C -> 0-100."""
    return norm(wbgt, 18.0, 34.0)


def heat_index_score(hi: float) -> float:
    """Heat Index 27-55 °C -> 0-100."""
    return norm(hi, 27.0, 55.0)


def utci_score(u: float) -> float:
    """UTCI proxy 22-50 °C -> 0-100."""
    return norm(u, 22.0, 50.0)


# ---------------------------------------------------------------------------
# Night-time recovery score (0-100, higher = worse recovery)
# ---------------------------------------------------------------------------
def night_recovery_score(tmin: float, night_hi: float, hot_nights: int, consecutive_warm_nights: int) -> dict:
    """Score how poorly the night allows the body to recover.

    Components:
      - minimum temperature (higher = worse)
      - night-time Heat Index
      - number of hot nights (Tmin >= 26 °C) in the recent run
      - consecutive warm nights
    Weights: 0.40 / 0.30 / 0.20 / 0.10
    """
    comps = {
        "min_temperature": norm(tmin, 22.0, 29.0),
        "night_heat_index": norm(night_hi, 26.0, 36.0),
        "hot_nights": norm(hot_nights, 0.0, 4.0),
        "consecutive_warm_nights": norm(consecutive_warm_nights, 0.0, 4.0),
    }
    score = (
        0.40 * comps["min_temperature"]
        + 0.30 * comps["night_heat_index"]
        + 0.20 * comps["hot_nights"]
        + 0.10 * comps["consecutive_warm_nights"]
    )
    return {"score": round(score, 1), "components": comps}


# ---------------------------------------------------------------------------
# Consecutive exposure score (0-100, higher = worse)
# ---------------------------------------------------------------------------
def consecutive_exposure_score(consec_hi_hours: int, consec_high_days: int, daily_exposure_hours: int) -> dict:
    """Score cumulative exposure to dangerous heat.

      - consecutive high-WBGT hours (WBGT >= 26 °C)
      - consecutive high-risk days (daily max WBGT >= 30 °C)
      - hours per day spent above WBGT 26 °C
    Weights: 0.50 / 0.30 / 0.20
    """
    comps = {
        "consecutive_high_wbgt_hours": norm(consec_hi_hours, 2.0, 14.0),
        "consecutive_high_risk_days": norm(consec_high_days, 0.0, 4.0),
        "daily_exposure_hours": norm(daily_exposure_hours, 2.0, 10.0),
    }
    score = (
        0.50 * comps["consecutive_high_wbgt_hours"]
        + 0.30 * comps["consecutive_high_risk_days"]
        + 0.20 * comps["daily_exposure_hours"]
    )
    return {"score": round(score, 1), "components": comps}


# ---------------------------------------------------------------------------
# Human Thermal Stress Index (HTSI) - 0-100
# ---------------------------------------------------------------------------
def htsi_index(
    wbgt: float,
    hi: float,
    utci: float,
    night: float,
    consecutive: float,
    weights: dict | None = None,
) -> dict:
    """HTSI = 0.35*WBGT + 0.20*HI + 0.15*UTCI + 0.15*Night + 0.15*Consecutive.

    Every component score is stored for explainability. Weights are
    configurable in Admin Settings.
    """
    w = weights or {"wbgt": 0.35, "heat_index": 0.20, "utci": 0.15, "night_recovery": 0.15, "consecutive_exposure": 0.15}
    comps = {
        "wbgt": wbgt_score(wbgt),
        "heat_index": heat_index_score(hi),
        "utci": utci_score(utci),
        "night_recovery": night,
        "consecutive_exposure": consecutive,
    }
    score = (
        w["wbgt"] * comps["wbgt"]
        + w["heat_index"] * comps["heat_index"]
        + w["utci"] * comps["utci"]
        + w["night_recovery"] * comps["night_recovery"]
        + w["consecutive_exposure"] * comps["consecutive_exposure"]
    )
    return {"score": round(score, 1), "components": comps}


def derived_metrics(t: float, rh: float, wind: float, solar: float, cloud: float) -> dict:
    """Compute all derived thermal metrics for one weather state."""
    hi, hi_method = heat_index(t, rh)
    tw = wet_bulb_stull(t, rh)
    tnwb = natural_wet_bulb(t, rh, solar, wind, cloud)
    tg = globe_temp(t, solar, wind, cloud)
    wbgt = wbgt_outdoor(t, rh, solar, wind, cloud)
    utci = utci_proxy(t, rh, wind, solar, cloud)
    return {
        "hi": hi,
        "hi_method": hi_method,
        "tw": round(tw, 1),
        "tnwb": round(tnwb, 1),
        "tg": round(tg, 1),
        "wbgt": wbgt,
        "utci_proxy": utci,
    }