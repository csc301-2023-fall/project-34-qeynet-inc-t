from dataclasses import dataclass
from typing import NewType

Tag = NewType('Tag', str)
type ParameterValue = bool | int | float


@dataclass(frozen=True)
class DisplayUnit:
    description: str
    symbol: str
    multiplier: float
    constant: float


@dataclass(frozen=True)
class Parameter:
    tag: Tag
    description: str
    dtype: type[ParameterValue]
    setpoint: ParameterValue | None
    display_units: DisplayUnit | None
