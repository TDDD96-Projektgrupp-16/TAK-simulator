import asyncio
import logging
from typing import Any, List, Tuple

from tak_simulator.emulator import Emulator
from tak_simulator.network.multicast import MulticastHandler
from tak_simulator.network.server import Server
from tak_simulator.scenario import Scenario
from tak_simulator.scenario_scheduler import ScenarioScheduler
from tak_simulator.time_keeper import TimeKeeper
from tak_simulator.wire import TakEnvelope
from tak_simulator.wire.v0 import V0Codec
from tak_simulator.wire.v1 import V1Codec

logger = logging.getLogger(__name__)

DEFAULT_START_PORT = 8000


class Simulator:
    def __init__(self):
        self.emulators: list[Emulator] = []
        self.time_keeper = TimeKeeper()
        self.scheduler = ScenarioScheduler(self.time_keeper)
        self.servers: List[Server] = [
            Server(
                "192.71.171.116",
                "./certs/ca.pem",
                "./certs/client.pem",
                "./certs/client.key",
                V0Codec(),
            )
        ]

    async def run(self, scenario: Scenario):
        port = DEFAULT_START_PORT
        async with asyncio.TaskGroup() as tg:
            self.multicast = await MulticastHandler.create_multicast_connection(
                V1Codec(),
                self.data_received,
            )

            tg.create_task(self.scheduler.run())

            for options in scenario.emulators:
                emulator = Emulator(
                    options,
                    self.time_keeper,
                    self.scheduler,
                    self.multicast,
                    port,
                    self.servers,
                )
                port += 1
                tg.create_task(emulator.run())
                self.emulators.append(emulator)

            self.time_keeper.start()

    def data_received(self, data: TakEnvelope, addr: Tuple[str | Any, int]) -> None:
        """Multicast data received handler. If we need to handle it, we can do so here."""
        logger.debug(f"Received data from {addr}")
