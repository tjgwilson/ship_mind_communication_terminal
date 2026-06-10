from __future__ import annotations

import logging
from datetime import datetime

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Static, TextArea

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
        width: 34;
        min-width: 34;
    }

    .panel_title {
        color: #8effb0;
        text-style: bold;
        margin-bottom: 1;
    }

    #sender_name {
        margin-bottom: 1;
    }

    #question_text {
        height: 12;
        margin-bottom: 1;
    }

    Button {
        width: 100%;
        margin-bottom: 1;
        background: #113a20;
        color: #d3ffe1;
    }

    #flash_message {
        color: #d4ff8f;
        height: 3;
    }

    DataTable {
        height: 1fr;
        background: #020904;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("f5", "refresh_now", "Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.runtime = ShipCoreRuntime()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("REFERENCE LISTENING", id="status_line")
        with Horizontal(id="main"):
            with Vertical(classes="panel", id="entry_panel"):
                yield Static("UPLINK INPUT", classes="panel_title")
                yield Input(placeholder="Name / callsign", id="sender_name")
                yield TextArea("", id="question_text")
                yield Button("Query The Core", id="submit_question", variant="primary")
                yield Static(
                    "Enter the question and send.\nReplies appear from the radio channel.",
                    id="flash_message",
                )
            with Vertical(classes="panel"):
                yield Static("CURRENT QUESTIONS", classes="panel_title")
                yield DataTable(id="current_table", zebra_stripes=True)
            with Vertical(classes="panel"):
                yield Static("QUESTIONS AND RESPONSES", classes="panel_title")
                yield DataTable(id="archive_table", zebra_stripes=True)
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "Ship's Core"
        self.sub_title = "Terminal Console"
        self._configure_tables()
        await self.runtime.initialize()
        await self.refresh_view()
        self.set_interval(1.0, self._schedule_tick)

    def _configure_tables(self) -> None:
        current = self.query_one("#current_table", DataTable)
        current.add_columns("ENTERED", "STATUS", "NAME", "QUESTION")
        current.cursor_type = "row"

        archive = self.query_one("#archive_table", DataTable)
        archive.add_columns("ANSWERED", "NAME", "QUESTION", "REPLY")
        archive.cursor_type = "row"

    async def _tick(self) -> None:
        await self.runtime.pump()
        await self.refresh_view()

    def _schedule_tick(self) -> None:
        self.run_worker(self._tick(), group="pump", exclusive=True)

    async def refresh_view(self) -> None:
        state = await self.runtime.state()
        status_line = self.query_one("#status_line", Static)
        if state.responder_id:
            label = f"SHIPS CORE ACTIVE | RESPONDER LINK {state.responder_id}"
        else:
            label = "REFERENCE LISTENING"
        status_line.update(label)

        current_table = self.query_one("#current_table", DataTable)
        current_table.clear(columns=False)
        for question in state.current_questions[:18]:
            current_table.add_row(
                format_timestamp(question.created_at),
                self._status_text(question.status.value),
                question.sender_name or "Unlisted",
                question.text,
            )

        archive_table = self.query_one("#archive_table", DataTable)
        archive_table.clear(columns=False)
        for question in state.answered_questions[:18]:
            archive_table.add_row(
                format_timestamp(question.answered_at),
                question.sender_name or "Unlisted",
                question.text,
                question.reply_text or "",
            )

    def _status_text(self, status: str) -> Text:
        styles = {
            "queued": "yellow",
            "active": "green",
            "timed_out": "red",
        }
        return Text(status.upper(), style=styles.get(status, "white"))

    @on(Button.Pressed, "#submit_question")
    async def handle_submit(self) -> None:
        sender_name = self.query_one("#sender_name", Input)
        question_text = self.query_one("#question_text", TextArea)
        flash = self.query_one("#flash_message", Static)

        text = question_text.text.strip()
        if not text:
            flash.update("Question field is empty.")
            return

        await self.runtime.submit_question(sender_name.value.strip() or "Unlisted", text)
        sender_name.value = ""
        question_text.load_text("")
        flash.update("Query accepted. Awaiting response from the channel.")
        await self.refresh_view()

    async def action_refresh_now(self) -> None:
        await self.runtime.pump()
        await self.refresh_view()


def main() -> None:
    ShipCoreConsole().run()


if __name__ == "__main__":
    main()
