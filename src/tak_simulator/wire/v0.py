from tak_simulator.wire.models import TakEnvelope


class V0Codec:
    def decode(self, data: bytes) -> TakEnvelope:
        raise NotImplementedError()

    def encode(self, message: TakEnvelope) -> bytes:
        raise NotImplementedError()
