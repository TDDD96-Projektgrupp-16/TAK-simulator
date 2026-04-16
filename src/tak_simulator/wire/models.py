from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class MessageContext:
    """Metadata discovered during decode or chosen before encode."""

    origin_format: int | None = None


@dataclass(slots=True)
class TakControl:
    """Protocol-level control data carried by TAK protobuf v1."""

    min_proto_version: int | None = None
    max_proto_version: int | None = None
    contact_uid: str | None = None
    extension_ids: list[int] = field(default_factory=list)


@dataclass(slots=True)
class Contact:
    endpoint: str | None = None
    callsign: str | None = None


@dataclass(slots=True)
class Group:
    name: str | None = None
    role: str | None = None


@dataclass(slots=True)
class PrecisionLocation:
    geopointsrc: str | None = None
    altsrc: str | None = None


@dataclass(slots=True)
class Status:
    battery: int | None = None


@dataclass(slots=True)
class TakVersion:
    device: str | None = None
    platform: str | None = None
    os: str | None = None
    version: str | None = None


@dataclass(slots=True)
class Track:
    speed: float | None = None
    course: float | None = None


@dataclass(slots=True)
class Point:
    lat: float
    lon: float
    hae: float | None = None
    ce: float | None = None
    le: float | None = None


@dataclass(slots=True)
class ExtensionDetail:
    """Extension-encoded detail payload used by protobuf v1."""

    extension_id: int
    data: bytes


@dataclass(slots=True)
class CotDetail:
    """Canonical detail model with room for typed and opaque content."""

    contact: Contact | None = None
    group: Group | None = None
    precision_location: PrecisionLocation | None = None
    status: Status | None = None
    takv: TakVersion | None = None
    track: Track | None = None
    opaque_xml: str | None = None
    extension_details: list[ExtensionDetail] = field(default_factory=list)


@dataclass(slots=True)
class CotEvent:
    """Wire-format-neutral representation of a CoT event."""

    uid: str
    type: str
    how: str
    send_time: datetime
    start_time: datetime
    stale_time: datetime
    point: Point
    detail: CotDetail | None = None
    access: str | None = None
    caveat: str | None = None
    releasable_to: str | None = None
    qos: str | None = None
    opex: str | None = None


@dataclass(slots=True)
class TakEnvelope:
    """Top-level TAK message abstraction.

    v0 XML typically carries only the CoT event.
    v1 protobuf may also carry protocol control information.
    """

    event: CotEvent | None = None
    control: TakControl | None = None
    context: MessageContext = field(default_factory=MessageContext)
