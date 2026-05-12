import logging

from textual.app import App, ComposeResult
from textual.message import Message
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Log,
    RadioSet,
    Select,
    Static,
    TabbedContent,
)

from tak_simulator.scenario import load_scenario
from tak_simulator.simulator import Simulator
from tak_simulator.ui.detail_view import EmulatorDetailMode
from tak_simulator.ui.list_view import EmulatorListMode
from tak_simulator.ui.load_view import LoadScenarioMode
from tak_simulator.ui.log_view import SystemLogsMode
from tak_simulator.ui.time_view import TimeTrackerMode


class SystemLogMessage(Message):
    def __init__(self, log_line: str):
        super().__init__()
        self.log_line = log_line


class TextualLogHandler(logging.Handler):
    def __init__(self, app: App):
        super().__init__()
        self.app = app
        self.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    def emit(self, record):
        try:
            msg = self.format(record)
            self.app.post_message(SystemLogMessage(msg))
        except Exception:
            self.handleError(record)


class TakApp(App):
    CSS = """
    #load_container, #time_container { padding: 2; height: auto; }
    #time_display { text-style: bold; color: green; margin-bottom: 1; }
    #msg_container { height: 3; margin-top: 1; }
    #msg_input { width: 1fr; }
    #detail_header { padding: 1; background: $surface; margin-bottom: 1; }
    #detail_log { border: solid $primary; height: 1fr; }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, filename: str | None = None):
        super().__init__()
        self.filename = filename
        self.simulator = Simulator()
        self.scenario = None
        self.active_uid = None

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="tabs"):
            yield LoadScenarioMode("1. Load Scenario", id="mode_load")
            yield TimeTrackerMode("2. Time Controls", id="mode_time")
            yield EmulatorListMode("3. Emulator List", id="mode_list")
            yield EmulatorDetailMode("4. Emulator Detail", id="mode_detail")
            yield SystemLogsMode("5. System Logs", id="mode_logs")
        yield Footer()

    async def on_mount(self) -> None:
        # set up logger - remove stdout handlers to avoid clashing with TUI
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            if isinstance(handler, logging.StreamHandler):
                root_logger.removeHandler(handler)
        self.textual_log_handler = TextualLogHandler(self)
        root_logger.addHandler(self.textual_log_handler)

        # set up data table
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_column("Callsign", key="callsign")
        table.add_column("UID", key="uid")
        table.add_column("Type", key="type")
        table.add_column("Status", key="status")

        if self.filename:
            try:
                self.query_one("#scenario_select", Select).value = self.filename
            except Exception:
                pass

        self.set_interval(0.1, self.update_view_state)

    def on_unmount(self) -> None:
        logging.getLogger().removeHandler(self.textual_log_handler)

    def on_system_log_message(self, message: SystemLogMessage) -> None:
        try:
            log_widget = self.query_one("#system_log", Log)
            log_widget.write_line(message.log_line)
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn_load":
            select = self.query_one("#scenario_select", Select)

            if select.value and select.value != Select.BLANK:
                self.load_scenario(str(select.value))
            else:
                self.notify(
                    "Please select a scenario from the dropdown.", severity="warning"
                )

        elif btn_id == "btn_start":
            if self.simulator.time_keeper.get_time() > 0.0:
                self.simulator.time_keeper.unpause()
            else:
                if not self.scenario:
                    self.notify("Please select a scenario first.", severity="warning")
                    return
                self.run_worker(
                    self.simulator.run(self.scenario), exclusive=True, thread=False
                )
        elif btn_id == "btn_pause":
            self.simulator.time_keeper.pause()
        elif btn_id == "btn_stop":
            self._stop_simulation()

    def load_scenario(self, filename: str):
        try:
            if self.simulator.time_keeper.get_time() > 0:
                self._stop_simulation()

            self.scenario = load_scenario(filename)

            self.notify(f"Loaded {filename} successfully.")

            self._change_tab("mode_time")
        except Exception as e:
            self.notify(f"Error loading scenario: {e}", severity="error")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "speed_radio_set":
            try:
                speed_str = (
                    event.pressed.id.split("_")[1]
                    + "."
                    + event.pressed.id.split("_")[2]
                )
                speed_multiplier = float(speed_str)

                self.simulator.time_keeper.set_speed(speed_multiplier)
                self.notify(f"Simulation speed set to {speed_multiplier}x")

            except Exception as e:
                self.notify(f"Error setting speed: {e}", severity="error")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.active_uid = event.row_key.value
        self._change_tab("mode_detail")
        self.query_one("#detail_log", Log).clear()
        self.query_one("#detail_log", Log).write_line(
            f"--- Connected to {self.active_uid} ---"
        )

    def update_view_state(self):
        time_display = self.query_one("#time_display", Label)
        status_display = self.query_one("#time_status", Label)

        current_time = self.simulator.time_keeper.get_time()
        is_paused = self.simulator.time_keeper.is_paused

        time_display.update(f"Simulation Time: {current_time:.2f}s")
        status_display.update(
            f"Status: {
                'Running'
                if not is_paused
                else 'Paused'
                if self.simulator.time_keeper.get_time() > 0.0
                else 'Stopped'
            }"
        )

        table = self.query_one(DataTable)
        for emu in self.simulator.emulators:
            status_text = "Online" if emu.is_connected else "Offline"
            if emu.options.uid in table.rows:
                table.update_cell(emu.options.uid, "status", status_text)
            else:  # not in table
                table.add_row(
                    emu.options.callsign,
                    emu.options.uid,
                    emu.options.type,
                    status_text,
                    key=emu.options.uid,
                )

        if self.active_uid:
            emu = next(
                (
                    e
                    for e in self.simulator.emulators
                    if e.options.uid == self.active_uid
                ),
                None,
            )
            if emu:
                header = self.query_one("#detail_header", Static)
                header.update(
                    f"[b]{emu.options.callsign}[/b] | {emu.options.uid} | {'Online' if emu.is_connected else 'Offline'}"
                )

    def send_message(self, message: str):
        if not self.active_uid or not message:
            return
        emu = next(
            (e for e in self.simulator.emulators if e.options.uid == self.active_uid),
            None,
        )
        if emu:
            log = self.query_one("#detail_log", Log)
            current_time = self.simulator.time_keeper.get_time()
            log.write_line(f"[{current_time:.2f}s] Sent: {message}")
            self.query_one("#msg_input", Input).value = ""

    def _stop_simulation(self):
        self.simulator.stop()
        self.query_one(DataTable).clear()
        self.query_one("#speed_radio_set").value = "speed_1.0"
        if self.active_uid:
            self.active_uid = None
            self.query_one("#detail_header", Static).update(
                "Select an emulator from the list."
            )
            self.query_one("#detail_log", Log).clear()

    def _change_tab(self, tab_id: str):
        self.query_one(TabbedContent).active = tab_id
        self.screen.set_focus(None)
