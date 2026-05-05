import asyncio
import logging
import socket
import struct
from typing import Callable, Self, Tuple

from tak_simulator.wire import Codec, TakEnvelope

MULTICAST_ADDR = "239.2.3.1"
MULTICAST_PORT = 6969

logger = logging.getLogger(__name__)


class MulticastHandler:
    def __init__(
        self,
        transport: asyncio.DatagramTransport | None,
        codec: Codec,
        callback: Callable[[TakEnvelope, tuple[str, int]], None],
    ) -> None:
        self.transport = transport
        self.codec = codec
        self.callback = callback
        self._user: dict[str, Tuple[str, int]] = {}

    @classmethod
    async def create_multicast_connection(
        cls,
        codec: Codec,
        callback: Callable[[TakEnvelope, tuple[str, int]], None],
    ) -> Self:

        instanse = cls(None, codec, callback)

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.bind(("0.0.0.0", MULTICAST_PORT))

        mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_ADDR), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 64)

        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)

        loop = asyncio.get_event_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: MulticastProtocol(instanse), sock=sock
        )
        instanse.transport = transport
        return instanse

    def _multicast_data_received(self, data: bytes, addr: tuple[str, int]) -> None:
        envelope = self.codec.decode(data)
        if envelope.event is not None:
            self._user[envelope.event.uid] = addr
        self.callback(envelope, addr)

    def get_user_addr(self, uid: str) -> Tuple[str, int] | None:
        return self._user.get(uid)

    def send(self, envelope: TakEnvelope) -> None:
        if self.transport is None:
            return
        data = self.codec.encode(envelope)
        logger.debug("sending multicast data")
        self.transport.sendto(data, (MULTICAST_ADDR, MULTICAST_PORT))


class MulticastProtocol(asyncio.DatagramProtocol):
    def __init__(self, handler: MulticastHandler) -> None:
        self.handler = handler

    def datagram_received(self, data: bytes, addr: tuple[str, int]):
        self.handler._multicast_data_received(data, addr)
