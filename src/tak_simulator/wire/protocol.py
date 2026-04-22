from typing import Protocol

from tak_simulator.wire import TakEnvelope


class Codec(Protocol):
    def decode(self, data: bytes) -> TakEnvelope: ...
    def encode(self, message: TakEnvelope) -> bytes: ...
