from datetime import UTC, datetime
from xml.etree import ElementTree as ET
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
    Point,
    MessageContext,
)

type Attrs = list[tuple[str, str | None]]

FRAME_PREFIX = "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>\n".encode()
UNKNOWN_NUMERIC_VALUE = 999999.0  # TODO: Refactor


class V0Codec:
    def decode(self, data: bytes, *, unframe: bool = True) -> TakEnvelope:
        raw = _unframe(data) if unframe else data

        if not raw:
            return TakEnvelope(event=None, context=MessageContext(origin_format=0))

        root = ET.fromstring(raw)

        if root.tag != "event":
            return TakEnvelope(event=None, context=MessageContext(origin_format=0))

        event = _decode_event(root)
        return TakEnvelope(event=event, context=MessageContext(origin_format=0))

    def encode(self, message: TakEnvelope, *, frame: bool = True) -> bytes:
        event = _encode_event(message.event)

        raw = event.encode()

        return _frame(raw) if frame else raw


def _frame(raw: bytes) -> bytes:
    return bytes(FRAME_PREFIX + raw)


def _unframe(data: bytes) -> bytes:
    if data.startswith(b"<?xml"):
        end = data.find(b"?>")
        if end != -1:
            return data[end + 2 :].lstrip()
    if data.startswith(FRAME_PREFIX):
        return data[len(FRAME_PREFIX) :]
    return data


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


def _parse_cot_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)
    except ValueError:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def _none_if_unknown(value: float | None) -> float | None:
    return None if value == UNKNOWN_NUMERIC_VALUE else value


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _decode_event(root: ET.Element) -> CotEvent:
    point_elem = root.find("point")
    detail_elem = root.find("detail")

    point = Point(
        # TODO: Protocol requires lat/lon - currently defaults to 0.0 if missing
        lat=float(point_elem.get("lat", 0)) if point_elem is not None else 0.0,
        lon=float(point_elem.get("lon", 0)) if point_elem is not None else 0.0,
        hae=_none_if_unknown(_parse_float(point_elem.get("hae")))
        if point_elem is not None
        else None,
        ce=_none_if_unknown(_parse_float(point_elem.get("ce")))
        if point_elem is not None
        else None,
        le=_none_if_unknown(_parse_float(point_elem.get("le")))
        if point_elem is not None
        else None,
    )

    detail = _decode_detail(detail_elem) if detail_elem is not None else None

    # TODO: Protocol requires uid, type, how - currently defaults to empty string/"Undefined" if missing
    # TODO: Protocol requires time/start/stale - currently defaults to current time if missing
    return CotEvent(
        uid=root.get("uid", ""),
        type=root.get("type", ""),
        how=root.get("how", ""),
        send_time=_parse_cot_timestamp(root.get("time")) or datetime.now(tz=UTC),
        start_time=_parse_cot_timestamp(root.get("start")) or datetime.now(tz=UTC),
        stale_time=_parse_cot_timestamp(root.get("stale")) or datetime.now(tz=UTC),
        point=point,
        detail=detail,
        access=root.get("access") or "Undefined",
        caveat=root.get("caveat") or None,
        releasable_to=root.get("releasableTo") or None,
        qos=root.get("qos") or None,
        opex=root.get("opex") or None,
    )


def _decode_detail(elem: ET.Element | None) -> CotDetail | None:
    if elem is None:
        return None

    detail = CotDetail()

    for child in elem:
        if child.tag == "contact":
            detail.contact = Contact(
                endpoint=child.get("endpoint") or None,
                callsign=child.get("callsign") or None,
            )
        elif child.tag == "__group":
            detail.group = Group(
                name=child.get("name") or None,
                role=child.get("role") or None,
            )
        elif child.tag == "precisionlocation":
            detail.precision_location = PrecisionLocation(
                geopointsrc=child.get("geopointsrc") or None,
                altsrc=child.get("altsrc") or None,
            )
        elif child.tag == "status":
            battery_str = child.get("battery")
            detail.status = Status(
                battery=int(battery_str) if battery_str else None,
            )
        elif child.tag == "takv":
            detail.takv = TakVersion(
                device=child.get("device") or None,
                platform=child.get("platform") or None,
                os=child.get("os") or None,
                version=child.get("version") or None,
            )
        elif child.tag == "track":
            detail.track = Track(
                speed=_parse_float(child.get("speed")),
                course=_parse_float(child.get("course")),
            )

    return detail
