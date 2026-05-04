import argparse

from tak_simulator.logging_conf import logging_setup
from tak_simulator.ui import TakApp
from tak_simulator.tak import TAK

import logging

logger = logging.getLogger(__name__)


def main():
    args = get_args()
    logging_setup(args.log)

    if args.notui:
        if not args.filename:
            print("Error: SCENARIO filename is required when running in headless mode.")
            return
        print(f"Running headless simulation for {args.filename}. Press Ctrl+C to stop.")
        app = TAK(filename=args.filename)
        app.start()
    else:
        app = TakApp(filename=args.filename)
        app.run()
        


def get_args():
    parser = argparse.ArgumentParser("tak_emulator")
    parser.add_argument("--filename", metavar="SCENARIO" ,default=None)
    parser.add_argument("--log", default="INFO")
    parser.add_argument("--notui", action="store_true", help="Disable Tui")
    return parser.parse_args()


if __name__ == "__main__":
    main()
