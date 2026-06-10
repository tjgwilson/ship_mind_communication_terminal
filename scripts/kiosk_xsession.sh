#!/usr/bin/env bash
set -euo pipefail

APP_URL="${SHIPS_CORE_KIOSK_URL:-http://127.0.0.1:8000}"
CHROMIUM_BIN="${SHIPS_CORE_CHROMIUM_BIN:-chromium-browser}"

xset -dpms || true
xset s off || true
xset s noblank || true

if command -v unclutter >/dev/null 2>&1; then
  unclutter -idle 0.2 -root &
fi

openbox-session &

until curl --silent --fail "$APP_URL/api/state" >/dev/null; do
  sleep 1
done

exec "$CHROMIUM_BIN" \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-features=Translate \
  --check-for-update-interval=31536000 \
  "$APP_URL"
