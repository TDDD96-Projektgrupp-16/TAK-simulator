from typing import Callable, Any
import ssl
from ssl import SSLContext
from tak_simulator.sender import TAKMessage
import asyncio


async def create_udp_client(hostname: str, hostport: int):
    reader, writer = await asyncio.open_connection(hostname, hostport)

    await asyncio.gather(udp_listener(reader, print), udp_sender(writer))

    return reader, writer


async def create_tcp_client(
    hostname: str, hostport: int, cafile: str, certfile: str, keyfile: str
):
    ctx = create_ssl_context(cafile, certfile, keyfile)
    reader, writer = await asyncio.open_connection(hostname, hostport, ssl=ctx)

    await asyncio.gather(udp_listener(reader, print), udp_sender(writer))

    return reader, writer


async def udp_listener(
    reader: asyncio.StreamReader, callback: Callable[[TAKMessage], Any]
):
    while True:
        data = await reader.read()
        message = TAKMessage.parse(data)
        callback(message)


async def udp_sender(writer: asyncio.StreamWriter):
    while True:
        message = TAKMessage()
        writer.write(message.encode())
        await writer.drain()
        await asyncio.sleep(3)


def create_ssl_context(cafile: str, certfile: str, keyfile: str) -> SSLContext:
    ctx = ssl.create_default_context(cafile=cafile)

    ctx.check_hostname = False  # TODO

    ctx.load_cert_chain(certfile, keyfile)  # TODO
    return ctx
