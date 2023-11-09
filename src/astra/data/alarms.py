from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import NewType

from astra.data.parameters import ParameterValue, Tag


@dataclass
class EventBase:
    persistence: float | None
    description: str


@dataclass
class RateOfChangeEventBase(EventBase):
    tag: Tag
    rate_of_fall_threshold: float | None
    rate_of_rise_threshold: float | None
    time_window: float


@dataclass
class StaticEventBase(EventBase):
    tag: Tag


@dataclass
class ThresholdEventBase(EventBase):
    tag: Tag
    lower_threshold: float | None
    upper_threshold: float | None


@dataclass
class SetpointEventBase(EventBase):
    tag: Tag
    setpoint: ParameterValue


@dataclass
class SOEEventBase(EventBase):
    event_bases: list[EventBase]
    intervals: list[tuple[float, float | None]]


@dataclass
class AllEventBase(EventBase):
    event_bases: list[EventBase]


@dataclass
class AnyEventBase(EventBase):
    event_bases: list[EventBase]


EventID = NewType('EventID', int)


@dataclass
class Event:
    base: EventBase
    id: EventID
    time: datetime
    description: str


class AlarmCriticality(Enum):
    WARNING = 'WARNING'
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'


AlarmPriority = AlarmCriticality


@dataclass
class AlarmBase:
    event_base: EventBase
    criticality: AlarmCriticality


@dataclass
class Alarm:
    event: Event
    criticality: AlarmCriticality
