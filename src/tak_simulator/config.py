import json

from dataclasses import dataclass
from dataclasses import fields
from enum import Enum
from typing import get_origin, get_args, Self, Any


def _parse_dataclass(cls, data):
    if data is None:
        return None
    
    origin = get_origin(cls)
    
    if origin is list:
        inner_type = get_args(cls)[0]
        return [_parse_dataclass(inner_type, item) for item in data]
    
    if isinstance(cls, type) and issubclass(cls, Enum):
        return cls(data)

    if hasattr(cls, "__dataclass_fields__") and not isinstance(data, cls):
        field_types = {f.name: f.type for f in fields(cls)}
        parsed = {}
        for name, field_type in field_types.items():
            if name not in data:
                continue
            
            parsed[name] = _parse_dataclass(field_type, data[name])
            
        return cls(**parsed)
    
    return data


@dataclass
class Metadata:
    description: str


@dataclass
class Group:
    name: str
    role: str


@dataclass
class Takv:
    device: str
    platform: str
    os: str
    version: str


@dataclass
class EmulatorConfig:
    type_: str
    access: str
    uid: str
    how: str
    callsign: str
    group: Group
    takv: Takv

    path: list[tuple[float, tuple[float, float]]]

@dataclass
class ActionType(Enum):
    MESSAGE = "MESSAGE"

@dataclass
class Action:
    type_: ActionType
    content: str
    time: float
    users: list[str]

@dataclass
class Config:
    metadata: Metadata
    emulators: list[EmulatorConfig]

    @classmethod
    def from_str(cls, s: str) -> Self:
        return cls.from_dict(json.loads(s))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return _parse_dataclass(cls, data)
