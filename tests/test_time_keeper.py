import pytest

from tak_simulator.time_keeper import TimeKeeper


class TestTimeKeeper:
    def test_init_is_paused(self):
        tk = TimeKeeper()
        assert tk.is_paused is True

    def test_get_time_returns_zero_when_paused_never_unpaused(self):
        tk = TimeKeeper()
        assert tk.get_time() == 0
