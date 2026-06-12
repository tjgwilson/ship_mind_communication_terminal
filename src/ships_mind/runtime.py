from __future__ import annotations
from .config import settings
from .meshtastic_gateway import GatewayConfig, MeshtasticGateway
from .models import PanelState, QuestionCreate, ReplyCreate
from .queue_manager import QueueManager


class ShipCoreRuntime:
    def __init__(self) -> None:
        self.queue_manager = QueueManager(
            settings.data_dir,
            settings.responder_id,
            settings.active_timeout_seconds,
        )
        self.gateway = MeshtasticGateway(
            GatewayConfig(
                device=settings.meshtastic_device,
                channel=settings.meshtastic_channel,
                responder_id=settings.responder_id,
            )
        )

    async def initialize(self) -> None:
        self.gateway.connect()
        await self.queue_manager.expire_active_question()

        active = await self.queue_manager.active_question()
        if active is not None:
            if self.gateway.online:
                sent = self.gateway.send_question(active)
                if not sent:
                    await self.queue_manager.timeout_active()
            else:
                await self.queue_manager.timeout_active()
            return

        await self.dispatch_next_question()

    async def dispatch_next_question(self) -> None:
        await self.queue_manager.expire_active_question()

        if not self.gateway.online:
            return

        active = await self.queue_manager.active_question()
        if active is not None:
            return

        next_question = await self.queue_manager.next_queued()
        if next_question is None:
            return

        activated = await self.queue_manager.mark_active(next_question.id)
        if activated is None:
            return

        sent = self.gateway.send_question(activated)
        if not sent:
            await self.queue_manager.timeout_active()

    async def submit_question(self, text: str):
        question = await self.queue_manager.enqueue(QuestionCreate(text=text))
        await self.dispatch_next_question()
        return question

    async def clear_questions(self) -> None:
        await self.queue_manager.clear_pending()

    async def state(self) -> PanelState:
        return await self.queue_manager.state(self.gateway.online, self.gateway.last_error)

    async def pump(self) -> None:
        self.gateway.check_connection()
        if not self.gateway.online:
            await self.queue_manager.timeout_active()
            self.gateway.connect()
            if not self.gateway.online:
                return
        await self._apply_gateway_reply_if_available()
        await self.dispatch_next_question()

    async def _apply_gateway_reply_if_available(self) -> None:
        active = await self.queue_manager.active_question()
        if active is None:
            self.gateway.consume_reply()
            return

        incoming = self.gateway.consume_reply()
        if incoming is None:
            return

        await self.queue_manager.answer_active(ReplyCreate(reply_text=incoming.text))
