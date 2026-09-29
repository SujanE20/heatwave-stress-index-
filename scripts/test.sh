#!/usr/bin/env bash
# Run the full test suite for HEATSHIELD INDIA.
set -e
cd "$(dirname "$0")/.."

echo "=== Backend: pytest ==="
cd backend
if [ -d "../.venv" ]; then
  PY="$(ls ../.venv/bin/python 2>/dev/null || ls ../.venv/Scripts/python.exe 2>/dev/null)"
  "$PY" -m pytest tests/ -q
else
  python -m pytest tests/ -q
fi

echo ""
echo "=== Frontend: typecheck ==="
cd ../frontend
npm run build