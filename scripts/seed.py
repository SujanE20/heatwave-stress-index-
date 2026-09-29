"""Standalone seed script.

Seeds the database (15 wards, hospitals, cooling centres, water points,
settings, 730 days of synthetic history, demo ML model) and exports the
static GeoJSON files + sample CSV into database/seed_data/.

Usage:
    python scripts/seed.py                 # uses DATABASE_URL from env / SQLite default
    DATABASE_URL=postgresql+psycopg2://... python scripts/seed.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.environ.setdefault("HEATSHIELD_EXPORT_SEED", "1")

from app.database import SessionLocal, init_db  # noqa: E402
from app.seed import export_seed_files, seed_all  # noqa: E402


def main():
    init_db()
    db = SessionLocal()
    try:
        summary = seed_all(db)
        if summary.get("seeded"):
            print("Database seeded:")
            for k, v in summary.items():
                if k != "model":
                    print(f"  - {k}: {v}")
            print("  - model:", summary.get("model", {}).get("model_type", "n/a"))
        else:
            print(summary.get("message"))
        exported = export_seed_files(db)
        print("Exported seed files:", ", ".join(exported.keys()))
    finally:
        db.close()


if __name__ == "__main__":
    main()