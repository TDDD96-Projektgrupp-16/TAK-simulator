import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import List

from tak_simulator.network.multicast import MulticastHandler
from tak_simulator.network.network_manager import NetworkManager
from tak_simulator.network.server import Server
from tak_simulator.scenario import EmulatorOptions, ScenarioEvent
from tak_simulator.scenario_scheduler import ScenarioScheduler, ScheduledEvent
from tak_simulator.time_keeper import TimeKeeper
from tak_simulator.wire import (
    Codec,
    Contact,
    CotDetail,
    CotEvent,
    Group,
    Point,
    Status,
    TakEnvelope,
    TakVersion,
)
from tak_simulator.wire.v0 import V0Codec


from tak_simulator.xml_parse import (
    build_chat_detail_for_direct_message,
    encode_chat_detail,
)

from tak_simulator.wire import TakControl

logger = logging.getLogger(__name__)


@dataclass
class Emulator:
    options: EmulatorOptions
    time_keeper: TimeKeeper
    scheduler: ScenarioScheduler
    multicast: MulticastHandler
    port: int
    servers: List[Server]

    simulation_start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    publish_position_event: ScheduledEvent | None = field(init=False, default=None)
    is_connected: bool = field(init=False, default=True)
    codec: Codec = field(default_factory=V0Codec)

    async def run(self) -> None:

        self.connection = await NetworkManager.create_connection(
            self.multicast, self.servers, self.port, self.codec
        )

        logger.info("started emulator with callsign: %s", self.options.callsign)

        self.publish_position_event = self.scheduler.schedule_recurring(
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

    async def publish_position(self) -> None:
        t = self.time_keeper.get_time()

        envelope = self.tak_env(t)
        self.connection.broadcast(envelope)

    async def handle_scenario_event(self, event: ScenarioEvent) -> None:
        current_time = self.time_keeper.get_time()

        if event.event_type == "chat":
            if not self.is_connected:
                logger.info(
                    "Skipping scenario chat event for disconnected emulator %s at t=%.3f",
                    self.options.callsign,
                    current_time,
                )
                return

            logger.info(
                "Scenario chat event for %s at t=%.3f: %s",
                self.options.callsign,
                current_time,
                event.message,
            )
            return

        if event.event_type == "connect":
            if self.is_connected:
                logger.info(
                    "%s is already connected at t=%.3f",
                    self.options.callsign,
                    current_time,
                )
                return

            self.is_connected = True
            logger.info(
                "Scenario connect event for %s at t=%.3f",
                self.options.callsign,
                current_time,
            )
            return

        if event.event_type == "disconnect":
            if not self.is_connected:
                logger.info(
                    "%s is already disconnected at t=%.3f",
                    self.options.callsign,
                    current_time,
                )
                return

            self.is_connected = False
            logger.info(
                "Scenario disconnect event for %s at t=%.3f",
                self.options.callsign,
                current_time,
            )
            return

    def _create_msg(self, t: float, msg: str, detail: bool) -> TakEnvelope:
        send_time = datetime.now(UTC)

        lat, lon = self.get_position(t)

        return TakEnvelope(
            event=CotEvent(
                type=self.options.type,
                access=self.options.access,
                caveat=None,
                releasable_to=None,
                qos=None,
                opex=None,
                uid=self.options.uid,
                send_time=send_time,
                start_time=send_time,
                stale_time=send_time + timedelta(seconds=75),  # TODO
                how=self.options.how,
                point=Point(
                    lat=lat,
                    lon=lon,
                ),
                detail=CotDetail(
                    contact=Contact(
                        endpoint=self.connection.get_endpoint(),
                        callsign=self.options.callsign,
                    ),
                    group=Group(
                        name=self.options.group.name,
                        role=self.options.group.role,
                    ),
                    status=Status(
                        battery=100,  # TODO
                    ),
                    takv=TakVersion(
                        device=self.options.takv.device,
                        platform=self.options.takv.platform,
                        os=self.options.takv.os,
                        version=self.options.takv.version,
                    ),
                    opaque_xml=msg,
                ),
            )
        )

    def tak_env(self, t: float) -> TakEnvelope:
        return self._create_msg(t, f'<uid Droid="{self.options.callsign}"/>', True)

    def _create_msg2(self, t: float, msg: str, to_uid: str) -> TakEnvelope:
        send_time = datetime.now(UTC)

        lat, lon = self.get_position(t)

        return TakEnvelope(
            event=CotEvent(
                type=self.options.type,
                access=self.options.access,
                caveat=None,
                releasable_to=None,
                qos=None,
                opex=None,
                uid=f"Geochat.{self.options.uid}.{to_uid}.{uuid.uuid4()}",
                send_time=send_time,
                start_time=send_time,
                stale_time=send_time + timedelta(seconds=75),  # TODO
                how=self.options.how,
                point=Point(
                    lat=lat,
                    lon=lon,
                ),
                detail=CotDetail(
                    opaque_xml=msg,
                ),
            ),
            control=TakControl(
                min_proto_version=None,
                max_proto_version=None,
                contact_uid=self.options.uid,
                extension_ids=[],
            ),
        )

    async def send_msg(self, to_uid: str, msg: str):
        chat_detail = build_chat_detail_for_direct_message(self.options, to_uid, msg)
        data = encode_chat_detail(chat_detail)
        env = self._create_msg2(self.time_keeper.get_time(), str(data)[10:-10], to_uid)
        await self.connection.send_to(to_uid, env)
        logger.info(
            "Emulator %s sent message %s to %s at time %.3f",
            self.options.uid,
            msg,
            to_uid,
            self.time_keeper.get_time(),
        )

    def get_position(self, t: float) -> tuple[float, float]:
        i = 0
        while i < len(self.options.path) and t > self.options.path[i][0]:
            i += 1

        if i == 0:
            return self.options.path[0][1]

        if i >= len(self.options.path):
            return self.options.path[-1][1]

        t1, (la1, lo1) = self.options.path[i - 1]
        t2, (la2, lo2) = self.options.path[i]

        n = (t - t1) / (t2 - t1)

        return (
            la1 + (la2 - la1) * n,
            lo1 + (lo2 - lo1) * n,
        )
