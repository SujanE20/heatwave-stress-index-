"""Pytest fixtures: in-memory SQLite app with seeded demo data."""
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["WEATHER_PROVIDER"] = "demo"
os.environ["DEMO_SCENARIO"] = "severe_humid"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    init_db()
    from app.seed import seed_all

    db = SessionLocal()
    try:
        summary = seed_all(db)
        assert summary.get("seeded"), f"Seed failed: {summary}"
    finally:
        db.close()
    yield


@pytest.fixture()
def client(seeded_db):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db(seeded_db):
    session = SessionLocal()
    yield session
    session.close()