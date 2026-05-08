from textual.app import ComposeResult
from textual.widgets import DataTable, TabPane


class EmulatorListMode(TabPane):
    def compose(self) -> ComposeResult:
        yield DataTable(id="emulator_table")
