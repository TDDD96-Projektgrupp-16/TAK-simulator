from __future__ import annotations

from datetime import UTC, datetime

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

from tak_simulator.cot_event import (
    Contact,
    CotDetail,
    CotEvent,
    ExtensionDetail,
    MessageContext,
    Point,
    PrecisionLocation,
    ProtobufTakCodec,
    Status,
    TakControl,
    TakEnvelope,
    TakVersion,
    Track,
    WireFormat,
    Group,
)

UNKNOWN_NUMERIC_VALUE = 999999.0


def _dt_to_ms(value: datetime) -> int:
    return int(value.astimezone(UTC).timestamp() * 1000)


def _ms_to_dt(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def _none_if_empty(value: str) -> str | None:
    return value or None


def _maybe_unframe_v1(payload: bytes) -> bytes:
    # Placeholder: strip TAK v1 transport framing here if present.
    return payload


def _maybe_frame_v1(payload: bytes) -> bytes:
    # Placeholder: add TAK v1 transport framing here if needed.
    return payload


class ProtobufTakCodecImpl(ProtobufTakCodec):
    def can_decode(self, payload: bytes) -> bool:
        # Real implementation should inspect TAK v1 framing/header.
        return True

    def decode(self, payload: bytes) -> TakEnvelope:
        raw = _maybe_unframe_v1(payload)

        proto = ProtoTakMessage()
        proto.ParseFromString(raw)

        return TakEnvelope(
            event=_decode_event(proto.cotEvent) if proto.HasField("cotEvent") else None,
            control=_decode_control(proto.takControl)
            if proto.HasField("takControl")
            else None,
            context=MessageContext(
                wire_format=WireFormat.PROTOBUF_V1,
                protocol_version=1,
                transport_framing="tak_v1",
            ),
        )

    def encode(self, message: TakEnvelope) -> bytes:
        proto = ProtoTakMessage()

        if message.control is not None:
            proto.takControl.CopyFrom(_encode_control(message.control))

        if message.event is not None:
            proto.cotEvent.CopyFrom(_encode_event(message.event))

        return _maybe_frame_v1(proto.SerializeToString())


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
    return CotEvent(
        uid=proto.uid,
        type=proto.type,
        how=proto.how,
        send_time=_ms_to_dt(proto.sendTime),
        start_time=_ms_to_dt(proto.startTime),
        stale_time=_ms_to_dt(proto.staleTime),
        point=Point(
            lat=proto.lat,
            lon=proto.lon,
            hae=proto.hae,
            ce=proto.ce,
            le=proto.le,
        ),
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
        lat=event.point.lat,
        lon=event.point.lon,
        hae=event.point.hae if event.point.hae is not None else UNKNOWN_NUMERIC_VALUE,
        ce=event.point.ce if event.point.ce is not None else UNKNOWN_NUMERIC_VALUE,
        le=event.point.le if event.point.le is not None else UNKNOWN_NUMERIC_VALUE,
    )

    if event.access not in (None, "", "Undefined"):  # TODO
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


def _decode_detail(proto: ProtoDetail) -> CotDetail:
    detail = CotDetail(
        opaque_xml=_none_if_empty(proto.xmlDetail),
        extension_details=[
            ExtensionDetail(extension_id=item.extensionId, data=item.data)
            for item in proto.extensionDetails
        ],
    )

    if proto.HasField("contact"):
        detail.contact = Contact(
            endpoint=_none_if_empty(proto.contact.endpoint),
            callsign=_none_if_empty(proto.contact.callsign),
        )

    if proto.HasField("group"):
        detail.group = Group(
            name=_none_if_empty(proto.group.name),
            role=_none_if_empty(proto.group.role),
        )

    if proto.HasField("precisionLocation"):
        detail.precision_location = PrecisionLocation(
            geopointsrc=_none_if_empty(proto.precisionLocation.geopointsrc),
            altsrc=_none_if_empty(proto.precisionLocation.altsrc),
        )

    if proto.HasField("status"):
        detail.status = Status(
            battery=proto.status.battery if proto.status.battery != 0 else None,
        )

    if proto.HasField("takv"):
        detail.takv = TakVersion(
            device=_none_if_empty(proto.takv.device),
            platform=_none_if_empty(proto.takv.platform),
            os=_none_if_empty(proto.takv.os),
            version=_none_if_empty(proto.takv.version),
        )

    if proto.HasField("track"):
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
