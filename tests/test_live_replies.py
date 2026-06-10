from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ships_mind.meshtastic_gateway import GatewayConfig, IncomingReply, MeshtasticGateway
from ships_mind.models import QuestionCreate
from ships_mind.queue_manager import QueueManager
from ships_mind.runtime import ShipCoreRuntime


class MeshtasticGatewayTests(unittest.TestCase):
    def test_accepts_any_sender_when_responder_id_is_default_placeholder(self) -> None:
        gateway = MeshtasticGateway(
            GatewayConfig(
                mode="serial",
                device="/dev/null",
                channel=0,
                responder_id="remote_responder",
            )
        )
        gateway._client = object()

        gateway._handle_incoming_text(
            {"decoded": {"text": "Reply from field node"}, "fromId": "!abcd1234"},
            gateway._client,
        )

        incoming = gateway.consume_reply()
        self.assertIsNotNone(incoming)
        self.assertEqual(incoming.text, "Reply from field node")
        self.assertEqual(incoming.sender_id, "!abcd1234")

    def test_filters_replies_to_configured_responder(self) -> None:
        gateway = MeshtasticGateway(
            GatewayConfig(
                mode="serial",
                device="/dev/null",
                channel=0,
                responder_id="!beadfeed",
            )
        )
        gateway._client = object()

        gateway._handle_incoming_text(
            {"decoded": {"text": "Ignore me"}, "fromId": "!abcd1234"},
            gateway._client,
        )
        gateway._handle_incoming_text(
            {"decoded": {"text": "Accepted"}, "fromId": "!beadfeed"},
            gateway._client,
        )

        incoming = gateway.consume_reply()
        self.assertIsNotNone(incoming)
        self.assertEqual(incoming.text, "Accepted")
        self.assertIsNone(gateway.consume_reply())


class ShipCoreRuntimeReplyTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_reply_answers_active_question_and_activates_next(self) -> None:
        runtime = ShipCoreRuntime.__new__(ShipCoreRuntime)

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime.queue_manager = QueueManager(Path(temp_dir), "remote_responder", 900)

            class StubGateway:
                def __init__(self) -> None:
                    self.mode = "serial"
                    self.online = True
                    self.sent_questions: list[str] = []
                    self._incoming = [IncomingReply(text="Roger that")]

                def send_question(self, question) -> None:
                    self.sent_questions.append(question.text)

                def consume_reply(self):
                    if not self._incoming:
                        return None
                    return self._incoming.pop(0)

            runtime.gateway = StubGateway()

            first = await runtime.queue_manager.enqueue(QuestionCreate(text="First question"))
            second = await runtime.queue_manager.enqueue(QuestionCreate(text="Second question"))
            await runtime.queue_manager.mark_active(first.id)

            await runtime.pump()

            state = await runtime.queue_manager.state(runtime.gateway.online)
            self.assertIsNotNone(state.answered_questions)
            self.assertEqual(state.answered_questions[0].text, "First question")
            self.assertEqual(state.answered_questions[0].reply_text, "Roger that")
            self.assertIsNotNone(state.active_question)
            self.assertEqual(state.active_question.text, "Second question")
            self.assertEqual(runtime.gateway.sent_questions, ["Second question"])
            self.assertEqual(second.id, state.active_question.id)


if __name__ == "__main__":
    unittest.main()
