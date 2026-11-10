#!/bin/sh
set -e

echo "Applying database migrations..."
alembic upgrade head || echo "Migration warning: proceeding with startup..."

echo "Starting Uvicorn application server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

