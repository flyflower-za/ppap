#!/bin/sh
# PPAP Backend Entrypoint — run bootstrap then start uvicorn.
# Idempotent: safe to run on every container restart.

set -e

# Bootstrap database users (creates admin / fixes null passwords)
echo "[entrypoint] Running user bootstrap..."
python scripts/bootstrap_users.py

echo "[entrypoint] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WORKERS:-1}"
