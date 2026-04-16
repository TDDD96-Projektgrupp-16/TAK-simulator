from datetime import UTC, datetime
from xml.sax.saxutils import escape

from .models import (
    TakEnvelope,
    CotEvent,
    Contact,
    PrecisionLocation,
    Status,
    TakVersion,
    Track,
    Group,
    CotDetail,
)

type Attrs = list[tuple[str, str | None]]

FRAME_PREFIX = "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>\n".encode()
UNKNOWN_NUMERIC_VALUE = 999999.0  # TODO: Refactor


class V0Codec:
    def decode(self, data: bytes, *, unframe: bool = True) -> TakEnvelope:
        raise NotImplementedError()

    def encode(self, message: TakEnvelope, *, frame: bool = True) -> bytes:
        event = _encode_event(message.event)

        raw = event.encode()

        return _frame(raw) if frame else raw


def _frame(raw: bytes) -> bytes:
    return bytes(FRAME_PREFIX + raw)


def _unframe(data: bytes) -> bytes:
    raise NotImplementedError()


def _escape_attr(value: str) -> str:
    return escape(value, {"'": "&apos;"})


def _format_float(value: float | None) -> str:
    if value is None:
        value = UNKNOWN_NUMERIC_VALUE

    text = f"{value:.15f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _format_cot_timestamp(dt: datetime) -> str:
    dt_utc = dt.astimezone(UTC)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt_utc.microsecond // 1000:03d}Z"


def _attr(name: str, value: str | None) -> str:
    if value is None:
        return ""
    return f" {name}='{_escape_attr(value)}'"


def _self_closing_tag(name: str, attrs: Attrs | None = None) -> str:
    if attrs is None:
        attrs = []
    return f"<{name}{''.join(_attr(k, v) for k, v in attrs)}/>"


def _paired_tag(name: str, content: str, attrs: Attrs | None = None) -> str:
    if attrs is None:
        attrs = []
    return f"<{name}{''.join(_attr(k, v) for k, v in attrs)}>{content}</{name}>"


def _encode_event(event: CotEvent | None) -> str:
    if event is None:
        return _self_closing_tag("event")

    access_value = (
        None if event.access in (None, "", "Undefined") else event.access
    )  # TODO

    event_attrs = [
        ("version", "2.0"),
        ("type", event.type),
        ("access", access_value),
        ("caveat", event.caveat),
        ("releasableTo", event.releasable_to),
        ("qos", event.qos),
        ("opex", event.opex),
        ("uid", event.uid),
        ("time", _format_cot_timestamp(event.send_time)),
        ("start", _format_cot_timestamp(event.start_time)),
        ("stale", _format_cot_timestamp(event.stale_time)),
        ("how", event.how),
    ]

    point_xml = _self_closing_tag(
        "point",
        [
            ("lat", _format_float(event.point.lat)),
            ("lon", _format_float(event.point.lon)),
            ("hae", _format_float(event.point.hae)),
            ("ce", _format_float(event.point.ce)),
            ("le", _format_float(event.point.le)),
        ],
    )

    detail_xml = (
        _encode_detail(event.detail) if event.detail else _self_closing_tag("detail")
    )

    return _paired_tag("event", point_xml + detail_xml, event_attrs)


def _encode_detail(detail: CotDetail | None) -> str:
    if detail is None:
        return _self_closing_tag("detail")

    children = []

    if detail.opaque_xml:
        children.append(detail.opaque_xml)

    if detail.contact is not None:
        children.append(_encode_contact(detail.contact))
    if detail.group is not None:
        children.append(_encode_group(detail.group))
    if detail.precision_location is not None:
        children.append(encode_precision_location(detail.precision_location))
    if detail.status is not None:
        children.append(_encode_status(detail.status))
    if detail.takv is not None:
        children.append(_encode_takv(detail.takv))
    if detail.track is not None:
        children.append(_encode_track(detail.track))

    if not children:
        return _self_closing_tag("detail")

    return _paired_tag("detail", "".join(children))


def _encode_contact(contact: Contact) -> str:
    return _self_closing_tag(
        "contact",
        [
            ("endpoint", contact.endpoint),
            ("callsign", contact.callsign),
        ],
    )


def _encode_group(group: Group) -> str:
    return _self_closing_tag(
        "__group",
        [
            ("name", group.name),
            ("role", group.role),
        ],
    )


def encode_precision_location(precision_location: PrecisionLocation) -> str:
    return _self_closing_tag(
        "precisionlocation",
        [
            ("geopointsrc", precision_location.geopointsrc),
            ("altsrc", precision_location.altsrc),
        ],
    )


def _encode_status(status: Status) -> str:
    return _self_closing_tag(
        "status",
        [
            ("battery", str(status.battery) if status.battery is not None else None),
        ],
    )


def _encode_takv(takv: TakVersion) -> str:
    return _self_closing_tag(
        "takv",
        [
            ("device", takv.device),
            ("platform", takv.platform),
            ("os", takv.os),
            ("version", takv.version),
        ],
    )


def _encode_track(track: Track) -> str:
    return _self_closing_tag(
        "track",
        [
            ("speed", _format_float(track.speed) if track.speed is not None else None),
            (
                "course",
                _format_float(track.course) if track.course is not None else None,
            ),
        ],
    )
