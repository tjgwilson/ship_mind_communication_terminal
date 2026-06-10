from __future__ import annotations

from dataclasses import dataclass

from .models import Question


@dataclass(slots=True)
class GatewayConfig:
    mode: str
    device: str
    channel: int
    responder_id: str


class MeshtasticGateway:
    def __init__(self, config: GatewayConfig) -> None:
        self._config = config
        self._online = False
        self._client = None

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
            return

        if self._config.mode != "serial":
            raise ValueError(f"Unsupported Meshtastic mode: {self._config.mode}")

        try:
            from meshtastic.serial_interface import SerialInterface
        except Exception as exc:  # pragma: no cover - import failure is runtime-specific
            raise RuntimeError("Could not import Meshtastic serial interface") from exc

        self._client = SerialInterface(devPath=self._config.device)
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
