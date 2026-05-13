import logging
import uuid
from datetime import UTC, datetime

from pydantic_xml import BaseXmlModel, attr, element

from tak_simulator import uid
from tak_simulator.scenario import EmulatorOptions

logger = logging.getLogger(__name__)


class ChatGroup(BaseXmlModel, tag="chatgrp"):
    id: str = attr()
    uid0: str = attr()
    uid1: str | None = attr(default=None)
    uid2: str | None = attr(default=None)


class Chat(BaseXmlModel, tag="__chat"):
    parent: str = attr()
    chatroom: str = attr()
    group_owner: bool = attr(name="groupOwner")
    id: str = attr()
    sender_callsign: str = attr(name="senderCallsign")
    message_id: str = attr(name="messageId")

    chatgrp: ChatGroup = element()


class Link(BaseXmlModel, tag="link"):
    uid: str = attr()
    type: str = attr()
    relation: str = attr()


class ServerDestination(BaseXmlModel, tag="__serverdestination"):
    destinations: str = attr()


class Remarks(BaseXmlModel, tag="remarks"):
    source: str = attr()
    source_id: str | None = attr(name="sourceID", default=None)
    to: str = attr()
    time: str = attr()

    text: str


class ChatDetail(BaseXmlModel, tag="detail"):
    chat: Chat = element(tag="__chat")
    link: Link = element()
    server_destination: ServerDestination | None = element(
        tag="__serverdestination", default=None
    )
    remarks: Remarks = element()


def build_chat_detail_for_direct_message(
    sender: EmulatorOptions,
    recipient_id: str,
    recipient_callsign: str,
    endpoint: str,
    message: str,
    *,
    time: datetime | None = None,
    message_id: str | None = None,
) -> ChatDetail:
    if time is None:
        time = datetime.now(UTC)

    if time.tzinfo is None or time.utcoffset() is None:
        time = time.replace(tzinfo=UTC)
    else:
        time = time.astimezone(UTC)
    time_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")

    if message_id is None:
        message_id = uuid.uuid4().hex

    # TODO: Derive this from elsewhere
    match sender.like.lower():
        case "atak":
            platform = "ATAK"
        case "wintak":
            platform = "WinTAK"
        case _:
            platform = "WinTAK"

    return ChatDetail(
        chat=Chat(
            parent="RootContactGroup",
            chatroom=recipient_callsign,
            group_owner=False,
            id=recipient_id,
            sender_callsign=sender.callsign,
            message_id=message_id,
            chatgrp=ChatGroup(
                id=recipient_id,
                uid0=sender.uid,
                uid1=recipient_id,
            ),
        ),
        link=Link(
            uid=sender.uid,
            type=sender.type,
            relation="p-p",
        ),
        server_destination=ServerDestination(destinations=f"{endpoint}:{sender.uid}"),
        remarks=Remarks(
            source=f"BAO.F.{platform}.{sender.uid}",
            source_id=sender.uid,
            to=recipient_id,
            time=time_str,
            text=message,
        ),
    )


def decode_chat_detail(detail: str) -> ChatDetail:
    detail = detail.strip()
    if not detail.startswith("<detail>"):
        detail = f"<detail>{detail}</detail>"

    return ChatDetail.from_xml(detail)


def encode_chat_detail(detail: ChatDetail) -> bytes:
    return detail.to_xml()[8:-9]
