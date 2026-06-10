#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_SOURCE="$ROOT_DIR/systemd/ships-core@.service"
SERVICE_TARGET="/etc/systemd/system/ships-core@.service"
RUN_USER="${1:-${SUDO_USER:-$USER}}"
HOME_DIR="$(eval echo "~$RUN_USER")"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"

if [[ ! -f "$SERVICE_SOURCE" ]]; then
    echo "Missing service template: $SERVICE_SOURCE" >&2
    exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Expected virtualenv interpreter at $PYTHON_BIN" >&2
    echo "Create it first with: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi

TMP_FILE="$(mktemp)"
cleanup() {
    rm -f "$TMP_FILE"
}
trap cleanup EXIT

sed \
    -e "s|/home/%i/ship_mind_communication|$ROOT_DIR|g" \
    -e "s|/home/%i/ship_mind_communication/.venv/bin/python|$PYTHON_BIN|g" \
    "$SERVICE_SOURCE" > "$TMP_FILE"

sudo install -m 0644 "$TMP_FILE" "$SERVICE_TARGET"
sudo systemctl daemon-reload
sudo systemctl enable "ships-core@$RUN_USER"
sudo systemctl restart "ships-core@$RUN_USER"

echo "Installed and started ships-core@$RUN_USER"
echo "Check status with: systemctl status ships-core@$RUN_USER"
