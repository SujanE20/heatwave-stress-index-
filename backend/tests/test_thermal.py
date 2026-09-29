"""Unit tests for thermal calculations (pure functions, no DB needed)."""
import math

import pytest

from app.services import thermal


def test_heat_index_known_value():
    # 38°C at 70% RH => high heat index (danger/extreme caution range)
    hi, method = thermal.heat_index(38.0, 70.0)
    assert 45.0 <= hi <= 66.0
    assert "Rothfusz" in method


def test_heat_index_cool_conditions_fallback():
    hi, method = thermal.heat_index(24.0, 50.0)
    assert hi <= 24.0  # never below air temperature
    assert "fallback" in method.lower() or "simple" in method.lower()


def test_heat_index_never_below_air_temp():
    for t in (15.0, 25.0, 30.0, 40.0):
        for rh in (5.0, 50.0, 95.0):
            hi, _ = thermal.heat_index(t, rh)
            assert hi >= t - 1e-6


def test_wet_bulb_stull_known_values():
    # At 100% RH wet-bulb ~= dry-bulb
    assert thermal.wet_bulb_stull(30.0, 100.0) == pytest.approx(30.0, abs=1.5)
    # Dry air => wet-bulb well below dry-bulb
    tw = thermal.wet_bulb_stull(40.0, 15.0)
    assert 20.0 < tw < 28.0


def test_globe_temp_bounds():
    tg_sun = thermal.globe_temp(40.0, 950.0, 1.0, 0.0)
    tg_night = thermal.globe_temp(25.0, 0.0, 1.0, 100.0)
    assert tg_sun >= 40.0 and tg_sun <= 55.0  # sun-heated globe warmer than air
    assert tg_night == pytest.approx(25.0, abs=0.5)  # no radiation => no offset


def test_natural_wet_bulb_boost():
    tw = thermal.wet_bulb_stull(35.0, 50.0)
    tnwb = thermal.natural_wet_bulb(35.0, 50.0, 900.0, 1.0, 0.0)
    assert tnwb > tw  # radiation warms the natural wet bulb
    assert tnwb - tw <= 3.0


def test_wbgt_outdoor_formula():
    t, rh, solar, wind, cloud = 38.0, 60.0, 800.0, 2.0, 20.0
    wbgt = thermal.wbgt_outdoor(t, rh, solar, wind, cloud)
    tnwb = thermal.natural_wet_bulb(t, rh, solar, wind, cloud)
    tg = thermal.globe_temp(t, solar, wind, cloud)
    expected = 0.7 * tnwb + 0.2 * tg + 0.1 * t
    assert wbgt == pytest.approx(expected, abs=0.2)
    assert 24.0 < wbgt < 38.0


def test_wbgt_rises_with_humidity_and_sun():
    base = thermal.wbgt_outdoor(36.0, 40.0, 500.0, 2.0, 10.0)
    humid = thermal.wbgt_outdoor(36.0, 85.0, 500.0, 2.0, 10.0)
    sunny = thermal.wbgt_outdoor(36.0, 40.0, 1000.0, 2.0, 0.0)
    assert humid > base
    assert sunny >= base


def test_utci_proxy_bounds():
    u = thermal.utci_proxy(40.0, 60.0, 2.0, 900.0, 5.0)
    assert 40.0 <= u <= 55.0  # hot conditions -> proxy above air temp
    cold = thermal.utci_proxy(20.0, 50.0, 5.0, 0.0, 90.0)
    assert cold <= 20.0


def test_night_recovery_score():
    good = thermal.night_recovery_score(21.0, 24.0, 0, 0)
    bad = thermal.night_recovery_score(29.5, 34.0, 4, 3)
    assert good["score"] < 20
    assert bad["score"] > 75
    assert set(good["components"]) == {"min_temperature", "night_heat_index", "hot_nights", "consecutive_warm_nights"}


def test_consecutive_exposure_score():
    low = thermal.consecutive_exposure_score(2, 0, 2)
    high = thermal.consecutive_exposure_score(12, 4, 9)
    assert low["score"] < 30
    assert high["score"] > 80


def test_htsi_weights_and_components():
    res = thermal.htsi_index(32.0, 48.0, 46.0, 70.0, 80.0)
    assert 0 <= res["score"] <= 100
    assert set(res["components"]) == {"wbgt", "heat_index", "utci", "night_recovery", "consecutive_exposure"}
    # weighted sum check
    w = {"wbgt": 0.35, "heat_index": 0.20, "utci": 0.15, "night_recovery": 0.15, "consecutive_exposure": 0.15}
    expected = sum(w[k] * res["components"][k] for k in w)
    assert res["score"] == pytest.approx(expected, abs=0.5)


def test_htsi_high_for_severe_humid():
    # Severe humid conditions should produce high HTSI
    res = thermal.htsi_index(33.0, 52.0, 48.0, 85.0, 90.0)
    assert res["score"] >= 60


def test_scenarios_produce_distinct_weather():
    from app.services.weather import DemoWeatherProvider, enrich_hours

    normal = enrich_hours(DemoWeatherProvider(15.36, 75.12, "normal_summer").get_hours(6))
    severe = enrich_hours(DemoWeatherProvider(15.36, 75.12, "severe_humid").get_hours(6))
    dry = enrich_hours(DemoWeatherProvider(15.36, 75.12, "extreme_dry").get_hours(6))

    max_t = lambda hs: max(h["t"] for h in hs)
    max_wbgt = lambda hs: max(h["wbgt"] for h in hs)
    max_hi = lambda hs: max(h["hi"] for h in hs)

    assert max_t(dry) > max_t(severe) > max_t(normal)
    assert max_hi(severe) > max_hi(normal)
    assert max_wbgt(severe) > max_wbgt(normal)
    # severe humid drives WBGT into the danger zone (>= 29)
    assert max_wbgt(severe) >= 29.0