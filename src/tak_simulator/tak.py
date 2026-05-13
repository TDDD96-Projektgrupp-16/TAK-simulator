import asyncio
import logging
import time
import threading

from tak_simulator.network.server import ServerConfig
from tak_simulator.scenario import load_scenario
from tak_simulator.simulator import Simulator

logger = logging.getLogger(__name__)


def _start_background_loop(loop: asyncio.AbstractEventLoop):
    """Helper to run the event loop in a background thread."""
    asyncio.set_event_loop(loop)
    loop.run_forever()


class TAK:
    def __init__(self, filename=None, server_configs: list[ServerConfig] | None = None):
        self.simulator = None
        self.filename = filename
        if server_configs is None:
            server_configs = []
        self.server_configs = server_configs

        self.loop = asyncio.new_event_loop()
        threading.Thread(
            target=_start_background_loop, args=(self.loop,), daemon=True
        ).start()

    def start(self):
        if self.filename is None:
            return
        scenario = load_scenario(self.filename)

        self.simulator = Simulator(server_configs=self.server_configs)

        self._run_future = asyncio.run_coroutine_threadsafe(
            self.simulator.run(scenario), self.loop
        )

        self._run_loop()

    def _run_loop(self):
        try:
            last_tick = 0.0
            while True:
                if self._run_future.done():
                    exc = self._run_future.exception()
                    if exc is not None:
                        logger.error("Simulator failed: %s", exc)
                    break
                t = self.simulator.time_keeper.get_time()
                if t - last_tick >= 5.0:
                    logger.info(
                        "Simulation running at %.2fs with %d emulator(s)",
                        t,
                        len(self.simulator.emulators),
                    )
                    last_tick = t
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.simulator.stop()
            print("\nSimulator shut down safely.")
