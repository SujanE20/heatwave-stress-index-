"""Hyperlocal map API: sub-ward risk pockets for the demo city."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services import hyperlocal
from ..services.settings_svc import load_settings

router = APIRouter(prefix="/api/v1/map", tags=["hyperlocal"])


@router.get("/hyperlocal")
def hyperlocal_map(
    ward_id: int | None = Query(None, description="Restrict to one ward (optional)"),
    db: Session = Depends(get_db),
):
    """Hyperlocal risk map: every ward subdivided into exposure pockets.

    All pockets share the same city-wide heat; zone risk levels differ by
    local exposure (street activity, shade, informal housing, elderly
    daytime presence, distance to cooling shelters).
    """
    settings = load_settings(db)
    return hyperlocal.hyperlocal_map(db, settings, ward_id=ward_id)
