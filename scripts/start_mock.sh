#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

export SHIP_MESHTASTIC_MODE=mock
exec "$ROOT_DIR/scripts/start_pi.sh"
