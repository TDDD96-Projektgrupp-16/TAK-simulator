from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    from tak_simulator.time_keeper import TimeKeeper

UNKNOWN_NUMERIC_VALUE = 999999.0

_DEFAULT_SIMULATION_START_TIME: datetime | None = None


# ---------------------------------------------------
# Helpers for XML encoding and CoT event construction
# ---------------------------------------------------


def _escape_attr(value: str) -> str:
    return escape(value, {'"': "&quot;"})


def _format_float(value: float) -> str:
    text = f"{value:.15f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _format_cot_timestamp(dt: datetime) -> str:
    dt_utc = dt.astimezone(UTC)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt_utc.microsecond // 1000:03d}Z"


def _resolve_now(
    now: datetime | None,
    time_keeper: TimeKeeper | None,
    simulation_start_time: datetime | None,
) -> datetime:
    global _DEFAULT_SIMULATION_START_TIME

    if now is not None:
        return now

    if time_keeper is None:
        return datetime.now(UTC)

    base_time = simulation_start_time
    if base_time is None:
        if _DEFAULT_SIMULATION_START_TIME is None:
            _DEFAULT_SIMULATION_START_TIME = datetime.now(UTC)
        base_time = _DEFAULT_SIMULATION_START_TIME

    return base_time + timedelta(seconds=time_keeper.get_time())


def _attr(name: str, value: str | None) -> str:
    if value is None:
        return ""
    return f' {name}="{_escape_attr(value)}"'


def _self_closing_tag(name: str, attrs: list[tuple[str, str | None]]) -> str:
    return f"<{name}{''.join(_attr(k, v) for k, v in attrs)}/>"


def _open_tag(name: str, attrs: list[tuple[str, str | None]]) -> str:
    return f"<{name}{''.join(_attr(k, v) for k, v in attrs)}>"


def _with_tcp_xml_framing(xml_body: str) -> str:
    """Wrap a CoT XML body using the traditional TAK TCP XML framing.

    TAK protocol version 0 uses an XML declaration, followed by one newline,
    followed by the full CoT XML body.
    """
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_body}'


# ---------------------------------------------------------
# Validation models for scenario data and CoT event details
# ---------------------------------------------------------


class GroupModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    role: str


class TakvModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device: str
    platform: str
    os: str
    version: str


class ContactModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint: str | None = None
    callsign: str


class PrecisionLocationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    geopointsrc: str = "GPS"
    altsrc: str = "GPS"


class StatusModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    battery: int | None = Field(default=None, ge=0, le=100)


class TrackModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    speed: float | None = None
    course: float | None = None


class ChatGroupModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    uid0: str
    uid1: str | None = None


class ChatDetailModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    chatroom: str
    sender_callsign: str
    group_owner: bool = False
    message_id: str
    parent: str | None = None
    chat_group: ChatGroupModel | None = None
    remarks: str | None = None

    @model_validator(mode="after")
    def validate_chat_payload(self) -> "ChatDetailModel":
        if self.chat_group is None and self.remarks is None:
            raise ValueError("chat detail must include chat_group or remarks")
        return self


class CotPointModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    hae: float = UNKNOWN_NUMERIC_VALUE
    ce: float = UNKNOWN_NUMERIC_VALUE
    le: float = UNKNOWN_NUMERIC_VALUE


class CotDetailModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    xml_detail: str | None = None
    contact: ContactModel | None = None
    group: GroupModel | None = None
    precision_location: PrecisionLocationModel | None = None
    status: StatusModel | None = None
    takv: TakvModel | None = None
    track: TrackModel | None = None


class CotEventModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type_: str
    uid: str
    send_time: datetime
    start_time: datetime
    stale_time: datetime
    how: str
    point: CotPointModel
    detail: CotDetailModel | None = None
    access: str | None = None
    caveat: str | None = None
    releasable_to: str | None = None
    qos: str | None = None
    opex: str | None = None

    @field_validator("send_time", "start_time", "stale_time")
    @classmethod
    def ensure_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        return value


# ---------------------------------------------------
# Encoding and building CoT events from scenario data
# ---------------------------------------------------


def encode_contact(contact: ContactModel) -> str:
    return _self_closing_tag(
        "contact",
        [
            ("endpoint", contact.endpoint),
            ("callsign", contact.callsign),
        ],
    )


def encode_group(group: GroupModel) -> str:
    return _self_closing_tag(
        "__group",
        [
            ("name", group.name),
            ("role", group.role),
        ],
    )


def encode_precision_location(precision_location: PrecisionLocationModel) -> str:
    return _self_closing_tag(
        "precisionlocation",
        [
            ("geopointsrc", precision_location.geopointsrc),
            ("altsrc", precision_location.altsrc),
        ],
    )


def encode_status(status: StatusModel) -> str:
    return _self_closing_tag(
        "status",
        [
            ("battery", str(status.battery) if status.battery is not None else None),
        ],
    )


def encode_takv(takv: TakvModel) -> str:
    return _self_closing_tag(
        "takv",
        [
            ("device", takv.device),
            ("platform", takv.platform),
            ("os", takv.os),
            ("version", takv.version),
        ],
    )


def encode_track(track: TrackModel) -> str:
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


def encode_chat_group(chat_group: ChatGroupModel) -> str:
    return _self_closing_tag(
        "chatgrp",
        [
            ("id", chat_group.id),
            ("uid0", chat_group.uid0),
            ("uid1", chat_group.uid1),
        ],
    )


def encode_remarks(text: str) -> str:
    return f"<remarks>{escape(text)}</remarks>"


def encode_chat_detail(chat: ChatDetailModel) -> str:
    children: list[str] = []

    if chat.chat_group is not None:
        children.append(encode_chat_group(chat.chat_group))
    if chat.parent is not None:
        children.append(_self_closing_tag("parent", [("messageId", chat.parent)]))
    if chat.remarks is not None:
        children.append(encode_remarks(chat.remarks))

    return (
        _open_tag(
            "__chat",
            [
                ("id", chat.id),
                ("chatroom", chat.chatroom),
                ("senderCallsign", chat.sender_callsign),
                ("groupOwner", "true" if chat.group_owner else "false"),
                ("messageId", chat.message_id),
            ],
        )
        + "".join(children)
        + "</__chat>"
    )


def encode_detail(detail: CotDetailModel | None) -> str:
    if detail is None:
        return "<detail/>"

    children: list[str] = []

    if detail.xml_detail:
        children.append(detail.xml_detail)

    if detail.contact is not None:
        children.append(encode_contact(detail.contact))
    if detail.group is not None:
        children.append(encode_group(detail.group))
    if detail.precision_location is not None:
        children.append(encode_precision_location(detail.precision_location))
    if detail.status is not None:
        children.append(encode_status(detail.status))
    if detail.takv is not None:
        children.append(encode_takv(detail.takv))
    if detail.track is not None:
        children.append(encode_track(detail.track))

    if not children:
        return "<detail/>"

    return f"<detail>{''.join(children)}</detail>"


def encode_cot_event(event: CotEventModel) -> str:
    access_value = None if event.access in (None, "", "Undefined") else event.access

    event_attrs: list[tuple[str, str | None]] = [
        ("version", "2.0"),
        ("type", event.type_),
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

    detail_xml = encode_detail(event.detail)

    return _open_tag("event", event_attrs) + point_xml + detail_xml + "</event>"


def encode_cot_event_for_tcp(event: CotEventModel) -> str:
    """Encode a CoT event and add traditional TAK TCP XML framing."""
    return _with_tcp_xml_framing(encode_cot_event(event))


def encode_chat_message_for_tcp(
    *,
    uid: str,
    sender_callsign: str,
    chatroom: str,
    message_id: str,
    point: tuple[float, float],
    now: datetime | None = None,
    time_keeper: "TimeKeeper" | None = None,
    simulation_start_time: datetime | None = None,
    stale_seconds: int = 75,
    chat_group_id: str | None = None,
    chat_group_uid0: str | None = None,
    chat_group_uid1: str | None = None,
    parent_message_id: str | None = None,
    remarks: str | None = None,
    access: str | None = None,
    how: str = "h-g-i-g-o",
    cot_type: str = "b-t-f",
) -> str:
    """Return a TAK chat message encoded as TCP-framed CoT XML."""
    return _with_tcp_xml_framing(
        encode_chat_message(
            uid=uid,
            sender_callsign=sender_callsign,
            chatroom=chatroom,
            message_id=message_id,
            point=point,
            now=now,
            time_keeper=time_keeper,
            simulation_start_time=simulation_start_time,
            stale_seconds=stale_seconds,
            chat_group_id=chat_group_id,
            chat_group_uid0=chat_group_uid0,
            chat_group_uid1=chat_group_uid1,
            parent_message_id=parent_message_id,
            remarks=remarks,
            access=access,
            how=how,
            cot_type=cot_type,
        )
    )


def build_chat_cot_event(
    *,
    uid: str,
    sender_callsign: str,
    chatroom: str,
    message_id: str,
    point: tuple[float, float],
    now: datetime | None = None,
    time_keeper: TimeKeeper | None = None,
    simulation_start_time: datetime | None = None,
    stale_seconds: int = 75,
    chat_group_id: str | None = None,
    chat_group_uid0: str | None = None,
    chat_group_uid1: str | None = None,
    parent_message_id: str | None = None,
    remarks: str | None = None,
    access: str | None = None,
    how: str = "h-g-i-g-o",
    cot_type: str = "b-t-f",
) -> CotEventModel:
    resolved_now = _resolve_now(now, time_keeper, simulation_start_time)

    chat_group = None
    if chat_group_id is not None and chat_group_uid0 is not None:
        chat_group = ChatGroupModel(
            id=chat_group_id,
            uid0=chat_group_uid0,
            uid1=chat_group_uid1,
        )

    chat_detail = ChatDetailModel(
        id=uid,
        chatroom=chatroom,
        sender_callsign=sender_callsign,
        message_id=message_id,
        parent=parent_message_id,
        chat_group=chat_group,
        remarks=remarks,
    )

    lat, lon = point
    return CotEventModel(
        type_=cot_type,
        uid=uid,
        send_time=resolved_now,
        start_time=resolved_now,
        stale_time=resolved_now + timedelta(seconds=stale_seconds),
        how=how,
        point=CotPointModel(lat=lat, lon=lon),
        detail=CotDetailModel(xml_detail=encode_chat_detail(chat_detail)),
        access=access,
    )


def encode_chat_message(
    *,
    uid: str,
    sender_callsign: str,
    chatroom: str,
    message_id: str,
    point: tuple[float, float],
    now: datetime | None = None,
    time_keeper: TimeKeeper | None = None,
    simulation_start_time: datetime | None = None,
    stale_seconds: int = 75,
    chat_group_id: str | None = None,
    chat_group_uid0: str | None = None,
    chat_group_uid1: str | None = None,
    parent_message_id: str | None = None,
    remarks: str | None = None,
    access: str | None = None,
    how: str = "h-g-i-g-o",
    cot_type: str = "b-t-f",
) -> str:
    event = build_chat_cot_event(
        uid=uid,
        sender_callsign=sender_callsign,
        chatroom=chatroom,
        message_id=message_id,
        point=point,
        now=now,
        time_keeper=time_keeper,
        simulation_start_time=simulation_start_time,
        stale_seconds=stale_seconds,
        chat_group_id=chat_group_id,
        chat_group_uid0=chat_group_uid0,
        chat_group_uid1=chat_group_uid1,
        parent_message_id=parent_message_id,
        remarks=remarks,
        access=access,
        how=how,
        cot_type=cot_type,
    )
    return encode_cot_event(event)
