import functools
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
    creation_time: datetime
    description: str


@functools.total_ordering
class AlarmCriticality(Enum):
    WARNING = 'WARNING'
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'

    def __le__(self, other):
        if isinstance(other, AlarmCriticality):
            return CRIT_TO_INT_LOOKUP[self] < CRIT_TO_INT_LOOKUP[other]
        return NotImplemented

    def __str__(self):
        return self.value


AlarmPriority = AlarmCriticality


CRIT_TO_INT_LOOKUP = {
    # This dictionary maps alarm criticality levels to integer values.
    # Used for comparing criticalities/priorities.
    AlarmCriticality.WARNING: 0,
    AlarmCriticality.LOW: 1,
    AlarmCriticality.MEDIUM: 2,
    AlarmCriticality.HIGH: 3,
    AlarmCriticality.CRITICAL: 4,
}


@dataclass(frozen=True)
class AlarmBase:
    event_base: EventBase
    criticality: AlarmCriticality


@dataclass(frozen=True)
class Alarm:
    event: Event
    criticality: AlarmCriticality
    acknowledgement: str
