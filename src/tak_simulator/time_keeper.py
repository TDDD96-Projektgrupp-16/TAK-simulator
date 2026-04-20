import time
import logging

logger = logging.getLogger(__name__)


class TimeKeeper:
    """
    Shared simulation clock.

    The time keeper maps real elapsed time to simulation time and is the single
    source of truth for the whole simulator. It supports pause/resume as well as
    speed changes.
    """

    _real_time_at_last_resume: float | None
    _fake_time_at_last_pause: float
    _is_paused: bool
    _speed: float

    def __init__(self):
        self._real_time_at_last_resume = None
        self._fake_time_at_last_pause = 0.0
        self._is_paused = True
        self._speed = 1.0

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def speed(self) -> float:
        return self._speed

    def get_time(self) -> float:
        if self.is_paused:
            return self._fake_time_at_last_pause

        assert self._real_time_at_last_resume is not None
        elapsed_real_time = time.monotonic() - self._real_time_at_last_resume
        return self._fake_time_at_last_pause + elapsed_real_time * self._speed

    def start(self) -> None:
        self._fake_time_at_last_pause = 0.0
        self._real_time_at_last_resume = time.monotonic()
        self._is_paused = False
        logger.info("Time keeper started")

    def unpause(self) -> None:
        if not self._is_paused:
            return

        self._real_time_at_last_resume = time.monotonic()
        self._is_paused = False
        logger.info("Time keeper resumed at t=%.3f", self._fake_time_at_last_pause)

    def pause(self) -> None:
        if self._is_paused:
            return

        self._fake_time_at_last_pause = self.get_time()
        self._real_time_at_last_resume = None
        self._is_paused = True
        logger.info("Time keeper paused at t=%.3f", self._fake_time_at_last_pause)

    def stop(self) -> None:
        self._real_time_at_last_resume = None
        self._fake_time_at_last_pause = 0.0
        self._is_paused = True
        logger.info("Time keeper stopped")

    def reset(self) -> None:
        if self._is_paused:
            self._fake_time_at_last_pause = 0.0
        else:
            self._fake_time_at_last_pause = 0.0
            self._real_time_at_last_resume = time.monotonic()

        logger.info("Time keeper reset")

    def set_speed(self, speed: float) -> None:
        if speed <= 0:
            raise ValueError("speed must be > 0")

        current_sim_time = self.get_time()
        self._fake_time_at_last_pause = current_sim_time
        self._speed = speed

        if not self._is_paused:
            self._real_time_at_last_resume = time.monotonic()

        logger.info("Time keeper speed changed to %.2fx", speed)