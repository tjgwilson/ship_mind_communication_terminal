from __future__ import annotations
from datetime import datetime, timezone

from .config import settings
from .meshtastic_gateway import GatewayConfig, MeshtasticGateway
from .models import PanelState, QuestionCreate, ReplyCreate
from .queue_manager import QueueManager


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


class ShipCoreRuntime:
    def __init__(self) -> None:
        self.queue_manager = QueueManager(
            settings.data_dir,
            settings.responder_id,
            settings.active_timeout_seconds,
        )
        self.gateway = MeshtasticGateway(
            GatewayConfig(
                mode=settings.meshtastic_mode,
                device=settings.meshtastic_device,
                channel=settings.meshtastic_channel,
                responder_id=settings.responder_id,
            )
        )

    async def initialize(self) -> None:
        self.gateway.connect()
        await self.dispatch_next_question()

    async def dispatch_next_question(self) -> None:
        await self.queue_manager.expire_active_question()

        active = await self.queue_manager.active_question()
        if active is not None:
            return

        next_question = await self.queue_manager.next_queued()
        if next_question is None:
            return

        activated = await self.queue_manager.mark_active(next_question.id)
        if activated is None:
            return

        self.gateway.send_question(activated)

    async def submit_question(self, text: str):
        question = await self.queue_manager.enqueue(QuestionCreate(text=text))
        await self.dispatch_next_question()
        return question

    async def state(self) -> PanelState:
        return await self.queue_manager.state(self.gateway.online)

    async def pump(self) -> None:
        await self._apply_mock_reply_if_due()
        await self.dispatch_next_question()

    async def _apply_mock_reply_if_due(self) -> None:
        if self.gateway.mode != "mock":
            return

        active = await self.queue_manager.active_question()
        if active is None:
            return

        sent_at = _parse_timestamp(active.sent_at)
        if sent_at is None:
            return

        elapsed = (datetime.now(timezone.utc) - sent_at).total_seconds()
        if elapsed < settings.mock_reply_seconds:
            return

        reply = self._mock_reply_text(active.text)
        await self.queue_manager.answer_active(ReplyCreate(reply_text=reply))

    def _mock_reply_text(self, prompt: str) -> str:
        cleaned = prompt.strip().rstrip("?.!")
        return (
            f"The Ship's Core has received your query regarding {cleaned}. "
            "Response lattice aligned. Further guidance will follow through the channel."
        )
