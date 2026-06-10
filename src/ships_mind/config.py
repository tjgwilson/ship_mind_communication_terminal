from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(slots=True)
class Settings:
    host: str = os.getenv("SHIPS_MIND_HOST", "0.0.0.0")
    port: int = int(os.getenv("SHIPS_MIND_PORT", "8000"))
    data_dir: Path = Path(os.getenv("SHIPS_MIND_DATA_DIR", "data"))
    responder_id: str = os.getenv("SHIPS_MIND_RESPONDER_ID", "remote_responder")
    meshtastic_mode: str = os.getenv("SHIP_MESHTASTIC_MODE", "mock")
    meshtastic_device: str = os.getenv("SHIP_MESHTASTIC_DEVICE", "/dev/ttyACM0")
    meshtastic_channel: int = int(os.getenv("SHIP_MESHTASTIC_CHANNEL", "0"))
    active_timeout_seconds: int = int(os.getenv("SHIP_ACTIVE_TIMEOUT_SECONDS", "900"))


settings = Settings()
