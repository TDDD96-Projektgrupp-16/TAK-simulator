from textual.app import ComposeResult
from textual.widgets import Log, TabPane

class SystemLogsMode(TabPane):
    def compose(self) -> ComposeResult:
        yield Log(id="system_log", highlight=True)