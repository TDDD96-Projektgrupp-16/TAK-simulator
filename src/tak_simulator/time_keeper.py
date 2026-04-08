import time

import logging

logger = logging.getLogger(__name__)


class TimeKeeper:
    _real_time_at_last_unpause: float
    _fake_time_at_last_pause: float
    _is_paused: bool

    def __init__(self):
        self._real_time_at_last_unpause = 0
        self._fake_time_at_last_pause = 0
        self._is_paused = True

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    def get_time(self) -> float:
        if self.is_paused:
            return self._fake_time_at_last_pause

        return (
            self._fake_time_at_last_pause
            + time.time()
            - self._real_time_at_last_unpause
        )

    def unpause(self):
        self._real_time_at_last_unpause = time.time()
        self._is_paused = False

    def pause(self):
        self._fake_time_at_last_pause = self.get_time()
        self._is_paused = True
