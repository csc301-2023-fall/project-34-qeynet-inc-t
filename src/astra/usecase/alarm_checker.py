from typing import Callable
from astra.data.alarms import *
from .alarm_strategies import *

# TODO TEST THIS

next_id = 0


def get_strategy(base: EventBase) -> Callable:
    """
    Matches an unknown form of EventBase to the correct strategy to check them

    :param base: An EventBase to evaluate
    """
    match base:
        case RateOfChangeEventBase():
            return rate_of_change_check
        case StaticEventBase():
            return static_check
        case ThresholdEventBase():
            return threshold_check
        case SetpointEventBase():
            return setpoint_check
        case SOEEventBase():
            return sequence_of_events_check
        case AllEventBase():
            return all_events_check
        case AnyEventBase():
            return any_events_check
        case _:
            return xor_events_check


def check_alarms(dm: DataManager, alarms: dict[AlarmCriticality: list[Alarm]],
                 earliest_time: datetime) -> None:
    """
    Goes through all possible alarms to check and, if any exists, adds them to <alarms>
    based on their criticality

    :param earliest_time:
    :param dm: The manager of all data known to the program
    :param alarms: The global variable storing all current alarms

    PRECONDITION: alarms has exactly 5 keys, the values of which are
    'WARNING', 'LOW', 'MEDIUM', HIGH', CRITICAL', all of which map to
    a list
    """
    global next_id

    alarm_bases = dm.alarm_bases
    for alarm_base in alarm_bases:
        base = alarm_base.event_base
        criticality = alarm_base.criticality

        strategy = get_strategy(base)
        alarm = strategy(dm, base, criticality, next_id, earliest_time)
        if alarm is not None:
            next_id += 1
            criticality = alarm.criticality
            alarms[criticality].append(alarm)
