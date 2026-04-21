import random

import logging
import uuid

logger = logging.getLogger(__name__)


def generate_believable_atak_uid() -> str:
    return "ANDROID-" + "".join(random.choices("0123456789abcdef", k=16))


def generate_believable_wintak_uid() -> str:
    return f"S-1-5-21-{_random_uint32()}-{_random_uint32()}-{_random_uint32()}-1001"


def generate_message_uid() -> str:
    return str(uuid.uuid4())


def generate_believable_uid(like: str) -> str:
    if like == "atak":
        return generate_believable_atak_uid()
    else:
        return generate_believable_wintak_uid()


def _random_uint32() -> int:
    return random.randint(0, 2**32)
