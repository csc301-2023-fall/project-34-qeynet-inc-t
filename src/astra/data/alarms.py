import functools
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import cached_property
from typing import ClassVar, NewType, override

from astra.data.parameters import ParameterValue, Tag


@dataclass(frozen=True)
class EventBase(ABC):
    type: ClassVar[str] = ''
    persistence: float | None
    description: str

    @property
    @abstractmethod
    def tags(self) -> Iterable[Tag]:
        raise NotImplementedError


@dataclass(frozen=True)
class SimpleEventBase(EventBase):
    tag: Tag

    @override
    @cached_property
    def tags(self) -> Iterable[Tag]:
        return {self.tag}


@dataclass(frozen=True)
class CompoundEventBase(EventBase):
    event_bases: list[EventBase]

    @override
    @cached_property
    def tags(self) -> Iterable[Tag]:
        return {tag for event_base in self.event_bases for tag in event_base.tags}


@dataclass(frozen=True)
class RateOfChangeEventBase(SimpleEventBase):
    type: ClassVar[str] = 'Rate of change'
    rate_of_fall_threshold: float | None
    rate_of_rise_threshold: float | None
    time_window: float


@dataclass(frozen=True)
class StaticEventBase(SimpleEventBase):
    type: ClassVar[str] = 'Static'


@dataclass(frozen=True)
class ThresholdEventBase(SimpleEventBase):
    type: ClassVar[str] = 'Threshold'
    lower_threshold: float | None
    upper_threshold: float | None


@dataclass(frozen=True)
class SetpointEventBase(SimpleEventBase):
    type: ClassVar[str] = 'Setpoint'
    setpoint: ParameterValue


@dataclass(frozen=True)
class SOEEventBase(CompoundEventBase):
    type: ClassVar[str] = 'SOE'
    intervals: list[tuple[float, float | None]]


@dataclass(frozen=True)
class AllEventBase(CompoundEventBase):
    type: ClassVar[str] = 'Logical AND'


@dataclass(frozen=True)
class AnyEventBase(CompoundEventBase):
    type: ClassVar[str] = 'Logical OR'


EventID = NewType('EventID', int)


@dataclass(frozen=True)
class Event:
    base: EventBase
    id: EventID
    register_time: datetime
    confirm_time: datetime
    creation_time: datetime
    description: str

    @property
    def type(self) -> str:
        return type(self.base).type


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


@dataclass(frozen=False)
class Alarm:
    event: Event
    criticality: AlarmCriticality
    priority: AlarmPriority
    acknowledgement: bool

    def __gt__(self, other) -> bool:
        return self.priority > other.priority

    def __lt__(self, other) -> bool:
        return self.priority < other.priority
