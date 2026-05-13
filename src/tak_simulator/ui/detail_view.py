from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Log, Select, Static, TabPane


class EmulatorDetailMode(TabPane):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Select an emulator from the list.", id="detail_header")
            yield Log(id="detail_log")
            with Horizontal(id="chat_controls"):
                yield Select(
                    [],
                    prompt="From emulator",
                    id="chat_from_select",
                    allow_blank=True,
                )
                yield Select(
                    [],
                    prompt="To destination",
                    id="chat_to_select",
                    allow_blank=True,
                )
                yield Input(placeholder="Type a message...", id="chat_input")
                yield Button("Send", id="btn_send_chat", variant="primary")
