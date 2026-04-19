import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, List, Tuple

from tak_simulator.network_handler import NetworkHandler, Server
from tak_simulator.proto.contact_pb2 import Contact
from tak_simulator.proto.cotevent_pb2 import CotEvent
from tak_simulator.proto.detail_pb2 import Detail
from tak_simulator.proto.group_pb2 import Group
from tak_simulator.proto.precisionlocation_pb2 import PrecisionLocation
from tak_simulator.proto.status_pb2 import Status
from tak_simulator.proto.takmessage_pb2 import TakMessage
from tak_simulator.proto.takv_pb2 import Takv
from tak_simulator.proto.track_pb2 import Track
from tak_simulator.scenario import EmulatorOptions
from tak_simulator.time_keeper import TimeKeeper

logger = logging.getLogger(__name__)


@dataclass
class Emulator:
    options: EmulatorOptions
    time_keeper: TimeKeeper
    host: str

    multicast_addr: Tuple[str, int] = ("239.2.3.1", 6969)  # TODO
    servers: List[Server] = field(
        default_factory=lambda: [
            Server(
                "192.71.171.115",
                "./certs/ca.pem",
                "./certs/client.pem",
                "./certs/client.key",
            )
        ]
    )
    simulation_start_time: datetime = field(default_factory=lambda: datetime.now(UTC))

    async def run(self):
        server = await asyncio.start_server(handle, "0.0.0.0")  # TODO
        addr, port = server.sockets[0].getsockname()
        self.endpoint = f"{self.host}:{port}:tcp"

        logger.info(f"Server started on {self.endpoint}")
        self.connection = await NetworkHandler.create_connection(
            self.multicast_addr[0],
            self.multicast_addr[1],
            self.dataReceived,
            self.servers,
        )

        while True:
            t = self.time_keeper.get_time()
            tak_message = self.tak_message(t)

            data = encode_tak_message(tak_message)
            self.connection.send_all(data)

            await asyncio.sleep(3)  # TODO

    def dataReceived(self, data: bytes, addr: Tuple[str | Any, int]) -> None:
        logger.debug(f"Received data from {addr}")

    def tak_message(self, t: float) -> TakMessage:
        send_time = int(time.time() * 1000)

        lat, lon = self.get_position(t)

        hae: float = 0  # TODO

        cot_event = CotEvent(
            type=self.options.type,
            access=self.options.access,
            caveat=None,
            releasableTo=None,
            qos=None,
            opex=None,
            uid=self.options.uid,
            sendTime=send_time,
            startTime=send_time,
            staleTime=send_time + 75000,  # TODO
            how=self.options.how,
            lat=lat,
            lon=lon,
            hae=hae,
            ce=999999,  # TODO
            le=999999,  # TODO
            detail=Detail(
                xmlDetail=f'<uid Droid="{self.options.callsign}"/>',
                contact=Contact(
                    endpoint=self.endpoint,
                    callsign=self.options.callsign,
                ),
                group=Group(
                    name=self.options.group.name,
                    role=self.options.group.role,
                ),
                precisionLocation=PrecisionLocation(
                    geopointsrc="GPS",
                    altsrc="GPS",
                ),
                status=Status(
                    battery=100,  # TODO
                ),
                takv=Takv(
                    device=self.options.takv.device,
                    platform=self.options.takv.platform,
                    os=self.options.takv.os,
                    version=self.options.takv.version,
                ),
                track=Track(
                    speed=None,  # TODO
                    course=None,  # TODO
                ),
            ),
        )

        return TakMessage(
            cotEvent=cot_event,
        )

    def get_position(self, t: float) -> tuple[float, float]:
        i = 0
        while i < len(self.options.path) and t > self.options.path[i][0]:
            i += 1

        if i == 0:
            return self.options.path[0][1]

        if i >= len(self.options.path):
            return self.options.path[-1][1]

        t1, p1 = self.options.path[i - 1]
        t2, p2 = self.options.path[i]

        x = (t - t1) / (t2 - t1)

        return tuple(a + (b - a) * x for a, b in zip(p1, p2))


async def handle(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
):
    raw = await reader.read()
    print(f"got message {raw=}")

    writer.close()
    await writer.wait_closed()


def encode_tak_message(tak_message: TakMessage) -> bytes:
    return b"\277\001\277" + tak_message.SerializeToString()
