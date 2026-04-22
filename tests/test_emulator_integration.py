import asyncio
from types import SimpleNamespace

from tak_simulator.scenario import Scenario


class FakeSocket:
    def bind(self, addr):
        return None

    def setsockopt(self, *args, **kwargs):
        return None

    def sendto(self, data, addr):
        return None


class FakeServer:
    sockets = [SimpleNamespace(getsockname=lambda: ("127.0.0.1", 5000))]

    async def serve_forever(self):
        await asyncio.Future()


def build_scenario_with_event() -> Scenario:
    return Scenario.model_validate(
        {
            "metadata": {"description": "integration test"},
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
                            "message": "I am on my way",
                        }
                    ],
                }
            ],
        }
    )


def test_scenario_event_type_alias_is_parsed() -> None:
    scenario = build_scenario_with_event()

    event = scenario.emulators[0].events[0]
    assert event.event_type == "chat"
    assert event.message == "I am on my way"
    assert event.time == 0.0
