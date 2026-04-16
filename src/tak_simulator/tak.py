import asyncio

from tak_simulator.scenario import load_scenario
from tak_simulator.util import host_ip
from tak_simulator.simulator import Simulator


class TAK:
    def __init__(self, filename = None):
        
        self.simulator = None
        self.filename = filename
    

    def start(self):
        if self.filename is None: 
            return
        scenario = load_scenario(self.filename)

        host = host_ip()
        self.simulator = Simulator()

        asyncio.run(self.simulator.run(scenario, host))     