from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Log, Static, TabPane


class EmulatorDetailMode(TabPane):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Select an emulator from the list.", id="detail_header")
            yield Log(id="detail_log")
            with Horizontal(id="msg_container"):
                ...
