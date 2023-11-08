import datetime

from astra.data.alarms import *
from astra.data.data_manager import DataManager
from .alarm_checker import get_strategy
from .utils import eval_param_value, get_tag_param_value, get_tag_params


def create_alarm(event_base: EventBase, id: int, time: datetime, description: str,
                 criticality: AlarmCriticality) -> Alarm:
    event = Event(event_base, id, time, description)

    return Alarm(event, criticality)


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
    cond_met = []

    tag_parameters = get_tag_params(tag, dm)

    # Checking which frames have tag values at setpoint and indicating it in <cond_met> in order
    num_frames = telemetry_data.num_telemetry_frames
    for i in range(num_frames):
        telemetry_frame = telemetry_data.get_telemetry_frame(i)

        raw_parameter_value = get_tag_param_value(i, tag, telemetry_data)
        true_parameter_value = eval_param_value(tag_parameters, raw_parameter_value)

        cond_met.append((true_parameter_value == setpoint, telemetry_frame.time))

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
