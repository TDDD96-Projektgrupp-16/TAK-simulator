import asyncio

import pytest

from tak_simulator.emulator import Emulator
from tak_simulator.scenario import Scenario
from tak_simulator.simulator import Simulator


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
                            "message": "I am on my way",
                        }
                    ],
                }
            ],
        }
    )


@pytest.mark.asyncio
async def test_simulator_uses_shared_timekeeper_scheduler_and_emulator_flow(monkeypatch):
    simulator = Simulator()
    scenario = build_scenario()

    triggered = []

    async def fake_emulator_run(self):
        assert self.time_keeper is simulator.time_keeper
        assert self.scheduler is simulator.scheduler

        for event in self.options.events:
            self.scheduler.schedule_once(
                due_time=event.time,
                callback=lambda event=event: triggered.append(event),
                name=f"{event.event_type}:{self.options.callsign}",
            )

        while simulator.scheduler._running:
            await asyncio.sleep(0.001)

    monkeypatch.setattr(Emulator, "run", fake_emulator_run)

    run_task = asyncio.create_task(simulator.run(scenario, "127.0.0.1"))

    while not triggered:
        await asyncio.sleep(0.001)

    simulator.scheduler.stop()

    await asyncio.wait_for(run_task, timeout=1.0)

    assert len(simulator.emulators) == 1
    assert simulator.time_keeper.is_paused is False
    assert len(triggered) == 1
    assert triggered[0].event_type == "chat"
    assert triggered[0].message == "I am on my way"