#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR/src"
export TERM="${TERM:-linux}"
export SHIP_MESHTASTIC_MODE="${SHIP_MESHTASTIC_MODE:-serial}"

if [[ "$SHIP_MESHTASTIC_MODE" == "serial" && -z "${SHIP_MESHTASTIC_DEVICE:-}" ]]; then
    for device in /dev/ttyACM* /dev/ttyUSB*; do
        if [[ -e "$device" ]]; then
            export SHIP_MESHTASTIC_DEVICE="$device"
            break
        fi
    done

    if [[ -z "${SHIP_MESHTASTIC_DEVICE:-}" ]]; then
        echo "No Meshtastic serial device found." >&2
        echo "Plug in the T-Beam and check: ls /dev/ttyACM* /dev/ttyUSB*" >&2
        echo "Or run with: SHIP_MESHTASTIC_DEVICE=/dev/ttyUSB0 ./scripts/start_pi.sh" >&2
        exit 1
    fi
fi

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    exec "$ROOT_DIR/.venv/bin/python" -m ships_mind.tui
fi

exec python3 -m ships_mind.tui
