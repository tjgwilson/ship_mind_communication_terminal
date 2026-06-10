#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUN_USER="${1:-${SUDO_USER:-$USER}}"

"$ROOT_DIR/scripts/remove_console_autostart.sh" "$RUN_USER"

if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl disable --now "ships-core@$RUN_USER" 2>/dev/null || true
    sudo systemctl daemon-reload
fi

echo "Disabled Ship's Core autostart for $RUN_USER"
echo "You can still run it manually with: $ROOT_DIR/scripts/start_pi.sh"
