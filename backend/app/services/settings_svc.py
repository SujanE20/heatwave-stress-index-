"""Settings persistence: load/merge user-editable settings with defaults."""
from .. import models
from ..config import DEFAULT_SETTINGS

EDITABLE_KEYS = [
    "risk_thresholds", "htsi_weights", "vuln_weights", "final_weights",
    "escalate_vulnerability_threshold", "escalate_consecutive_days",
    "weather_provider", "demo_scenario", "city_id",
]


def _sanitize(value, key: str):
    """Guard against corrupted/drifted values in the settings table.

    Risk thresholds must be four strictly increasing numbers in (0, 100];
    weight maps must sum to ~1 and contain exactly the expected keys.
    Anything else silently falls back to the default so a bad Admin edit can
    never break the whole risk engine.
    """
    if key == "risk_thresholds":
        if (
            isinstance(value, list)
            and len(value) == 4
            and all(isinstance(v, (int, float)) and 0 < v <= 100 for v in value)
            and all(value[i] < value[i + 1] for i in range(3))
        ):
            return value
        return DEFAULT_SETTINGS["risk_thresholds"]
    if key in ("htsi_weights", "vuln_weights", "final_weights"):
        expected = set(DEFAULT_SETTINGS[key])
        if isinstance(value, dict) and set(value) == expected:
            weights = {k: float(v) for k, v in value.items() if isinstance(v, (int, float)) and v >= 0}
            if len(weights) == len(expected) and abs(sum(weights.values()) - 1.0) < 0.05:
                return weights
        return dict(DEFAULT_SETTINGS[key])
    if key in ("escalate_vulnerability_threshold", "escalate_consecutive_days"):
        try:
            v = float(value)
        except (TypeError, ValueError):
            return DEFAULT_SETTINGS[key]
        lo, hi = (0.0, 100.0) if key == "escalate_vulnerability_threshold" else (1.0, 10.0)
        return v if lo <= v <= hi else DEFAULT_SETTINGS[key]
    return value


def load_settings(db) -> dict:
    settings = dict(DEFAULT_SETTINGS)
    for row in db.query(models.Setting).all():
        if row.key in DEFAULT_SETTINGS:
            settings[row.key] = _sanitize(row.value, row.key)
    return settings


def save_settings(db, updates: dict) -> dict:
    for key, value in updates.items():
        if key not in EDITABLE_KEYS:
            continue
        # persist the sanitised value so invalid Admin edits are rejected
        # rather than stored and re-loaded forever
        safe = _sanitize(value, key)
        if safe != value and key in ("risk_thresholds", "htsi_weights", "vuln_weights", "final_weights"):
            continue
        row = db.query(models.Setting).filter_by(key=key).first()
        if row is None:
            row = models.Setting(key=key, value=safe)
            db.add(row)
        else:
            row.value = safe
    db.commit()
    return load_settings(db)