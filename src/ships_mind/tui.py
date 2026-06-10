from __future__ import annotations

import logging
from datetime import datetime

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static

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

    .log_panel {
        border: solid #113a20;
        background: #020904;
        height: 1fr;
        overflow-y: auto;
        padding: 1;
        color: #8effb0;
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
            with Vertical(classes="panel"):
                yield Static("QUESTION QUEUE", classes="panel_title")
                yield Static("", id="current_log", classes="log_panel")
            with Vertical(classes="panel"):
                yield Static("QUESTION LOG", classes="panel_title")
                yield Static("", id="archive_log", classes="log_panel")
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "Ship's Core"
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
        answered_questions = state.answered_questions[:10]
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

        current_log = self.query_one("#current_log", Static)
        current_log.update(self._render_queue_lines(current_questions))

        archive_log = self.query_one("#archive_log", Static)
        archive_log.update(self._render_log_lines(answered_questions))

    def _render_queue_lines(self, questions) -> str:
        if not questions:
            return ""

        lines = []
        for question in questions:
            lines.append(
                f"{format_timestamp(question.created_at)}: {question.status.value}: {self._clip(question.text, 44)}"
            )
        return "\n".join(lines)

    def _render_log_lines(self, questions) -> str:
        if not questions:
            return ""

        lines = []
        for question in questions:
            lines.append(
                f"{format_timestamp(question.created_at)}: question: {self._clip(question.text, 40)}"
            )
            lines.append(
                f"{format_timestamp(question.answered_at)}: answer: {self._clip(question.reply_text or '', 42)}"
            )
        return "\n".join(lines)

    def _clip(self, text: str, limit: int) -> str:
        cleaned = " ".join(text.split())
        if len(cleaned) <= limit:
            return cleaned
        return f"{cleaned[:limit - 3]}..."

    @on(Input.Submitted, "#question_input")
    async def handle_submit(self, event: Input.Submitted) -> None:
        text = event.value.strip()

        if not text:
            return

        if len(text) > 100:
            return

        await self.runtime.submit_question(text)
        question_input = self.query_one("#question_input", Input)
        question_input.value = ""
        await self.refresh_view()

    async def action_refresh_now(self) -> None:
        await self.runtime.pump()
        await self.refresh_view()


def main() -> None:
    ShipCoreConsole().run()


if __name__ == "__main__":
    main()
