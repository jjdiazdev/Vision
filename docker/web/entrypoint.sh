#!/bin/bash
set -e

echo "[entrypoint] Applying database migrations..."
flask db upgrade --directory dashboard_app/migrations

echo "[entrypoint] Starting: $@"
exec "$@"
