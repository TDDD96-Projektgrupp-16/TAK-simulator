import asyncio
import heapq
import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from tak_simulator.time_keeper import TimeKeeper


logger = logging.getLogger(__name__)


Callback = Callable[..., Any]


@dataclass(order=True)
class ScheduledEvent:
    due_time: float
    priority: int
    event_id: int = field(compare=True)
    callback: Callback = field(compare=False)
    args: tuple[Any, ...] = field(default_factory=tuple, compare=False)
    kwargs: dict[str, Any] = field(default_factory=dict, compare=False)
    interval: float | None = field(default=None, compare=False)
    repeat: bool = field(default=False, compare=False)
    cancelled: bool = field(default=False, compare=False)
    name: str = field(default="event", compare=False)


class ScenarioScheduler:
    """
    Central scheduler for all scenario actions.

    The scheduler uses the shared "TimeKeeper" as the single source of truth for
    simulation time. Emulators can register one-shot or recurring events here
    instead of checking the clock themselves.
    """

    def __init__(self, time_keeper: TimeKeeper, poll_interval: float = 0.05):
        self.time_keeper = time_keeper
        self.poll_interval = poll_interval

        self._queue: list[ScheduledEvent] = []
        self._next_event_id = 0
        self._next_priority = 0
        self._running = False
        self._wake_up = asyncio.Event()

    def schedule_once(
        self,
        due_time: float,
        callback: Callback,
        *args: Any,
        priority: int | None = None,
        name: str | None = None,
        **kwargs: Any,
    ) -> ScheduledEvent:
        event = ScheduledEvent(
            due_time=due_time,
            priority=self._allocate_priority(priority),
            event_id=self._allocate_event_id(),
            callback=callback,
            args=args,
            kwargs=kwargs,
            repeat=False,
            interval=None,
            name=name or getattr(callback, "__name__", "event"),
        )
        heapq.heappush(self._queue, event)
        self._wake_up.set()
        logger.debug("Scheduled one-shot event '%s' at t=%.3f", event.name, due_time)
        return event

    def schedule_recurring(
        self,
        start_time: float,
        interval: float,
        callback: Callback,
        *args: Any,
        priority: int | None = None,
        name: str | None = None,
        **kwargs: Any,
    ) -> ScheduledEvent:
        if interval <= 0:
            raise ValueError("interval must be > 0")

        event = ScheduledEvent(
            due_time=start_time,
            priority=self._allocate_priority(priority),
            event_id=self._allocate_event_id(),
            callback=callback,
            args=args,
            kwargs=kwargs,
            repeat=True,
            interval=interval,
            name=name or getattr(callback, "__name__", "recurring_event"),
        )
        heapq.heappush(self._queue, event)
        self._wake_up.set()
        logger.debug(
            "Scheduled recurring event '%s' at t=%.3f every %.3fs",
            event.name,
            start_time,
            interval,
        )
        return event

    def cancel(self, event: ScheduledEvent) -> None:
        event.cancelled = True
        self._wake_up.set()
        logger.debug("Cancelled event '%s'", event.name)

    def clear(self) -> None:
        self._queue.clear()
        self._wake_up.set()
        logger.debug("Cleared all scheduled events")

    async def run(self) -> None:
        self._running = True
        logger.info("Scenario scheduler started")

        while self._running:
            self._drop_cancelled_events()

            if not self._queue:
                await self._sleep_until_woken()
                continue

            if self.time_keeper.is_paused:
                await asyncio.sleep(self.poll_interval)
                continue

            next_event = self._queue[0]
            now = self.time_keeper.get_time()

            if now < next_event.due_time:
                await self._sleep_until_due(next_event.due_time - now)
                continue

            event = heapq.heappop(self._queue)
            if event.cancelled:
                continue

            await self._execute_event(event)

            if event.repeat and not event.cancelled and event.interval is not None:
                self._reschedule_recurring_event(event)

        logger.info("Scenario scheduler stopped")

    def stop(self) -> None:
        self._running = False
        self._wake_up.set()

    async def _execute_event(self, event: ScheduledEvent) -> None:
        try:
            result = event.callback(*event.args, **event.kwargs)
            if inspect.isawaitable(result):
                await result
        except Exception:
            logger.error(
                "Event '%s' raised an exception at t=%.3f",
                event.name,
                self.time_keeper.get_time(),
                exc_info=True,
            )

    def _reschedule_recurring_event(self, event: ScheduledEvent) -> None:
        """
        Move recurring event to its next scheduled simulation time.

        If the simulation has advanced more than one interval, jump forward to the
        first future slot instead of replaying every missed interval.
        """
        assert event.interval is not None

        now = self.time_keeper.get_time()
        next_due_time = event.due_time + event.interval

        while next_due_time <= now:
            next_due_time += event.interval

        event.due_time = next_due_time
        heapq.heappush(self._queue, event)
        self._wake_up.set()

    def _drop_cancelled_events(self) -> None:
        while self._queue and self._queue[0].cancelled:
            heapq.heappop(self._queue)

    async def _sleep_until_due(self, delay: float) -> None:
        timeout = max(0.0, min(delay, self.poll_interval))
        self._wake_up.clear()
        try:
            await asyncio.wait_for(self._wake_up.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

    async def _sleep_until_woken(self) -> None:
        self._wake_up.clear()
        try:
            await asyncio.wait_for(self._wake_up.wait(), timeout=self.poll_interval)
        except asyncio.TimeoutError:
            pass

    def _allocate_event_id(self) -> int:
        event_id = self._next_event_id
        self._next_event_id += 1
        return event_id

    def _allocate_priority(self, priority: int | None) -> int:
        if priority is not None:
            return priority

        allocated_priority = self._next_priority
        self._next_priority += 1
        return allocated_priority
