from typing import Self, Optional, Literal
from dataclasses import dataclass

from tak_simulator.proto.takmessage_pb2 import TakMessage as ProtoTAKMessage


class TAKEnvelope:
    origin: Optional[Literal["v0", "v1"]] = None


@dataclass
class TAKMessage:
    @classmethod
    def parse_from(cls, data: str) -> Self:
        try:
            return cls.parse_from_xml(data)
        except NotImplementedError:
            pass

        return cls.parse_from_protobuf(data)

    @classmethod
    def parse_from_xml(cls, data: str) -> Self:
        raise NotImplementedError()

    @classmethod
    def parse_from_protobuf(cls, data: str) -> Self:
        message = ProtoTAKMessage()
        message.ParseFromString(data)
        return cls.from_protobuf(message)

    @classmethod
    def from_protobuf(cls, message: ProtoTAKMessage) -> Self:
        raise NotImplementedError()
