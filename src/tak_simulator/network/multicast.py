import asyncio
import logging
import socket
import struct
from typing import Callable, Self, Tuple


from tak_simulator.wire import TakEnvelope
from tak_simulator.wire.exceptions import DecodeError
from tak_simulator.wire.v0 import V0Codec
from tak_simulator.wire.v1 import V1Codec

MULTICAST_ADDR = "239.2.3.1"
MULTICAST_PORT = 6969

logger = logging.getLogger(__name__)


class MulticastHandler:
    def __init__(
        self,
        transport: asyncio.DatagramTransport | None,
        callback: Callable[[TakEnvelope, tuple[str, int]], None],
    ) -> None:
        self.transport = transport
        self.callback = callback
        self.v0_codec = V0Codec()
        self.v1_codec = V1Codec()
        self._user: dict[str, Tuple[str, int]] = {}
        self._callsigns: dict[str, str] = {}

    @classmethod
    async def create_multicast_connection(
        cls,
        callback: Callable[[TakEnvelope, tuple[str, int]], None],
    ) -> Self:

        instance = cls(None, callback)

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.bind(("0.0.0.0", MULTICAST_PORT))

        mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_ADDR), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 64)

        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)

        loop = asyncio.get_event_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: MulticastProtocol(instance), sock=sock
        )
        instance.transport = transport
        return instance

    def _multicast_data_received(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            if data.startswith(b"\277\001\277"):
                envelope = self.v1_codec.decode(data)
            else:
                envelope = self.v0_codec.decode(data)
        except DecodeError:
            logger.warning("Failed to decode multicast packet from %s", addr)
            return

        logger.debug("Received multicast envelope from %s", addr)

        if (
            envelope.event is not None
            and envelope.event.detail is not None
            and envelope.event.detail.contact is not None
            and envelope.event.detail.contact.endpoint is not None
            and envelope.event.detail.contact is not None
            and envelope.event.detail.contact.callsign is not None
        ):
            try:
                user, port, protocol = envelope.event.detail.contact.endpoint.split(":")

                if protocol.lower() == "tcp":
                    self._user[envelope.event.uid] = (user, int(port))
                    self._callsigns[envelope.event.uid] = (
                        envelope.event.detail.contact.callsign
                    )
                    logger.debug(
                        "Registered TCP endpoint for %s: %s:%s",
                        envelope.event.uid,
                        user,
                        port,
                    )
            except ValueError:
                logger.warning(
                    "Ignoring malformed contact endpoint: %s",
                    envelope.event.detail.contact.endpoint,
                )
                return

        self.callback(envelope, addr)

    def get_user_addr(self, uid: str) -> Tuple[str, int] | None:
        return self._user.get(uid)

    def get_user_callsign(self, uid: str) -> str | None:
        return self._callsigns.get(uid)

    def get_known_users(self) -> dict[str, str]:
        return dict(self._callsigns)

    def send(self, envelope: TakEnvelope) -> None:
        if self.transport is None:
            return

        data = self.v1_codec.encode(envelope)
        logger.debug(
            "Sending multicast envelope to %s:%s", MULTICAST_ADDR, MULTICAST_PORT
        )
        self.transport.sendto(data, (MULTICAST_ADDR, MULTICAST_PORT))


class MulticastProtocol(asyncio.DatagramProtocol):
    def __init__(self, handler: MulticastHandler) -> None:
        self.handler = handler

    def datagram_received(self, data: bytes, addr: tuple[str, int]):
        self.handler._multicast_data_received(data, addr)
