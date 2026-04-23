import asyncio

from tak_simulator.emulator import Emulator
from tak_simulator.scenario import Scenario
from tak_simulator.scenario_scheduler import ScenarioScheduler
from tak_simulator.time_keeper import TimeKeeper


class Simulator:
    def __init__(self):
        self.emulators: list[Emulator] = []
        self.time_keeper = TimeKeeper()
        self.scheduler = ScenarioScheduler(self.time_keeper)
        self.first_port = 8000

    async def run(self, scenario: Scenario):
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.scheduler.run())

            for options in scenario.emulators:
                emulator = Emulator(
                    options, self.time_keeper, self.scheduler, self.first_port
                )
                self.first_port += 1
                tg.create_task(emulator.run())
                self.emulators.append(emulator)

            self.time_keeper.start()
