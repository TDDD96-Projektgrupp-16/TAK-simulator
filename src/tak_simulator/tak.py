import asyncio
import threading
import time

from tak_simulator.scenario import load_scenario
from tak_simulator.util import host_ip
from tak_simulator.simulator import Simulator

def _start_background_loop(loop: asyncio.AbstractEventLoop):
    """Helper to run the event loop in a background thread."""
    asyncio.set_event_loop(loop)
    loop.run_forever()

class TAK:
    def __init__(self, filename = None):
        
        self.simulator = None
        self.filename = filename

        self.loop = asyncio.new_event_loop()
        threading.Thread(target=_start_background_loop, args=(self.loop,), daemon=True).start()


    def start(self):
        if self.filename is None: 
            return
        scenario = load_scenario(self.filename)

        host = host_ip()
        self.simulator = Simulator()

        asyncio.run_coroutine_threadsafe(
            self.simulator.run(scenario, host), 
            self.loop
        )