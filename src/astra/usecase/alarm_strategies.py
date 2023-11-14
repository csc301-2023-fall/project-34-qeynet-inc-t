import datetime
import math
from datetime import datetime, timedelta
from itertools import pairwise

from astra.data.alarms import *
from astra.data.data_manager import DataManager
from .utils import get_tag_param_value
from typing import Callable
from astra.data.telemetry_data import TelemetryData

UNACKNOWLEDGED = 'UA'
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

    return Alarm(event, criticality, UNACKNOWLEDGED)


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
    tag_values = td.get_parameter_values(tag)
    for i in range(num_frames):
        telemetry_frame = td.get_telemetry_frame(i)
        telemetry_time = telemetry_frame.time

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


def fall_threshold_check():
    """
    Returns a list of tuples, (bool, datetime), where the bool is
    True IFF the rate of change from the datetime until the <time_window> time
    is above the <rise_threshold>. It is false otherwise. There is one tuple
    for each time in <td>.
    It also returns a list of indices of the first list, where the bool is False.
    """
    pass


def rise_threshold_check():
    pass


def rate_of_change_check(dm: DataManager, alarm_base: RateOfChangeEventBase,
                         criticality: AlarmCriticality, earliest_time: datetime) \
        -> (list[Alarm], list[tuple[datetime, bool]]):
    """
    Checks if in the telemetry frames with times in the range
    (<earliest_time> - <alarm_base.persistence> -> present), there exists
    a sequence lasting <alarm_base.persistence> seconds where:
    a) <alarm_base.tag> reported a rate of change above <alarm_base.rate_of_rise_threshold>
    b) <alarm_base.tag> reported a rate of change below <alarm_base.rate_of_fall_threshold>
    Returns an appropriate Alarm if the check is satisfied

    :param dm: All data known to the program
    :param alarm_base: Stores all parties related to the check
    :param criticality: The base criticality of the alarm
    :param earliest_time: The earliest time from a set of the most recently added
    telemetry frames
    :return:  A list of all alarms that should be newly raised, and a list of bools
    where each index i represents that the associated telemetry frame has an alarm active.
    """
    # TODO figure out correct time window searching.
    # as in, if the window (frame 1) -> (time frame 1 + time_window) reaches a threshold rate of
    # change, then we consider it true on alarm conditions
    # and we just evaluate from endpoint to endpoint for the rate of change within the time window

    alarms = []
    # Calculating the range of time that needs to be checked
    first_time, sequence = find_first_time(alarm_base, earliest_time)

    # Getting all Telemetry Frames associated with the relevant timeframe
    tag = alarm_base.tag
    telemetry_data = dm.get_telemetry_data(first_time, None, [tag])

    # Check which indices satisfy the rate of rise threshold.
    if alarm_base.rate_of_rise_threshold is not None:
        rise_cond_met, rise_false_indices = rise_threshold_check(
            telemetry_data, tag, alarm_base.rate_of_rise_threshold, alarm_base.time_window)

        # check which sequences satisfy persistence
        rise_alarm_indices = persistence_check(rise_cond_met, sequence, rise_false_indices)

        # generate the alarms based on the given indices and add them to the return list
        rise_first_indices = []
        for alarm_index in rise_alarm_indices:
            rise_first_indices.append(alarm_index[0])
            description = "rise rate-of-change threshold crossed"
            new_alarm = create_alarm(alarm_index, telemetry_data,
                                     description, alarm_base, criticality)
            alarms.append(new_alarm)

        # Gets the indices of frames where the alarm is active
        rise_alarm_frames = find_alarm_indexes(rise_first_indices, rise_cond_met)

    # Check which indices satisfy the rate of fall threshold.
    if alarm_base.rate_of_fall_threshold is not None:
        fall_cond_met, fall_false_indices = fall_threshold_check(
            telemetry_data, tag, alarm_base.rate_of_fall_threshold)

        # check which sequences satisfy persistence
        fall_alarm_indices = persistence_check(fall_cond_met, sequence, fall_false_indices)

        # generate the alarms based on the given indices and add them to the return list
        fall_first_indices = []
        for alarm_index in fall_alarm_indices:
            fall_first_indices.append(alarm_index[0])
            description = "fall rate-of-change threshold crossed"
            new_alarm = create_alarm(alarm_index, telemetry_data,
                                     description, alarm_base, criticality)
            alarms.append(new_alarm)

        # Gets the indices of frames where the alarm is active
        fall_alarm_frames = find_alarm_indexes(fall_first_indices, fall_cond_met)

    # combining all results.
    # TODO: make sure this works.
    all_alarm_frames = []
    for i in range(len(fall_alarm_frames)):
        all_alarm_frames.append(fall_alarm_frames[i] or rise_alarm_frames[i])

    return alarms, all_alarm_frames


def repeat_checker(td: TelemetryData, tag: Tag) -> tuple[list[tuple[bool, datetime]], list[int]]:
    """
    Checks all the frames in <td> and returns a list of tuples where each tuple
    contains a boolean indicating if the value of <tag> is the same as the previous
    frame, and the datetime associated with the frame.

    :param tag: The tag to check the values of.
    :param td: The relevant telemetry data to check.
    :return: A list of tuples where each tuple contains a boolean indicating if the value of
    <tag> is the same as the previous frame, and the datetime associated with the frame.
    """

    sequences_of_static = []
    false_indices = []

    # First frame is vacuously a sequence of static values
    sequences_of_static.append((True, td.get_telemetry_frame(0).time))

    values_at_times = td.get_parameter_values(tag)
    # Iterate over each pair of timestamps and add a (True, datetime) to the list each time they
    # are the same or (False, datetime) when they aren't.
    for prev_time, curr_time in pairwise(values_at_times.keys()):
        prev_value = values_at_times[prev_time]
        curr_value = values_at_times[curr_time]

        # Determine if this frame held the same value as the last one
        if prev_value == curr_value:
            sequences_of_static.append((True, curr_time))
        else:
            sequences_of_static.append((False, curr_time))
            false_indices.append(len(sequences_of_static)-1)

    return sequences_of_static, false_indices


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
    if param_value is not None:
        return param_value > upper_threshold
    return False


def lower_threshold_cond(param_value: ParameterValue, lower_threshold: ParameterValue) -> bool:
    """checks if <param_value> is below the lower threshold

    :param param_value: The true value of the given parameter
    :param lower_threshold: TYhe upper threshold to compare against
    :return A boolean indicating if <param_value> exceeds the threshold
    """
    if param_value is not None:
        return param_value < lower_threshold
    return False


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
        lower_cond_met, lower_false_indexes = check_conds(telemetry_data, tag, lower_threshold_cond,
                                                          lower_threshold)
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
        upper_cond_met, upper_false_indexes = check_conds(telemetry_data, tag,
                                                          upper_threshold_cond, upper_threshold)
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
    if param_value is not None:
        return param_value == setpoint
    return False


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
    """
    Checks that the alarms described in <alarm_base> were all raised and persisted,
    and occured within the appropriate time window in correct sequential order.

    :param dm: The source of all data known to the program
    :param alarm_base: Defines events to check
    :param criticality: default criticality for the alarm base
    :param earliest_time: The earliest time from a set of the most recently added
    telemetry frames
    :return: A list of all alarms that should be newly raised, and a list of bools
    where each index i represents that the associated telemetry frame has an alarm active
    """
    first_time, sequence = find_first_time(alarm_base, earliest_time)
    possible_events = alarm_base.event_bases
    telemetry_data = dm.get_telemetry_data(first_time, None, dm.tags)

    # iterate through each of the eventbases and get their list indicating where alarm conditions where met
    inner_alarm_indexes = []
    alarm_indexes = []
    for possible_event in possible_events:
        strategy = get_strategy(possible_event)
        alarm, alarm_indexes = strategy(dm, possible_event, criticality, earliest_time)

        # checking persistence on each alarm raised
        false_indexes = []
        frame_conditions = []
        for i in range(0, len(alarm_indexes)):
            associated_frame = telemetry_data.get_telemetry_frame(i)
            associated_time = associated_frame.time
            if not alarm_indexes[i]:
                false_indexes.append(i)
            frame_conditions.append((alarm_indexes[i], associated_time))
        alarm_indexes = persistence_check(frame_conditions, sequence, false_indexes)
        inner_alarm_indexes.append(alarm_indexes)

    # Now, we go through each interval of times and check if the appropriate sequence occurred
    for i in range(0, len(alarm_base.intervals)):
        lower_interval = timedelta(seconds=alarm_base.intervals[i][0])
        if alarm_base.intervals[i][1] is not None:
            upper_interval = timedelta(seconds=alarm_base.intervals[i][1])
        else:
            upper_interval = math.inf
        for first_event_index in inner_alarm_indexes[i]:
            # getting the time interval a chain of events needs to occur in
            last_index = first_event_index[0]
            associated_frame = telemetry_data.get_telemetry_frame(last_index)
            minimum_time = associated_frame.time + lower_interval
            maximum_time = associated_frame.time + upper_interval
            pruned_indexes = []

            # Now, we go through all alarms raised of the next type and check if it happened in
            # the correct timeframe. If it didnt, prune it from the list of alarms to consider
            for second_event_index in inner_alarm_indexes[i + 1]:

                first_index = second_event_index[0]
                associated_time = telemetry_data.get_telemetry_frame(first_index).time
                if associated_time < minimum_time or associated_time > maximum_time:
                    pruned_indexes.append(second_event_index)

            for index in pruned_indexes:
                inner_alarm_indexes[i + 1].remove(index)

    active_indexes = [False] * (len(inner_alarm_indexes) - 1)
    alarms = []
    if inner_alarm_indexes[len(inner_alarm_indexes) - 1]:
        # Indicates that at the last chain of events, we had an unpruned alarm, meaning a
        # sequence occurred

        # for now, i assume that a chain of events can only occur once
        first_index = inner_alarm_indexes[0][0][0]
        last_alarm_type_index = len(inner_alarm_indexes) - 1
        last_index = inner_alarm_indexes[last_alarm_type_index][len(inner_alarm_indexes[
                                                                        last_alarm_type_index])][1]
        for i in range(0, len(alarm_indexes)):
            if i < first_index or i > last_index:
                active_indexes.append(False)
            else:
                active_indexes.append(True)
        new_alarm = create_alarm((last_index, last_index), telemetry_data,
                                 "Sequence of events:", alarm_base,
                                 criticality)
        alarms = [new_alarm]
    return alarms, active_indexes


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
    :return: A list of all alarms that should be newly raised, and a list of bools
    where each index i represents that the associated telemetry frame has an alarm active
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
    :return: A list of all alarms that should be newly raised, and a list of bools
    where each index i represents that the associated telemetry frame has an alarm active
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
