from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import NewType

from astra.data.parameters import ParameterValue, Tag


@dataclass(frozen=True)
class EventBase:
    persistence: float | None
    description: str


@dataclass(frozen=True)
class RateOfChangeEventBase(EventBase):
    tag: Tag
    rate_of_fall_threshold: float | None
    rate_of_rise_threshold: float | None
    time_window: float


@dataclass(frozen=True)
class StaticEventBase(EventBase):
    tag: Tag


@dataclass(frozen=True)
class ThresholdEventBase(EventBase):
    tag: Tag
    lower_threshold: float | None
    upper_threshold: float | None


@dataclass(frozen=True)
class SetpointEventBase(EventBase):
    tag: Tag
    setpoint: ParameterValue


@dataclass(frozen=True)
class SOEEventBase(EventBase):
    event_bases: list[EventBase]
    intervals: list[tuple[float, float | None]]


@dataclass(frozen=True)
class AllEventBase(EventBase):
    event_bases: list[EventBase]


@dataclass(frozen=True)
class AnyEventBase(EventBase):
    event_bases: list[EventBase]


EventID = NewType('EventID', int)


@dataclass(frozen=True)
class Event:
    base: EventBase
    id: EventID
    register_time: datetime
    confirm_time: datetime
    description: str


class AlarmCriticality(Enum):
    WARNING = 'WARNING'
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'

    def __lt__(self, other):
        return PRIORITIES[self] < PRIORITIES[other]

    def __gt__(self, other):
        return PRIORITIES[self] > PRIORITIES[other]

    def __str__(self):
        return self.name


PRIORITIES = {AlarmCriticality.CRITICAL: 4, AlarmCriticality.HIGH: 3, AlarmCriticality.MEDIUM: 2,
              AlarmCriticality.LOW: 1, AlarmCriticality.WARNING: 0}

AlarmPriority = AlarmCriticality


@dataclass(frozen=True)
class AlarmBase:
    event_base: EventBase
    criticality: AlarmCriticality


@dataclass(frozen=True)
class Alarm:
    event: Event
    criticality: AlarmCriticality
    acknowledgement: str
