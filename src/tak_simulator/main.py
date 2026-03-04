import asyncio
import argparse

from tak_simulator.config import Config
from tak_simulator.time_keeper import TimeKeeper
from tak_simulator.util import host_ip
from tak_simulator.emulator import Emulator


def main():
    args = get_args()

    with open(args.filename) as f:
        config = f.read()

    config = Config.from_str(config)
    host = host_ip()

    asyncio.run(run(config, host))


async def run(config: Config, host: str):
    time_keeper = TimeKeeper()

    async with asyncio.TaskGroup() as tg:
        for conf in config.emulators:
            emulator = Emulator(conf, time_keeper, host)
            tg.create_task(emulator.run())

        time_keeper.unpause()


def get_args():
    parser = argparse.ArgumentParser("tak_emulator")
    parser.add_argument("filename", metavar="SCENARIO")
    return parser.parse_args()


if __name__ == "__main__":
    main()
