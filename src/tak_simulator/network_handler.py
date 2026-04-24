import asyncio
import logging
import socket
import ssl
import struct
from typing import Any, Callable, Self, cast

from tak_simulator.util import host_ip
from tak_simulator.wire.v1 import V1Codec

logger = logging.getLogger(__name__)


class NetworkHandler:
    def __init__(
        self,
        transport,
        multicast_addr: str,
        multicast_port: int,
        server_port: int,
        servers: list[Server],
    ):
        self.transport = transport
        self.multicast_addr = multicast_addr
        self.multicast_port = multicast_port
        self.servers: list[Server] = servers
        self.server_port = server_port
        self.server: asyncio.Server | None = None
        self._users: dict[str, TcpUser] = {}

    @classmethod
    async def create_connection(
        cls,
        multicast_addr: str,
        multicast_port: int,
        server_port: int,
        callback: Callable[[bytes, tuple[str | Any, int]], None],
        servers: list[Server] = [],
    ) -> Self:
        """Creates a multicast connection and optionally connects to servers."""
        instance = cls(None, multicast_addr, multicast_port, server_port, servers)

        logger.info(
            f"Setting up multicast connection to {multicast_addr}:{multicast_port}"
        )

        transport, protocol = await cls._setup_multicast(
            multicast_addr, multicast_port, callback
        )

        instance.transport = transport

        logger.info(
            f"Multicast connection established to {multicast_addr}:{multicast_port}"
        )

        asyncio.create_task(instance._start_tcp_server())

        logger.info(f"Setting up servers ({len(servers)})")
        await cls._setup_servers(servers, callback)

        return instance

    @classmethod
    async def _setup_multicast(
        cls,
        multicast_addr: str,
        multicast_port: int,
        callback: Callable[[bytes, tuple[str | Any, int]], None],
    ):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.bind(("0.0.0.0", multicast_port))

        mreq = struct.pack("4sl", socket.inet_aton(multicast_addr), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 64)

        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)

        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: MulticastProtocol(callback), sock=sock
        )
        return transport, protocol

    @classmethod
    async def _setup_servers(
        cls,
        servers: list[Server],
        callback: Callable[[bytes, tuple[str | Any, int]], None],
    ):
        tasks = [cls._setup_server(server, callback) for server in servers]
        return await asyncio.gather(*tasks)

    @classmethod
    async def _setup_server(
        cls, server: Server, callback: Callable[[bytes, tuple[str | Any, int]], None]
    ):
        # Create an SSL context for the server
        ctx = ssl.create_default_context(cafile=server.cafile)
        ctx.check_hostname = False  # TODO
        ctx.load_cert_chain(certfile=server.certfile, keyfile=server.keyfile)

        loop = asyncio.get_running_loop()
        on_con_lost = loop.create_future()
        transport, protocol = await loop.create_connection(
            lambda: ServerProtocol(on_con_lost, callback),
            server.ip,
            server.port,
            ssl=ctx,
        )

        server.set_server(transport, protocol)
        return transport, protocol

    async def _start_tcp_server(self):
        loop = asyncio.get_running_loop()
        self.server = await loop.create_server(
            lambda: ServerTcpProtocol(self._tcp_data_received),
            "0.0.0.0",
            self.server_port,
        )
        await self.server.serve_forever()

    def send_all(self, data: bytes):
        """Sends data to multicast and all connected servers. (Must be XML. Server only supports XML.)"""
        self.multicast_send(data)
        self.send_to_servers(data)

    def multicast_send(self, data: bytes):
        """Sends data to multicast."""
        self.transport.sendto(data, (self.multicast_addr, self.multicast_port))

    def send_to_servers(self, data: bytes):
        """Sends data to all connected servers."""
        for server in self.servers:
            server.send(data)

    def get_endpoint(self) -> str:
        """Returns the endpoint of the TCP server, or an empty string if not available."""
        if not self.server:
            return ""
        return f"{host_ip()}:{self.server_port}:tcp"

    def send_to_user(self, uid: str, data: bytes):
        """Sends data to a specific user."""
        if uid not in self._users:
            return
        self._users[uid].send(data)

    def set_callback_for_user(
        self, uid: str, callback: Callable[[bytes, tuple[str | Any, int]], None]
    ):
        """Sets the callback for a specific user."""
        if uid not in self._users:
            return
        self._users[uid].set_callback(callback)

    def _tcp_data_received(
        self, data: bytes, addr: tuple[str | Any, int], transport: asyncio.Transport
    ) -> None:
        logger.debug(f"Received data from {addr}: {data}")

        envelope = V1Codec().decode(data)
        if not envelope.event:
            return
        uid = envelope.event.uid

        user = self._users.get(uid)
        if not user:
            user = TcpUser(uid, addr[0], addr[1])
            user.transport = transport
            self._users[uid] = user
        user.trigger_callback(data)


class MulticastProtocol(asyncio.DatagramProtocol):
    def __init__(self, callback: Callable[[bytes, tuple[str | Any, int]], None]):
        self.transport = None
        self.callback = callback

    def connection_made(self, transport) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str | Any, int]) -> None:
        self.callback(data, addr)


class ServerProtocol(asyncio.Protocol):
    def __init__(
        self,
        on_con_lost: asyncio.Future,
        callback: Callable[[bytes, tuple[str | Any, int]], None],
    ):
        self.transport = None
        self.callback = callback
        self.on_con_lost = on_con_lost

    def connection_made(self, transport) -> None:
        self.transport = transport

    def data_received(self, data: bytes) -> None:
        if self.transport:
            self.callback(data, self.transport.get_extra_info("peername"))

    def connection_lost(self, exc) -> None:
        self.on_con_lost.set_result(True)


class ServerTcpProtocol(asyncio.Protocol):
    def __init__(
        self,
        callback: Callable[[bytes, tuple[str | Any, int], asyncio.Transport], None],
    ):
        self.callback = callback

    def connection_made(self, transport) -> None:
        self.transport = cast(asyncio.Transport, transport)

    def data_received(self, data: bytes) -> None:
        if self.transport:
            self.callback(
                data, self.transport.get_extra_info("peername"), self.transport
            )


class Server:
    def __init__(
        self, ip: str, cafile: str, certfile: str, keyfile: str, port: int = 8089
    ) -> None:
        """Files are str paths to the CA, cert, and key files."""
        self.ip = ip
        self.port = port
        self.cafile = cafile
        self.certfile = certfile
        self.keyfile = keyfile
        self.transport = None
        self.protocol = None

    def set_server(
        self, transport: asyncio.Transport, protocol: asyncio.Protocol
    ) -> None:
        self.transport = transport
        self.protocol = protocol

    def send(self, data: bytes) -> None:
        if self.transport:
            self.transport.write(data)


class TcpUser:
    def __init__(self, uid: str, ip: str, port: int) -> None:
        self.uid = uid
        self.ip = ip
        self.port = port
        self.transport = None
        self.callback = self._temp_callback

    def set_transport(self, transport: asyncio.Transport) -> None:
        self.transport = transport

    def send(self, data: bytes) -> None:
        if self.transport:
            self.transport.write(data)

    def set_callback(self, callback: Callable[[bytes, tuple[str, int]], None]) -> None:
        self.callback = callback

    def _temp_callback(self, data: bytes, peername: tuple[str, int]) -> None: ...

    def trigger_callback(self, data: bytes) -> None:
        logger.debug(f"Triggering callback with data: {data}")
        self.callback(data, (self.ip, self.port))
