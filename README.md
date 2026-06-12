# Ship's Core Terminal Console

Terminal-first Raspberry Pi control panel for a Meshtastic-linked "Ship's Core" question-and-response experience.

## What this does

- Runs directly in the Raspberry Pi console on Raspberry Pi OS Lite
- Accepts local messages from keyboard input in a full-screen terminal UI
- Stores questions in a local queue on the Pi
- Sends only one question at a time to the responder's T-Beam setup
- Checks the radio connection continuously while running
- Keeps new questions queued while the radio is offline
- Times out an active question if the radio drops mid-send, then moves it to the log
- Automatically resumes with the next queued question when the radio comes back online
- Waits for a reply before advancing the queue
- Shows three dense sci-fi panels for input, current queue, and answered history

## Project layout

- `requirements.txt` - Python dependencies
- `src/ships_mind/` - queue, gateway, runtime, and terminal UI
- `scripts/start_pi.sh` - local run script
- `scripts/install_console_autostart.sh` - installs console autostart setup
- `scripts/remove_console_autostart.sh` - removes the console autostart hook
- `scripts/disable_autostart.sh` - disables both console and service autostart
- `scripts/install_service.sh` - installs and enables the boot service
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

## Run The App

The normal Pi launcher starts the real radio app and automatically uses the first matching `/dev/ttyACM*` or `/dev/ttyUSB*` device:

```bash
./scripts/start_pi.sh
```

The top status line shows the connection state:

- `SHIP'S CORE ACTIVE` means the radio is connected and the queue can send.
- `SHIP'S CORE OFFLINE` means the app is running, queueing new questions, and waiting for the radio to return.

If you need to force a specific serial path, set it before launching:

```bash
SHIP_MESHTASTIC_DEVICE=/dev/ttyUSB0 ./scripts/start_pi.sh
```

If no radio device is found, run:

```bash
chmod +x scripts/check_radio.sh
./scripts/check_radio.sh
```

## Run On Boot

The intended boot setup is Raspberry Pi OS `Console Autologin`, then `scripts/start_pi.sh` from the user's `tty1` shell. The app shows `OFFLINE` if the radio is missing, keeps checking for the radio, and begins sending queued messages once the radio comes online.

1. Enable console autologin:

```bash
sudo raspi-config
```

Choose:

```text
System Options
Boot / Auto Login
Console Autologin
```

2. Install the console autostart hook:

```bash
chmod +x scripts/start_pi.sh scripts/install_console_autostart.sh
./scripts/install_console_autostart.sh YOUR_USERNAME
```

Example for user `tjgw`:

```bash
./scripts/install_console_autostart.sh tjgw
```

The autostart hook launches the real radio app and uses the same serial auto-detection as `scripts/start_pi.sh`.

3. If you previously enabled the old `tty1` service, disable it:

```bash
sudo systemctl disable --now ships-core@YOUR_USERNAME
```

4. Reboot:

```bash
sudo reboot
```

To remove the autostart later:

```bash
./scripts/disable_autostart.sh YOUR_USERNAME
```

Legacy option:
`scripts/install_service.sh` still installs the original `systemd` service, but that direct-`tty1` approach can glitch the console on some Pi setups and is no longer the recommended path.

If the app restarts while a question is already active, startup now retransmits that in-flight question instead of silently leaving it stuck in the active state.

## Environment variables

Optional environment variables:

- `SHIPS_MIND_DATA_DIR` default `./data`
- `SHIPS_MIND_RESPONDER_ID` default `remote_responder`
- `SHIP_MESHTASTIC_DEVICE` default `/dev/ttyACM0`
- `SHIP_MESHTASTIC_CHANNEL` default `0`
- `SHIP_ACTIVE_TIMEOUT_SECONDS` default `900`

## Meshtastic notes

This version uses a USB-connected T-Beam with outbound questions and inbound text replies.

Before live use you will likely need to:

1. Confirm the connected T-Beam serial path with `ls /dev/ttyACM* /dev/ttyUSB*`
2. Pair and test the device with the Meshtastic Python tooling
3. Optionally set `SHIPS_MIND_RESPONDER_ID` to the other node ID, such as `!abcd1234`, if you want the app to ignore replies from any other mesh node

## Operator flow

1. Write the message
2. Press `Enter` to send
3. The question becomes active when the radio path is free
4. A reply advances the queue and moves the exchange into history
