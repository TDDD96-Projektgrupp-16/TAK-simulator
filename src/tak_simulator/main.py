from tak_simulator.cli import get_args
from tak_simulator.logging_conf import logging_setup
from tak_simulator.tak import TAK


def main():
    args = get_args()
    logging_setup(args.log)

    app = TAK(args.filename, server_configs=args.servers)
    app.start()


if __name__ == "__main__":
    main()
