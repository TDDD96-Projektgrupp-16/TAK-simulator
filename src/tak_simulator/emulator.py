import asyncio
import time
import socket
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from tak_simulator.scenario import EmulatorOptions, ScenarioEvent
from tak_simulator.scenario_scheduler import ScenarioScheduler
from tak_simulator.time_keeper import TimeKeeper

from tak_simulator.proto.contact_pb2 import Contact
from tak_simulator.proto.cotevent_pb2 import CotEvent
from tak_simulator.proto.detail_pb2 import Detail
from tak_simulator.proto.group_pb2 import Group
from tak_simulator.proto.precisionlocation_pb2 import PrecisionLocation
from tak_simulator.proto.status_pb2 import Status
from tak_simulator.proto.takmessage_pb2 import TakMessage
from tak_simulator.proto.takv_pb2 import Takv
from tak_simulator.proto.track_pb2 import Track

import logging

logger = logging.getLogger(__name__)


@dataclass
class Emulator:
    options: EmulatorOptions
    time_keeper: TimeKeeper
    scheduler: ScenarioScheduler
    host: str

    multicast_addr: Any = ("239.2.3.1", 6969)  # TODO
    simulation_start_time: datetime = field(default_factory=lambda: datetime.now(UTC))

    endpoint: str = field(init=False, default="")
    sock: socket.socket | None = field(init=False, default=None)
    server: asyncio.AbstractServer | None = field(init=False, default=None)

    async def run(self):
        logger.info("started emulator with callsign: %s", self.options.callsign)
        self.server = await asyncio.start_server(handle, "0.0.0.0")  # TODO

        addr, port = self.server.sockets[0].getsockname()
        self.endpoint = f"{self.host}:{port}:tcp"

        self.sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
        )

        self.sock.bind((self.host, 0))

        self.sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_IF,
            socket.inet_aton(self.host),
        )

        self.sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_TTL,
            64,
        )

        self.sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_LOOP,
            1,
        )

        self.scheduler.schedule_recurring(
            start_time=0.0,
            interval=3.0,
            callback=self.publish_position,
            name=f"publish_position:{self.options.callsign}",
        )

        for event in self.options.events:
            self.scheduler.schedule_once(
                due_time=event.time,
                callback=self.handle_scenario_event,
                event=event,
                name=f"{event.event_type}:{self.options.callsign}",
            )

        logger.info(
            "Emulator %s registered recurring position updates and %d scenario events",
            self.options.callsign,
            len(self.options.events),
        )

        await asyncio.Future()

    async def publish_position(self) -> None:
        if self.sock is None:
            logger.warning("Emulator %s has no socket yet", self.options.callsign)
            return

        t = self.time_keeper.get_time()
        tak_message = self.tak_message(t)
        data = encode_tak_message(tak_message)
        self.sock.sendto(data, self.multicast_addr)

    async def handle_scenario_event(self, event: ScenarioEvent) -> None:
        if event.event_type == "chat":
            logger.info(
                "Scenario chat event for %s at t=%.3f: %s",
                self.options.callsign,
                self.time_keeper.get_time(),
                event.message,
            )
            return

        if event.event_type == "connect":
            logger.info(
                "Scenario connect event for %s at t=%.3f",
                self.options.callsign,
                self.time_keeper.get_time(),
            )
            return

        if event.event_type == "disconnect":
            logger.info(
                "Scenario disconnect event for %s at t=%.3f",
                self.options.callsign,
                self.time_keeper.get_time(),
            )
            return

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
