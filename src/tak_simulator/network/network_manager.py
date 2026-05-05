import asyncio
import logging
from typing import List, Tuple, cast

from tak_simulator.network.multicast import MulticastHandler
from tak_simulator.network.network_user import NetworkUser
from tak_simulator.network.server import Server, ServerHandler
from tak_simulator.util import host_ip
from tak_simulator.wire import Codec, TakEnvelope
from tak_simulator.wire.v0 import V0Codec

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
        self.users: dict[str, NetworkUser] = {}
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

    def callback(
        self, envelope: TakEnvelope, addr: Tuple[str, int], transport: asyncio.Transport
    ) -> None:
        logger.debug(f"Received data from {addr}: {envelope}")
        if envelope.event is None:
            return
        uid = envelope.event.uid

        if uid not in self.users:
            self.users[uid] = NetworkUser(uid, addr, V0Codec(), transport)

        self.users[uid].callback(envelope)

    def broadcast(self, envelope: TakEnvelope):
        """Sends data to all servers and multicast group."""
        self.multicast.send(envelope)
        self.server_handler.send(envelope)

    async def send_to(self, uid: str, envelope: TakEnvelope) -> bool:
        """Sends data to a specific user via tcp or server."""
        if uid not in self.users:
            addr = self.multicast.get_user_addr(uid)
            if addr is not None:
                self.users[uid] = NetworkUser(uid, addr, V0Codec())
                await self.users[uid].make_connection()
            else:
                return False
        await self.users[uid].send(envelope)
        return True

    def get_endpoint(self):
        return f"{host_ip()}:{self.port}:tcp"


class ServerProtocol(asyncio.Protocol):
    def __init__(self, network_manager: NetworkManager) -> None:
        self._transport = None
        self.network_manager = network_manager

    def connection_made(self, transport):
        self._transport = cast(asyncio.Transport, transport)
        logger.debug(
            f"Connection made from {self._transport.get_extra_info('peername')}"
        )

    def data_received(self, data):
        print(data)
        if self._transport is not None:
            self.network_manager.callback(
                self.network_manager.codec.decode(data),
                self._transport.get_extra_info("peername"),
                self._transport,
            )
