from __future__ import annotations

import logging
from datetime import UTC, datetime
from xml.etree import ElementTree as ET

from tak_simulator.wire.exceptions import DecodeError
from tak_simulator.wire.models import (
    Contact,
    CotDetail,
    CotEvent,
    ExtensionDetail,
    Group,
    MessageContext,
    Point,
    PrecisionLocation,
    Status,
    TakControl,
    TakEnvelope,
    TakVersion,
    Track,
)

from tak_simulator.proto.cotevent_pb2 import CotEvent as ProtoCotEvent
from tak_simulator.proto.contact_pb2 import Contact as ProtoContact
from tak_simulator.proto.detail_pb2 import Detail as ProtoDetail
from tak_simulator.proto.group_pb2 import Group as ProtoGroup
from tak_simulator.proto.precisionlocation_pb2 import (
    PrecisionLocation as ProtoPrecisionLocation,
)
from tak_simulator.proto.status_pb2 import Status as ProtoStatus
from tak_simulator.proto.takcontrol_pb2 import TakControl as ProtoTakControl
from tak_simulator.proto.takmessage_pb2 import TakMessage as ProtoTakMessage
from tak_simulator.proto.takv_pb2 import Takv as ProtoTakv
from tak_simulator.proto.track_pb2 import Track as ProtoTrack

FRAME_PREFIX = b"\xbf\001\xbf"
UNKNOWN_NUMERIC_VALUE = 999999.0

logger = logging.getLogger(__name__)


class V1Codec:
    def decode(self, data: bytes, *, unframe: bool = True) -> TakEnvelope:
        raw = _unframe(data) if unframe else data

        proto = ProtoTakMessage()
        proto.ParseFromString(raw)

        return TakEnvelope(
            event=_decode_event(proto.cotEvent) if proto.HasField("cotEvent") else None,
            control=(
                _decode_control(proto.takControl)
                if proto.HasField("takControl")
                else None
            ),
            context=MessageContext(origin_format=1),
        )

    def encode(self, message: TakEnvelope, *, frame: bool = True) -> bytes:
        proto = ProtoTakMessage()

        if message.control is not None:
            proto.takControl.CopyFrom(_encode_control(message.control))

        if message.event is not None:
            proto.cotEvent.CopyFrom(_encode_event(message.event))

        raw = proto.SerializeToString()

        return _frame(raw) if frame else raw


def _frame(raw: bytes) -> bytes:
    return bytes(FRAME_PREFIX + raw)


def _unframe(data: bytes) -> bytes:
    return data.removeprefix(FRAME_PREFIX)


def _dt_to_ms(value: datetime) -> int:
    return int(value.astimezone(UTC).timestamp() * 1000)


def _ms_to_dt(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def _none_if_empty(value: str) -> str | None:
    return value or None


def _decode_control(proto: ProtoTakControl) -> TakControl:
    return TakControl(
        min_proto_version=proto.minProtoVersion or None,
        max_proto_version=proto.maxProtoVersion or None,
        contact_uid=_none_if_empty(proto.contactUid),
        extension_ids=list(proto.extensionIds),
    )


def _encode_control(control: TakControl) -> ProtoTakControl:
    proto = ProtoTakControl()

    if control.min_proto_version is not None:
        proto.minProtoVersion = control.min_proto_version
    if control.max_proto_version is not None:
        proto.maxProtoVersion = control.max_proto_version
    if control.contact_uid is not None:
        proto.contactUid = control.contact_uid
    proto.extensionIds.extend(control.extension_ids)

    return proto


def _decode_event(proto: ProtoCotEvent) -> CotEvent:
    if not proto.uid:
        raise DecodeError("Missing required field: uid", field="uid")
    if not proto.type:
        raise DecodeError("Missing required field: type", field="type")
    if not proto.how:
        raise DecodeError("Missing required field: how", field="how")

    # TODO: Comment
    if proto.sendTime == 0:
        raise DecodeError("Missing required field: send", field="send")
    if proto.startTime == 0:
        raise DecodeError("Missing required field: start", field="start")
    if proto.staleTime == 0:
        raise DecodeError("Missing required field: stale", field="stale")

    # "you cannot determine whether the default (zero) value was set or parsed from the wire or not provided at all"
    #   - https://protobuf.dev/programming-guides/proto3/
    lat = proto.lat
    lon = proto.lon
    hae = proto.hae
    ce = proto.ce
    le = proto.le

    return CotEvent(
        uid=proto.uid,
        type=proto.type,
        how=proto.how,
        send_time=_ms_to_dt(proto.sendTime),
        start_time=_ms_to_dt(proto.startTime),
        stale_time=_ms_to_dt(proto.staleTime),
        point=Point(lat=lat, lon=lon, hae=hae, ce=ce, le=le),
        detail=_decode_detail(proto.detail) if proto.HasField("detail") else None,
        access=_none_if_empty(proto.access),
        caveat=_none_if_empty(proto.caveat),
        releasable_to=_none_if_empty(proto.releasableTo),
        qos=_none_if_empty(proto.qos),
        opex=_none_if_empty(proto.opex),
    )


def _encode_event(event: CotEvent) -> ProtoCotEvent:
    proto = ProtoCotEvent(
        type=event.type,
        uid=event.uid,
        sendTime=_dt_to_ms(event.send_time),
        startTime=_dt_to_ms(event.start_time),
        staleTime=_dt_to_ms(event.stale_time),
        how=event.how,
    )

    if event.point.lat is not None:
        proto.lat = event.point.lat
    if event.point.lon is not None:
        proto.lon = event.point.lon
    if event.point.hae is not None:
        proto.hae = event.point.hae
    if event.point.ce is not None:
        proto.ce = event.point.ce
    if event.point.le is not None:
        proto.le = event.point.le
    if event.access is not None:
        proto.access = event.access

    if event.caveat is not None:
        proto.caveat = event.caveat
    if event.releasable_to is not None:
        proto.releasableTo = event.releasable_to
    if event.qos is not None:
        proto.qos = event.qos
    if event.opex is not None:
        proto.opex = event.opex
    if event.detail is not None:
        proto.detail.CopyFrom(_encode_detail(event.detail))

    return proto


_KNOWN_TAGS = {"contact", "__group", "precisionlocation", "status", "takv", "track"}


def _parse_xml_detail(xml_detail: str) -> dict[str, ET.Element]:
    wrapped = f'<?xml version="1.0" encoding="UTF-8"?><detail>{xml_detail}</detail>'
    try:
        root = ET.fromstring(wrapped)
    except ET.ParseError:
        return {}

    result: dict[str, ET.Element] = {}
    for child in root:
        tag = child.tag
        if tag in _KNOWN_TAGS:
            result[tag] = child
    return result


def _decode_detail(proto: ProtoDetail) -> CotDetail:
    detail = CotDetail(
        opaque_xml=_none_if_empty(proto.xmlDetail),
        extension_details=[
            ExtensionDetail(extension_id=item.extensionId, data=item.data)
            for item in proto.extensionDetails
        ],
    )

    xml_known = _parse_xml_detail(proto.xmlDetail) if proto.xmlDetail else {}

    elem = xml_known.get("contact")
    if elem is not None:
        detail.contact = Contact(
            endpoint=elem.get("endpoint") or None,
            callsign=elem.get("callsign") or None,
        )
        if proto.HasField("contact"):
            logger.warning("xmlDetail <contact> overrides typed contact field")
    elif proto.HasField("contact"):
        detail.contact = Contact(
            endpoint=_none_if_empty(proto.contact.endpoint),
            callsign=_none_if_empty(proto.contact.callsign),
        )

    elem = xml_known.get("__group")
    if elem is not None:
        detail.group = Group(
            name=elem.get("name") or None,
            role=elem.get("role") or None,
        )
        if proto.HasField("group"):
            logger.warning("xmlDetail <__group> overrides typed group field")
    elif proto.HasField("group"):
        detail.group = Group(
            name=_none_if_empty(proto.group.name),
            role=_none_if_empty(proto.group.role),
        )

    elem = xml_known.get("precisionlocation")
    if elem is not None:
        detail.precision_location = PrecisionLocation(
            geopointsrc=elem.get("geopointsrc") or None,
            altsrc=elem.get("altsrc") or None,
        )
        if proto.HasField("precisionLocation"):
            logger.warning(
                "xmlDetail <precisionlocation> overrides typed precisionLocation field"
            )
    elif proto.HasField("precisionLocation"):
        detail.precision_location = PrecisionLocation(
            geopointsrc=_none_if_empty(proto.precisionLocation.geopointsrc),
            altsrc=_none_if_empty(proto.precisionLocation.altsrc),
        )

    elem = xml_known.get("status")
    if elem is not None:
        battery_str = elem.get("battery")
        detail.status = Status(
            battery=int(battery_str) if battery_str else None,
        )
        if proto.HasField("status"):
            logger.warning("xmlDetail <status> overrides typed status field")
    elif proto.HasField("status"):
        detail.status = Status(
            battery=proto.status.battery if proto.status.battery != 0 else None,
        )

    elem = xml_known.get("takv")
    if elem is not None:
        detail.takv = TakVersion(
            device=elem.get("device") or None,
            platform=elem.get("platform") or None,
            os=elem.get("os") or None,
            version=elem.get("version") or None,
        )
        if proto.HasField("takv"):
            logger.warning("xmlDetail <takv> overrides typed takv field")
    elif proto.HasField("takv"):
        detail.takv = TakVersion(
            device=_none_if_empty(proto.takv.device),
            platform=_none_if_empty(proto.takv.platform),
            os=_none_if_empty(proto.takv.os),
            version=_none_if_empty(proto.takv.version),
        )

    elem = xml_known.get("track")
    if elem is not None:
        speed_str = elem.get("speed")
        course_str = elem.get("course")
        detail.track = Track(
            speed=float(speed_str) if speed_str else None,
            course=float(course_str) if course_str else None,
        )
        if proto.HasField("track"):
            logger.warning("xmlDetail <track> overrides typed track field")
    elif proto.HasField("track"):
        detail.track = Track(
            speed=proto.track.speed,
            course=proto.track.course,
        )

    return detail


def _encode_detail(detail: CotDetail) -> ProtoDetail:
    proto = ProtoDetail()

    if detail.opaque_xml:
        proto.xmlDetail = detail.opaque_xml

    if detail.contact is not None:
        proto.contact.CopyFrom(
            ProtoContact(
                endpoint=detail.contact.endpoint or "",
                callsign=detail.contact.callsign or "",
            )
        )

    if detail.group is not None:
        proto.group.CopyFrom(
            ProtoGroup(
                name=detail.group.name or "",
                role=detail.group.role or "",
            )
        )

    if detail.precision_location is not None:
        proto.precisionLocation.CopyFrom(
            ProtoPrecisionLocation(
                geopointsrc=detail.precision_location.geopointsrc or "",
                altsrc=detail.precision_location.altsrc or "",
            )
        )

    if detail.status is not None and detail.status.battery is not None:
        proto.status.CopyFrom(ProtoStatus(battery=detail.status.battery))

    if detail.takv is not None:
        proto.takv.CopyFrom(
            ProtoTakv(
                device=detail.takv.device or "",
                platform=detail.takv.platform or "",
                os=detail.takv.os or "",
                version=detail.takv.version or "",
            )
        )

    if detail.track is not None:
        proto.track.CopyFrom(
            ProtoTrack(
                speed=detail.track.speed or 0.0,
                course=detail.track.course or 0.0,
            )
        )

    for item in detail.extension_details:
        ext = proto.extensionDetails.add()
        ext.extensionId = item.extension_id
        ext.data = item.data

    return proto
