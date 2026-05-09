import asyncio
import logging
from typing import Tuple

from tak_simulator.wire import Codec, TakEnvelope

logger = logging.getLogger(__name__)


class NetworkUser:
    def __init__(
        self,
        uid: str,
        addr: Tuple[str, int],
        codec: Codec,
        transport: asyncio.Transport | None = None,
    ) -> None:
        self.uid = uid
        self.addr = addr
        self.transport = transport
        self.codec = codec

    async def send(self, data: bytes):
        """Sends data to the user via multicast and server."""
        if self.transport is None:
            await self.make_connection()
        if self.transport is not None:
            # data = b'\xbf\x01\xbf\n\x1a\x1a\x18algal\x12\xb2\x05\n\x05b-t-f\x12\tUndefined*KGeoChat.algal.ANDROID-6eb795c71729d40b.b2072ac9-0c8f-4e5e-be6c-66171f799b8b0\xd2\x94\xd0\xed\xe038\xd2\x94\xd0\xed\xe03@\xd2\xcc\xe9\x96\xe13J\th-g-i-g-oQ\x11\xe2\xca\xd9;\x01M@Y\xdd\x99\t\x86s\xfd-@a\x93\x18\x04V\x0e1n@i\x00\x00\x00\x00\x00\x00\x18@q\x00\x00\x00\xe0\xcf\x12cAz\x83\x04\n\x80\x04<__chat parent="RootContactGroup" groupOwner="false" messageId="b2072ac9-0c8f-4e5e-be6c-66171f799b8b" chatroom="MISSIONARY" id="ANDROID-6eb795c71729d40b" senderCallsign="Algot Johansson"><chatgrp uid0="algal" uid1="ANDROID-6eb795c71729d40b" id="ANDROID-6eb795c71729d40b"/></__chat><link uid="algal" type="a-f-G-U-C" relation="p-p"/><__serverdestination destinations="192.168.31.10:4242:tcp:algal"/><remarks source="BAO.F.ATAK.algal" to="ANDROID-6eb795c71729d40b" time="2026-05-09T17:06:03.474Z">bfcvfcnihob</remarks>'
            self.transport.write(data)

    async def make_connection(self):
        loop = asyncio.get_running_loop()
        host, port = self.addr

        transport, _ = await loop.create_connection(
            lambda: TcpUserProtocol(self), host, port
        )
        self.transport = transport

    def callback(self, data: TakEnvelope):
        logger.info(f"Received data from {self.uid}: {data}")


class TcpUserProtocol(asyncio.Protocol):
    def __init__(self, user: NetworkUser):
        self.user = user

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        return super().connection_made(transport)

    def data_received(self, data: bytes):
        self.user.callback(self.user.codec.decode(data))
