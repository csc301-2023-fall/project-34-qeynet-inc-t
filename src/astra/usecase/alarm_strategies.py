import datetime
from datetime import datetime, timedelta

from astra.data.alarms import *
from astra.data.data_manager import DataManager
from .utils import get_tag_param_value
from typing import Callable
from astra.data.telemetry_data import TelemetryData

next_id = EventID(0)


# TODO: if alarm descriptions are "formulaic", extract helper method for making alarms from list

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
        case _:
            return any_events_check


def find_first_time(alarm_base: EventBase, earliest_time: datetime) -> (datetime, datetime):
    """Finds the first time to check for persistence and returns it, along with
    the length of time to check for persistence

    :param alarm_base: the event for which persistence must be checked
    :param earliest_time: The earliest time linked to the newest telemetry frame
    recently added
    :return A tuple where the first item is the first time which must be checked,
    and the second is the length of time to check
    """

    # Calculating the range of time that needs to be checked
    if alarm_base.persistence is None:
        subtract_time = timedelta(seconds=0)
        sequence = 0
    else:
        subtract_time = timedelta(seconds=alarm_base.persistence)
        sequence = alarm_base.persistence

    # Getting all Telemetry Frames associated with the relevant timeframe
    first_time = earliest_time - subtract_time
    return first_time, sequence


def create_alarm(alarm_indexes: tuple[int, int], td: TelemetryData, description: str,
                 event_base: EventBase,
                 criticality: AlarmCriticality) -> Alarm:
    """
    Uses information on telemetry indexes to create an appropriate alarm

    :param alarm_indexes: A tuple listing the index where an alarm condition is first met,
    and another listing the first where the persistence time check is met
    :param td: All telemetry data relevant to the alarm being checked
    :param description: Describes information about the event
    :param event_base: The underlying type of alarm that occured
    :param criticality: The base importance of the alarm
    :return: An alarm detailing a certain event that has occured
    """
    global next_id

    register_frame = td.get_telemetry_frame(alarm_indexes[0])
    register_timestamp = register_frame.time

    confirm_frame = td.get_telemetry_frame(alarm_indexes[1])
    confirm_timestamp = confirm_frame.time

    event = Event(event_base, next_id, register_timestamp, confirm_timestamp, description)
    next_id += 1

    return Alarm(event, criticality)


def check_conds(td: TelemetryData, tag: Tag, condition: Callable,
                comparison: ParameterValue) -> (list[tuple[bool, datetime]], list[int]):
    """
    Checks all telemetry frames in <td> where <condition> returns true
    Note: This should only be used for conditions where only 1 tag is relevant

    :param tag: The tag to use for checking conditions
    :param td: Contains all telemetry frames to examine
    :param condition: A function that returns a boolean with parameters
                      (ParameterValue, ParameterValue
    :param comparison: A list of all ParameterValues to be used as a point of comparison
    :return: A list where each index i refers to the i-th telemetry frame in TelemetryData,
    the boolean in the tuple refers to the associated return from <condition>, and the datetime
    refers to the associated time of the telemetry frame, and a list of indexes where the condition
    was False. Also returns a list of indexes where conditions where not mot
    """
    cond_met = []
    false_index = []
    num_frames = td.num_telemetry_frames
    for i in range(num_frames):
        telemetry_frame = td.get_telemetry_frame(i)
        telemetry_time = telemetry_frame.time

        tag_values = td.get_parameter_values(tag)
        raw_parameter_value = tag_values[telemetry_time]
        cond_frame_met = condition(raw_parameter_value, comparison)

        cond_met.append((cond_frame_met, telemetry_time))
        if not cond_frame_met:
            false_index.append(i)
    return cond_met, false_index


def find_alarm_indexes(first_indexes: list[int],
                       alarm_conditions: list[tuple[bool, datetime]]) -> list[bool]:
    """
    Finds the telemetry frames where an alarm is considered active

    :param first_indexes: A list of all first indexes where an alarm condition becomes active
    :param alarm_conditions: A list of booleans where each i-th element represents that the
    i-th telemetry has met alarm conditions
    :return: A list of i booleans where the i-th boolean indicates if the associated telemetry
    frame has an alarm condition active
    """
    alarm_active = []
    alarm_considered = False
    for i in range(len(alarm_conditions)):
        if i in first_indexes:
            alarm_considered = True

        if alarm_considered and alarm_conditions[i][0]:
            alarm_active.append(True)
        else:
            alarm_active.append(False)
    return alarm_active


def find_confirm_time(tuples: list[tuple[bool, datetime]], persistence: float) -> int:
    """
    Finds the first time when the persistence duration has been met

    :param tuples: Contains tuples indicating whether an alarm condition was
    met, and the time associated with the telemetry frame
    :param persistence: How much time in seconds the alarm condition must be met for
    :return: The first index where the persistence timeframe had been met

    PRECONDITION: The last time in <tuples> is >= the exact time the persistence duration was met
    """
    best_index = len(tuples) - 1
    exact_confirm_time = tuples[0][1] + timedelta(seconds=persistence)
    for i in range(1, len(tuples)):
        index = -i
        if tuples[i][1] < exact_confirm_time:
            return best_index
        best_index = len(tuples) - i
    return best_index


def persistence_check(tuples: list[tuple[bool, datetime]], persistence: float,
                      false_indexes: list[int]) -> list[tuple[int, int]]:
    """
    Checks if there exists any sequence of booleans amongst tuples in <tuples>
    where all booleans are true and associated datetimes are every datetime in
    <tuples> within the range of (first datetime in the sequence + persistence seconds)
    
    :param tuples: Contains tuples indicating whether an alarm condition was
    met, and the time associated with the telemetry frame 
    :param persistence: How much time in seconds the alarm condition must be met for
    :param false_indexes: Lists all indexes in <tuples> where the first element is false
    :return: The first index in the all sequences satisfying the persistence check, and the
    last index in all sequences satisfying the check. Returns [] if no such sequence exists
    
    PRECONDITION: <tuples> is sorted by ascending datetime, and indexes in <false_indexes>
    are listed iff the associated tuple in <tuples> stores false
    """

    times = []
    if len(false_indexes) == 0:
        # Indicates that we have all trues, hence we only need to check if the period of time
        # is long enough
        first_time = tuples[0][1]
        last_time = tuples[len(tuples) - 1][1]
        if last_time - first_time >= timedelta(seconds=persistence):
            register_time = find_confirm_time(tuples, persistence)
            times.append((0, register_time))
    else:
        times = []
        for i in range(len(false_indexes) + 1):
            if i == 0:
                # checking the start of the list to the first false
                first_index = 0
                last_index = false_indexes[0] - 1
            elif i == len(false_indexes):
                # checking the last false to the end of the list
                first_index = false_indexes[i - 1] + 1
                last_index = len(tuples) - 1
            else:
                # checking between false occurrences
                first_index = false_indexes[i - 1] + 1
                last_index = false_indexes[i] - 1

            if first_index <= last_index:
                first_time = tuples[first_index][1]
                last_time = tuples[last_index][1]
                if last_time - first_time >= timedelta(seconds=persistence):
                    register_time = find_confirm_time(tuples[first_index:last_index + 1], persistence) + first_index
                    times.append((first_index, register_time))
    return times


def rate_of_change_check(dm: DataManager, alarm_base: RateOfChangeEventBase,
                         criticality: AlarmCriticality, earliest_time: datetime) \
        -> (list[Alarm], list[tuple[datetime, bool]]):
    ...


def repeat_checker(td: TelemetryData, tag: Tag) -> tuple[list[tuple[bool, datetime]], list[int]]:
    """
    Checks all the frames in <td> and returns a list of tuples where each tuple 
    contains a boolean indicating if the value of <tag> is the same as the previous
    frame, and the datetime associated with the frame.

    :param tag:
    :param td: The relevant telemetry data to check.
    :return: A list of tuples where each tuple contains a boolean indicating if the value of
    <tag> is the same as the previous frame, and the datetime associated with the frame.
    """

    num_frames = td.num_telemetry_frames
    sequences_of_static = []
    false_index = []

    # First frame is vacuously a sequence of static values
    sequences_of_static.append((True, td.get_telemetry_frame(0).time))

    # Iterate over each frame and add a true value to the list if the value is the same as the
    # previous one.
    tag_values = td.get_parameter_values(tag)
    for i in range(1, num_frames):
        if i == 1:
            prev_frame = td.get_telemetry_frame(i - 1)
            prev_frame_time = prev_frame.time
            last_value = tag_values[prev_frame_time]
        else:
            last_value = curr_value

        curr_frame = td.get_telemetry_frame(i)
        frame_time = curr_frame.time
        curr_value = tag_values[frame_time]

        if curr_value == last_value:
            sequences_of_static.append((True, curr_frame.time))
        else:
            sequences_of_static.append((False, curr_frame.time))
            false_index.append(i)

    return sequences_of_static, false_index


def static_check(dm: DataManager, alarm_base: StaticEventBase,
                 criticality: AlarmCriticality, earliest_time: datetime) \
        -> (list[Alarm], list[bool]):
    """
    Checks if in the telemetry frames with times in the range
    (<earliest_time> - <alarm_base.persistence> -> present), there exists
    a sequence lasting <alarm_base.persistence> seconds where <alarm_base.tag> reported
    the same value. Returns an appropriate Alarm if the check is satisfied

    :param dm: All data known to the program
    :param alarm_base: Stores all parties related to the check
    :param criticality: The base criticality of the alarm
    :param earliest_time: The earliest time from a set of the most recently added
    telemetry frames
    :return:  A list of all alarms that should be newly raised, and a list of bools
    where each index i represents that the associated telemetry frame has an alarm active
    """

    # Calculating the range of time that needs to be checked
    first_time, sequence = find_first_time(alarm_base, earliest_time)

    # Getting all Telemetry Frames associated with the relevant timeframe
    tag = alarm_base.tag
    telemetry_data = dm.get_telemetry_data(first_time, None, [tag])

    # Check which frames share the same value as the previous frame.
    cond_met, false_indexes = repeat_checker(telemetry_data, tag)

    alarm_indexes = persistence_check(cond_met, sequence, false_indexes)

    alarms = []
    first_indexes = []
    for index in alarm_indexes:
        first_indexes.append(index[0])
        description = "static alarm triggered"
        new_alarm = create_alarm(index, telemetry_data, description, alarm_base, criticality)
        alarms.append(new_alarm)

    alarm_frames = find_alarm_indexes(first_indexes, cond_met)
    return alarms, alarm_frames


def upper_threshold_cond(param_value: ParameterValue, upper_threshold: ParameterValue) -> bool:
    """checks if <param_value> is above the upper threshold

    :param param_value: The true value of the given parameter
    :param upper_threshold: TYhe upper threshold to compare against
    :return A boolean indicating if <param_value> exceeds the threshold
    """
    return param_value > upper_threshold


def lower_threshold_cond(param_value: ParameterValue, lower_threshold: ParameterValue) -> bool:
    """checks if <param_value> is below the lower threshold

    :param param_value: The true value of the given parameter
    :param lower_threshold: TYhe upper threshold to compare against
    :return A boolean indicating if <param_value> exceeds the threshold
    """
    return param_value < lower_threshold


def threshold_check(dm: DataManager, alarm_base: ThresholdEventBase,
                    criticality: AlarmCriticality, earliest_time: datetime) \
        -> (list[Alarm], list[bool]):
    """
    Checks if in the telemetry frames with times in the range
    (<earliest_time> - <alarm_base.persistence> -> present), there exists
    a sequence lasting <alarm_base.persistence> seconds where a) <alarm_base.tag>
    reported values above <alarm_base.upper_threshold> or b) <alarm_base.tag> reported
    values below <alarm)_base.lower_threshold>

    :param dm: All data known to the program
    :param alarm_base: Stores all parties related to the check
    :param criticality: The base criticality of the alarm
    :param earliest_time: The earliest time from a set of the most recently added
    telemetry frames
    :return: A list of all alarms that should be newly raised, and a list of bools
    where each index i represents that the associated telemetry frame has an alarm active
    """
    first_time, sequence = find_first_time(alarm_base, earliest_time)
    tag = alarm_base.tag
    telemetry_data = dm.get_telemetry_data(first_time, None, [tag])

    upper_threshold = alarm_base.upper_threshold
    lower_threshold = alarm_base.lower_threshold

    alarms = []
    lower_alarm_frames = []
    upper_alarm_frames = []
    if lower_threshold is not None:
        # Checking + generating all alarms for crossing the lower threshold
        lower_cond_met, lower_false_indexes = check_conds(telemetry_data, tag, setpoint_cond,
                                                          upper_threshold)
        lower_alarm_indexes = persistence_check(lower_cond_met, sequence, lower_false_indexes)
        lower_first_indexes = []
        for alarm_index in lower_alarm_indexes:
            lower_first_indexes.append(alarm_index[0])
            description = "lower threshold crossed"
            new_alarm = create_alarm(alarm_index, telemetry_data, description, alarm_base, criticality)
            alarms.append(new_alarm)
        lower_alarm_frames = find_alarm_indexes(lower_first_indexes, lower_cond_met)
    if upper_threshold is not None:
        # Checking + generating all alarms for crossing the upper threshold
        upper_cond_met, upper_false_indexes = check_conds(telemetry_data, tag, setpoint_cond,
                                                          lower_threshold)
        upper_alarm_indexes = persistence_check(upper_cond_met, sequence, upper_false_indexes)
        upper_first_indexes = []
        for alarm_index in upper_alarm_indexes:
            upper_first_indexes.append(alarm_index[0])
            description = "upper threshold crossed"
            new_alarm = create_alarm(alarm_index, telemetry_data, description, alarm_base, criticality)
            alarms.append(new_alarm)
        upper_alarm_frames = find_alarm_indexes(upper_first_indexes, upper_cond_met)

    # combining all results
    all_alarm_frames = []
    for i in range(len(lower_alarm_frames)):
        all_alarm_frames.append(lower_alarm_frames[i] or upper_alarm_frames[i])
    return alarms, all_alarm_frames


def setpoint_cond(param_value: ParameterValue, setpoint: ParameterValue) -> bool:
    """
    Checks if param_value is at it's associated setpoint exactly

    :param param_value: The true value of the given parameter
    :param setpoint: The setpoint value to compare against
    :return: A boolean indicating if param_value is at the setpoint
    """
    return param_value == setpoint[0]


def setpoint_check(dm: DataManager, alarm_base: SetpointEventBase,
                   criticality: AlarmCriticality, earliest_time: datetime) \
        -> (list[Alarm], list[bool]):
    """
    Checks if in the telemetry frames with times in the range
    (<earliest_time> - <alarm_base.persistence> -> present), there exists
    a sequence lasting <alarm_base.persistence> seconds where <alarm_base.tag> reported
    its setpoint value. Returns an appropriate Alarm if the check is satisfied

    :param dm: All data known to the program
    :param alarm_base: Stores all parties related to the check
    :param criticality: The base criticality of the alarm
    :param earliest_time: The earliest time from a set of the most recently added
    telemetry frames
    :return: A list of all alarms that should be newly raised, and a list of bools
    where each index i represents that the associated telemetry frame has an alarm active
    """

    first_time, sequence = find_first_time(alarm_base, earliest_time)
    tag = alarm_base.tag
    telemetry_data = dm.get_telemetry_data(first_time, None, [tag])

    setpoint = alarm_base.setpoint

    # Checking which frames have tag values at setpoint and indicating it in <cond_met> in order
    cond_met, false_indexes = check_conds(telemetry_data, tag, setpoint_cond, setpoint)

    alarm_indexes = persistence_check(cond_met, sequence, false_indexes)

    first_indexes = []
    alarms = []
    for alarm_index in alarm_indexes:
        first_indexes.append(alarm_index[0])
        description = "setpoint value recorded"
        new_alarm = create_alarm(alarm_index, telemetry_data, description, alarm_base, criticality)
        alarms.append(new_alarm)

    alarm_frames = find_alarm_indexes(first_indexes, cond_met)
    return alarms, alarm_frames


def sequence_of_events_check(dm: DataManager, alarm_base: SOEEventBase,
                             criticality: AlarmCriticality, earliest_time: datetime) \
        -> (list[Alarm], list[bool]):
    ...


def all_events_check(dm: DataManager, alarm_base: AllEventBase,
                     criticality: AlarmCriticality, earliest_time: datetime) \
        -> (list[Alarm], list[bool]):
    """
    Checks that all event bases in <alarm_base> have occurred, and returns appropriate
    Alarms, and a list of bools where each index i represents that the associated telemetry
    frame has an alarm active

    :param dm: The source of all data known to the program
    :param alarm_base: Defines events to check
    :param criticality: default criticality for the alarm base
    :param earliest_time: The earliest time from a set of the most recently added
    telemetry frames
    :return: An Alarm containing all data about the recent event, or None if the check
    is not satisfied
    """
    first_time, sequence = find_first_time(alarm_base, earliest_time)
    possible_events = alarm_base.event_bases
    telemetry_data = dm.get_telemetry_data(first_time, None, dm.tags)

    # iterate through each of the eventbases and get their list indicating where alarm conditions where met
    inner_alarm_indexes = []
    for possible_event in possible_events:
        strategy = get_strategy(possible_event)
        alarm, alarm_indexes = strategy(dm, possible_event, criticality, earliest_time)
        inner_alarm_indexes.append(alarm_indexes)

    # now, iterate through the all previous lists and find where alarms were unanimously raised
    conds_met = []
    false_indexes = []
    for i in range(len(inner_alarm_indexes[0])):
        telemetry_frame = telemetry_data.get_telemetry_frame(i)
        telemetry_time = telemetry_frame.time
        frame_meets_condition = True
        for j in range(len(inner_alarm_indexes)):
            frame_meets_condition = frame_meets_condition and inner_alarm_indexes[j][i]
        conds_met.append((frame_meets_condition, telemetry_time))
        if not frame_meets_condition:
            false_indexes.append(i)

    # create the appropriate alarms
    alarm_indexes = persistence_check(conds_met, sequence, false_indexes)
    alarms = []
    first_indexes = []
    for alarm_index in alarm_indexes:
        first_indexes.append(alarm_index[0])
        description = 'All events were triggered.'
        new_alarm = create_alarm(alarm_index, telemetry_data, description, alarm_base, criticality)
        alarms.append(new_alarm)
    alarm_frames = find_alarm_indexes(first_indexes, conds_met)
    return alarms, alarm_frames


def any_events_check(dm: DataManager, alarm_base: AnyEventBase,
                     criticality: AlarmCriticality, new_id: int,
                     earliest_time: datetime) -> (list[Alarm], list[bool]):
    """
    Checks that any of the event bases in <alarm_base> occurred, and returns a appropraite alarms,
    and a list of bools where each index i represents that the associated telemetry
    frame has an alarm active

    :param dm: The source of all data known to the program
    :param alarm_base: Defines events to check
    :param criticality: default criticality for the alarm base
    :param new_id: the id to assign a potential new alarm
    :param earliest_time: The earliest time from a set of the most recently added
    telemetry frames
    :return: An Alarm containing all data about the recent event, or None if the check
    is not satisfied
    """

    first_time, sequence = find_first_time(alarm_base, earliest_time)
    possible_events = alarm_base.event_bases
    telemetry_data = dm.get_telemetry_data(first_time, None, dm.tags)

    inner_alarm_indexes = []
    for possible_event in possible_events:
        strategy = get_strategy(possible_event)
        alarm, alarm_indexes = strategy(dm, possible_event, criticality, earliest_time)
        inner_alarm_indexes.append(alarm_indexes)

    # now, iterate through the all previous lists and find where any alarms was unanimously raised
    conds_met = []
    false_indexes = []
    for i in range(len(inner_alarm_indexes[0])):
        telemetry_frame = telemetry_data.get_telemetry_frame(i)
        telemetry_time = telemetry_frame.time
        frame_meets_condition = False
        for j in range(len(inner_alarm_indexes)):
            frame_meets_condition = frame_meets_condition or inner_alarm_indexes[j][i]
        conds_met.append((frame_meets_condition, telemetry_time))
        if not frame_meets_condition:
            false_indexes.append(i)

    # create the appropriate alarms
    alarm_indexes = persistence_check(conds_met, sequence, false_indexes)
    alarms = []
    first_indexes = []
    for alarm_index in alarm_indexes:
        first_indexes.append(alarm_index[0])
        description = 'Any events was triggered.'
        new_alarm = create_alarm(alarm_index, telemetry_data, description, alarm_base, criticality)
        alarms.append(new_alarm)
    alarm_frames = find_alarm_indexes(first_indexes, conds_met)
    return alarms, alarm_frames
