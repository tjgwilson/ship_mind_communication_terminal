#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR/src"
export TERM="${TERM:-linux}"
export SHIP_MESHTASTIC_MODE="${SHIP_MESHTASTIC_MODE:-serial}"
export SHIP_MESHTASTIC_DEVICE="${SHIP_MESHTASTIC_DEVICE:-/dev/ttyACM0}"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    exec "$ROOT_DIR/.venv/bin/python" -m ships_mind.tui
fi

exec python3 -m ships_mind.tui
