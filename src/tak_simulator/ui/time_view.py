from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, TabPane

class TimeTrackerMode(TabPane):
    def compose(self) -> ComposeResult:
        with Vertical(id="time_container"):
            yield Label("Simulation Time: 0.00s", id="time_display")
            yield Label("Status: Stopped", id="time_status")
            with Horizontal():
                yield Button("Start", id="btn_start", variant="success")
                yield Button("Pause", id="btn_pause", variant="warning")
                yield Button("Stop", id="btn_stop", variant="error")