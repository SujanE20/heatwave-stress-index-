"""Final ward risk level - temperature based.

Mysore's air temperature is city-wide on a given day, so the displayed ward
risk level follows today's forecast MAXIMUM air temperature:

    Low       25 - 30 °C
    Moderate  30 - 35 °C
    High      35 - 40 °C
    Very High 40 - 44 °C
    Extreme   >= 45 °C

Ward-to-ward weather no longer varies, so all wards share the same heat
category. Vulnerability / health / thermal-stress analysis is still computed
and shown per ward as detail - it informs actions and shelter planning, but
it no longer manufactures a different colour for the same city temperature.
"""
from ..config import temperature_level, temperature_score
from ..models import Ward


def final_risk(
    ward: Ward,
    day: dict,
    htsi: dict,          # kept for pipeline symmetry (not used for the level)
    vuln: dict,          # kept for pipeline symmetry (not used for the level)
    health: dict,        # kept for pipeline symmetry (not used for the level)
    settings: dict,
) -> dict:
    """Return the ward risk level for a forecast day based on its tmax."""
    tmax = day.get("tmax")
    if tmax is None:
        tmax = day.get("hi_max", 30.0)  # edge fallback when no tmax available
    tmax = float(tmax)

    level = temperature_level(tmax)
    score = temperature_score(tmax)

    explanation = (
        f"Ward {ward.code} is classified {level['label']} because today's forecast "
        f"maximum air temperature is {tmax:.1f} °C "
        f"(Low ≤ 30 °C · Moderate 30-35 · High 35-40 · Very High 40-44 · Extreme ≥ 45 °C). "
        f"Temperature is city-wide in Mysore - all wards share this heat category. "
        f"[Decision-support estimate]"
    )

    return {
        "score": score,
        "base_score": score,
        "level": level["key"],
        "label": level["label"],
        "base_level": level["key"],
        "base_label": level["label"],
        "escalations": [],
        "explanation": explanation,
        "weights": settings.get("final_weights", {}),
        "temperature_c": round(tmax, 1),
        "bands": {
            "Low": "≤ 30 °C", "Moderate": "30-35 °C", "High": "35-40 °C",
            "Very High": "40-44 °C", "Extreme": "≥ 45 °C",
        },
    }
