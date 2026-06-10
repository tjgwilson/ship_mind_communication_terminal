#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR/src"
export SHIPS_MIND_HOST="${SHIPS_MIND_HOST:-0.0.0.0}"
export SHIPS_MIND_PORT="${SHIPS_MIND_PORT:-8000}"

exec python3 -m uvicorn ships_mind.app:app --host "$SHIPS_MIND_HOST" --port "$SHIPS_MIND_PORT"
