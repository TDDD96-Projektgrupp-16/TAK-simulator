import asyncio

import pytest

from tak_simulator.scenario_scheduler import ScenarioScheduler
from tak_simulator.time_keeper import TimeKeeper


class TestScenarioScheduler:
    @pytest.mark.asyncio
    async def test_schedule_once_runs_callback_when_time_is_due(self):
        time_keeper = TimeKeeper()
        scheduler = ScenarioScheduler(time_keeper, poll_interval=0.001)
        called = []

        def callback(value: str) -> None:
            called.append(value)
            scheduler.stop()

        scheduler.schedule_once(0.0, callback, "hello")

        time_keeper.start()
        await scheduler.run()

        assert called == ["hello"]

    @pytest.mark.asyncio
    async def test_schedule_recurring_runs_multiple_times(self):
        time_keeper = TimeKeeper()
        scheduler = ScenarioScheduler(time_keeper, poll_interval=0.001)
        called = []

        def callback() -> None:
            called.append(time_keeper.get_time())
            if len(called) >= 3:
                scheduler.stop()

        scheduler.schedule_recurring(0.0, 0.01, callback)

        time_keeper.start()
        await scheduler.run()

        assert len(called) == 3

    @pytest.mark.asyncio
    async def test_cancel_prevents_scheduled_event_from_running(self):
        time_keeper = TimeKeeper()
        scheduler = ScenarioScheduler(time_keeper, poll_interval=0.001)
        called = []

        def callback() -> None:
            called.append("ran")

        event = scheduler.schedule_once(0.0, callback)
        scheduler.cancel(event)

        async def stop_scheduler() -> None:
            await asyncio.sleep(0.01)
            scheduler.stop()

        time_keeper.start()
        await asyncio.gather(scheduler.run(), stop_scheduler())

        assert called == []

    @pytest.mark.asyncio
    async def test_pause_prevents_due_events_until_unpaused(self):
        time_keeper = TimeKeeper()
        scheduler = ScenarioScheduler(time_keeper, poll_interval=0.001)
        called = []

        def callback() -> None:
            called.append("ran")
            scheduler.stop()

        scheduler.schedule_once(0.01, callback)

        time_keeper.start()
        time_keeper.pause()

        async def resume_later() -> None:
            await asyncio.sleep(0.02)
            assert called == []
            time_keeper.unpause()

        await asyncio.gather(scheduler.run(), resume_later())

        assert called == ["ran"]

    @pytest.mark.asyncio
    async def test_async_callback_is_awaited(self):
        time_keeper = TimeKeeper()
        scheduler = ScenarioScheduler(time_keeper, poll_interval=0.001)
        called = []

        async def callback() -> None:
            await asyncio.sleep(0)
            called.append("async")
            scheduler.stop()

        scheduler.schedule_once(0.0, callback)

        time_keeper.start()
        await scheduler.run()

        assert called == ["async"]

    @pytest.mark.asyncio
    async def test_clear_removes_all_scheduled_events(self):
        time_keeper = TimeKeeper()
        scheduler = ScenarioScheduler(time_keeper, poll_interval=0.001)
        called = []

        def callback() -> None:
            called.append("ran")

        scheduler.schedule_once(0.0, callback)
        scheduler.schedule_once(0.0, callback)
        scheduler.clear()

        async def stop_scheduler() -> None:
            await asyncio.sleep(0.01)
            scheduler.stop()

        time_keeper.start()
        await asyncio.gather(scheduler.run(), stop_scheduler())

        assert called == []

    def test_schedule_recurring_raises_for_non_positive_interval(self):
        time_keeper = TimeKeeper()
        scheduler = ScenarioScheduler(time_keeper)

        with pytest.raises(ValueError, match="interval must be > 0"):
            scheduler.schedule_recurring(0.0, 0.0, lambda: None)

        with pytest.raises(ValueError, match="interval must be > 0"):
            scheduler.schedule_recurring(0.0, -1.0, lambda: None)
