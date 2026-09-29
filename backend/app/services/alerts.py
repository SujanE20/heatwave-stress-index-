"""Bilingual alert templates (English + Kannada) and simulation helpers.

IMPORTANT: The application NEVER sends real SMS/WhatsApp messages.
`sent_via` marks simulated delivery only.
"""
from ..models import CoolingCentre, Ward


def _format_window(start_hour: int, end_hour: int) -> tuple[str, str, str]:
    def h12(h: int) -> str:
        return f"{h % 12 if h % 12 else 12} {'AM' if h < 12 else 'PM'}"
    return h12(start_hour), h12(end_hour), f"{start_hour:02d}:00-{end_hour:02d}:00"


def build_alert_messages(
    ward: Ward,
    risk_level: str,
    start_hour: int = 11,
    end_hour: int = 16,
    cooling_centre: CoolingCentre | None = None,
    dist_km: float | None = None,
) -> dict:
    """Build EN + KN alert content for a ward."""
    s12, e12, window = _format_window(start_hour, end_hour)
    cc_name = cooling_centre.name if cooling_centre else "your nearest cooling centre"
    cc_dist = dist_km if dist_km is not None else 0.0
    severity = {"red": "DANGEROUS HEAT", "maroon": "EXTREME HEAT", "orange": "HEAT ALERT"}.get(
        risk_level, "HEAT ALERT"
    )

    body_en = (
        f"HEAT ALERT - Ward {ward.code} ({ward.name}): {severity} expected from "
        f"{s12} to {e12} tomorrow. Avoid outdoor work, drink water frequently, and check "
        f"elderly family members. Nearest cooling centre: {cc_name}, {cc_dist:.1f} km away."
    )
    body_kn = (
        f"ಬಿಸಿ ಎಚ್ಚರಿಕೆ - ವಾರ್ಡ್ {ward.code}: ನಾಳೆ ಬೆಳಿಗ್ಗೆ {s12.replace(' AM', '').replace(' PM', '')} ರಿಂದ "
        f"ಸಂಜೆ {e12.replace(' AM', '').replace(' PM', '')} ರವರೆಗೆ ಅಪಾಯಕಾರಿ ಬಿಸಿಯ ವಾತಾವರಣ ನಿರೀಕ್ಷಿಸಲಾಗಿದೆ. "
        f"ಹೊರಾಂಗಣ ಕೆಲಸ ತಪ್ಪಿಸಿ, ಸಾಕಷ್ಟು ನೀರು ಕುಡಿಯಿರಿ ಮತ್ತು ವೃದ್ಧರನ್ನು ಪರಿಶೀಲಿಸಿ. "
        f"ಸಮೀಪದ ಶೀತಲ ಕೇಂದ್ರ: {cc_name}, {cc_dist:.1f} ಕಿ.ಮೀ."
    )
    sms = f"HEAT ALERT Ward {ward.code}: {severity} {window} tomorrow. Drink water, avoid outdoor work 11-4. {cc_name} {cc_dist:.1f}km."
    whatsapp = (
        f"🔴 *{severity}* - Ward {ward.code} ({ward.name})\n\n"
        f"⚠️ Dangerous heat expected {s12}-{e12} tomorrow.\n"
        f"💧 Drink water frequently • 🏠 Avoid outdoor work • 👵 Check elderly neighbours\n"
        f"❄️ Nearest cooling centre: {cc_name} ({cc_dist:.1f} km)\n\n"
        f"_HeatShield India - decision-support alert (simulated)_"
    )
    return {
        "title": f"{severity} - Ward {ward.code}",
        "body_en": body_en,
        "body_kn": body_kn,
        "sms": sms,
        "whatsapp": whatsapp,
        "window": window,
        "severity": severity.lower(),
        "risk_level": risk_level,
    }


ALERT_CHANNELS = ["dashboard", "sms", "whatsapp", "webhook"]


def simulate_delivery(alert, channels: list[str] | None = None) -> dict:
    """Mark an alert as delivered through the requested channels (simulated)."""
    from datetime import datetime

    ch = channels or ALERT_CHANNELS
    sent = []
    for c in ch:
        sent.append({
            "channel": c,
            "status": "Delivered (simulated)",
            "delivered_at": datetime.utcnow().isoformat() + "Z",
        })
    return {"sent_via": sent, "note": "No real messages were sent. Delivery is simulated for demo purposes."}