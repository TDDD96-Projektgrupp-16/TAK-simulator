import asyncio
import logging
from typing import Tuple

from tak_simulator.wire import Codec, TakEnvelope

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT = 3.0


class NetworkUser:
    def __init__(
        self,
        uid: str,
        callsign: str,
        addr: Tuple[str, int],
        codec: Codec,
        transport: asyncio.Transport | None = None,
    ) -> None:
        self.uid = uid
        self.callsign = callsign
        self.addr = addr
        self.transport = transport
        self.codec = codec

    async def send(self, envelope: TakEnvelope):
        """Sends data to the user via a short-lived TCP connection."""
        logger.debug("Sending data to %s at %s: %s", self.uid, self.addr, envelope)

        transport = await self._open_ephemeral_transport()
        if transport is None:
            logger.debug("Failed to open transport for uid=%s", self.uid)
            return

        try:
            payload = self.codec.encode(envelope)
            logger.debug(
                "Sending TCP data to %s at %s: %s", self.uid, self.addr, payload
            )
            transport.write(payload)
        finally:
            transport.close()

    async def _open_ephemeral_transport(
        self, timeout: float | None = CONNECT_TIMEOUT
    ) -> asyncio.Transport | None:
        loop = asyncio.get_running_loop()
        host, port = self.addr
        logger.debug(
            "Attempting ephemeral connect to %s at %s:%s (timeout=%s)",
            self.uid,
            host,
            port,
            timeout,
        )
        connect_coro = loop.create_connection(lambda: TcpUserProtocol(self), host, port)
        try:
            if timeout is None:
                transport, _ = await connect_coro
            else:
                transport, _ = await asyncio.wait_for(connect_coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error("Timed out connecting to %s at %s:%s", self.uid, host, port)
            return None
        except Exception:
            logger.exception("Failed to connect to %s at %s:%s", self.uid, host, port)
            return None
        logger.debug(
            "Ephemeral connection established to %s at %s:%s", self.uid, host, port
        )
        return transport

    def callback(self, data: TakEnvelope):
        logger.info(f"Received data from {self.uid}: {data}")


class TcpUserProtocol(asyncio.Protocol):
    def __init__(self, user: NetworkUser):
        self.user = user

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        return super().connection_made(transport)

    def data_received(self, data: bytes):
        logger.debug(f"Received TCP data from {self.user.uid}: {data}")
        self.user.callback(self.user.codec.decode(data))
