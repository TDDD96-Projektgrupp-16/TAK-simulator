import argparse
import json

from pydantic import TypeAdapter, ValidationError

from tak_simulator.network.server import ServerConfig

_UPGRADE_VALUES = {"yes", "no", "1", "0", "true", "false"}


def _parse_upgrade(value: str) -> bool:
    return value.lower() in ("1", "true", "yes")


def parse_server_arg(value: str) -> ServerConfig:
    parts = value.split(":")
    if len(parts) not in (2, 3, 5, 6):
        raise argparse.ArgumentTypeError(
            f"Expected 2, 3, 5, or 6 colon-separated fields. "
            f"Valid forms: HOST:PORT[:UPGRADE] | HOST:PORT:CAFILE:CERTFILE:KEYFILE[:UPGRADE], "
            f"got {len(parts)} part(s)"
        )
    ip = parts[0]
    try:
        port = int(parts[1])
    except ValueError:
        raise argparse.ArgumentTypeError(f"Port must be an integer, got '{parts[1]}'")
    upgrade = False
    cafile = certfile = keyfile = None
    if len(parts) == 3:
        if parts[2].lower() not in _UPGRADE_VALUES:
            raise argparse.ArgumentTypeError(
                f"Expected upgrade flag (yes/no/1/0/true/false), got '{parts[2]}'"
            )
        upgrade = _parse_upgrade(parts[2])
    elif len(parts) >= 5:
        cafile = parts[2] or None
        certfile = parts[3] or None
        keyfile = parts[4] or None
        if len(parts) == 6:
            upgrade = _parse_upgrade(parts[5])

    return ServerConfig(
        ip=ip,
        port=port,
        cafile=cafile,
        certfile=certfile,
        keyfile=keyfile,
        upgrade=upgrade,
    )


_server_list_adapter = TypeAdapter(list[ServerConfig])


def load_servers_file(path: str) -> list[ServerConfig]:
    with open(path) as f:
        try:
            return _server_list_adapter.validate_python(json.load(f))
        except json.JSONDecodeError as e:
            raise ValueError(f"Servers file is not valid JSON: {e}") from e
        except ValidationError as e:
            raise ValueError(f"Servers file is invalid: {e}") from e


def get_args():
    parser = argparse.ArgumentParser("tak_emulator")

    # Changed from required positional to optional positional
    parser.add_argument(
        "filename",
        metavar="SCENARIO",
        nargs="?",
        default=None,
        help="Path to the scenario file (optional if using TUI)",
    )

    parser.add_argument("--log", default="INFO")
    parser.add_argument(
        "--notui",
        action="store_true",
        help="Run in headless mode without the graphical interface",
    )
    parser.add_argument(
        "--server",
        dest="servers",
        type=parse_server_arg,
        action="append",
        default=[],
        help="Server connection: HOST:PORT[:UPGRADE] | HOST:PORT:CAFILE:CERTFILE:KEYFILE[:UPGRADE]",
    )
    parser.add_argument(
        "--servers-file",
        default=None,
        help="JSON file with an array of server configurations",
    )

    args = parser.parse_args()

    if args.servers_file:
        file_servers = load_servers_file(args.servers_file)
        args.servers = args.servers + file_servers

    return args
