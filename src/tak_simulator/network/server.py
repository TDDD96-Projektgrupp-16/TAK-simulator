import asyncio
import ssl
from typing import Callable, List, Self, cast
from xml.etree import ElementTree as ET

from tak_simulator.wire import Codec, TakEnvelope


class ServerHandler:
    def __init__(self, servers: List[Server]) -> None:
        self.servers: List[Server] = servers
        self.callback: (
            Callable[[TakEnvelope, tuple[str, int], asyncio.Transport], None] | None
        ) = None

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

    def _callback(
        self, envelope: TakEnvelope, addr: tuple[str, int], transport: asyncio.Transport
    ) -> None:
        if self.callback:
            self.callback(envelope, addr, transport)


class Server:
    def __init__(
        self,
        ip: str,
        cafile: str,
        certfile: str,
        keyfile: str,
        codec: Codec,
        port: int = 8089,
    ) -> None:
        """Files are str paths to the CA, cert, and key files."""
        self.ip = ip
        self.port = port
        self.cafile = cafile
        self.certfile = certfile
        self.keyfile = keyfile
        self.codec = codec
        self.transport = None
        self.callback = None

    def set_server(self, transport: asyncio.Transport) -> None:
        self.transport = transport

    def set_callback(
        self,
        callback: Callable[[TakEnvelope, tuple[str, int], asyncio.Transport], None],
    ) -> None:
        self.callback = callback

    def send(self, data: TakEnvelope) -> None:
        if self.transport:
            self.transport.write(self.codec.encode(data))

    async def connect(self) -> None:
        ctx = ssl.create_default_context(cafile=self.cafile)
        ctx.check_hostname = False  # TODO
        ctx.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)

        loop = asyncio.get_event_loop()
        transport, _ = await loop.create_connection(
            lambda: ServerProtocol(self), self.ip, self.port, ssl=ctx
        )
        self.set_server(transport)

    def _callback(
        self, data: bytes, addr: tuple[str, int], transport: asyncio.Transport
    ) -> None:
        if self.callback:
            self.callback(self.codec.decode(data), addr, transport)


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
                self.server._callback(self.buffer, addr, self.transport)
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
                        self.server._callback(first_msg, addr, self.transport)

                    # 4. Save the "junk" (the next message) for the next while-loop iteration
                    self.buffer = self.buffer[split_idx:]
                else:
                    # An actual parse error or incomplete stream; wait for more data
                    break
