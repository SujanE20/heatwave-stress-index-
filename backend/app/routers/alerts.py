"""Alerts centre: dashboard alerts, bilingual generation, simulated delivery."""
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services import geo
from ..services.alerts import ALERT_CHANNELS, build_alert_messages, simulate_delivery
from ..services.risk_pipeline import city_context, ward_current
from ..services.settings_svc import load_settings

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


class GenerateIn(BaseModel):
    min_level: str = Field(default="orange", description="Minimum ward risk level to alert (green|yellow|orange|red|maroon)")
    channels: list[str] = Field(default=["dashboard", "sms", "whatsapp", "webhook"])


class SendIn(BaseModel):
    alert_ids: list[int] | None = None
    channels: list[str] | None = None


def _channel_previews(body_en: str) -> dict:
    """Derive compact SMS / WhatsApp previews from the stored EN body."""
    core = re.sub(r"^HEAT ALERT - ", "", body_en)
    m = re.match(r"(Ward \S+ \([^)]+\)): ([A-Z ]+HEAT) expected", core)
    title = f"{m.group(2)} - {m.group(1)}" if m else core.split(':')[0].strip()
    short = re.split(r" Avoid outdoor work", core)[0] + "."
    sms = f"HS-ALERT {short}" if len(short) <= 140 else f"HS-ALERT {short[:137]}..."
    whatsapp = f"*{title}*\n\n{core}"
    return {"sms": sms, "whatsapp": whatsapp}


@router.get("")
def list_alerts(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(models.Alert).order_by(models.Alert.ts.desc()).limit(limit).all()
    return [
        {
            "id": a.id, "ward_id": a.ward_id, "ts": a.ts.isoformat(),
            "severity": a.severity, "title": a.title, "body_en": a.body_en,
            "body_kn": a.body_kn, "channels": a.channels, "status": a.status,
            "sent_via": a.sent_via,
            "delivered_at": a.delivered_at.isoformat() if a.delivered_at else None,
            **_channel_previews(a.body_en),
        }
        for a in rows
    ]


@router.post("/generate")
def generate_alerts(payload: GenerateIn, db: Session = Depends(get_db)):
    settings = load_settings(db)
    ctx = city_context(db, settings)
    order = {"green": 0, "yellow": 1, "orange": 2, "red": 3, "maroon": 4}
    min_idx = order.get(payload.min_level, 2)
    cooling = [{"id": c.id, "name": c.name, "lat": c.lat, "lon": c.lon}
               for c in db.query(models.CoolingCentre).all()]
    created = []
    for w in ctx["wards"]:
        result = ward_current(w, ctx["weather"], settings)
        level = result["final"]["level"]
        if order[level] < min_idx:
            continue
        n_c, d_c = geo.nearest(cooling, w.centroid_lat, w.centroid_lon)
        cc = db.query(models.CoolingCentre).get(n_c["id"]) if n_c else None
        msg = build_alert_messages(w, level, cooling_centre=cc, dist_km=d_c)
        alert = models.Alert(
            ward_id=w.id, severity=msg["severity"], title=msg["title"],
            body_en=msg["body_en"], body_kn=msg["body_kn"],
            channels=payload.channels, status="Draft",
        )
        db.add(alert)
        db.flush()
        created.append({
            "id": alert.id, "ward_id": w.id, "ward_code": w.code, "ward_name": w.name,
            "risk_level": level, "title": msg["title"], "body_en": msg["body_en"],
            "body_kn": msg["body_kn"], "sms": msg["sms"], "whatsapp": msg["whatsapp"],
            "window": msg["window"], "channels": payload.channels, "status": "Draft",
        })
    db.commit()
    if not created:
        raise HTTPException(status_code=400, detail="No wards currently meet the minimum alert level.")
    return {"generated": len(created), "alerts": created,
            "note": "Alerts are drafts. Use POST /api/v1/alerts/send to simulate delivery. No real messages are sent."}


@router.post("/send")
def send_alerts(payload: SendIn, db: Session = Depends(get_db)):
    # Only draft alerts are ever sent. Sending is idempotent: already-sent
    # alerts are skipped so a second click never re-delivers.
    q = db.query(models.Alert).filter(models.Alert.status == "Draft")
    if payload.alert_ids:
        q = q.filter(models.Alert.id.in_(payload.alert_ids))
    rows = q.order_by(models.Alert.ts.desc()).limit(100).all()
    if not rows:
        raise HTTPException(status_code=404, detail="No draft alerts found to send.")
    now = datetime.utcnow()
    sent = []
    for a in rows:
        delivery = simulate_delivery(a, payload.channels)
        a.status = "Sent (simulated)"
        a.sent_via = delivery["sent_via"]
        a.delivered_at = now
        sent.append({
            "id": a.id, "title": a.title, "ward_id": a.ward_id,
            "sent_via": delivery["sent_via"],
        })
    db.commit()
    return {
        "sent": len(sent),
        "alerts": sent,
        "note": "Delivery is SIMULATED - no SMS/WhatsApp messages were actually sent. "
                "Webhook delivery is logged only. Integrate real gateways before operational use.",
    }