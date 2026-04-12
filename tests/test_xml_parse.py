"""Pytest tests for CoT XML parsing.

Run automated tests with:
    uv run pytest tests/test_xml_parse.py

Run manual chat parsing with:
    uv run python tests/test_xml_parse.py
"""

import pytest
from tak_simulator.xml_parse import parse_tak_group_chat, GroupChatMessage

# Group Chat (3 people)
RAW_GROUP_CHAT = b'\xbf\x01\xbf\n.\x1a,S-1-5-21-599088404-856123360-4043671938-1003\x12\xe8\t\n\x05b-t-f\x12\tUndefined*~GeoChat.S-1-5-21-599088404-856123360-4043671938-1003.89f9a147-ee79-4d8d-9a24-f214a4a3ebec.00c82d7c-c54d-490f-a593-86972b91939e0\x9c\xb2\xb2\xe8\xd638\x9c\xb2\xb2\xe8\xd63@\x9c\xea\xcb\x91\xd73J\th-g-i-g-oa\x00\x00\x00\xe0\xcf\x12cAi\x00\x00\x00\xe0\xcf\x12cAq\x00\x00\x00\xe0\xcf\x12cAz\x98\x08\n\x95\x08<__chat id="89f9a147-ee79-4d8d-9a24-f214a4a3ebec" chatroom="New Group" senderCallsign="MUDBUG" groupOwner="true" messageId="00c82d7c-c54d-490f-a593-86972b91939e"><chatgrp id="89f9a147-ee79-4d8d-9a24-f214a4a3ebec" uid0="S-1-5-21-599088404-856123360-4043671938-1003" uid1="ANDROID-45869c12c0ed009f" uid2="S-1-5-21-3298798845-1049192405-551056456-1001"/><hierarchy><group uid="UserGroups" name="Groups"><group uid="89f9a147-ee79-4d8d-9a24-f214a4a3ebec" name="New Group"><contact uid="ANDROID-45869c12c0ed009f" name="Algot Johansson"/><contact uid="S-1-5-21-3298798845-1049192405-551056456-1001" name="Arvid Ramsberg"/><contact uid="S-1-5-21-599088404-856123360-4043671938-1003" name="MUDBUG"/></group></group></hierarchy></__chat><link uid="S-1-5-21-599088404-856123360-4043671938-1003" type="a-f-G-U-C-I" relation="p-p"/><remarks source="BAO.F.WinTAK.S-1-5-21-599088404-856123360-4043671938-1003" sourceID="S-1-5-21-599088404-856123360-4043671938-1003" to="89f9a147-ee79-4d8d-9a24-f214a4a3ebec" time="2026-04-08T12:23:55.42Z">in position</remarks>'

# Direct Message (2 people)
RAW_DIRECT_MSG = b'\xbf\x01\xbf\n.\x1a,S-1-5-21-599088404-856123360-4043671938-1003\x12\xf6\x06\n\x05b-t-f\x12\tUndefined*\x87\x01GeoChat.S-1-5-21-599088404-856123360-4043671938-1003.S-1-5-21-881805813-4011829539-2499212253-1001.b9833d56-660b-4e21-8797-1d5cd2c2a97f0\xde\xe5\x87\x8f\xd738\xde\xe5\x87\x8f\xd73@\xde\x9d\xa1\xb8\xd73J\th-g-i-g-oi\x00\x00\x00\xe0\xcf\x12cAq\x00\x00\x00\xe0\xcf\x12cAz\xa5\x05\n\xa2\x05<__chat id="S-1-5-21-881805813-4011829539-2499212253-1001" chatroom="Arvid Ramsberg" senderCallsign="MUDBUG" groupOwner="false" messageId="b9833d56-660b-4e21-8797-1d5cd2c2a97f"><chatgrp id="S-1-5-21-881805813-4011829539-2499212253-1001" uid0="S-1-5-21-599088404-856123360-4043671938-1003" uid1="S-1-5-21-881805813-4011829539-2499212253-1001"/></__chat><link uid="S-1-5-21-599088404-856123360-4043671938-1003" type="a-f-G-U-C-I" relation="p-p"/><remarks source="BAO.F.WinTAK.S-1-5-21-599088404-856123360-4043671938-1003" sourceID="S-1-5-21-599088404-856123360-4043671938-1003" to="S-1-5-21-881805813-4011829539-2499212253-1001" time="2026-04-09T10:55:26.43Z">at VDO</remarks>'

def test_parse_group_chat() -> None:
    """Validate parsing of a standard TAK group chat with hierarchy."""
    result = parse_tak_group_chat(RAW_GROUP_CHAT)
    
    assert result.chatroom_name == "New Group"
    assert result.sender_callsign == "MUDBUG"
    assert result.message == "in position"
    assert len(result.participant_uids) == 3
    assert result.contacts["ANDROID-45869c12c0ed009f"] == "Algot Johansson"

def test_parse_direct_message() -> None:
    """Validate parsing of a 1-on-1 direct message (no hierarchy)."""
    result = parse_tak_group_chat(RAW_DIRECT_MSG)
    
    assert result.chatroom_name == "Arvid Ramsberg"
    assert result.sender_callsign == "MUDBUG"
    assert result.message == "at VDO"
    assert len(result.participant_uids) == 2
    assert len(result.contacts) == 0

def test_parse_invalid_data() -> None:
    """Ensure parser raises ValueError on non-XML data."""
    with pytest.raises(ValueError):
        parse_tak_group_chat(b"Invalid Binary Header Data")

def manual_parse_xml() -> None:
    print("--- Manual TAK XML Parser ---")
    print("Paste your raw TAK data (bytes string or XML) below and press Enter:")
    
    user_input = input("> ").strip()
    
    if user_input.startswith("b'") or user_input.startswith('b"'):
        import ast
        try:
            raw_data = ast.literal_eval(user_input)
        except Exception:
            raw_data = user_input.encode("utf-8")
    else:
        raw_data = user_input.encode("utf-8")

    try:
        result = parse_tak_group_chat(raw_data)
        print(f"  Chatroom: {result.chatroom_name}")
        print(f"  Sender:   {result.sender_callsign}")
        print(f"  Message:  {result.message}")
        print(f"  Participants: {len(result.participant_uids)}")
    except Exception as e:
        print(f"\n[ERROR] Failed to parse: {e}")

if __name__ == "__main__":
    manual_parse_xml()