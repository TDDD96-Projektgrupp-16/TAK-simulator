import asyncio

from tak_simulator.time_keeper import TimeKeeper
from tak_simulator.emulator import Emulator
from tak_simulator.scenario import Scenario


class Simulator:
    def __init__(self):
        self.emulators: list[Emulator] = []
        self.time_keeper: TimeKeeper = TimeKeeper()

    async def run(self, scenario: Scenario, host: str):
        async with asyncio.TaskGroup() as tg:
            for options in scenario.emulators:
                emulator = Emulator(options, self.time_keeper, host)
                tg.create_task(emulator.run())
                self.emulators.append(emulator)

            self.time_keeper.unpause()