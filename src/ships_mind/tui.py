from __future__ import annotations

import logging
from datetime import datetime

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static

from .models import Question
from .runtime import ShipCoreRuntime

logging.basicConfig(level=logging.INFO)


def format_timestamp(value: str | None) -> str:
    if not value:
        return "--:--:--"
    return datetime.fromisoformat(value).astimezone().strftime("%H:%M:%S")


class ShipCoreConsole(App[None]):
    CSS = """
    Screen {
        layout: vertical;
        background: #041109;
        color: #d3ffe1;
    }

    Header {
        dock: top;
    }

    #status_line {
        height: 1;
        color: #8effb0;
        background: #0a2111;
        padding: 0 1;
    }

    #main {
        layout: horizontal;
        height: 1fr;
    }

    .panel {
        width: 1fr;
        height: 1fr;
        border: solid #1f7a45;
        margin: 0 1 1 1;
        padding: 1;
    }

    #entry_panel {
        width: 38;
        min-width: 38;
    }

    .panel_title {
        color: #8effb0;
        text-style: bold;
        margin-bottom: 1;
    }

    #question_input {
        margin-bottom: 1;
    }

    #flash_message {
        color: #d4ff8f;
        height: 4;
    }

    .log_panel {
        border: solid #113a20;
        background: #020904;
        height: 1fr;
        overflow-y: auto;
        padding: 1;
    }

    .log_entry {
        border: solid #1f7a45;
        margin-bottom: 1;
        padding: 0 1 1 1;
    }

    .log_head {
        color: #8effb0;
        text-style: bold;
    }

    .log_block {
        border: round #113a20;
        margin-top: 1;
        padding: 0 1;
        color: #d3ffe1;
    }

    .empty_note {
        color: #6ab588;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("f5", "refresh_now", "Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.runtime = ShipCoreRuntime()
        self._last_render_key: tuple | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("REFERENCE LISTENING", id="status_line")
        with Horizontal(id="main"):
            with Vertical(classes="panel", id="entry_panel"):
                yield Static("UPLINK INPUT", classes="panel_title")
                yield Input(placeholder="Write message and press Enter", id="question_input", max_length=100)
                yield Static(
                    "Write message, press Enter, await response.\n"
                    "Messages are limited to 100 characters.\n"
                    "Replies appear from the radio channel.",
                    id="flash_message",
                )
            with Vertical(classes="panel"):
                yield Static("CURRENT LOG", classes="panel_title")
                yield Vertical(id="current_log", classes="log_panel")
            with Vertical(classes="panel"):
                yield Static("QUESTIONS AND RESPONSES", classes="panel_title")
                yield Vertical(id="archive_log", classes="log_panel")
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "Ship's Core"
        self.sub_title = "Terminal Console"
        await self.runtime.initialize()
        await self.refresh_view()
        self.set_interval(1.0, self._schedule_tick)

    async def _tick(self) -> None:
        await self.runtime.pump()
        await self.refresh_view()

    def _schedule_tick(self) -> None:
        self.run_worker(self._tick(), group="pump", exclusive=True)

    async def refresh_view(self) -> None:
        state = await self.runtime.state()
        current_questions = state.current_questions[:10]
        answered_questions = state.answered_questions[:5]
        render_key = (
            state.radio_online,
            tuple(
                (
                    question.id,
                    question.status.value,
                    question.text,
                    question.reply_text,
                    question.created_at,
                    question.answered_at,
                )
                for question in current_questions
            ),
            tuple(
                (
                    question.id,
                    question.status.value,
                    question.text,
                    question.reply_text,
                    question.created_at,
                    question.answered_at,
                )
                for question in answered_questions
            ),
        )
        if render_key == self._last_render_key:
            return

        self._last_render_key = render_key
        status_line = self.query_one("#status_line", Static)
        status_line.update("SHIPS CORE ACTIVE" if state.radio_online else "REFERENCE LISTENING")

        current_log = self.query_one("#current_log", Vertical)
        await current_log.remove_children()
        if current_questions:
            for question in current_questions:
                await current_log.mount(self._build_log_entry(question, include_reply=False))
        else:
            await current_log.mount(Static("No current questions in the queue.", classes="empty_note"))

        archive_log = self.query_one("#archive_log", Vertical)
        await archive_log.remove_children()
        if answered_questions:
            for question in answered_questions:
                await archive_log.mount(self._build_log_entry(question, include_reply=True))
        else:
            await archive_log.mount(Static("No responses recorded yet.", classes="empty_note"))

    def _build_log_entry(self, question: Question, include_reply: bool) -> Vertical:
        timestamp = question.answered_at if include_reply else question.created_at
        children = [
            Static(
                Text.assemble(
                    (format_timestamp(timestamp), "cyan"),
                    ("  ", ""),
                    (question.status.value.upper(), self._status_style(question.status.value)),
                ),
                classes="log_head",
            )
        ]
        children.append(Static(f"QUESTION\n{question.text}", classes="log_block"))
        if include_reply:
            children.append(Static(f"REPLY\n{question.reply_text or ''}", classes="log_block"))
        return Vertical(*children, classes="log_entry")

    def _status_style(self, status: str) -> str:
        return {
            "queued": "yellow",
            "active": "green",
            "timed_out": "red",
            "answered": "cyan",
        }.get(status, "white")

    @on(Input.Submitted, "#question_input")
    async def handle_submit(self, event: Input.Submitted) -> None:
        flash = self.query_one("#flash_message", Static)
        text = event.value.strip()

        if not text:
            flash.update("Question field is empty.")
            return

        if len(text) > 100:
            flash.update("Message too long. Keep it under 100 characters.")
            return

        await self.runtime.submit_question(text)
        question_input = self.query_one("#question_input", Input)
        question_input.value = ""
        flash.update("Query accepted. Awaiting response from the channel.")
        await self.refresh_view()

    async def action_refresh_now(self) -> None:
        await self.runtime.pump()
        await self.refresh_view()


def main() -> None:
    ShipCoreConsole().run()


if __name__ == "__main__":
    main()
