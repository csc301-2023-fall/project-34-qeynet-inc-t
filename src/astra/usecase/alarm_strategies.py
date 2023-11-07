from astra.data.alarms import *
from astra.data.data_manager import DataManager


def rate_of_change_check(dm: DataManager, alarm_base: RateOfChangeEventBase) -> Alarm | None:
    ...


def static_check(dm: DataManager, alarm_base: StaticEventBase) -> Alarm | None:
    ...


def threshold_check(dm: DataManager, alarm_base: ThresholdEventBase) -> Alarm | None:
    ...


def setpoint_check(dm: DataManager, alarm_base: SetpointEventBase) -> Alarm | None:
    ...


def sequence_of_events_check(dm: DataManager, alarm_base: SOEEventBase) -> Alarm | None:
    ...


def all_events_check(dm: DataManager, alarm_base: AllEventBase) -> Alarm | None:
    ...


def any_events_check(dm: DataManager, alarm_base: AnyEventBase) -> Alarm | None:
    ...


def xor_events_check(dm: DataManager, alarm_base: XOREventBase) -> Alarm | None:
    ...


def not_events_check(dm: DataManager, alarm_base: NotEventBase) -> Alarm | None:
    ...

