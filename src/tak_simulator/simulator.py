import asyncio
import logging
from typing import Any, List, Tuple

from tak_simulator.emulator import Emulator
from tak_simulator.network_handler import NetworkHandler, Server
from tak_simulator.scenario import Scenario
from tak_simulator.scenario_scheduler import ScenarioScheduler
from tak_simulator.time_keeper import TimeKeeper

logger = logging.getLogger(__name__)

DEFAULT_PORT = 8000


class Simulator:
    def __init__(self):
        self.emulators: list[Emulator] = []
        self.time_keeper = TimeKeeper()
        self.scheduler = ScenarioScheduler(self.time_keeper)
        self.multicast_addr: Tuple[str, int] = ("239.2.3.1", 6969)  # TODO
        self.servers: List[Server] = [
            Server(
                "192.71.171.115",
                "./certs/ca.pem",
                "./certs/client.pem",
                "./certs/client.key",
            )
        ]

    async def run(self, scenario: Scenario):
        async with asyncio.TaskGroup() as tg:
            self.connection = await NetworkHandler.create_connection(
                self.multicast_addr[0],
                self.multicast_addr[1],
                DEFAULT_PORT,
                self.data_received,
                self.servers,
            )

            tg.create_task(self.scheduler.run())

            for options in scenario.emulators:
                emulator = Emulator(
                    options,
                    self.time_keeper,
                    self.scheduler,
                    self.connection,
                )
                tg.create_task(emulator.run())
                self.emulators.append(emulator)

            self.time_keeper.start()

    def data_received(self, data: bytes, addr: Tuple[str | Any, int]) -> None:
        logger.debug(f"Received data from {addr}")
