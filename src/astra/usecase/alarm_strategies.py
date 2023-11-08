import datetime

from astra.data.alarms import *
from astra.data.data_manager import DataManager
from .alarm_checker import get_strategy
from .utils import eval_param_value, get_tag_param_value, get_tag_params
from typing import Callable, Iterable
from astra.data.telemetry_data import TelemetryData


def create_alarm(event_base: EventBase, id: int, time: datetime, description: str,
                 criticality: AlarmCriticality) -> Alarm:
    event = Event(event_base, id, time, description)

    return Alarm(event, criticality)


def check_conds(td: TelemetryData, tag: Tag, condition: Callable,
                comparison: list[ParameterValue]) -> list[tuple[bool, datetime]]:
    """
    Checks all telemetry frames in <td> where <condition> returns true
    Note: This should only be used for conditions where only 1 tag is relevant

    :param tag: The tag to use for checking conditions
    :param td: Contains all telemetry frames to examine
    :param condition: A function that returns a boolean with parameters
                      (ParameterValue, list[ParameterValue]
    :param comparison: A list of all ParameterValues to be used as a point of comparison
    :return: A list where each index i refers to the i-th telemetry frame in TelemetryData,
    the boolean in the tuple refers to the associated return from <condition>, and the datetime
    refers to the associated time of the telemetry frame
    """
    cond_met = []
    num_frames = td.num_telemetry_frames
    for i in range(num_frames):
        telemetry_frame = td.get_telemetry_frame(i)

        # Note: I believe we don't need to covnert to true value because both sides of
        # comparison would be applied the same transformation anyway
        raw_parameter_value = get_tag_param_value(i, tag, td)

        cond_met.append((condition(raw_parameter_value, comparison), telemetry_frame.time))
    return cond_met


def forward_checking(tuples: list[tuple[bool, datetime]], persistence) -> int:
    """
    Checks if there exists any sequence of booleans amongst tuples in <tuples>
    where all booleans are true and associated datetimes are every datetime in
    <tuples> within the range of (first datetime in the sequence + persistence seconds)
    
    :param tuples: Contains tuples indicating whether an alarm condition was
    met, and the time associated with the telemetry frame 
    :param persistence: How much time in seconds the alarm condition must be met for
    :return: The first index in the last sequence satisfying the persistence check. Returns
    -1 if no such sequence exists
    
    PRECONDITION: <tuples is sorted by ascending datetime
    """
    last = -1
    first_index = 0
    currently_raise_alarm = False
    first_time = tuples[0][1]
    end_time = first_time + datetime.timedelta(seconds=persistence)

    for i in range(len(tuples)):
        check_tuple = tuples[i]

        if check_tuple[1] > end_time:
            # Indicates were now outside the persistence check range
            if currently_raise_alarm:
                # Never saw False in the range, so indicate an alarm at the start
                last = first_index

        if not tuples[0]:
            # Alarm condition was not met, so reset this condition
            currently_raise_alarm = False
        else:
            if not currently_raise_alarm:
                # indicates a new start for persitence check

                # redundancy here if the very first one is true, but can't think of elegant
                # solution
                first_index = i
                currently_raise_alarm = True
                first_time = check_tuple[1]
                end_time = first_time + datetime.timedelta(seconds=persistence)

    if persistence == 0 and last == -1 and currently_raise_alarm:
        # edge case if the last tuple should be the returned value when persistence
        # check need not be applied
        last = first_index

    return last


def rate_of_change_check(dm: DataManager, alarm_base: RateOfChangeEventBase,
                         criticality: AlarmCriticality, new_id: int,
                         earliest_time: datetime) -> Alarm | None:
    ...


def static_check(dm: DataManager, alarm_base: StaticEventBase,
                 criticality: AlarmCriticality, new_id: int,
                 earliest_time: datetime) -> Alarm | None:
    ...


def threshold_check(dm: DataManager, alarm_base: ThresholdEventBase,
                    criticality: AlarmCriticality, new_id: int,
                    earliest_time: datetime) -> Alarm | None:
    ...


def setpoint_cond(param_value: ParameterValue, setpoint: list[ParameterValue]) -> bool:
    """
    Checks if param_value is at it's associated setpoint exactly

    :param param_value: The true value of the given parameter
    :param setpoint: The setpoint value to compare against
    :return: A boolean indicating if param_value is at the setpoint
    """
    return param_value == setpoint[0]


def setpoint_check(dm: DataManager, alarm_base: SetpointEventBase,
                   criticality: AlarmCriticality, new_id: int,
                   earliest_time: datetime) -> Alarm | None:
    """
    Checks if in the telemetry frames with times in the range
    (<earliest_time> - <alarm_base.persistence> -> present), there exists
    a sequence lasting <alarm_base.persistence> seconds where <alarm_base.tag> reported
    its setpoint value. Returns an appropriate Alarm if the check is satisfied

    :param dm: All data known to the program
    :param alarm_base: Stores all parties related to the check
    :param criticality: The base criticality of the alarm
    :param new_id: If an alarm must be raised, the id to assign it to
    :param earliest_time: The earliest time from a set of the most recently added
    telemetry frames
    :return: An Alarm containing all data about the recent event, or None if the check
    is not satisfied
    """

    # Calculating the range of time that needs to be checked
    if alarm_base.persistence is None:
        subtract_time = datetime.timedelta(seconds=0)
        sequence = 0
    else:
        subtract_time = datetime.timedelta(seconds=alarm_base.persistence)
        sequence = alarm_base.persistence

    # Getting all Telemetry Frames associated with the relevant timeframe
    first_time = earliest_time - subtract_time
    tag = alarm_base.tag
    telemetry_data = dm.get_telemetry_data(first_time, None, [tag])

    setpoint = alarm_base.setpoint

    # Checking which frames have tag values at setpoint and indicating it in <cond_met> in order
    cond_met = check_conds(dm, telemetry_data, tag, setpoint_cond, [setpoint])

    first_index = forward_checking(cond_met, sequence)
    if first_index == -1:
        return None
    relevant_frame = telemetry_data.get_telemetry_frame(first_index)
    timestamp = relevant_frame.time
    description = "setpoint value recorded"

    return create_alarm(alarm_base, new_id, timestamp, description, criticality)


def sequence_of_events_check(dm: DataManager, alarm_base: SOEEventBase,
                             criticality: AlarmCriticality, new_id: int,
                             earliest_time: datetime) -> Alarm | None:
    ...


def all_events_check(dm: DataManager, alarm_base: AllEventBase,
                     criticality: AlarmCriticality, new_id: int,
                     earliest_time: datetime) -> Alarm | None:
    """
    Checks that all event bases in <alarm_base> have occurred, and returns an appropriate
    Alarm. Otherwise, returns None

    :param earliest_time:
    :param dm: The source of all data known to the program
    :param alarm_base: Defines events to check
    :param criticality: default criticality for the alarm base
    :param new_id: the id to assign a potential new alarm
    :return: An alarm object defining details of a determined event
    """

    possible_events = alarm_base.event_bases
    for possible_event in possible_events:
        strategy = get_strategy(possible_event)
        alarm = strategy(dm, possible_event)
        if alarm is None:
            return None


def any_events_check(dm: DataManager, alarm_base: AnyEventBase,
                     criticality: AlarmCriticality, new_id: int,
                     earliest_time: datetime) -> Alarm | None:
    ...


def xor_events_check(dm: DataManager, alarm_base: XOREventBase,
                     criticality: AlarmCriticality, new_id: int,
                     earliest_time: datetime) -> Alarm | None:
    ...


def not_events_check(dm: DataManager, alarm_base: NotEventBase,
                     criticality: AlarmCriticality, new_id: int,
                     earliest_time: datetime) -> Alarm | None:
    ...
