from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Label, Select, TabPane


class LoadScenarioMode(TabPane):
    def compose(self) -> ComposeResult:
        with Vertical(id="load_container"):
            yield Label("Select from examples:")
            yield Select([], prompt="Choose a scenario...", id="scenario_select")

            yield Button("Load Scenario", id="btn_load", variant="primary")

    def on_mount(self) -> None:
        """Scan the examples directory and populate the dropdown."""
        select = self.query_one("#scenario_select", Select)
        examples_dir = Path("examples")

        if examples_dir.exists() and examples_dir.is_dir():
            options = [(f.name, str(f)) for f in examples_dir.glob("*.json")]
            select.set_options(options)
