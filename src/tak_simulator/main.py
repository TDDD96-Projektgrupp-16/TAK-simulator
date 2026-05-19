import logging

from tak_simulator.cli import get_args
from tak_simulator.logging_conf import logging_setup
from tak_simulator.tak import TAK
from tak_simulator.ui import TakApp

logger = logging.getLogger(__name__)


def main():
    args = get_args()
    logging_setup(args.log)

    if args.notui:
        if not args.filename:
            print("Error: SCENARIO filename is required when running in headless mode.")
            return
        logger.info("TAK Simulator starting (headless mode)")
        logger.info("Loading scenario: %s", args.filename)
        app = TAK(filename=args.filename, server_configs=args.servers)
        app.start()
    else:
        # Remove stdout handlers before TUI starts to prevent log output
        # from corrupting the Textual display
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            if isinstance(handler, logging.StreamHandler) and type(handler) is logging.StreamHandler:
                root_logger.removeHandler(handler)
        logger.info("TAK Simulator starting (TUI mode)")
        app = TakApp(filename=args.filename, server_configs=args.servers)
        app.run()


if __name__ == "__main__":
    main()
