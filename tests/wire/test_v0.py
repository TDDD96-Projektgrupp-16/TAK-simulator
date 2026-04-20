from datetime import UTC, datetime, timedelta

from tak_simulator.wire import (
    Contact,
    CotDetail,
    CotEvent,
    Group,
    MessageContext,
    Point,
    PrecisionLocation,
    Status,
    TakEnvelope,
    TakVersion,
    Track,
)
from tak_simulator.wire.v0 import FRAME_PREFIX, V0Codec

SEND_TIME = datetime(2026, 4, 15, 11, 50, 35, tzinfo=UTC)
START_TIME = SEND_TIME + timedelta(seconds=5)
STALE_TIME = SEND_TIME + timedelta(seconds=75)


def _build_envelope(*, access: str | None = "U") -> TakEnvelope:
    return TakEnvelope(
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
            ),
            access=access,
            caveat="NONE",
            releasable_to="USA",
            qos="0",
            opex="0",
        ),
    )


class TestV0Codec:
    def test_decode_framed_message_with_detail(self):
        envelope = _build_envelope()
        data = V0Codec().encode(envelope)

        message = V0Codec().decode(data)

        assert message.context == MessageContext(origin_format=0)
        assert message.event is not None
        assert message.event.uid == "TEST-1234567890"
        assert message.event.type == "a-f-G-U-C-I"
        assert message.event.point.lat == 58.3980771
        assert message.event.point.lon == 15.5770142
        assert message.event.detail is not None
        assert message.event.detail.contact is not None
        assert message.event.detail.contact.callsign == "DRAKO"
        assert message.event.detail.group is not None
        assert message.event.detail.group.name == "Cyan"
        assert message.event.detail.track is not None
        assert message.event.detail.track.speed == 12.5

    def test_decode_unframed_message(self):
        envelope = _build_envelope()
        data = V0Codec().encode(envelope, frame=False)

        message = V0Codec().decode(data, unframe=True)

        assert message.event is not None
        assert message.event.uid == "TEST-1234567890"

    def test_decode_empty_message_returns_empty_envelope(self):
        message = V0Codec().decode(b"", unframe=False)

        assert message == TakEnvelope(
            event=None,
            context=MessageContext(origin_format=0),
        )

    def test_decode_unknown_point_values_as_none(self):
        envelope = _build_envelope()
        envelope.event.point.hae = None
        envelope.event.point.ce = None
        envelope.event.point.le = None

        data = V0Codec().encode(envelope, frame=False)
        message = V0Codec().decode(data, unframe=False)

        assert message.event is not None
        assert message.event.point.hae is None
        assert message.event.point.ce is None
        assert message.event.point.le is None

    def test_encode_produces_expected_xml_format(self):
        envelope = _build_envelope()
        data = V0Codec().encode(envelope, frame=True)

        assert data.startswith(FRAME_PREFIX)
        xml = data.decode()
        assert "<?xml version='1.0'" in xml
        assert "<event" in xml
        assert "version='2.0'" in xml

    def test_encode_with_minimal_event(self):
        envelope = TakEnvelope(
            event=CotEvent(
                uid="minimal",
                type="a-f-G",
                how="h-e",
                send_time=SEND_TIME,
                start_time=START_TIME,
                stale_time=STALE_TIME,
                point=Point(lat=0.0, lon=0.0),
            ),
        )

        data = V0Codec().encode(envelope, frame=False)

        assert b"<event" in data
        assert b"uid='minimal'" in data
        assert b"type='a-f-G'" in data

    def test_round_trip_preserves_event(self):
        original = _build_envelope()

        encoded = V0Codec().encode(original)
        decoded = V0Codec().decode(encoded)

        assert encoded.startswith(FRAME_PREFIX)
        assert decoded.event == original.event
        assert decoded.context == MessageContext(origin_format=0)

    def test_decode_extracts_contact_from_detail(self):
        xml = b"""<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<event version='2.0' uid='test-uid' type='a-u-G' time='2026-04-15T11:50:35.000Z' start='2026-04-15T11:50:40.000Z' stale='2026-04-15T11:51:50.000Z' how='h-e'>
<point lat='38.856650' lon='-77.063642' hae='100.0' ce='5.0' le='10.0'/>
<detail><contact callsign='TEST-CALLSIGN' endpoint='192.0.2.1:4242:tcp'/></detail>
</event>"""

        message = V0Codec().decode(xml)

        assert message.event is not None
        assert message.event.detail is not None
        assert message.event.detail.contact is not None
        assert message.event.detail.contact.callsign == "TEST-CALLSIGN"
        assert message.event.detail.contact.endpoint == "192.0.2.1:4242:tcp"
