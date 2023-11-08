from astra.data.alarms import *
from astra.data.data_manager import DataManager
from .alarm_checker import get_strategy


def rate_of_change_check(dm: DataManager, alarm_base: RateOfChangeEventBase,
                         criticality: AlarmCriticality, new_id: int) -> Alarm | None:
    ...


def static_check(dm: DataManager, alarm_base: StaticEventBase,
                 criticality: AlarmCriticality, new_id: int) -> Alarm | None:
    ...


def threshold_check(dm: DataManager, alarm_base: ThresholdEventBase,
                    criticality: AlarmCriticality, new_id: int) -> Alarm | None:
    ...


def setpoint_check(dm: DataManager, alarm_base: SetpointEventBase,
                   criticality: AlarmCriticality, new_id: int) -> Alarm | None:
    ...


def sequence_of_events_check(dm: DataManager, alarm_base: SOEEventBase,
                             criticality: AlarmCriticality, new_id: int) -> Alarm | None:
    ...


def all_events_check(dm: DataManager, alarm_base: AllEventBase,
                     criticality: AlarmCriticality, new_id: int) -> Alarm | None:

    possible_events = alarm_base.event_bases
    for possible_event in possible_events:
        strategy = get_strategy(possible_event)
        alarm = strategy(dm, possible_event)
        if alarm is None:
            return None


def any_events_check(dm: DataManager, alarm_base: AnyEventBase,
                     criticality: AlarmCriticality, new_id: int) -> Alarm | None:
    ...


def xor_events_check(dm: DataManager, alarm_base: XOREventBase,
                     criticality: AlarmCriticality, new_id: int) -> Alarm | None:
    ...


def not_events_check(dm: DataManager, alarm_base: NotEventBase,
                     criticality: AlarmCriticality, new_id: int) -> Alarm | None:
    ...
