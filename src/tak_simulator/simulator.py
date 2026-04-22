import asyncio

from tak_simulator.emulator import Emulator
from tak_simulator.time_keeper import TimeKeeper
from tak_simulator.scenario import Scenario
from tak_simulator.scenario_scheduler import ScenarioScheduler


class Simulator:
    def __init__(self):
        self.emulators: list[Emulator] = []
        self.time_keeper = TimeKeeper()
        self.scheduler = ScenarioScheduler(self.time_keeper)

    async def run(self, scenario: Scenario, host: str):
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.scheduler.run())

            for options in scenario.emulators:
                emulator = Emulator(options, self.time_keeper, self.scheduler, host)
                tg.create_task(emulator.run())
                self.emulators.append(emulator)

            self.time_keeper.start()
