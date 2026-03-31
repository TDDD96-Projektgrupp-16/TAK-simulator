import json
import sys

from typing import Optional

from pydantic import BaseModel, Field, field_validator

import logging

logger = logging.getLogger(__name__)


def load_scenario(file: int | str) -> Scenario:
    with open(file) as f:
        return Scenario.model_validate(json.load(f))


class Scenario(BaseModel):
    metadata: Optional[Metadata] = None
    emulators: list[EmulatorConfig]


class Metadata(BaseModel):
    description: Optional[str] = None


class EmulatorConfig(BaseModel):
    type_: str = Field(alias="type")
    access: str
    uid: str
    how: str
    callsign: str
    group: Group
    takv: Takv

    path: list[tuple[float, tuple[float, float]]]

    @field_validator("path")
    @classmethod
    def path_must_be_in_chronological_order(cls, path):
        if path != sorted(path, key=lambda p: p[0]):
            raise ValueError("path must be in chronological order")
        return path


class Group(BaseModel):
    name: str
    role: str


class Takv(BaseModel):
    device: str
    platform: str
    os: str
    version: str
