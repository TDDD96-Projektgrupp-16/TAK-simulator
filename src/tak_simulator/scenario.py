import json
from typing import Optional, Literal, Annotated, Union

import names
from pydantic import BaseModel, Field, field_validator

from tak_simulator.uid import (
    generate_believable_atak_uid,
    generate_believable_wintak_uid,
)

import logging

logger = logging.getLogger(__name__)


# All display type options from WINTAK, ATAK has a gazillion more.
# Ground Troop, Armoured Vehicle, Civilian Vehicle,
# Generic Air, Generic Ground, Generic Sea Surface
Type = Literal[
    "a-f-G-U-C-I",
    "a-f-G-E-V-A",
    "a-f-G-E-V-C",
    "a-f-A",
    "a-f-G-U",
    "a-f-S",
]

How = Literal["h-e", "m-g"]

Team = Literal[
    "White",
    "Yellow",
    "Orange",
    "Magenta",
    "Red",
    "Maroon",
    "Purple",
    "Dark Blue",
    "Blue",
    "Cyan",
    "Teal",
    "Green",
    "Dark Green",
    "Brown",
]

# All team role options from WinTAK, ATAK has more.
Role = Literal[
    "Team Member",
    "Team Lead",
    "HQ",
    "Medic",
    "Forward Observer",
    "RTO",
    "K9",
]

EventType = Literal[
    "chat",
    "connect",
    "disconnect",
]


class Metadata(BaseModel):
    """Optional metadata for the scenario."""

    description: Optional[str] = Field(
        default=None,
        description="Brief description of the scenario.",
    )


class Group(BaseModel):
    """Team and role configuration for the emulator."""

    name: Team | str = Field(
        default="Cyan",
        description="Team/squad the emulator belongs to.",
        examples=["Cyan", "Red", "Blue"],
    )
    role: Role | str = Field(
        default="Team Member",
        description="Operational role of the emulator.",
        examples=["Team Member", "Team Lead", "Medic"],
    )


class Takv(BaseModel):
    """Device and platform metadata for the emulator."""

    device: str = Field(
        description="Device model identifier.",
    )
    platform: str = Field(
        description="TAK platform identifier, e.g. `ATAK-CIV` or `WinTAK-CIV`.",
    )
    os: str = Field(
        description="Operating system name and version.",
    )
    version: str = Field(
        description="TAK application version string.",
    )


class ATAKTakv(Takv):
    """Device and platform metadata for an ATAK-CIV client."""

    platform: str = "ATAK-CIV"
    os: str = "36"  # Android 16
    version: str = "5.6.0.12 [9c9a5897](playstore).1769863102-CIV"  # Latest stable ATAK-CIV version as of 2026-03-31


class WinTAKTakv(Takv):
    """Device and platform metadata for a WinTAK-CIV client."""

    platform: str = "WinTAK-CIV"
    os: str = "Microsoft Windows 11 Home"
    version: str = "5.6.0.151"  # Latest stable WinTAK-CIV version as of 2026-03-31


class ScenarioEventBase(BaseModel):
    """A timed event for one emulator in the scenario."""

    type: EventType = Field(
        description="Type of scenario event.",
        alias="type",
    )
    time: float = Field(
        description="Simulation time when the event should happen.",
    )


class ChatEvent(ScenarioEventBase):
    type: Literal["chat"]
    recipient_uid: str = Field(description="The uid of the chat recipient.")
    message: str = Field(description="The chat content.")


ScenarioEvent = Annotated[ChatEvent, Field(discriminator="type")]


class EmulatorOptionsBase(BaseModel):
    """Base configuration for emulator options."""

    type: Type | str = Field(
        description="Display type.",
    )
    access: str = Field(
        default="Undefined",
        description="Access level.",
    )
    uid: str = Field(
        description="Unique identifier for the emulator.",
    )
    how: How | str = Field(
        default="m-g",
        description="CoT how.",
        examples=["m-g", "h-e"],
    )
    callsign: str = Field(
        default_factory=names.get_full_name,
        description="Callsign for the emulator. A random first and last name if omitted.",
    )
    group: Group = Field(
        default_factory=Group,
        description="Team and role for the emulator.",
    )
    takv: Takv = Field(
        description="Device and platform metadata for the emulator.",
    )

    path: list[tuple[float, tuple[float, float]]] = Field(
        description="List of (timestamp, (lat, lon)) waypoints.",
    )

    @field_validator("path")
    @classmethod
    def path_must_be_in_chronological_order(cls, path):
        """Ensures path timestamps are in chronological order."""
        if path != sorted(path, key=lambda p: p[0]):
            raise ValueError("path must be in chronological order")
        return path

    events: list[ScenarioEvent] = Field(
        default_factory=list,
        description="Timed events for this emulator.",
    )


class ATAKEmulatorOptions(EmulatorOptionsBase):
    """Emulator options for an ATAK client."""

    like: Literal["atak"]

    type: Type | str = "a-f-G-U-C"
    uid: str = Field(
        default_factory=generate_believable_atak_uid,
        description="Unique identifier for the emulator. A random ATAK like uid if omitted",
    )
    takv: ATAKTakv = Field(
        default_factory=ATAKTakv,
        description="Device and platform metadata for the emulator.",
    )


class WinTakEmulatorOptions(EmulatorOptionsBase):
    """Emulator options for a WinTAK client."""

    like: Literal["wintak"]

    type: Type | str = "a-f-G-U-C-I"
    uid: str = Field(
        default_factory=generate_believable_wintak_uid,
        description="Unique identifier for the emulator. A random WinTAK like uid if omitted",
    )
    takv: WinTAKTakv = Field(
        default_factory=WinTAKTakv,
        description="Device and platform metadata for the emulator.",
    )


EmulatorOptions = Annotated[
    Union[ATAKEmulatorOptions, WinTakEmulatorOptions], Field(discriminator="like")
]


class Scenario(BaseModel):
    """A scenario defining a set of emulators to run."""

    metadata: Optional[Metadata] = Field(
        default=None,
        description="Optional scenario metadata.",
    )
    emulators: list[EmulatorOptions] = Field(
        description="List of emulators to run.",
    )


def export_scenario_schema():
    """Print the JSON schema for a scenario to stdout"""
    print(json.dumps(Scenario.model_json_schema(), indent=2))


def load_scenario(file: int | str) -> Scenario:
    """Load and validate a scenario from a JSON file"""
    with open(file) as f:
        return Scenario.model_validate(json.load(f))
