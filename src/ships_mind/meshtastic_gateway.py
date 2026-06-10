from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from .models import Question


@dataclass(slots=True)
class GatewayConfig:
    mode: str
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

    @property
    def mode(self) -> str:
        return self._config.mode

    @property
    def responder_id(self) -> str:
        return self._config.responder_id

    @property
    def online(self) -> bool:
        return self._online

    def connect(self) -> None:
        if self._config.mode == "mock":
            self._online = True
            return

        if self._config.mode != "serial":
            raise ValueError(f"Unsupported Meshtastic mode: {self._config.mode}")

        try:
            from pubsub import pub
            from meshtastic.serial_interface import SerialInterface
        except Exception as exc:  # pragma: no cover - import failure is runtime-specific
            raise RuntimeError("Could not import Meshtastic serial interface") from exc

        self._client = SerialInterface(devPath=self._config.device)
        pub.subscribe(self._handle_incoming_text, "meshtastic.receive.text")
        self._online = True

    def send_question(self, question: Question) -> None:
        if self._config.mode == "mock":
            return

        if self._client is None:
            raise RuntimeError("Meshtastic client is not connected")

        message = (
            "Ship's Core query\n"
            f"Question ID: {question.id}\n"
            f"Question: {question.text}"
        )

        # This broadcast-style send is the safe starting point. You can replace it
        # with direct node routing once you confirm the responder node ID layout.
        self._client.sendText(message, channelIndex=self._config.channel)

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
