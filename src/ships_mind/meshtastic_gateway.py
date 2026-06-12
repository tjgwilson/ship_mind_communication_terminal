from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from glob import glob
from pathlib import Path
from typing import Any

from .models import Question


@dataclass(slots=True)
class GatewayConfig:
    device: str
    channel: int
    responder_id: str


@dataclass(slots=True)
class IncomingReply:
    text: str
    sender_id: str | None = None


class MeshtasticGateway:
    def __init__(self, config: GatewayConfig) -> None:
        self._config = config
        self._online = False
        self._client = None
        self._incoming_replies: deque[IncomingReply] = deque()
        self._last_error: str | None = None

    @property
    def responder_id(self) -> str:
        return self._config.responder_id

    @property
    def online(self) -> bool:
        return self._online

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def _find_serial_device(self) -> str | None:
        devices = sorted(glob("/dev/ttyACM*")) + sorted(glob("/dev/ttyUSB*"))
        return devices[0] if devices else None

    def check_connection(self) -> None:
        if self._online and not Path(self._config.device).exists():
            self._client = None
            self._online = False
            self._last_error = f"Serial device disconnected: {self._config.device}"

    def connect(self) -> None:
        if self._online:
            return

        if not Path(self._config.device).exists():
            detected_device = self._find_serial_device()
            if detected_device is not None:
                self._config.device = detected_device

        if not Path(self._config.device).exists():
            self._online = False
            self._last_error = f"Serial device not found: {self._config.device}"
            return

        try:
            from pubsub import pub
            from meshtastic.serial_interface import SerialInterface
        except Exception as exc:  # pragma: no cover - import failure is runtime-specific
            self._online = False
            self._last_error = f"Could not import Meshtastic serial interface: {exc}"
            return

        try:
            self._client = SerialInterface(devPath=self._config.device)
            pub.subscribe(self._handle_incoming_text, "meshtastic.receive.text")
            self._online = True
            self._last_error = None
        except Exception as exc:  # pragma: no cover - hardware/runtime-specific
            self._client = None
            self._online = False
            self._last_error = f"Could not open {self._config.device}: {exc}"

    def send_question(self, question: Question) -> bool:
        if self._client is None:
            self._online = False
            self._last_error = "Meshtastic client is not connected"
            return False

        message = (
            "Ship's Core query\n"
            f"Question ID: {question.id}\n"
            f"Question: {question.text}"
        )

        # This broadcast-style send is the safe starting point. You can replace it
        # with direct node routing once you confirm the responder node ID layout.
        try:
            self._client.sendText(message, channelIndex=self._config.channel)
            self._last_error = None
            return True
        except Exception as exc:  # pragma: no cover - hardware/runtime-specific
            self._online = False
            self._last_error = f"Could not send question: {exc}"
            return False

    def consume_reply(self) -> IncomingReply | None:
        if not self._incoming_replies:
            return None
        return self._incoming_replies.popleft()

    def _handle_incoming_text(self, packet: dict[str, Any], interface: Any) -> None:
        if self._client is None or interface is not self._client:
            return

        text = packet.get("decoded", {}).get("text")
        if not isinstance(text, str):
            return

        cleaned = text.strip()
        if not cleaned:
            return

        sender_id = packet.get("fromId")
        if not self._should_accept_sender(sender_id):
            return

        self._incoming_replies.append(IncomingReply(text=cleaned, sender_id=sender_id))

    def _should_accept_sender(self, sender_id: Any) -> bool:
        if sender_id is not None and not isinstance(sender_id, str):
            return False

        responder_id = self._config.responder_id.strip()
        if not responder_id or responder_id == "remote_responder":
            return True

        return sender_id == responder_id
