#!/usr/bin/env bash
set -euo pipefail

echo "Serial devices:"
found=0
for device in /dev/ttyACM* /dev/ttyUSB*; do
    if [[ -e "$device" ]]; then
        found=1
        ls -l "$device"
    fi
done

if [[ "$found" -eq 0 ]]; then
    echo "  No /dev/ttyACM* or /dev/ttyUSB* devices found."
fi

echo
echo "USB devices:"
if command -v lsusb >/dev/null 2>&1; then
    lsusb
else
    echo "  lsusb is not installed. Install it with: sudo apt install -y usbutils"
fi

echo
echo "Recent kernel USB/serial messages:"
if command -v dmesg >/dev/null 2>&1; then
    dmesg | tail -n 80 | grep -Ei 'usb|tty|cp210|ch34|meshtastic|serial' || true
else
    echo "  dmesg is not available."
fi

echo
echo "Current user groups:"
id
