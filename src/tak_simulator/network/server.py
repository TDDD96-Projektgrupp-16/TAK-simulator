import asyncio
import ssl
from typing import Callable, List, Self, cast
from xml.etree import ElementTree as ET

from pydantic import BaseModel

from tak_simulator.wire import Codec, TakEnvelope


class ServerConfig(BaseModel):
    ip: str
    port: int
    cafile: str | None = None
    certfile: str | None = None
    keyfile: str | None = None
    upgrade: bool = False


class ServerHandler:
    def __init__(self, servers: List[Server]) -> None:
        self.servers: List[Server] = servers
        self.callback: Callable[[TakEnvelope, tuple[str, int]], None] | None = None

    @classmethod
    async def create_server_connection(
        cls,
        servers: List[Server],
    ) -> Self:
        instance = cls(servers)
        for server in instance.servers:
            await server.connect()
            server.set_callback(instance._callback)
        return instance

    def send(self, envelope: TakEnvelope) -> None:
        for server in self.servers:
            server.send(envelope)

    def _callback(self, envelope: TakEnvelope, addr: tuple[str, int]) -> None:
        if self.callback:
            self.callback(envelope, addr)

    def get_user_addr(self, uid: str) -> tuple[str, int] | None:
        for server in self.servers:
            addr = server.get_user_addr(uid)
            if addr is not None:
                return addr
        return None

    def get_user_callsign(self, uid: str) -> str | None:
        for server in self.servers:
            callsign = server.get_user_callsign(uid)
            if callsign is not None:
                return callsign
        return None


class Server:
    def __init__(
        self,
        ip: str,
        port: int,
        codec: Codec,
        *,
        cafile: str | None = None,
        certfile: str | None = None,
        keyfile: str | None = None,
        upgrade: bool = False,
    ) -> None:

        self.ip = ip
        self.port = port
        self.codec = codec
        self.cafile = cafile
        self.certfile = certfile
        self.keyfile = keyfile
        self.upgrade = upgrade
        self.transport = None
        self.callback = None
        self._users: dict[str, tuple[str, int]] = {}
        self._callsigns: dict[str, str | None] = {}

    def set_server(self, transport: asyncio.Transport) -> None:
        self.transport = transport

    def set_callback(
        self,
        callback: Callable[[TakEnvelope, tuple[str, int]], None],
    ) -> None:
        self.callback = callback

    def send(self, data: TakEnvelope) -> None:
        if self.transport:
            self.transport.write(self.codec.encode(data))

    async def connect(self) -> None:
        if self.upgrade:
            raise NotImplementedError("Using a server with upgrade=True is unsupported")

        if self.cafile is None or self.certfile is None or self.keyfile is None:
            raise ValueError(
                "Certificate files (cafile, certfile, keyfile) are required for TLS connection"
            )
        ctx = ssl.create_default_context(cafile=self.cafile)
        ctx.check_hostname = False  # TODO
        ctx.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)

        loop = asyncio.get_event_loop()
        transport, _ = await loop.create_connection(
            lambda: ServerProtocol(self), self.ip, self.port, ssl=ctx
        )
        self.set_server(transport)

    def _callback(self, data: bytes, addr: tuple[str, int]) -> None:
        envelope = self.codec.decode(data)
        if envelope.event is not None and envelope.event.detail is not None:
            contact = envelope.event.detail.contact
            if contact is not None and contact.endpoint is not None:
                try:
                    user, port, protocol = contact.endpoint.split(":")
                    if protocol.lower() == "tcp":
                        self._users[envelope.event.uid] = (user, int(port))
                        self._callsigns[envelope.event.uid] = contact.callsign
                except ValueError:
                    pass
        if self.callback:
            self.callback(envelope, addr)

    def get_user_addr(self, uid: str) -> tuple[str, int] | None:
        return self._users.get(uid)

    def get_user_callsign(self, uid: str) -> str | None:
        return self._callsigns.get(uid)


class ServerProtocol(asyncio.Protocol):
    def __init__(self, server: Server) -> None:
        self.server = server
        self.transport: asyncio.Transport | None = None
        self.buffer = b""

    def connection_made(self, transport) -> None:
        self.transport = cast(asyncio.Transport, transport)

    def data_received(self, data: bytes) -> None:
        """Ai slop method for parsing XML data from the network.
        It needs when multiple xml documents are received in a single chunk."""
        self.buffer += data
        if not self.transport:
            return

        addr = self.transport.get_extra_info("peername")
        while self.buffer:
            try:
                ET.fromstring(self.buffer)
                # If we get here, the entire buffer is one valid XML document
                self.server._callback(self.buffer, addr)
                self.buffer = b""
                break
            except ET.ParseError as e:
                err_msg = str(e)
                if "junk after document element" in err_msg:
                    import re

                    # 1. Extract both line and column
                    match = re.search(r"line (\d+), column (\d+)", err_msg)
                    if not match:
                        self.buffer = b""
                        break

                    line = int(match.group(1))
                    col = int(match.group(2))

                    # 2. Calculate absolute byte offset across multiple lines
                    lines = self.buffer.splitlines(keepends=True)
                    split_idx = sum(len(line) for line in lines[: line - 1]) + col

                    # 3. Slice exactly at split_idx (do not subtract 1)
                    first_msg = self.buffer[:split_idx]

                    if first_msg:
                        self.server._callback(first_msg, addr)

                    # 4. Save the "junk" (the next message) for the next while-loop iteration
                    self.buffer = self.buffer[split_idx:]
                else:
                    # An actual parse error or incomplete stream; wait for more data
                    break
