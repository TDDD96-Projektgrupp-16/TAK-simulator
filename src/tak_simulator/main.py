import argparse

from tak_simulator.logging_conf import logging_setup
from tak_simulator.ui import TakApp

import logging

logger = logging.getLogger(__name__)


def main():
    args = get_args()
    logging_setup(args.log)

    app = TakApp(filename=args.filename)
    app.run()


def get_args():
    parser = argparse.ArgumentParser("tak_emulator")
    parser.add_argument("--filename", metavar="SCENARIO", nargs=1 ,default=None)
    parser.add_argument("--log", default="INFO")
    return parser.parse_args()


if __name__ == "__main__":
    main()
