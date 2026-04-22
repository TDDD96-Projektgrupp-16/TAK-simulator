from datetime import UTC, datetime, timedelta

from tak_simulator.wire import (
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
from tak_simulator.wire.v1 import FRAME_PREFIX, V1Codec
from tak_simulator.proto.contact_pb2 import Contact as ProtoContact
from tak_simulator.proto.cotevent_pb2 import CotEvent as ProtoCotEvent
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

SEND_TIME = datetime(2026, 4, 15, 11, 50, 35, tzinfo=UTC)
START_TIME = SEND_TIME + timedelta(seconds=5)
STALE_TIME = SEND_TIME + timedelta(seconds=75)


def _dt_to_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _build_envelope(*, access: str | None = "U") -> TakEnvelope:
    return TakEnvelope(
        control=TakControl(
            min_proto_version=1,
            max_proto_version=3,
            contact_uid="TEST-1234567890",
            extension_ids=[7, 9],
        ),
        event=CotEvent(
            uid="TEST-1234567890",
            type="a-f-G-U-C-I",
            how="h-e",
            send_time=SEND_TIME,
            start_time=START_TIME,
            stale_time=STALE_TIME,
            point=Point(
                lat=58.3980771,
                lon=15.5770142,
                hae=112.5,
                ce=4.5,
                le=7.25,
            ),
            detail=CotDetail(
                contact=Contact(
                    endpoint="192.0.2.10:4242:tcp",
                    callsign="DRAKO",
                ),
                group=Group(name="Cyan", role="Team Member"),
                precision_location=PrecisionLocation(
                    geopointsrc="GPS",
                    altsrc="GPS",
                ),
                status=Status(battery=87),
                takv=TakVersion(
                    device="SAMSUNG SM-S901B",
                    platform="ATAK-CIV",
                    os="36",
                    version="5.6.0.12",
                ),
                track=Track(speed=12.5, course=270.0),
                opaque_xml="<remarks>hello</remarks>",
                extension_details=[
                    ExtensionDetail(extension_id=42, data=b"\x01\x02\x03"),
                ],
            ),
            access=access,
            caveat="NONE",
            releasable_to="USA",
            qos="0",
            opex="0",
        ),
    )


def _build_proto_message(*, access: str = "U") -> ProtoTakMessage:
    detail = ProtoDetail(
        xmlDetail="<remarks>hello</remarks>",
        contact=ProtoContact(
            endpoint="192.0.2.10:4242:tcp",
            callsign="DRAKO",
        ),
        group=ProtoGroup(
            name="Cyan",
            role="Team Member",
        ),
        precisionLocation=ProtoPrecisionLocation(
            geopointsrc="GPS",
            altsrc="GPS",
        ),
        status=ProtoStatus(battery=87),
        takv=ProtoTakv(
            device="SAMSUNG SM-S901B",
            platform="ATAK-CIV",
            os="36",
            version="5.6.0.12",
        ),
        track=ProtoTrack(speed=12.5, course=270.0),
    )
    ext = detail.extensionDetails.add()
    ext.extensionId = 42
    ext.data = b"\x01\x02\x03"

    return ProtoTakMessage(
        takControl=ProtoTakControl(
            minProtoVersion=1,
            maxProtoVersion=3,
            contactUid="TEST-1234567890",
            extensionIds=[7, 9],
        ),
        cotEvent=ProtoCotEvent(
            uid="TEST-1234567890",
            type="a-f-G-U-C-I",
            how="h-e",
            sendTime=_dt_to_ms(SEND_TIME),
            startTime=_dt_to_ms(START_TIME),
            staleTime=_dt_to_ms(STALE_TIME),
            lat=58.3980771,
            lon=15.5770142,
            hae=112.5,
            ce=4.5,
            le=7.25,
            access=access,
            caveat="NONE",
            releasableTo="USA",
            qos="0",
            opex="0",
            detail=detail,
        ),
    )


class TestV1Codec:
    def test_decode_framed_message_with_control_and_detail(self):
        data = FRAME_PREFIX + _build_proto_message().SerializeToString()

        message = V1Codec().decode(data)

        assert message == TakEnvelope(
            control=TakControl(
                min_proto_version=1,
                max_proto_version=3,
                contact_uid="TEST-1234567890",
                extension_ids=[7, 9],
            ),
            event=_build_envelope().event,
            context=MessageContext(origin_format=1),
        )

    def test_decode_empty_message_returns_empty_envelope(self):
        message = V1Codec().decode(b"", unframe=False)

        assert message == TakEnvelope(
            event=None,
            control=None,
            context=MessageContext(origin_format=1),
        )

    def test_decode_unknown_point_values_as_none(self):
        proto = ProtoTakMessage(
            cotEvent=ProtoCotEvent(
                uid="TEST-1234567890",
                type="a-f-G-U-C-I",
                how="h-e",
                sendTime=_dt_to_ms(SEND_TIME),
                startTime=_dt_to_ms(START_TIME),
                staleTime=_dt_to_ms(STALE_TIME),
                lat=58.3980771,
                lon=15.5770142,
                hae=999999.0,
                ce=999999.0,
                le=999999.0,
            )
        )

        message = V1Codec().decode(proto.SerializeToString(), unframe=False)

        assert message.event is not None
        assert message.event.point == Point(
            lat=58.3980771,
            lon=15.5770142,
            hae=999999.0,
            ce=999999.0,
            le=999999.0,
        )
        assert message.control is None

    def test_encode_serializes_expected_proto_fields_without_framing(self):
        data = V1Codec().encode(_build_envelope(), frame=False)

        proto = ProtoTakMessage()
        proto.ParseFromString(data)

        assert proto.HasField("takControl")
        assert proto.HasField("cotEvent")
        assert proto.takControl.contactUid == "TEST-1234567890"
        assert list(proto.takControl.extensionIds) == [7, 9]
        assert proto.cotEvent.uid == "TEST-1234567890"
        assert proto.cotEvent.access == "U"
        assert proto.cotEvent.detail.contact.callsign == "DRAKO"
        assert proto.cotEvent.detail.track.speed == 12.5
        assert proto.cotEvent.detail.track.course == 270.0
        assert proto.cotEvent.detail.xmlDetail == "<remarks>hello</remarks>"
        assert len(proto.cotEvent.detail.extensionDetails) == 1
        assert proto.cotEvent.detail.extensionDetails[0].extensionId == 42
        assert proto.cotEvent.detail.extensionDetails[0].data == b"\x01\x02\x03"

    def test_encode_omits_none_access(self):
        envelope = _build_envelope(access=None)
        envelope.control = None
        assert envelope.event is not None
        envelope.event.point = Point(lat=58.3980771, lon=15.5770142)

        data = V1Codec().encode(envelope, frame=False)

        proto = ProtoTakMessage()
        proto.ParseFromString(data)

        assert not proto.HasField("takControl")
        assert proto.cotEvent.access == ""

    def test_decode_missing_access_returns_none(self):
        proto = ProtoTakMessage(
            cotEvent=ProtoCotEvent(
                uid="TEST-1234567890",
                type="a-f-G-U-C-I",
                how="h-e",
                sendTime=_dt_to_ms(SEND_TIME),
                startTime=_dt_to_ms(START_TIME),
                staleTime=_dt_to_ms(STALE_TIME),
                lat=58.3980771,
                lon=15.5770142,
                hae=112.5,
                ce=4.5,
                le=7.25,
            )
        )

        message = V1Codec().decode(proto.SerializeToString(), unframe=False)

        assert message.event is not None
        assert message.event.access is None

    def test_round_trip_preserves_event_and_control(self):
        original = _build_envelope()

        encoded = V1Codec().encode(original)
        decoded = V1Codec().decode(encoded)

        assert encoded.startswith(FRAME_PREFIX)
        assert decoded.event == original.event
        assert decoded.control == original.control
        assert decoded.context == MessageContext(origin_format=1)
