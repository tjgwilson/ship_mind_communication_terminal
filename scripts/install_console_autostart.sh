#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUN_USER="${1:-${SUDO_USER:-$USER}}"
HOME_DIR="$(eval echo "~$RUN_USER")"
PROFILE_FILE="$HOME_DIR/.bash_profile"
MARKER_BEGIN="# >>> ships_mind autostart >>>"
MARKER_END="# <<< ships_mind autostart <<<"
START_SCRIPT="$ROOT_DIR/scripts/start_pi.sh"

if [[ ! -d "$HOME_DIR" ]]; then
    echo "Could not resolve home directory for user: $RUN_USER" >&2
    exit 1
fi

if [[ ! -x "$START_SCRIPT" ]]; then
    echo "Expected executable start script at $START_SCRIPT" >&2
    echo "Run: chmod +x scripts/start_pi.sh" >&2
    exit 1
fi

if [[ ! -x "$ROOT_DIR/.venv/bin/python" ]]; then
    echo "Expected virtualenv interpreter at $ROOT_DIR/.venv/bin/python" >&2
    echo "Create it first with: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi

TMP_FILE="$(mktemp)"
cleanup() {
    rm -f "$TMP_FILE"
}
trap cleanup EXIT

if [[ -f "$PROFILE_FILE" ]]; then
    awk -v begin="$MARKER_BEGIN" -v end="$MARKER_END" '
        $0 == begin { skip=1; next }
        $0 == end { skip=0; next }
        !skip { print }
    ' "$PROFILE_FILE" > "$TMP_FILE"
else
    : > "$TMP_FILE"
fi

cat >> "$TMP_FILE" <<EOF
$MARKER_BEGIN
if [[ -z "\${SSH_TTY:-}" && "\$(tty)" == "/dev/tty1" ]]; then
    cd "$ROOT_DIR"
    export SHIP_MESHTASTIC_MODE="\${SHIP_MESHTASTIC_MODE:-serial}"
    export SHIP_MESHTASTIC_DEVICE="\${SHIP_MESHTASTIC_DEVICE:-/dev/ttyACM0}"
    exec "$START_SCRIPT"
fi
$MARKER_END
EOF

install_cmd=(install -m 0644 "$TMP_FILE" "$PROFILE_FILE")
if [[ "$USER" != "$RUN_USER" ]]; then
    sudo "${install_cmd[@]}"
    sudo chown "$RUN_USER":"$RUN_USER" "$PROFILE_FILE"
else
    "${install_cmd[@]}"
fi

echo "Installed console autostart into $PROFILE_FILE for $RUN_USER"
echo "Next steps:"
echo "1. Enable Raspberry Pi console autologin"
echo "2. Disable the old tty1 service if it was enabled:"
echo "   sudo systemctl disable --now ships-core@$RUN_USER"
echo "3. Reboot"
