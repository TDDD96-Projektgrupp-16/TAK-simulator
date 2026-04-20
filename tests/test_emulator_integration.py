

import asyncio
from types import SimpleNamespace

import pytest

from tak_simulator.emulator import Emulator
from tak_simulator.scenario import Scenario
from tak_simulator.scenario_scheduler import ScenarioScheduler
from tak_simulator.time_keeper import TimeKeeper


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


@pytest.mark.asyncio
async def test_emulator_registers_and_runs_scenario_event(monkeypatch) -> None:
    scenario = build_scenario_with_event()
    options = scenario.emulators[0]

    time_keeper = TimeKeeper()
    scheduler = ScenarioScheduler(time_keeper, poll_interval=0.001)
    emulator = Emulator(options, time_keeper, scheduler, "127.0.0.1")

    triggered = []

    async def fake_start_server(*args, **kwargs):
        return FakeServer()

    async def fake_handle_scenario_event(event):
        triggered.append(event)
        scheduler.stop()

    monkeypatch.setattr(asyncio, "start_server", fake_start_server)
    monkeypatch.setattr("tak_simulator.emulator.socket.socket", lambda *args, **kwargs: FakeSocket())
    monkeypatch.setattr(emulator, "handle_scenario_event", fake_handle_scenario_event)

    emulator_task = asyncio.create_task(emulator.run())

    await asyncio.sleep(0)
    time_keeper.start()
    await scheduler.run()

    emulator_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await emulator_task

    assert len(triggered) == 1
    assert triggered[0].event_type == "chat"
    assert triggered[0].message == "I am on my way"