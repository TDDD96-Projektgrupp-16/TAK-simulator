import xml.etree.ElementTree as ET
from typing import List, Dict
from pydantic import BaseModel, ConfigDict, Field

class GroupChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chatroom_name: str
    sender_callsign: str
    message: str
    time: str
    participant_uids: List[str] = Field(default_factory=list)
    contacts: Dict[str, str] = Field(default_factory=dict)

def parse_tak_group_chat(raw_bytes: bytes) -> GroupChatMessage:
    # Strip the TAK binary header (\xbf\x01\xbf...)
    start_index = raw_bytes.find(b"<__chat")
    if start_index == -1:
        raise ValueError("No XML found in payload")

    xml_part = raw_bytes[start_index:].decode("utf-8")
    root = ET.fromstring(f"<root>{xml_part}</root>")

    # Get basic chat info
    chat_el = root.find("__chat")
    remarks_el = root.find("remarks")

    msg = GroupChatMessage(
        chatroom_name=chat_el.get("chatroom"),
        sender_callsign=chat_el.get("senderCallsign"),
        message=remarks_el.text,
        time=remarks_el.get("time"),
    )

    # Extract all UIDs from <chatgrp>
    grp_el = chat_el.find("chatgrp")
    if grp_el is not None:
        msg.participant_uids = [
            val for key, val in grp_el.attrib.items() if key.startswith("uid")
        ]

    # Parse the <hierarchy> to get real names for the contacts
    for contact in root.findall(".//contact"):
        uid = contact.get("uid")
        name = contact.get("name")
        if uid and name:
            msg.contacts[uid] = name

    return msg