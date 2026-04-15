import datetime
import ssl
from abc import ABC, abstractmethod
from typing import Any, Self


import socket


class TAKMessage:
    pass

    @classmethod
    def parse(cls, data: bytes) -> Self:
        raise NotImplementedError()

    def encode(self) -> bytes:
        raise NotImplementedError()


class MessageEncoder(ABC):
    @abstractmethod
    def encode(self, message: TAKMessage) -> bytes: ...


class MockXMLEncoder(MessageEncoder):
    def format(self, message: TAKMessage) -> bytes:
        now = datetime.datetime.utcnow()
        stale = now + datetime.timedelta(minutes=5)

        time_fmt = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        stale_fmt = stale.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Constructing the XML string
        cot_xml = f"""<?xml version="1.0" standalone="yes"?>
        <event version="2.0"
            uid="ANDROID-e99c38bfa54c8dc2"
            type="a-f-G-U-C"
            time="{time_fmt}"
            start="{time_fmt}"
            stale="{stale_fmt}"
            how="m-g">
            <point lat="0.0" lon="0.0" hae="0.0" ce="10.0" le="10.0"/>
            <detail>
                <contact callsign="Python-Bot"/>
                <takv device="Python Script" platform="Python" os="1.0" version="1.0"/>
                <group name="Cyan" role="Team Member"/>
            </detail>
        </event>"""

        return cot_xml.encode()


class MessageSender(ABC):
    encoder: MessageEncoder = MockXMLEncoder()

    def send(self, message: TAKMessage):
        self._send(self.encoder.encode(message))

    @abstractmethod
    def _send(self, message: bytes): ...


class UDPSender(MessageSender):
    socket: socket.socket
    host: str

    multicast_addr: Any = ("239.2.3.1", 6969)  # TODO

    def __init__(self, host: str):
        self.host = host

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
        )

        sock.bind((self.host, 0))

        sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_IF,
            socket.inet_aton(self.host),
        )

        sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_TTL,
            64,
        )

        sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_LOOP,
            1,
        )

        self.socket = sock

    def _send(self, message: bytes):
        self.socket.sendto(message, self.multicast_addr)


class TCPSender(MessageSender):
    socket: ssl.SSLSocket
    host: str

    def __init__(
        self,
        host: str,
        cafile: str,
        certfile: str,
        keyfile: str,
        server_name: str,
        server_port: int,
    ):
        self.host = host

        ctx = ssl.create_default_context(cafile=cafile)

        ctx.check_hostname = False  # TODO

        ctx.load_cert_chain(certfile, keyfile)  # TODO

        raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        sock = ctx.wrap_socket(raw_socket, server_hostname=server_name)
        sock.connect((server_name, server_port))

        self.socket = sock

    def _send(self, message: bytes):
        self.socket.sendall(message)
