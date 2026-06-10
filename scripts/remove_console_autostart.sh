#!/usr/bin/env bash
set -euo pipefail

RUN_USER="${1:-${SUDO_USER:-$USER}}"
HOME_DIR="$(eval echo "~$RUN_USER")"
PROFILE_FILE="$HOME_DIR/.bash_profile"
MARKER_BEGIN="# >>> ships_mind autostart >>>"
MARKER_END="# <<< ships_mind autostart <<<"

if [[ ! -f "$PROFILE_FILE" ]]; then
    echo "No $PROFILE_FILE found for $RUN_USER"
    exit 0
fi

TMP_FILE="$(mktemp)"
cleanup() {
    rm -f "$TMP_FILE"
}
trap cleanup EXIT

awk -v begin="$MARKER_BEGIN" -v end="$MARKER_END" '
    $0 == begin { skip=1; next }
    $0 == end { skip=0; next }
    !skip { print }
' "$PROFILE_FILE" > "$TMP_FILE"

install_cmd=(install -m 0644 "$TMP_FILE" "$PROFILE_FILE")
if [[ "$USER" != "$RUN_USER" ]]; then
    sudo "${install_cmd[@]}"
    sudo chown "$RUN_USER":"$RUN_USER" "$PROFILE_FILE"
else
    "${install_cmd[@]}"
fi

echo "Removed console autostart from $PROFILE_FILE for $RUN_USER"
