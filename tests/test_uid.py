import pytest

from tak_simulator.uid import (
    generate_believable_atak_uid,
    generate_believable_wintak_uid,
)


class TestGenerateBelievableAtakUid:
    def test_starts_with_android_prefix(self):
        uid = generate_believable_atak_uid()
        assert uid.startswith("ANDROID-")

    def test_has_correct_length(self):
        uid = generate_believable_atak_uid()
        assert len(uid) == 8 + 16

    def test_contains_only_hex_characters_after_prefix(self):
        uid = generate_believable_atak_uid()
        hex_part = uid[8:]
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_returns_different_values(self):
        uids = [generate_believable_atak_uid() for _ in range(100)]
        assert len(set(uids)) > 1


class TestGenerateBelievableWintakUid:
    def test_starts_with_s_1_prefix(self):
        uid = generate_believable_wintak_uid()
        assert uid.startswith("S-1-")

    def test_returns_different_values(self):
        uids = [generate_believable_wintak_uid() for _ in range(100)]
        assert len(set(uids)) > 1
