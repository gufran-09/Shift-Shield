#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export SHIFTSHIELD_MODE="${SHIFTSHIELD_MODE:-demo}"
export STORAGE_BACKEND="${STORAGE_BACKEND:-local}"
./.venv/bin/uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 &
api_pid=$!
cleanup() {
  kill "$api_pid" 2>/dev/null || true
  wait "$api_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
pnpm --filter @shiftshield/frontend dev
