import asyncio
import threading

from tak_simulator.scenario import load_scenario
from tak_simulator.simulator import Simulator


def _start_background_loop(loop: asyncio.AbstractEventLoop):
    """Helper to run the event loop in a background thread."""
    asyncio.set_event_loop(loop)
    loop.run_forever()


class TAK:
    def __init__(self, filename=None):
        self.active_uid = None
        self.simulator = None
        self.filename = filename

        self.loop = asyncio.new_event_loop()
        threading.Thread(
            target=_start_background_loop, args=(self.loop,), daemon=True
        ).start()

    def start(self):
        if self.filename is None:
            return
        scenario = load_scenario(self.filename)

        self.simulator = Simulator()

        asyncio.run_coroutine_threadsafe(
            self.simulator.run(scenario), self.loop
        )

        self._run_loop()

    def _run_loop(self):
        try:
            while True:
                ...
        except KeyboardInterrupt:
            pass # Caught Ctrl+C
        finally:
            self.simulator.stop()
            print("\nSimulator shut down safely.")
