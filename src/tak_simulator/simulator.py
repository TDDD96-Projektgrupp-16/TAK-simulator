import asyncio
import logging
from typing import Any, Tuple

from tak_simulator.emulator import Emulator
from tak_simulator.network.multicast import MulticastHandler
from tak_simulator.network.server import Server, ServerConfig
from tak_simulator.scenario import Scenario
from tak_simulator.scenario_scheduler import ScenarioScheduler
from tak_simulator.time_keeper import TimeKeeper
from tak_simulator.wire import TakEnvelope
from tak_simulator.wire.v0 import V0Codec
from tak_simulator.wire.v1 import V1Codec

logger = logging.getLogger(__name__)

DEFAULT_START_PORT = 8000


class Simulator:
    def __init__(self, server_configs: list[ServerConfig] | None = None):
        self.emulators: list[Emulator] = []
        self.time_keeper = TimeKeeper()
        self.scheduler = ScenarioScheduler(self.time_keeper)

        if server_configs is None:
            server_configs = []

        self.servers = [
            Server(
                ip=config.ip,
                port=config.port,
                codec=V0Codec(),
                cafile=config.cafile,
                certfile=config.certfile,
                keyfile=config.keyfile,
                upgrade=config.upgrade,
            )
            for config in server_configs
        ]
        self.servers = []  # ingen server

    async def run(self, scenario: Scenario):
        port = DEFAULT_START_PORT
        async with asyncio.TaskGroup() as tg:
            self.multicast = await MulticastHandler.create_multicast_connection(
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

            tg.create_task(self.rea())

            self.time_keeper.start()

    async def rea(self):
        for i in range(40):
            await asyncio.sleep(10)
            a = "ANDROID-dbdc90afc2ca1328"
            # a = "argar"
            logger.info(f"Sending chat message to {a}")
            await self.emulators[0].send_msg(a, "Hej")

    def data_received(self, data: TakEnvelope, addr: Tuple[str | Any, int]) -> None:
        """Multicast data received handler. If we need to handle it, we can do so here."""
        logger.debug(f"Received data from {addr}: {data}")

    def stop(self):
        self.time_keeper.stop()
        self.scheduler.stop()
        self.scheduler.clear()

        if hasattr(self, "multicast") and self.multicast and self.multicast.transport:
            self.multicast.transport.close()

        for emu in self.emulators:
            emu.is_connected = False
            if hasattr(emu, "connection") and emu.connection and emu.connection._server:
                emu.connection._server.close()

        self.emulators.clear()
