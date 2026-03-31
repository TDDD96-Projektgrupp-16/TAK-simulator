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


class Metadata(BaseModel):
    description: Optional[str] = None


class Group(BaseModel):
    name: Team | str = "Cyan"
    role: Role | str = "Team Member"


class Takv(BaseModel):
    device: str
    platform: str
    os: str
    version: str


class ATAKTakv(Takv):
    platform: str = "ATAK-CIV"
    os: str = "36"  # Android 16
    version: str = "5.6.0.12 [9c9a5897](playstore).1769863102-CIV"  # Latest stable ATAK-CIV version as of 2026-03-31


class WinTAKTakv(Takv):
    platform: str = "WinTAK-CIV"
    os: str = "Microsoft Windows 11 Home"
    version: str = "5.6.0.151"  # Latest stable WinTAK-CIV version as of 2026-03-31


class EmulatorOptionsBase(BaseModel):
    type: Type | str
    access: str = "Undefined"
    uid: str
    how: How | str = "m-g"
    callsign: str = Field(default_factory=names.get_full_name)
    group: Group = Field(default_factory=Group)
    takv: Takv

    path: list[tuple[float, tuple[float, float]]]

    @field_validator("path")
    @classmethod
    def path_must_be_in_chronological_order(cls, path):
        if path != sorted(path, key=lambda p: p[0]):
            raise ValueError("path must be in chronological order")
        return path


class ATAKEmulatorOptions(EmulatorOptionsBase):
    like: Literal["atak"]

    type: Type | str = "a-f-G-U-C"
    uid: str = Field(default_factory=generate_believable_atak_uid)
    takv: ATAKTakv


class WinTakEmulatorOptions(EmulatorOptionsBase):
    like: Literal["wintak"]

    type: Type | str = "a-f-G-U-C-I"
    uid: str = Field(default_factory=generate_believable_wintak_uid)
    takv: WinTAKTakv


EmulatorOptions = Annotated[
    Union[ATAKEmulatorOptions, WinTakEmulatorOptions], Field(discriminator="like")
]


class Scenario(BaseModel):
    metadata: Optional[Metadata] = None
    emulators: list[EmulatorOptions]


def export_scenario_schema():
    print(json.dumps(Scenario.model_json_schema(), indent=2))


def load_scenario(file: int | str) -> Scenario:
    with open(file) as f:
        return Scenario.model_validate(json.load(f))
