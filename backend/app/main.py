"""HEATSHIELD INDIA - FastAPI application entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS, DATABASE_URL
from .database import SessionLocal, init_db
from .routers import admin, alerts, core, health, hyperlocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("heatshield")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from .seed import seed_all

    db = SessionLocal()
    try:
        summary = seed_all(db)
        if summary.get("seeded"):
            logger.info("Seed complete: %s", summary)
        else:
            logger.info("Database already seeded - %s", summary.get("message"))
    finally:
        db.close()
    yield


app = FastAPI(
    title="HEATSHIELD INDIA API",
    description=(
        "Localized heat-health early warning system for Indian cities. "
        "Transforms weather forecast -> human thermal stress -> ward-level vulnerability "
        "-> hospitalization/mortality risk -> recommended authority action -> citizen alerts. "
        "Demo city: Mysore, Karnataka."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(core.router)
app.include_router(alerts.router)
app.include_router(admin.router)
app.include_router(hyperlocal.router)


@app.get("/")
def root():
    return {
        "service": "HEATSHIELD INDIA API",
        "tagline": "Predicting what heat will do to people, not just what the weather will be.",
        "docs": "/docs",
        "health": "/health",
        "demo_mode": True,
        "database_url": ("postgresql+postgis (Docker)" if "postgres" in DATABASE_URL else "sqlite (local demo)"),
    }