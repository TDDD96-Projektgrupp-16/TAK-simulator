from typing import Any
import asyncio
import time
import socket

from dataclasses import dataclass

from tak_simulator.proto.track_pb2 import Track
from tak_simulator.proto.takv_pb2 import Takv
from tak_simulator.proto.status_pb2 import Status
from tak_simulator.proto.precisionlocation_pb2 import PrecisionLocation
from tak_simulator.proto.group_pb2 import Group
from tak_simulator.proto.contact_pb2 import Contact
from tak_simulator.proto.detail_pb2 import Detail
from tak_simulator.proto.takmessage_pb2 import TakMessage
from tak_simulator.proto.cotevent_pb2 import CotEvent

from tak_simulator.config import EmulatorConfig
from tak_simulator.time_keeper import TimeKeeper


@dataclass
class Emulator:
    config: EmulatorConfig
    time_keeper: TimeKeeper
    host: str

    multicast_addr: Any = ("239.2.3.1", 6969)  # TODO

    async def run(self):
        server = await asyncio.start_server(handle, "0.0.0.0")  # TODO

        addr, port = server.sockets[0].getsockname()
        self.endpoint = f"{self.host}:{port}:tcp"

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

        while True:
            t = self.time_keeper.get_time()
            tak_message = self.tak_message(t)

            data = encode_tak_message(tak_message)
            sock.sendto(data, self.multicast_addr)

            tak_action = self.handle_action(t)

            if tak_action is not None:
                pass

            await asyncio.sleep(3)  # TODO

    def tak_message(self, t: float) -> TakMessage:
        send_time = int(time.time() * 1000)

        lat, lon = self.get_position(t)

        hae: float = 0  # TODO

        cot_event = CotEvent(
            type=self.config.type_,
            access=self.config.access,
            caveat=None,
            releasableTo=None,
            qos=None,
            opex=None,
            uid=self.config.uid,
            sendTime=send_time,
            startTime=send_time,
            staleTime=send_time + 75000,  # TODO
            how=self.config.how,
            lat=lat,
            lon=lon,
            hae=hae,
            ce=999999,  # TODO
            le=999999,  # TODO
            detail=Detail(
                xmlDetail=f'<uid Droid="{self.config.callsign}"/>',
                contact=Contact(
                    endpoint=self.endpoint,
                    callsign=self.config.callsign,
                ),
                group=Group(
                    name=self.config.group.name,
                    role=self.config.group.role,
                ),
                precisionLocation=PrecisionLocation(
                    geopointsrc="GPS",
                    altsrc="GPS",
                ),
                status=Status(
                    battery=100,  # TODO
                ),
                takv=Takv(
                    device=self.config.takv.device,
                    platform=self.config.takv.platform,
                    os=self.config.takv.os,
                    version=self.config.takv.version,
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
        while i < len(self.config.path) and t > self.config.path[i][0]:
            i += 1

        if i == 0:
            return self.config.path[0][1]

        if i >= len(self.config.path):
            return self.config.path[-1][1]

        t1, p1 = self.config.path[i - 1]
        t2, p2 = self.config.path[i]

        x = (t - t1) / (t2 - t1)

        return tuple(a + (b - a) * x for a, b in zip(p1, p2))

    
    def handle_action(self, t: float):
        pass


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
