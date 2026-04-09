import argparse
import asyncio
import logging

from tak_simulator.emulator import Emulator
from tak_simulator.logging_conf import logging_setup
from tak_simulator.scenario import Scenario, load_scenario
from tak_simulator.time_keeper import TimeKeeper
from tak_simulator.util import host_ip

logger = logging.getLogger(__name__)


def main():
    args = get_args()

    logging_setup(args.log)

    scenario = load_scenario(args.filename)

    host = host_ip()

    asyncio.run(run(scenario, host))


async def run(scenario: Scenario, host: str):
    time_keeper = TimeKeeper()

    async with asyncio.TaskGroup() as tg:
        for options in scenario.emulators:
            emulator = Emulator(options, time_keeper, host)
            tg.create_task(emulator.run())

        time_keeper.unpause()


def get_args():
    parser = argparse.ArgumentParser("tak_emulator")
    parser.add_argument("filename", metavar="SCENARIO")
    parser.add_argument("--log", default="INFO")
    return parser.parse_args()


if __name__ == "__main__":
    main()
