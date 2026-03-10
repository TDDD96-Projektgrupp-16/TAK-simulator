import time


class TimeKeeper:
    _real_time_at_last_unpause: float
    _fake_time_at_last_pause: float
    _is_paused: bool
    _playback_speed: float

    def __init__(self):
        self._real_time_at_last_unpause = 0
        self._fake_time_at_last_pause = 0
        self._is_paused = True
        self._playback_speed = 1.0

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def playback_speed(self) -> float:
        return self._playback_speed

    def get_time(self) -> float:
        if self.is_paused:
            return self._fake_time_at_last_pause

        return (
            self._fake_time_at_last_pause
            + (time.time() - self._real_time_at_last_unpause) * self.playback_speed
        )

    def unpause(self):
        self._real_time_at_last_unpause = time.time()
        self._is_paused = False

    def pause(self):
        self._fake_time_at_last_pause = self.get_time()
        self._is_paused = True

    def set_playback_speed(self, speed: float):
        self._fake_time_at_last_pause = self.get_time()
        self._real_time_at_last_unpause = time.time()
        self._playback_speed = speed
