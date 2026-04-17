import argparse

from tak_simulator.logging_conf import logging_setup
from tak_simulator.tak import TAK

import logging

logger = logging.getLogger(__name__)


def main():
    args = get_args()
    logging_setup(args.log)

    app = TAK(args.filename)
    app.start()


def get_args():
    parser = argparse.ArgumentParser("tak_emulator")
    parser.add_argument("filename", metavar="SCENARIO")
    parser.add_argument("--log", default="INFO")
    return parser.parse_args()


if __name__ == "__main__":
    main()
