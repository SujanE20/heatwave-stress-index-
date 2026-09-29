"""Health-risk prediction engine.

Converts thermal stress + ward vulnerability into:
  - Hospitalization-risk band (Low..Extreme)
  - Estimated increase in health demand above baseline (%, decision support)
  - Excess mortality-risk band (Low..Extreme)
  - Confidence (Low / Medium / High)
  - Risk drivers with contribution percentages

Safety rules (mandatory):
  - Never claim an exact number of deaths.
  - Outputs are labelled "decision-support estimates" that "require
    calibration using local public-health data".
"""
from ..models import Ward

HOSP_BANDS = [
    (25, "Low"), (45, "Moderate"), (65, "High"), (80, "Very High"), (1000, "Extreme"),
]
MORTALITY_BANDS = [
    (30, "Low"), (50, "Moderate"), (70, "High"), (85, "Very High"), (1000, "Extreme"),
]

SAFETY_NOTES = [
    "Decision-support estimate - requires calibration using local public-health data.",
    "No exact number of deaths is claimed; only an excess mortality-risk band is provided.",
    "Estimated WBGT is not a replacement for a calibrated onsite WBGT instrument.",
]


def _band(score: float, bands) -> str:
    for limit, label in bands:
        if score < limit:
            return label
    return "Extreme"


def compute_health_risk(
    ward: Ward,
    day: dict,
    htsi: dict,
    vuln: dict,
    settings: dict,
    ml_prediction: float | None = None,
) -> dict:
    """Compute health risk for one ward on one forecast day."""
    night = day.get("night_score", {}).get("score", 0.0)
    consec = day.get("consec_score", {}).get("score", 0.0)
    wbgt = day["wbgt_max"]
    hi = day["hi_max"]
    utci = day["utci_max"]
    rh = day["rh"]
    wind = day["wind"]
    access = ward.hospital_access_score

    score = (
        0.40 * htsi["score"]
        + 0.20 * vuln["score"]
        + 0.15 * night
        + 0.15 * consec
        + 0.10 * (100.0 - access)
    )
    score = round(min(100.0, score), 1)

    # --- estimated demand increase above baseline ---------------------------
    rule_based = 4.0 + score * 0.55  # %, monotonic, explainable
    if ml_prediction is not None:
        blended = 0.5 * ml_prediction + 0.5 * rule_based
        model_used, confidence = "RandomForest (trained on 730-day synthetic history)", "High"
    else:
        blended, model_used, confidence = rule_based, "Rule-based fallback", "Medium"
    lo = max(0.0, (blended * 0.75) // 5 * 5)
    hi_band = max(lo + 5, round(blended * 1.2 / 5.0) * 5)

    # --- drivers (normalised contributions) ---------------------------------
    raw = {
        "Thermal stress (HTSI)": 0.40 * htsi["score"],
        "Ward vulnerability": 0.20 * vuln["score"],
        "Poor night-time recovery": 0.15 * night,
        "Cumulative exposure": 0.15 * consec,
        "Poor hospital access": 0.10 * (100.0 - access),
    }
    total = sum(raw.values()) or 1.0
    drivers = [
        {"name": k, "contribution_pct": round(v / total * 100.0, 1)}
        for k, v in sorted(raw.items(), key=lambda kv: kv[1], reverse=True)
    ]

    return {
        "score": score,
        "hospitalization_risk": _band(score, HOSP_BANDS),
        "mortality_risk_band": _band(score, MORTALITY_BANDS),
        "demand_increase_pct": {
            "predicted": round(blended, 1),
            "range_pct": f"{lo:.0f}-{hi_band:.0f}",
            "min": lo,
            "max": hi_band,
            "source": model_used,
            "label": "Predicted increase in health demand (decision-support estimate)",
        },
        "confidence": confidence,
        "drivers": drivers,
        "inputs": {
            "htsi": htsi["score"],
            "wbgt": wbgt,
            "heat_index": hi,
            "utci_proxy": utci,
            "relative_humidity": rh,
            "wind_speed": wind,
            "night_recovery": night,
            "consecutive_exposure": consec,
            "vulnerability": vuln["score"],
            "hospital_access": access,
        },
        "safety_notes": SAFETY_NOTES,
        "requires_calibration": True,
        "label": "Decision-support estimate - not a clinical forecast",
    }