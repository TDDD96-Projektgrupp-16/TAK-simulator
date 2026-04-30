import asyncio
from typing import List, Tuple, cast

from tak_simulator.network.multicast import MulticastHandler
from tak_simulator.network.server import Server, ServerHandler


class NetworkManager:
    def __init__(
        self, multicast: MulticastHandler, server_handler: ServerHandler
    ) -> None:
        self._server = None
        self.multicast = multicast
        self.server_handler = server_handler

    @classmethod
    async def create_connection(
        cls, multicast: MulticastHandler, servers: List[Server], port: int
    ):
        server_handler = await ServerHandler.create_server_connection(servers)

        instance = cls(multicast, server_handler)
        asyncio.create_task(instance._start_server(port))

        return instance

    async def _start_server(self, port: int):
        loop = asyncio.get_event_loop()
        self._server = await loop.create_server(
            lambda: ServerProtocol(self), "0.0.0.0", port
        )
        await self._server.serve_forever()

    def callback(self, data: bytes, addr: Tuple[str, int]) -> None:
        pass


class ServerProtocol(asyncio.Protocol):
    def __init__(self, network_manager: NetworkManager) -> None:
        self._transport = None
        self.network_manager = network_manager

    def connection_made(self, transport):
        self._transport = cast(asyncio.Transport, transport)

    def data_received(self, data):
        if self._transport is not None:
            self.network_manager.callback(
                data, self._transport.get_extra_info("peername")
            )
