from datetime import UTC, datetime, timedelta, timezone
import uuid
from xml.etree import ElementTree

import pytest

from tak_simulator.xml_parse import (
    build_chat_detail_for_direct_message,
    decode_chat_detail,
)
from tak_simulator.scenario import (
    ATAKEmulatorOptions,
    ATAKTakv,
    WinTakEmulatorOptions,
    WinTAKTakv,
    EmulatorOptions,
)


FIXED_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")

RAW_DETAIL_FRAGMENT = (
    '<__chat chatroom="S-1-2-3" groupOwner="false" id="S-1-2-3" '
    'parent="RootContactGroup" '
    'senderCallsign="Raven" messageId="12345678123456781234567812345678">'
    '<chatgrp id="S-1-2-3" uid0="ANDROID-0123456789abcdef" uid1="S-1-2-3"/>'
    "</__chat>"
    '<link uid="ANDROID-0123456789abcdef" type="a-f-G-U-C-I" relation="p-p"/>'
    '<remarks source="BAO.F.WinTAK.ANDROID-0123456789abcdef" '
    'sourceID="ANDROID-0123456789abcdef" to="S-1-2-3" '
    'time="2026-04-28T09:30:00Z">hello world</remarks>'
)


def make_atak_sender() -> ATAKEmulatorOptions:
    return ATAKEmulatorOptions(
        like="atak",
        uid="ANDROID-0123456789abcdef",
        callsign="Raven",
        takv=ATAKTakv(device="Pixel 9"),
        path=[(0.0, (59.0, 18.0))],
    )


def make_wintak_sender() -> WinTakEmulatorOptions:
    return WinTakEmulatorOptions(
        like="wintak",
        uid="S-1-5-21-111-222-333-1001",
        callsign="Viper",
        takv=WinTAKTakv(device="Surface Pro 11"),
        path=[(0.0, (59.0, 18.0))],
    )


@pytest.mark.parametrize(
    ("sender", "expected_platform"),
    [
        (make_atak_sender(), "ATAK"),
        (make_wintak_sender(), "WinTAK"),
    ],
)
def test_build_chat_detail_for_direct_message_populates_fields(
    sender: EmulatorOptions,
    expected_platform: str,
) -> None:
    recipient_uid = "S-1-5-21-444-555-666-1002"
    recipient_callsign = "RCPT"
    endpoint = "127.0.0.1:4242:tcp"
    sent_at = datetime(2026, 4, 28, 9, 30, 0, tzinfo=UTC)

    detail = build_chat_detail_for_direct_message(
        sender=sender,
        recipient_id=recipient_uid,
        recipient_callsign=recipient_callsign,
        endpoint=endpoint,
        message="Roger!",
        time=sent_at,
        message_id=FIXED_UUID.hex,
    )

    assert detail.chat.parent == "RootContactGroup"
    assert detail.chat.chatroom == recipient_callsign
    assert detail.chat.group_owner is False
    assert detail.chat.id == recipient_uid
    assert detail.chat.sender_callsign == sender.callsign
    assert detail.chat.message_id == FIXED_UUID.hex
    assert detail.chat.chatgrp.id == recipient_uid
    assert detail.chat.chatgrp.uid0 == sender.uid
    assert detail.chat.chatgrp.uid1 == recipient_uid
    assert detail.chat.chatgrp.uid2 is None

    assert detail.link.uid == sender.uid
    assert detail.link.type == sender.type
    assert detail.link.relation == "p-p"

    assert detail.server_destination.destinations == f"{endpoint}:{sender.uid}"

    assert detail.remarks.source == f"BAO.F.{expected_platform}.{sender.uid}"
    assert detail.remarks.source_id == sender.uid
    assert detail.remarks.to == recipient_uid
    assert detail.remarks.time == "2026-04-28T09:30:00Z"
    assert detail.remarks.text == "Roger!"


def test_build_chat_detail_for_direct_message_converts_time_to_utc() -> None:
    detail = build_chat_detail_for_direct_message(
        sender=make_wintak_sender(),
        recipient_id="S-1-5-21-444-555-666-1002",
        recipient_callsign="RCPT",
        endpoint="127.0.0.1:4242:tcp",
        message="hold position",
        time=datetime(
            2026,
            4,
            28,
            9,
            30,
            0,
            tzinfo=timezone(timedelta(hours=2)),
        ),
        message_id=FIXED_UUID.hex,
    )

    assert detail.remarks.time == "2026-04-28T07:30:00Z"


@pytest.mark.parametrize(
    "raw_detail",
    [
        RAW_DETAIL_FRAGMENT,
        f"<detail>{RAW_DETAIL_FRAGMENT}</detail>",
        f" \n\t<detail>{RAW_DETAIL_FRAGMENT}</detail>\n",
    ],
)
def test_decode_chat_detail_accepts_fragment_and_wrapped_detail(
    raw_detail: str,
) -> None:
    detail = decode_chat_detail(raw_detail)

    assert detail.chat.chatroom == "S-1-2-3"
    assert detail.chat.group_owner is False
    assert detail.chat.sender_callsign == "Raven"
    assert detail.chat.chatgrp.uid0 == "ANDROID-0123456789abcdef"
    assert detail.chat.chatgrp.uid1 == "S-1-2-3"
    assert detail.link.relation == "p-p"
    assert detail.remarks.source == "BAO.F.WinTAK.ANDROID-0123456789abcdef"
    assert detail.remarks.text == "hello world"


def test_build_chat_detail_for_direct_message_serializes_expected_xml() -> None:
    detail = build_chat_detail_for_direct_message(
        sender=WinTakEmulatorOptions(
            like="wintak",
            uid="S-1-5-21-599088404-856123360-4043671938-1003",
            callsign="MUDBUG",
            takv=WinTAKTakv(device="Surface Pro 11"),
            path=[(0.0, (59.0, 18.0))],
        ),
        recipient_id="S-1-5-21-881805813-4011829539-2499212253-1001",
        recipient_callsign="DEST",
        endpoint="127.0.0.1:4242:tcp",
        message="at VDO",
        time=datetime(2026, 4, 9, 10, 55, 26, 430000, tzinfo=UTC),
        message_id="b9833d56-660b-4e21-8797-1d5cd2c2a97f",
    )

    xml = detail.to_xml()

    assert isinstance(xml, bytes)
    expected_xml = (
        '<detail><__chat chatroom="DEST" '
        'groupOwner="false" id="S-1-5-21-881805813-4011829539-2499212253-1001" '
        'messageId="b9833d56-660b-4e21-8797-1d5cd2c2a97f" '
        'parent="RootContactGroup" '
        'senderCallsign="MUDBUG">'
        '<chatgrp id="S-1-5-21-881805813-4011829539-2499212253-1001" '
        'uid0="S-1-5-21-599088404-856123360-4043671938-1003" '
        'uid1="S-1-5-21-881805813-4011829539-2499212253-1001" uid2="" /></__chat>'
        '<link uid="S-1-5-21-599088404-856123360-4043671938-1003" type="a-f-G-U-C-I" '
        'relation="p-p" />'
        '<__serverdestination destinations="127.0.0.1:4242:tcp:S-1-5-21-599088404-856123360-4043671938-1003" />'
        '<remarks '
        'source="BAO.F.WinTAK.S-1-5-21-599088404-856123360-4043671938-1003" '
        'sourceID="S-1-5-21-599088404-856123360-4043671938-1003" '
        'to="S-1-5-21-881805813-4011829539-2499212253-1001" '
        'time="2026-04-09T10:55:26Z">at VDO</remarks></detail>'
    )

    assert_xml_trees_equal(xml.decode(), expected_xml)


def assert_xml_trees_equal(actual_xml: str, expected_xml: str) -> None:
    actual = ElementTree.canonicalize(actual_xml, strip_text=True)
    expected = ElementTree.canonicalize(expected_xml, strip_text=True)

    assert actual == expected
