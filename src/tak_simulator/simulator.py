import asyncio
import logging
from pathlib import Path
from typing import Any, List, Tuple

from tak_simulator.emulator import Emulator
from tak_simulator.network.multicast import MulticastHandler
from tak_simulator.network.server import Server
from tak_simulator.scenario import Scenario
from tak_simulator.scenario_scheduler import ScenarioScheduler
from tak_simulator.time_keeper import TimeKeeper
from tak_simulator.wire import TakEnvelope
from tak_simulator.wire.v0 import V0Codec

logger = logging.getLogger(__name__)

DEFAULT_START_PORT = 8000


class Simulator:
    def __init__(self):
        self.emulators: list[Emulator] = []
        self.time_keeper = TimeKeeper()
        self.scheduler = ScenarioScheduler(self.time_keeper)

        self.servers: List[Server] = []

        if Path("./certs/ca.pem").exists():
            self.servers.append(
                Server(
                    "192.71.171.115",
                    "./certs/ca.pem",
                    "./certs/client.pem",
                    "./certs/client.key",
                    V0Codec(),
                )
            )

    async def run(self, scenario: Scenario):
        port = DEFAULT_START_PORT
        async with asyncio.TaskGroup() as tg:
            self.multicast = await MulticastHandler.create_multicast_connection(
                V0Codec(),
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

    def stop(self):
        self.time_keeper.stop()
        self.scheduler.stop()
        self.scheduler.clear()

        if hasattr(self, 'multicast') and self.multicast and self.multicast.transport:
            self.multicast.transport.close()

        for emu in self.emulators:
            emu.is_connected = False
            if hasattr(emu, 'connection') and emu.connection and emu.connection._server:
                emu.connection._server.close()
        
        self.emulators.clear()
