import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from tak_simulator.emulator import Emulator
from tak_simulator.scenario import Scenario
from tak_simulator.simulator import Simulator


class FakeConnection:
    def __init__(self):
        self.send_all = MagicMock()
        self.multicast_send = MagicMock()
        self.send_to_servers = MagicMock()
        self.get_endpoint = MagicMock(return_value="127.0.0.1:8000:tcp")
        self.send_to_user = MagicMock()
        self.set_callback_for_user = MagicMock()


def build_scenario() -> Scenario:
    return Scenario.model_validate(
        {
            "metadata": {"description": "simulator integration test"},
            "emulators": [
                {
                    "like": "atak",
                    "type": "a-f-G-U-C",
                    "uid": "ANDROID-TEST-1",
                    "callsign": "Algot Johansson",
                    "how": "m-g",
                    "group": {
                        "name": "Cyan",
                        "role": "Team Member",
                    },
                    "takv": {
                        "device": "SAMSUNG SM-S901B",
                        "platform": "ATAK-CIV",
                        "os": "36",
                        "version": "5.6.0.12",
                    },
                    "path": [
                        [0, [58.4135, 15.5629]],
                    ],
                    "events": [
                        {
                            "time": 0.0,
                            "type": "chat",
                            "recipient_uid": "ANDROID-RECIPIENT-1",
                            "message": "I am on my way",
                        }
                    ],
                }
            ],
        }
    )
