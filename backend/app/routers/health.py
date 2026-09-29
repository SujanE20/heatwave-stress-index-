"""Health check endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.settings_svc import load_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    settings = load_settings(db)
    return {
        "status": "ok",
        "service": "heatshield-backend",
        "version": "1.0.0",
        "database": "up",
        "demo_mode": settings.get("weather_provider") == "demo",
        "scenario": settings.get("demo_scenario"),
        "docs": "/docs",
    }