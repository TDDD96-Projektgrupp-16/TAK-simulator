from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Label, Select, TabPane


class LoadScenarioMode(TabPane):
    def compose(self) -> ComposeResult:
        with Vertical(id="load_container"):
            yield Label("Select from scenarios:")
            yield Select([], prompt="Choose a scenario...", id="scenario_select")

            yield Button("Load Scenario", id="btn_load", variant="primary")

    def on_mount(self) -> None:
        """Scan the scenarios directory and populate the dropdown."""
        select = self.query_one("#scenario_select", Select)
        scenarios_dir = Path("scenarios")

        if scenarios_dir.exists() and scenarios_dir.is_dir():
            options = [(f.name, str(f)) for f in scenarios_dir.glob("*.json")]
            select.set_options(options)
