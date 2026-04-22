import pytest

from tak_simulator.time_keeper import TimeKeeper


class TestTimeKeeper:
    def test_init_starts_paused_at_zero_and_normal_speed(self):
        tk = TimeKeeper()

        assert tk.is_paused is True
        assert tk.get_time() == 0.0
        assert tk.speed == 1.0

    def test_start_unpauses_and_time_increases(self):
        tk = TimeKeeper()

        tk.start()
        first = tk.get_time()
        second = tk.get_time()

        assert tk.is_paused is False
        assert second >= first >= 0.0

    def test_pause_freezes_time(self):
        tk = TimeKeeper()

        tk.start()
        tk.pause()

        paused_time = tk.get_time()
        later_time = tk.get_time()

        assert tk.is_paused is True
        assert later_time == paused_time

    def test_unpause_resumes_from_paused_time(self):
        tk = TimeKeeper()

        tk.start()
        tk.pause()
        paused_time = tk.get_time()

        tk.unpause()
        resumed_time = tk.get_time()

        assert tk.is_paused is False
        assert resumed_time >= paused_time

    def test_stop_resets_time_and_pauses_clock(self):
        tk = TimeKeeper()

        tk.start()
        tk.stop()

        assert tk.is_paused is True
        assert tk.get_time() == 0.0

    def test_reset_while_paused_keeps_paused_and_sets_time_to_zero(self):
        tk = TimeKeeper()

        tk.start()
        tk.pause()
        tk.reset()

        assert tk.is_paused is True
        assert tk.get_time() == 0.0

    def test_reset_while_running_keeps_running_and_resets_time(self):
        tk = TimeKeeper()

        tk.start()
        tk.reset()

        assert tk.is_paused is False
        assert tk.get_time() >= 0.0

    def test_set_speed_changes_speed_value(self):
        tk = TimeKeeper()

        tk.set_speed(2.0)

        assert tk.speed == 2.0

    def test_set_speed_raises_for_non_positive_values(self):
        tk = TimeKeeper()

        with pytest.raises(ValueError, match="speed must be > 0"):
            tk.set_speed(0)

        with pytest.raises(ValueError, match="speed must be > 0"):
            tk.set_speed(-1)
