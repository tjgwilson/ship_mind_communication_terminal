#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR/src"
export TERM="${TERM:-linux}"
export SHIP_RADIO_WAIT_SECONDS="${SHIP_RADIO_WAIT_SECONDS:-30}"

if [[ -z "${SHIP_MESHTASTIC_DEVICE:-}" ]]; then
    deadline=$((SECONDS + SHIP_RADIO_WAIT_SECONDS))
    while [[ "$SECONDS" -le "$deadline" ]]; do
        for device in /dev/ttyACM* /dev/ttyUSB*; do
            if [[ -e "$device" ]]; then
                export SHIP_MESHTASTIC_DEVICE="$device"
                break 2
            fi
        done
        sleep 1
    done

    if [[ -z "${SHIP_MESHTASTIC_DEVICE:-}" ]]; then
        echo "No Meshtastic serial device found after ${SHIP_RADIO_WAIT_SECONDS}s." >&2
        echo "The app will still start offline and keep queued questions local." >&2
        echo "Check the radio with: ./scripts/check_radio.sh" >&2
        export SHIP_MESHTASTIC_DEVICE="/dev/ttyACM0"
    fi
fi

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    exec "$ROOT_DIR/.venv/bin/python" -m ships_mind.tui
fi

exec python3 -m ships_mind.tui
