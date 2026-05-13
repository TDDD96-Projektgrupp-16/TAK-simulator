import asyncio
import logging
import socket
from typing import List, Tuple, cast

from tak_simulator.network.multicast import MulticastHandler
from tak_simulator.network.server import Server, ServerHandler
from tak_simulator.util import host_ip
from tak_simulator.wire import Codec, TakEnvelope
from tak_simulator.wire.v0 import V0Codec
from tak_simulator.wire.v1 import V1Codec

logger = logging.getLogger(__name__)


class NetworkManager:
    def __init__(
        self,
        multicast: MulticastHandler,
        server_handler: ServerHandler,
        codec: Codec,
        port: int,
    ) -> None:
        self._server = None
        self.multicast = multicast
        self.server_handler = server_handler
        self.codec = codec
        self.port = port

    @classmethod
    async def create_connection(
        cls, multicast: MulticastHandler, servers: List[Server], port: int, codec: Codec
    ):

        server_handler = await ServerHandler.create_server_connection(servers)
        instance = cls(multicast, server_handler, codec, port)
        server_handler.callback = instance.callback
        asyncio.create_task(instance._start_server(port))

        return instance

    async def _start_server(self, port: int):
        loop = asyncio.get_event_loop()
        self._server = await loop.create_server(
            lambda: ServerProtocol(self), "0.0.0.0", port
        )
        await self._server.serve_forever()

    def callback(self, envelope: TakEnvelope, addr: Tuple[str, int]) -> None:
        if envelope.event is None:
            return

    def broadcast(self, envelope: TakEnvelope):
        """Sends data to all servers and multicast group."""
        self.multicast.send(envelope)
        self.server_handler.send(envelope)

    async def send_to(self, uid: str, envelope: TakEnvelope) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            addr = self.multicast.get_user_addr(
                uid
            ) or self.server_handler.get_user_addr(uid)
            if addr is None:
                logger.warning(
                    "Could not find address for %s in multicast or server", uid
                )
                return False
            try:
                s.connect(addr)
                data = V1Codec().encode(envelope)
                s.sendall(data)
            except OSError:
                logger.error(
                    "Failed to send message to %s at %s:%d", uid, addr[0], addr[1]
                )
                return False

        return True

    def get_endpoint(self):
        return f"{host_ip()}:{self.port}:tcp"


class ServerProtocol(asyncio.Protocol):
    def __init__(self, network_manager: NetworkManager) -> None:
        self._transport = None
        self.network_manager = network_manager

    def connection_made(self, transport):
        self._transport = cast(asyncio.Transport, transport)

    def data_received(self, data):

        if self._transport is not None:
            if data.startswith(b"\277\001\277"):
                envelope = V1Codec().decode(data)
            else:
                envelope = V0Codec().decode(data)

            self.network_manager.callback(
                envelope, self._transport.get_extra_info("peername")
            )
