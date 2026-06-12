from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ships_mind.commands import is_clear_command, is_quit_command
from ships_mind.meshtastic_gateway import GatewayConfig, IncomingReply, MeshtasticGateway
from ships_mind.models import QuestionCreate, ReplyCreate
from ships_mind.queue_manager import QueueManager
from ships_mind.runtime import ShipCoreRuntime


class MeshtasticGatewayTests(unittest.TestCase):
    def test_missing_serial_device_sets_error_without_raising(self) -> None:
        gateway = MeshtasticGateway(
            GatewayConfig(
                device="/definitely/not/a/serial/device",
                channel=0,
                responder_id="remote_responder",
            )
        )

        gateway.connect()

        self.assertFalse(gateway.online)
        self.assertIn("Serial device not found", gateway.last_error or "")

    def test_accepts_any_sender_when_responder_id_is_default_placeholder(self) -> None:
        gateway = MeshtasticGateway(
            GatewayConfig(
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
    async def test_offline_gateway_keeps_new_question_queued(self) -> None:
        runtime = ShipCoreRuntime.__new__(ShipCoreRuntime)

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime.queue_manager = QueueManager(Path(temp_dir), "remote_responder", 900)

            class StubGateway:
                online = False
                last_error = "offline for test"

                def connect(self) -> None:
                    return None

                def check_connection(self) -> None:
                    return None

                def send_question(self, question) -> bool:
                    raise AssertionError("offline gateway should not send")

                def consume_reply(self):
                    return None

            runtime.gateway = StubGateway()

            await runtime.submit_question("Queued until radio returns")

            state = await runtime.state()
            self.assertIsNone(state.active_question)
            self.assertEqual(len(state.current_questions), 1)
            self.assertEqual(state.current_questions[0].text, "Queued until radio returns")
            self.assertEqual(state.current_questions[0].status.value, "queued")
            self.assertEqual(state.radio_error, "offline for test")

    async def test_clear_questions_removes_only_pending_items(self) -> None:
        runtime = ShipCoreRuntime.__new__(ShipCoreRuntime)

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime.queue_manager = QueueManager(Path(temp_dir), "remote_responder", 900)

            class StubGateway:
                def __init__(self) -> None:
                    self.online = True

                def send_question(self, question) -> bool:
                    return True

                def consume_reply(self):
                    return None

            runtime.gateway = StubGateway()

            first = await runtime.queue_manager.enqueue(QuestionCreate(text="First question"))
            second = await runtime.queue_manager.enqueue(QuestionCreate(text="Second question"))
            await runtime.queue_manager.mark_active(first.id)
            await runtime.queue_manager.answer_active(ReplyCreate(reply_text="Resolved"))

            state_before = await runtime.queue_manager.state(runtime.gateway.online)
            self.assertEqual(len(state_before.current_questions), 1)
            self.assertEqual(len(state_before.answered_questions), 1)

            await runtime.clear_questions()

            state_after = await runtime.queue_manager.state(runtime.gateway.online)
            self.assertIsNone(state_after.active_question)
            self.assertEqual(state_after.current_questions, [])
            self.assertEqual(len(state_after.answered_questions), 1)
            self.assertEqual(state_after.answered_questions[0].text, "First question")
            self.assertIsNone(state_after.last_transmission)

    async def test_initialize_resends_persisted_active_question(self) -> None:
        runtime = ShipCoreRuntime.__new__(ShipCoreRuntime)

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime.queue_manager = QueueManager(Path(temp_dir), "remote_responder", 900)

            class StubGateway:
                def __init__(self) -> None:
                    self.online = True
                    self.connected = False
                    self.sent_questions: list[str] = []

                def connect(self) -> None:
                    self.connected = True

                def send_question(self, question) -> bool:
                    self.sent_questions.append(question.text)
                    return True

                def consume_reply(self):
                    return None

            runtime.gateway = StubGateway()

            first = await runtime.queue_manager.enqueue(QuestionCreate(text="Recover me"))
            await runtime.queue_manager.mark_active(first.id)

            await runtime.initialize()

            state = await runtime.queue_manager.state(runtime.gateway.online)
            self.assertTrue(runtime.gateway.connected)
            self.assertIsNotNone(state.active_question)
            self.assertEqual(state.active_question.text, "Recover me")
            self.assertEqual(runtime.gateway.sent_questions, ["Recover me"])

    async def test_pump_times_out_active_question_when_radio_goes_offline(self) -> None:
        runtime = ShipCoreRuntime.__new__(ShipCoreRuntime)

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime.queue_manager = QueueManager(Path(temp_dir), "remote_responder", 900)

            class StubGateway:
                def __init__(self) -> None:
                    self.online = True
                    self.last_error = None

                def check_connection(self) -> None:
                    self.online = False
                    self.last_error = "radio dropped"

                def connect(self) -> None:
                    return None

                def send_question(self, question) -> bool:
                    return True

                def consume_reply(self):
                    return None

            runtime.gateway = StubGateway()

            first = await runtime.queue_manager.enqueue(QuestionCreate(text="Lost in transit"))
            second = await runtime.queue_manager.enqueue(QuestionCreate(text="Wait for radio"))
            await runtime.queue_manager.mark_active(first.id)

            await runtime.pump()

            state = await runtime.state()
            self.assertIsNone(state.active_question)
            self.assertEqual(len(state.current_questions), 1)
            self.assertEqual(state.current_questions[0].id, second.id)
            self.assertEqual(len(state.answered_questions), 1)
            self.assertEqual(state.answered_questions[0].status.value, "timed_out")
            self.assertEqual(state.answered_questions[0].text, "Lost in transit")
            self.assertEqual(state.radio_error, "radio dropped")

    async def test_pump_sends_next_queued_question_after_radio_reconnects(self) -> None:
        runtime = ShipCoreRuntime.__new__(ShipCoreRuntime)

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime.queue_manager = QueueManager(Path(temp_dir), "remote_responder", 900)

            class StubGateway:
                def __init__(self) -> None:
                    self.online = False
                    self.last_error = "waiting for radio"
                    self.sent_questions: list[str] = []

                def check_connection(self) -> None:
                    return None

                def connect(self) -> None:
                    self.online = True
                    self.last_error = None

                def send_question(self, question) -> bool:
                    self.sent_questions.append(question.text)
                    return True

                def consume_reply(self):
                    return None

            runtime.gateway = StubGateway()

            await runtime.queue_manager.enqueue(QuestionCreate(text="Send when radio returns"))

            await runtime.pump()

            state = await runtime.state()
            self.assertIsNotNone(state.active_question)
            self.assertEqual(state.active_question.text, "Send when radio returns")
            self.assertEqual(runtime.gateway.sent_questions, ["Send when radio returns"])
            self.assertIsNone(state.radio_error)

    async def test_live_reply_answers_active_question_and_activates_next(self) -> None:
        runtime = ShipCoreRuntime.__new__(ShipCoreRuntime)

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime.queue_manager = QueueManager(Path(temp_dir), "remote_responder", 900)

            class StubGateway:
                def __init__(self) -> None:
                    self.online = True
                    self.sent_questions: list[str] = []
                    self._incoming = [IncomingReply(text="Roger that")]

                def check_connection(self) -> None:
                    return None

                def send_question(self, question) -> bool:
                    self.sent_questions.append(question.text)
                    return True

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


class TuiCommandTests(unittest.TestCase):
    def test_clear_command_recognizes_reserved_input(self) -> None:
        self.assertTrue(is_clear_command("clear"))
        self.assertTrue(is_clear_command("/clear"))
        self.assertTrue(is_clear_command("  CLEAR  "))
        self.assertFalse(is_clear_command("clear this queue please"))
        self.assertFalse(is_clear_command("normal question"))

    def test_quit_command_recognizes_reserved_input(self) -> None:
        self.assertTrue(is_quit_command("quit"))
        self.assertTrue(is_quit_command("/quit"))
        self.assertTrue(is_quit_command("exit"))
        self.assertTrue(is_quit_command("/exit"))
        self.assertFalse(is_quit_command("exit the queue please"))
        self.assertFalse(is_quit_command("normal question"))


if __name__ == "__main__":
    unittest.main()
