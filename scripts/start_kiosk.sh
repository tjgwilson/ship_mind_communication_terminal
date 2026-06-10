#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

exec startx "$ROOT_DIR/scripts/kiosk_xsession.sh" -- :0 -nocursor
