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

    async def send(self, envelope: TakEnvelope):
        """Sends data to the user via multicast and server."""
        logger.debug(
            f"SEND: Transport {self.transport}, envelope control {envelope.control}"
        )
        if self.transport is None:
            await self.make_connection()
        if envelope.control is not None and self.transport is not None:
            self.transport.write(self.codec.encode(envelope))

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
        print(data)
        self.user.callback(self.user.codec.decode(data))
