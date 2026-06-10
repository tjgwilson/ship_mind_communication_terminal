# Ship's Core Communications Console

Local Raspberry Pi control panel for a Meshtastic-linked "Ship's Core" question-and-response experience.

## What this does

- Accepts questions from a browser UI running on the Raspberry Pi
- Stores questions in a local queue on the Pi
- Sends only one question at a time to the responder's T-Beam/phone setup
- Waits for a responder reply before sending the next queued question
- Shows a three-panel sci-fi control interface for the operator

## Project layout

- `requirements.txt` - Python dependencies
- `src/ships_mind/` - application code
- `scripts/start_pi.sh` - local run script
- `scripts/start_kiosk.sh` - starts the local HDMI kiosk display on Raspberry Pi OS Lite
- `systemd/ships-mind.service` - service file for auto-start on Raspberry Pi OS
- `systemd/ships-core-kiosk.service` - kiosk display service for Raspberry Pi OS Lite

## Recommended Pi setup

Tested target:

- Raspberry Pi 5
- Raspberry Pi OS Bookworm
- Python 3.11+
- One LILYGO T-Beam connected by USB to the Pi

Suggested OS setup:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git tmux
```

For Raspberry Pi OS Lite with a screen connected directly to the Pi, also install the minimal display stack:

```bash
sudo apt install -y xserver-xorg x11-xserver-utils xinit openbox chromium-browser unclutter curl
```

## Terminal access on the Pi

Enable SSH:

```bash
sudo raspi-config
```

Then:

1. Go to `Interface Options`
2. Enable `SSH`
3. Find the Pi IP with `hostname -I`
4. SSH in from your laptop:

```bash
ssh pi@YOUR_PI_IP
```

For a resilient remote terminal session, use `tmux`:

```bash
tmux new -s shipsmind
```

Detach with `Ctrl+B`, then `D`.

## Install the app

From the project directory on the Pi:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Run in mock mode first

Mock mode lets you test the queue and UI before Meshtastic is wired up.

```bash
source .venv/bin/activate
./scripts/start_pi.sh
```

Then open:

```text
http://YOUR_PI_IP:8000
```

## Run directly on Raspberry Pi OS Lite

Raspberry Pi OS Lite does not include a browser or desktop. To show the console on a screen connected to the Pi, this project uses a minimal kiosk setup:

- `ships-mind.service` runs the Python web app
- `ships-core-kiosk.service` starts a tiny X session and opens Chromium full screen
- the kiosk loads `http://127.0.0.1:8000`, so it works without a network browser

Install the app and the Lite display packages first, then install both services:

```bash
sudo cp systemd/ships-mind.service /etc/systemd/system/ships-mind.service
sudo cp systemd/ships-core-kiosk.service /etc/systemd/system/ships-core-kiosk.service
sudo systemctl daemon-reload
sudo systemctl enable ships-mind ships-core-kiosk
sudo systemctl start ships-mind ships-core-kiosk
```

Check them with:

```bash
systemctl status ships-mind
systemctl status ships-core-kiosk
```

If Chromium is installed under a different command name on your Pi, edit `SHIPS_CORE_CHROMIUM_BIN` in `systemd/ships-core-kiosk.service`. Try `chromium` if `chromium-browser` is not present.

## Environment variables

Optional environment variables:

- `SHIPS_MIND_HOST` default `0.0.0.0`
- `SHIPS_MIND_PORT` default `8000`
- `SHIPS_MIND_DATA_DIR` default `./data`
- `SHIPS_MIND_RESPONDER_ID` default `remote_responder`
- `SHIP_MESHTASTIC_MODE` default `mock`
- `SHIP_MESHTASTIC_DEVICE` default `/dev/ttyACM0`
- `SHIP_MESHTASTIC_CHANNEL` default `0`

## Meshtastic notes

This scaffold includes a gateway layer with:

- `mock` mode for local testing
- a `serial` mode placeholder for a USB-connected T-Beam

Before live use you will likely need to:

1. Confirm the connected T-Beam serial path with `ls /dev/ttyACM* /dev/ttyUSB*`
2. Pair and test the device with the Meshtastic Python tooling
3. Extend `src/ships_mind/meshtastic_gateway.py` with your exact responder node/channel logic

The code is structured so that queueing and UI logic stay stable while radio details evolve.

## Production run with systemd

Copy and adapt the service file:

```bash
sudo cp systemd/ships-mind.service /etc/systemd/system/ships-mind.service
sudo systemctl daemon-reload
sudo systemctl enable ships-mind
sudo systemctl start ships-mind
sudo systemctl status ships-mind
```

You will need to edit the service file paths so they match your Pi username and project location.

## Main operator flow

1. Visitor types a question into the Pi UI
2. Question is added to the queue
3. If nothing is currently active, the question is transmitted to the responder
4. Responder replies in character as the ship
5. Reply marks the active question complete
6. The next queued question is transmitted automatically

## Next hardware step

Once the UI and queue flow look right in mock mode, the next practical step is connecting the real Meshtastic serial client inside `meshtastic_gateway.py`.
