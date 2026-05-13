import logging
import sys

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

from tak_simulator.network.server import ServerConfig
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
            logging.Formatter("%(asctime)s [%(levelname)-5s] %(name)s: %(message)s")
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
    #chat_controls { height: auto; margin-top: 1; padding: 1 2; }
    #chat_controls > * { margin-right: 1; }
    #chat_controls Select { min-width: 30; }
    #chat_input { width: 1fr; }
    #detail_header { padding: 1; background: $surface; margin-bottom: 1; }
    #detail_log { border: solid $primary; height: 1fr; }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(
        self,
        filename: str | None = None,
        server_configs: list[ServerConfig] | None = None,
    ):
        super().__init__()
        self.filename = filename
        if server_configs is None:
            server_configs = []
        self.server_configs = server_configs
        self.simulator = Simulator(server_configs=self.server_configs)
        self.scenario = None
        self.active_uid = None
        self._chat_from_uids: tuple[str, ...] = ()
        self._chat_to_options: tuple[tuple[str, str], ...] = ()
        self._tui_sent_keys: set[tuple[str, str, str]] = set()
        self._msg_log_per_uid: dict[str, list[str]] = {}
        self._msg_keys_per_uid: dict[str, set[tuple[str, str, str, str]]] = {}

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
        # keep any existing stderr/warning handlers
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            if isinstance(handler, logging.StreamHandler) and getattr(handler, "stream", None) is sys.stdout:
                root_logger.removeHandler(handler)
        self.textual_log_handler = TextualLogHandler(self)
        root_logger.addHandler(self.textual_log_handler)

        if not any(
            isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is sys.stderr
            for h in root_logger.handlers
        ):
            stderr_handler = logging.StreamHandler(sys.stderr)
            stderr_handler.setLevel(logging.WARNING)
            stderr_handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            )
            root_logger.addHandler(stderr_handler)

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

        self.set_interval(0.5, self.update_view_state)
        self.set_interval(1.0, self._refresh_chat_targets)

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

            if select.value and select.value != Select.NULL:
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
        elif btn_id == "btn_send_chat":
            self._submit_chat_message()

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
        log = self.query_one("#detail_log", Log)
        log.clear()
        log.write_line(
            f"--- Connected to {self.active_uid} ---"
        )
        for line in self._msg_log_per_uid.get(self.active_uid, []):
            log.write_line(line)

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
            status_text = "Online"
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
                    f"[b]{emu.options.callsign}[/b] | {emu.options.uid} | Online"
                )

            log = self.query_one("#detail_log", Log)
            all_received: list = list(self.simulator.received_messages)
            for e in self.simulator.emulators:
                all_received.extend(e.get_received_messages())

            keys = self._msg_keys_per_uid.setdefault(self.active_uid, set())
            stored = self._msg_log_per_uid.setdefault(self.active_uid, [])

            for recv in all_received:
                sent_key = (recv.from_uid, recv.to_uid, recv.message)
                if sent_key in self._tui_sent_keys and recv.from_uid == self.active_uid:
                    continue
                key = (recv.from_uid, recv.to_uid, recv.message, recv.from_callsign)
                if key in keys:
                    continue
                if recv.to_uid == self.active_uid or recv.from_uid == self.active_uid:
                    line = f"[{self.simulator.time_keeper.get_time():.2f}s] From {recv.from_callsign} ({recv.from_uid}): {recv.message}"
                    log.write_line(line)
                    stored.append(line)
                keys.add(key)

        self._refresh_chat_from_options()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat_input":
            self._submit_chat_message()

    def send_message(self, from_uid: str, to_uid: str, message: str) -> None:
        if not from_uid or not to_uid or not message:
            return
        emu = next(
            (e for e in self.simulator.emulators if e.options.uid == from_uid),
            None,
        )
        if emu is None:
            self.notify("Select a valid sender emulator.", severity="warning")
            return
        if not hasattr(emu, "connection") or emu.connection is None:
            self.notify("Sender emulator is not connected yet.", severity="warning")
            return
        self.run_worker(
            emu.send_msg(to_uid, message), exclusive=False, thread=False
        )
        self._tui_sent_keys.add((from_uid, to_uid, message))
        log = self.query_one("#detail_log", Log)
        current_time = self.simulator.time_keeper.get_time()
        line = f"[{current_time:.2f}s] Sent to {to_uid}: {message}"
        log.write_line(line)
        if from_uid in self._msg_log_per_uid:
            self._msg_log_per_uid[from_uid].append(line)
        self.query_one("#chat_input", Input).value = ""

    def _stop_simulation(self):
        self.simulator.stop()
        self.query_one(DataTable).clear()
        self.query_one("#speed_radio_set").value = "speed_1.0"
        self._reset_chat_controls()
        self._tui_sent_keys.clear()
        self._msg_log_per_uid.clear()
        self._msg_keys_per_uid.clear()
        if self.active_uid:
            self.active_uid = None
            self.query_one("#detail_header", Static).update(
                "Select an emulator from the list."
            )
            self.query_one("#detail_log", Log).clear()

    def _change_tab(self, tab_id: str):
        self.query_one(TabbedContent).active = tab_id
        self.screen.set_focus(None)

    def _reset_chat_controls(self) -> None:
        self.query_one("#chat_from_select", Select).clear()
        self.query_one("#chat_to_select", Select).clear()
        self.query_one("#chat_input", Input).value = ""
        self._chat_from_uids = ()
        self._chat_to_options = ()

    def _refresh_chat_from_options(self) -> None:
        from_select = self.query_one("#chat_from_select", Select)
        current_uids = tuple(emu.options.uid for emu in self.simulator.emulators)
        if current_uids != self._chat_from_uids:
            self._chat_from_uids = current_uids
            previous_value = from_select.value
            from_options = [
                (f"{emu.options.callsign} ({emu.options.uid})", emu.options.uid)
                for emu in self.simulator.emulators
            ]
            if from_options:
                from_select.set_options(from_options)
                if previous_value in current_uids:
                    from_select.value = previous_value
                elif self.active_uid in current_uids:
                    from_select.value = self.active_uid
            else:
                from_select.clear()
                return

        if (
            from_select.value in (None, Select.NULL)
            and self.active_uid in current_uids
        ):
            from_select.value = self.active_uid

    def _refresh_chat_targets(self) -> None:
        to_select = self.query_one("#chat_to_select", Select)
        known: dict[str, str] = {}
        for emu in self.simulator.emulators:
            known.update(emu.get_known_users())

        for emu in self.simulator.emulators:
            known.setdefault(emu.options.uid, emu.options.callsign)

        sorted_known = sorted(known.items(), key=lambda item: item[1])
        option_keys = tuple(sorted_known)
        if option_keys != self._chat_to_options:
            self._chat_to_options = option_keys
            previous_value = to_select.value
            options = [(f"{callsign} ({uid})", uid) for uid, callsign in sorted_known]
            if options:
                to_select.set_options(options)
                if previous_value in known:
                    to_select.value = previous_value
            else:
                to_select.clear()
                return

        if to_select.value in (None, Select.NULL) and sorted_known:
            to_select.value = sorted_known[0][0]

    def _submit_chat_message(self) -> None:
        from_select = self.query_one("#chat_from_select", Select)
        to_select = self.query_one("#chat_to_select", Select)
        message_input = self.query_one("#chat_input", Input)
        message = message_input.value.strip()
        from_uid = from_select.value
        to_uid = to_select.value
        if from_uid in (None, Select.NULL):
            self.notify("Select a sender emulator.", severity="warning")
            return
        if to_uid in (None, Select.NULL):
            self.notify("Select a destination.", severity="warning")
            return
        if not message:
            self.notify("Enter a chat message.", severity="warning")
            return
        self.send_message(str(from_uid), str(to_uid), message)
