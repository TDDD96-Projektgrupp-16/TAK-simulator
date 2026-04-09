"""Pytest tests for CoT XML encoding.

Run automated tests with:
    uv run pytest tests/test_xml_encode.py

Run manual chat encoding with:
    uv run python tests/test_xml_encode.py
"""

from datetime import UTC, datetime
from xml.etree import ElementTree as ET

from tak_simulator.xml_encoder import encode_chat_message, encode_chat_message_for_tcp


def test_encode_chat_message() -> None:
    xml_message = encode_chat_message(
        uid="ANDROID-180a4dc924264cf1",
        sender_callsign="DRAKO",
        chatroom="Lloyd Prudencio",
        message_id="09800474-e84c-4b4d-970b-b3b604d2d087",
        point=(58.4135, 15.5629444444),
        now=datetime(2026, 4, 8, 8, 15, 30, tzinfo=UTC),
        chat_group_id="9873603eac25455a8a636b14c08a9bc2",
        chat_group_uid0="S-1-5-21-71047030-3540295278-26651015-1001",
        remarks="Hello from emulator",
    )

    root = ET.fromstring(xml_message)
    assert root.tag == "event"
    assert root.attrib["uid"] == "ANDROID-180a4dc924264cf1"
    assert root.attrib["type"] == "b-t-f"
    assert root.attrib["how"] == "h-g-i-g-o"

    point = root.find("point")
    assert point is not None
    assert abs(float(point.attrib["lat"]) - 58.4135) < 1e-9
    assert abs(float(point.attrib["lon"]) - 15.5629444444) < 1e-9

    detail = root.find("detail")
    assert detail is not None

    chat = detail.find("__chat")
    assert chat is not None
    assert chat.attrib["id"] == "ANDROID-180a4dc924264cf1"
    assert chat.attrib["chatroom"] == "Lloyd Prudencio"
    assert chat.attrib["senderCallsign"] == "DRAKO"
    assert chat.attrib["groupOwner"] == "false"
    assert chat.attrib["messageId"] == "09800474-e84c-4b4d-970b-b3b604d2d087"

    chat_group = chat.find("chatgrp")
    assert chat_group is not None
    assert chat_group.attrib["id"] == "9873603eac25455a8a636b14c08a9bc2"
    assert chat_group.attrib["uid0"] == "S-1-5-21-71047030-3540295278-26651015-1001"

    remarks = chat.find("remarks")
    assert remarks is not None
    assert remarks.text == "Hello from emulator"


def test_encode_chat_message_for_tcp() -> None:
    xml_message = encode_chat_message_for_tcp(
        uid="ANDROID-180a4dc924264cf1",
        sender_callsign="DRAKO",
        chatroom="Lloyd Prudencio",
        message_id="09800474-e84c-4b4d-970b-b3b604d2d087",
        point=(58.4135, 15.5629444444),
        now=datetime(2026, 4, 8, 8, 15, 30, tzinfo=UTC),
        chat_group_id="9873603eac25455a8a636b14c08a9bc2",
        chat_group_uid0="S-1-5-21-71047030-3540295278-26651015-1001",
        remarks="Hello from emulator",
    )

    assert xml_message.startswith('<?xml version="1.0" encoding="UTF-8"?>\n<event')

    xml_body = xml_message.split("\n", 1)[1]
    root = ET.fromstring(xml_body)
    assert root.tag == "event"

    detail = root.find("detail")
    assert detail is not None
    chat = detail.find("__chat")
    assert chat is not None

    remarks = chat.find("remarks")
    assert remarks is not None
    assert remarks.text == "Hello from emulator"


def manual_encode_chat_message() -> None:
    message = input("Write chat message: ").strip()

    xml_message = encode_chat_message(
        uid="ANDROID-180a4dc924264cf1",
        sender_callsign="DRAKO",
        chatroom="Lloyd Prudencio",
        message_id="09800474-e84c-4b4d-970b-b3b604d2d087",
        point=(58.4135, 15.5629444444),
        now=datetime(2026, 4, 8, 8, 15, 30, tzinfo=UTC),
        chat_group_id="9873603eac25455a8a636b14c08a9bc2",
        chat_group_uid0="S-1-5-21-71047030-3540295278-26651015-1001",
        remarks=message,
    )

    root = ET.fromstring(xml_message)
    detail = root.find("detail")
    assert detail is not None

    chat = detail.find("__chat")
    assert chat is not None

    remarks = chat.find("remarks")
    assert remarks is not None
    assert remarks.text == message

    print("PASSED: Chat message correctly encoded in XML.")


if __name__ == "__main__":
    manual_encode_chat_message()
