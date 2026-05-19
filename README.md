# TAK Simulator

A **TAK (Team Awareness Kit) client simulator** that emulates multiple ATAK and WinTAK devices with realistic behaviour. Each virtual client broadcasts its position via standard TAK networking protocols (multicast CoT, TCP, mTLS), sends and receives chat messages, follows configurable movement paths, and can connect to real TAK servers — all driven by a simulation clock with variable speed, pause/resume, and event scheduling.

## Features

- **Multi-client simulation** — Spin up any number of ATAK or WinTAK emulators with realistic device UIDs and metadata
- **Movement paths** — Define waypoints with timestamps; positions are linearly interpolated between them
- **Event scheduling** — Schedule chat messages, connect/disconnect events on a per-emulator basis
- **Dual codec support** — Speaks both TAK v0 (XML CoT) and TAK v1 (Protocol Buffers) wire formats
- **Network protocol** — Broadcasts on the standard TAK multicast group (`239.2.3.1:6969`), connects to upstream TAK servers via TCP with optional mTLS
- **Variable simulation speed** — Run at 0.5× to 1000× real time, with pause/resume
- **Terminal UI** — 5-tab Textual TUI: load scenarios, control time, inspect emulators, view logs
- **Headless mode** — Run without the TUI for scripting and automation

## Usage

```sh
# Run simulator (opens TUI)
uv run tak_simulator

# Run with a specific scenario
uv run tak_simulator scenarios/scenario.json

# Run headless
uv run tak_simulator --notui scenarios/scenario.json

# Connect with mTLS
uv run tak_simulator --server HOST:PORT:CAFILE:CERTFILE:KEYFILE scenarios/scenario.json
```

## Scenario Format

Scenarios are JSON files defining emulators and their behaviour over simulated time.

```json
{
  "$schema": "../scenario.schema.json",
  "metadata": { "description": "My scenario" },
  "emulators": [
    {
      "like": "atak",
      "callsign": "Alpha",
      "group": { "name": "Cyan", "role": "Team Member" },
      "path": [
        [0.0, [48.8566, 2.3522]],
        [30.0, [48.8588, 2.3469]]
      ],
      "events": [
        { "type": "chat", "time": 10.0, "recipient_uid": "...", "message": "Contact" }
      ]
    }
  ]
}
```

Generate the JSON schema with:
```sh
uv run scenario_schema > scenario.schema.json
```


## CLI Options

```
tak_simulator [SCENARIO] [--notui] [--log LEVEL]
              [--server HOST:PORT[:UPGRADE]]
              [--servers-file FILE]
```

| Option | Description |
|--------|-------------|
| `SCENARIO` | Path to a scenario JSON file |
| `--notui` | Run without the terminal UI |
| `--log` | Log level (default: `INFO`) |
| `--server` | TAK server address (`HOST:PORT`, `HOST:PORT:UPGRADE`, or `HOST:PORT:CAFILE:CERTFILE:KEYFILE[:UPGRADE]`) |
| `--servers-file` | JSON file containing an array of server configurations |

## Development

```sh
# Update environment
uv sync --locked && uv build

# Run tests
uv run pytest tests/

# Run tests with coverage
uv run pytest tests/ --cov=src/tak_simulator --cov-report=term-missing

# Install pre-commit hooks
uv run pre-commit install

# Format code
./format.sh        # Linux / macOS
./format.bat       # Windows
```
