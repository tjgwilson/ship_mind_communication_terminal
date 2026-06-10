# Ship's Core Terminal Console

Terminal-first Raspberry Pi control panel for a Meshtastic-linked "Ship's Core" question-and-response experience.

## What this does

- Runs directly in the Raspberry Pi console on Raspberry Pi OS Lite
- Accepts local messages from keyboard input in a full-screen terminal UI
- Stores questions in a local queue on the Pi
- Sends only one question at a time to the responder's T-Beam setup
- Waits for a reply before advancing the queue
- Shows three dense sci-fi panels for input, current queue, and answered history

## Project layout

- `requirements.txt` - Python dependencies
- `src/ships_mind/` - queue, gateway, runtime, and terminal UI
- `scripts/start_pi.sh` - local run script
- `systemd/ships-core@.service` - terminal service template for Raspberry Pi boot

## Recommended Pi setup

Target:

- Raspberry Pi 5
- Raspberry Pi OS Lite (64-bit)
- Python 3.11+
- One LILYGO T-Beam connected by USB to the Pi

Install base packages:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip tmux
```

## Install the app

From the project directory on the Pi:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
chmod +x scripts/start_pi.sh
```

## Run in mock mode

Mock mode keeps the full queue flow but generates an automatic reply after a short delay so you can test the screen without the radio link:

```bash
source .venv/bin/activate
./scripts/start_pi.sh
```

## Run on boot in the Pi console

The service template runs the terminal UI directly on `tty1`, so no browser, X server, or kiosk stack is needed.

Install the service:

```bash
sudo cp systemd/ships-core@.service /etc/systemd/system/ships-core@.service
sudo systemctl daemon-reload
sudo systemctl enable ships-core@YOUR_USERNAME
sudo systemctl start ships-core@YOUR_USERNAME
```

Example for user `tjgw`:

```bash
sudo systemctl enable ships-core@tjgw
sudo systemctl start ships-core@tjgw
```

Check status:

```bash
systemctl status ships-core@YOUR_USERNAME
```

The service template assumes the project lives at `/home/YOUR_USERNAME/ship_mind_communication`.
If you cloned it under a different folder name such as `ship_mind_communication_terminal`, either rename the folder or edit the service file after copying it into `/etc/systemd/system/`.

## Environment variables

Optional environment variables:

- `SHIPS_MIND_DATA_DIR` default `./data`
- `SHIPS_MIND_RESPONDER_ID` default `remote_responder`
- `SHIP_MESHTASTIC_MODE` default `mock`
- `SHIP_MESHTASTIC_DEVICE` default `/dev/ttyACM0`
- `SHIP_MESHTASTIC_CHANNEL` default `0`
- `SHIP_ACTIVE_TIMEOUT_SECONDS` default `900`
- `SHIP_MOCK_REPLY_SECONDS` default `12`

## Meshtastic notes

This version keeps a swappable gateway layer with:

- `mock` mode for local testing
- `serial` mode for a USB-connected T-Beam with outbound questions and inbound text replies

Before live use you will likely need to:

1. Confirm the connected T-Beam serial path with `ls /dev/ttyACM* /dev/ttyUSB*`
2. Pair and test the device with the Meshtastic Python tooling
3. Optionally set `SHIPS_MIND_RESPONDER_ID` to the other node ID, such as `!abcd1234`, if you want the app to ignore replies from any other mesh node

## Operator flow

1. Write the message
2. Press `Enter` to send
3. The question becomes active when the radio path is free
4. A reply advances the queue and moves the exchange into history
