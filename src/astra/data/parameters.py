"""This module defines various types relevant to tags and parameters."""

from dataclasses import dataclass
from typing import NewType

Tag = NewType('Tag', str)
ParameterValue = bool | int | float


@dataclass(frozen=True)
class DisplayUnit:
    """
    Information on how to display a value, separate from the storage of the value.

    More or less follows Panoptes.

    value --display-> f'{multiplier * value + constant} {symbol}'
    """
    description: str
    symbol: str
    multiplier: float
    constant: float


@dataclass(frozen=True)
class Parameter:
    """
    A specific kind of telemetry data to monitor.

    Equivalent to TagEntry in Panoptes.

    Restriction: for dtype bool, display_units should always be None.
    """
    tag: Tag
    description: str
    dtype: type[ParameterValue]
    setpoint: ParameterValue | None
    display_units: DisplayUnit | None
