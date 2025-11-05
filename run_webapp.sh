#!/usr/bin/env bash
set -euo pipefail

UVICORN_APP="gdelt_pipeline.webapp:app"
PORT="${PORT:-8000}"

exec uvicorn "$UVICORN_APP" --host 0.0.0.0 --port "$PORT"
