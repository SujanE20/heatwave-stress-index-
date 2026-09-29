#!/usr/bin/env bash
# HEATSHIELD INDIA - full stack via Docker Compose (offline demo mode by default).
set -e
cd "$(dirname "$0")/.."

echo "▶ Starting HEATSHIELD INDIA (PostGIS + backend + frontend)..."
echo "  Dashboard:  http://localhost:3000"
echo "  API docs:   http://localhost:8000/docs"

docker compose up --build

# Stop with: docker compose down
# Reset demo data with: docker compose down -v