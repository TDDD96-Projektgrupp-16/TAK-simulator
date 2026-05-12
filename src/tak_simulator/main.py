from tak_simulator.cli import get_args
from tak_simulator.logging_conf import logging_setup
from tak_simulator.tak import TAK
from tak_simulator.ui import TakApp


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


if __name__ == "__main__":
    main()
