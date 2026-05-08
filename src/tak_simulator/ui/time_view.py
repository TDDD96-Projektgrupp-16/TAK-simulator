from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, RadioButton, RadioSet, TabPane


class TimeTrackerMode(TabPane):
    DEFAULT_CSS = """
    #speed_controls {
        height: auto;
        align: center middle;
        background: $panel;
        padding: 1 1;
        border: panel $primary;
        width: auto;
    }

    #speed_label {
        content-align: left middle;
        text-style: bold;
        margin-right: 2;
        color: $text;
    }

    #speed_radio_set {
        layout: horizontal;
        border: none;
        height: auto;
        background: transparent;
    }

    #speed_radio_set > RadioButton {
        margin: 0 1;
        background: transparent;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="time_container"):
            yield Label("Simulation Time: 0.00s", id="time_display")
            yield Label("Status: Stopped", id="time_status")
            with Horizontal(id="control_buttons"):
                yield Button("Start", id="btn_start", variant="success")
                yield Button("Pause", id="btn_pause", variant="warning")
                yield Button("Stop", id="btn_stop", variant="error")
            with Horizontal(id="speed_controls"):
                yield Label("Playback speed:", id="speed_label")
                with RadioSet(id="speed_radio_set"):
                    yield RadioButton("0.5x", id="speed_0_5")
                    yield RadioButton("1x", id="speed_1_0", value=True)
                    yield RadioButton("2x", id="speed_2_0")
                    yield RadioButton("5x", id="speed_5_0")
                    yield RadioButton("10x", id="speed_10_0")
                    yield RadioButton("100x", id="speed_100_0")
                    yield RadioButton("1000x", id="speed_1000_0")
