from itertools import pairwise
from astra.data.alarms import (EventID, Alarm, EventBase, RateOfChangeEventBase,
                               StaticEventBase, ThresholdEventBase, SetpointEventBase,
                               SOEEventBase, AllEventBase, AlarmCriticality, Event, AnyEventBase)
from astra.data.data_manager import DataManager
from typing import Callable, Mapping
from astra.data.parameters import Tag, ParameterValue
from astra.data.telemetry_data import TelemetryData
from datetime import timedelta, datetime

UNACKNOWLEDGED = True
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


def find_first_time(alarm_base: EventBase, earliest_time: datetime) -> tuple[datetime, float]:
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


def create_alarm(alarm_indexes: tuple[int, int], times: list[datetime],
                 event_base: EventBase,
                 criticality: AlarmCriticality) -> Alarm:
    """
    Uses information on telemetry indexes to create an appropriate alarm

    :param alarm_indexes: A tuple listing the index where an alarm condition is first met,
    and another listing the first where the persistence time check is met
    :param times: Lists in order the time of the i-th telemetry frame to be examined
    :param description: Describes information about the event
    :param event_base: The underlying type of alarm that occured
    :param criticality: The base importance of the alarm
    :return: An alarm detailing a certain event that has occured
    """
    global next_id

    register_timestamp = times[alarm_indexes[0]]

    confirm_timestamp = times[alarm_indexes[1]]

    event = Event(event_base, next_id, register_timestamp, confirm_timestamp, datetime.now(),
                  event_base.description)
    next_id += 1

    # Note: priority needs to be determined externally, so we temporarily set it to provided
    # criticality
    return Alarm(event, criticality, criticality, UNACKNOWLEDGED)


def check_conds(td: TelemetryData, tag: Tag, condition: Callable,
                comparison: ParameterValue, persistence: float) -> (
        tuple)[list[tuple[int, int]], list[bool]]:
    """
    Checks all telemetry frames in <td> where <condition> returns true
    Note: This should only be used for conditions where only 1 tag is relevant

    :param tag: The tag to use for checking conditions
    :param td: Contains all telemetry frames to examine
    :param condition: A function that returns a boolean with parameters
                      (ParameterValue, ParameterValue
    :param comparison: ParameterValues to be used as a point of comparison
    :param persistence: How long the condition has to last
    :return: A list of tuples where the first tuple element is the index of telemetry frame where
    an alarm was registered, and the second is the index of telemetry frame where the alarm was
    confirmed. Also returns a list of booleans where each index i refers to whether or not the
    i-th frame of <td> had an active alarm.
    """
    alarm_data = []
    alarm_indices = []
    tag_values = td.get_parameter_values(tag)
    all_times = tag_values.keys()

    # tracking variables for the proceeding loop
    required_time = datetime.now()
    active_sequence = False
    confirmed_alarm = False
    curr_first_index = -1
    i = 0

    # Iterate through all frames and keep track of if an active sequence of alarm conditions
    # being met is occuring
    for telemetry_time in all_times:
        raw_parameter_value = tag_values[telemetry_time]
        cond_frame_met = condition(raw_parameter_value, comparison)

        # First time we see true after a false
        if cond_frame_met and not active_sequence:
            active_sequence = True
            required_time = telemetry_time + timedelta(seconds=persistence)
            curr_first_index = i

        # First frame that satisfies the persistence check
        if cond_frame_met and telemetry_time >= required_time:
            if not confirmed_alarm:
                confirmed_alarm = True
                alarm_data.append((curr_first_index, i))

        if not cond_frame_met:
            if confirmed_alarm:
                true_indices = [True] * (i - curr_first_index)
                alarm_indices += true_indices
                confirmed_alarm = False
                active_sequence = False
            elif active_sequence:
                false_indices = [False] * (i - curr_first_index)
                alarm_indices += false_indices
                active_sequence = False
            alarm_indices.append(False)
        i += 1

    if confirmed_alarm:
        true_indices = [True] * (i - curr_first_index)
        alarm_indices += true_indices
    elif active_sequence:
        false_indices = [False] * (i - curr_first_index)
        alarm_indices += false_indices

    return alarm_data, alarm_indices


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
        if tuples[index][1] < exact_confirm_time:
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
    if len(false_indexes) == 0 and len(tuples) > 0:
        # Indicates that we have all trues, hence we only need to check if the period of time
        # is long enough
        first_time = tuples[0][1]
        last_time = tuples[len(tuples) - 1][1]
        if last_time - first_time >= timedelta(seconds=persistence):
            register_time = find_confirm_time(tuples, persistence)
            times.append((0, register_time))
    elif len(false_indexes) > 0:
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
                    register_time = find_confirm_time(tuples[first_index:last_index + 1],
                                                      persistence) + first_index
                    times.append((first_index, register_time))
    return times


def roc_from_time_check(data: Mapping[datetime, ParameterValue | None], times: list[datetime],
                        start_date: datetime, time_window: float) -> float:
    """
    Gets the rate of change of the tag within the <td> from <start_date> to <end_date>.

    :param data: The data to check
    :param times: The times associated with <data> (its keys)
    :param start_date: The start date to check from
    :param end_date: The end date to check to
    :return: The rate of change of the tag within the <td> from <start_date> to <end_date>.

    PRECONDITION: <start_date> is in <times> and <times> are the keys of <data>.
    """
    end_date = start_date + timedelta(seconds=time_window)
    curr_index = times.index(start_date)
    initial_index = curr_index
    curr_time = start_date
    total = 0.0

    # Loop until we find the last time in the time window, while summing up the values.
    while (curr_index < len(times)) and (end_date >= times[curr_index]):
        curr_time = times[curr_index]
        curr_value = data[curr_time]
        if curr_value is None:
            total += 0.0
        else:
            total += curr_value

        curr_index += 1

    # If loop ended with <curr_time> as the same as <start_date>, then we have roc = 0.0
    if curr_time == start_date:
        return 0.0

    # otherwise we have the n-point running average.
    roc = total / (curr_index - initial_index)

    return roc


def rate_of_change_check(dm: DataManager, alarm_base: RateOfChangeEventBase,
                         criticality: AlarmCriticality, earliest_time: datetime,
                         compound: bool) -> tuple[list[Alarm], list[bool]]:
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
    :param compound: If this algorithm is being called as part of a compound alarm
    :return:  A list of bools where each index i represents that the associated telemetry frame
    has an alarm active.
    """

    # Calculating the range of time that needs to be checked
    first_time, sequence = find_first_time(alarm_base, earliest_time)

    # Getting all the values relevant to this alarm.
    tag = alarm_base.tag
    telemetry_data = dm.get_telemetry_data(first_time, None, [tag])
    tag_values = telemetry_data.get_parameter_values(tag)
    times = list(tag_values.keys())

    rate_of_rise_threshold = alarm_base.rate_of_rise_threshold
    rate_of_fall_threshold = alarm_base.rate_of_fall_threshold

    # A list of 1s, -1s, and 0s, where 1 indicates a rate of rise alarm, -1 indicates a rate of
    # fall alarm, and 0 indicates no alarm.
    rising_or_falling_list = []

    curr_roc = 0.0
    # Calculate the rate of change for each time window, and add the appropriate
    # number to the list.
    for start_date in times:

        curr_roc = roc_from_time_check(tag_values, times, start_date, alarm_base.time_window)

        if (rate_of_rise_threshold is not None) and (curr_roc > rate_of_rise_threshold):
            rising_or_falling_list.append(1)
        elif (rate_of_fall_threshold is not None) and (-1 * curr_roc > rate_of_fall_threshold):
            rising_or_falling_list.append(-1)
        else:
            rising_or_falling_list.append(0)

    # Now I will create one list for rising and falling alarms, and
    # check for persistence.
    rising_alarm_indexes = []
    rising_false_indexes = []
    falling_alarm_indexes = []
    falling_false_indexes = []
    all_alarm_frames = []
    for i in range(len(rising_or_falling_list)):

        # Determine which alarm was raised, and set the appropriate
        # index to True and the other to False. Then we can check for persistence.
        if rising_or_falling_list[i] == 1:
            rising_alarm_indexes.append((True, times[i]))
            falling_alarm_indexes.append((False, times[i]))
            falling_false_indexes.append(i)
            all_alarm_frames.append(True)

        elif rising_or_falling_list[i] == -1:
            falling_alarm_indexes.append((True, times[i]))
            rising_alarm_indexes.append((False, times[i]))
            rising_false_indexes.append(i)
            all_alarm_frames.append(True)
        else:  # in this case, the value in the list was a 0, so no alarm was raised.
            rising_alarm_indexes.append((False, times[i]))
            falling_alarm_indexes.append((False, times[i]))
            rising_false_indexes.append(i)
            falling_false_indexes.append(i)
            all_alarm_frames.append(False)

    rising_persistence = persistence_check(rising_alarm_indexes, sequence, rising_false_indexes)
    falling_persistence = persistence_check(falling_alarm_indexes, sequence, falling_false_indexes)
    alarms = []

    for index in rising_persistence:
        new_alarm = create_alarm(index, times, alarm_base, criticality)
        alarms.append(new_alarm)

    for index in falling_persistence:
        new_alarm = create_alarm(index, times, alarm_base, criticality)
        alarms.append(new_alarm)

    if not compound:
        dm.add_alarms(alarms)
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

    if td.num_telemetry_frames == 0:
        return [], []
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
            false_indices.append(len(sequences_of_static) - 1)

    return sequences_of_static, false_indices


def static_check(dm: DataManager, alarm_base: StaticEventBase,
                 criticality: AlarmCriticality, earliest_time: datetime,
                 compound: bool) -> list[bool]:
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
    :param compound: If this algorithm is being called as part of a compound alarm
    :return:  A list of all alarms that should be newly raised, and a list of bools
    where each index i represents that the associated telemetry frame has an alarm active
    """

    # Calculating the range of time that needs to be checked
    first_time, sequence = find_first_time(alarm_base, earliest_time)

    # Getting all Telemetry Frames associated with the relevant timeframe
    tag = alarm_base.tag
    telemetry_data = dm.get_telemetry_data(first_time, None, [tag])
    times = list(telemetry_data.get_parameter_values(tag).keys())

    # Check which frames share the same value as the previous frame.
    cond_met, false_indexes = repeat_checker(telemetry_data, tag)

    alarm_indexes = persistence_check(cond_met, sequence, false_indexes)

    alarms = []
    first_indexes = []
    for index in alarm_indexes:
        first_indexes.append(index[0])
        new_alarm = create_alarm(index, times, alarm_base, criticality)
        alarms.append(new_alarm)

    alarm_frames = find_alarm_indexes(first_indexes, cond_met)
    if not compound:
        dm.add_alarms(alarms)
    return alarm_frames


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
                    criticality: AlarmCriticality, earliest_time: datetime,
                    compound: bool) -> list[bool]:
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
    :param all_alarms: Container for the list of all alarms
    :param compound: If this algorithm is being called as part of a compound alarm
    :return: A list of all alarms that should be newly raised, and a list of bools
    where each index i represents that the associated telemetry frame has an alarm active
    """
    first_time, sequence = find_first_time(alarm_base, earliest_time)
    tag = alarm_base.tag
    telemetry_data = dm.get_telemetry_data(first_time, None, [tag])

    upper_threshold = alarm_base.upper_threshold
    lower_threshold = alarm_base.lower_threshold

    alarms = []
    times = list(telemetry_data.get_parameter_values(tag).keys())
    all_alarm_frames = []
    if lower_threshold is not None:
        # Checking + generating all alarms for crossing the lower threshold
        lower_alarms, lower_alarm_frames = check_conds(telemetry_data, tag, lower_threshold_cond,
                                                       lower_threshold, sequence)
        lower_first_indexes = []
        for alarm in lower_alarms:
            lower_first_indexes.append(alarm[0])
            new_alarm = create_alarm(alarm, times, alarm_base, criticality)
            alarms.append(new_alarm)

        all_alarm_frames = lower_alarm_frames
    if upper_threshold is not None:
        # Checking + generating all alarms for crossing the upper threshold
        upper_alarms, upper_alarm_frames = check_conds(telemetry_data, tag, upper_threshold_cond,
                                                       upper_threshold, sequence)
        upper_first_indexes = []
        for alarm in upper_alarms:
            upper_first_indexes.append(alarm[0])
            new_alarm = create_alarm(alarm, times, alarm_base, criticality)
            alarms.append(new_alarm)

        # combining all results
        if lower_threshold is not None:
            for i in range(telemetry_data.num_telemetry_frames):
                all_alarm_frames[i] = all_alarm_frames[i] or upper_alarm_frames[i]
        else:
            all_alarm_frames = upper_alarm_frames

        if not compound:
            dm.add_alarms(alarms)
        return all_alarm_frames


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
                   criticality: AlarmCriticality, earliest_time: datetime,
                   compound: bool) -> list[bool]:
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
    :param compound: If this algorithm is being called as part of a compound alarm
    :return: A list of all alarms that should be newly raised, and a list of bools
    where each index i represents that the associated telemetry frame has an alarm active
    """

    first_time, sequence = find_first_time(alarm_base, earliest_time)
    tag = alarm_base.tag
    telemetry_data = dm.get_telemetry_data(first_time, None, [tag])
    times = list(telemetry_data.get_parameter_values(tag).keys())

    setpoint = alarm_base.setpoint

    # Checking which frames have tag values at setpoint and indicating it in <cond_met> in order
    new_alarms, alarm_frames = check_conds(telemetry_data, tag, setpoint_cond, setpoint, sequence)

    # first_indexes = []
    alarms = []
    for alarm in new_alarms:
        # first_indexes.append(alarms[0])
        new_alarm = create_alarm(alarm, times, alarm_base, criticality)
        alarms.append(new_alarm)

    if not compound:
        dm.add_alarms(alarms)
    return alarm_frames


def sequence_of_events_check(dm: DataManager, alarm_base: SOEEventBase,
                             criticality: AlarmCriticality, earliest_time: datetime,
                             compound: bool) -> list[bool]:
    """
    Checks that the alarms described in <alarm_base> were all raised and persisted,
    and occured within the appropriate time window in correct sequential order.

    :param dm: The source of all data known to the program
    :param alarm_base: Defines events to check
    :param criticality: default criticality for the alarm base
    :param earliest_time: The earliest time from a set of the most recently added
    telemetry frames
    :param compound: If this algorithm is being called as part of a compound alarm
    :return: A list of all alarms that should be newly raised, and a list of bools
    where each index i represents that the associated telemetry frame has an alarm active
    """
    first_time, sequence = find_first_time(alarm_base, earliest_time)
    possible_events = alarm_base.event_bases
    telemetry_data = dm.get_telemetry_data(first_time, None, dm.tags)
    return [False] * telemetry_data.num_telemetry_frames

    all_tags = dm.tags
    for tag in all_tags:
        any_tag = tag
        break
    times = list(telemetry_data.get_parameter_values(any_tag).keys())

    # iterate through each of the eventbases and get their list indicating where alarm conditions
    # where met
    inner_alarm_indexes = []
    alarm_indexes = []
    for possible_event in possible_events:
        strategy = get_strategy(possible_event)
        alarm_indexes = strategy(dm, possible_event, criticality, earliest_time, True)

        # checking persistence on each alarm raised
        false_indexes = []
        frame_conditions = []
        for i in range(0, len(alarm_indexes)):
            associated_time = times[i]
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
            upper_interval = None

        if not inner_alarm_indexes[i]:
            break
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
                if (associated_time < minimum_time or (
                        maximum_time is not None and associated_time > maximum_time)):
                    pruned_indexes.append(second_event_index)

            for index in pruned_indexes:
                inner_alarm_indexes[i + 1].remove(index)

    active_indexes = [False] * telemetry_data.num_telemetry_frames
    alarms = []
    if inner_alarm_indexes[len(inner_alarm_indexes) - 1]:
        # Indicates that at the last chain of events, we had an unpruned alarm, meaning a
        # sequence occurred

        # for now, i assume that a chain of events can only occur once
        first_index = inner_alarm_indexes[0][0][0]
        last_alarm_type_index = len(inner_alarm_indexes) - 1
        last_index = inner_alarm_indexes[last_alarm_type_index][
            len(inner_alarm_indexes[last_alarm_type_index])][1]
        for i in range(0, len(alarm_indexes)):
            if i < first_index or i > last_index:
                active_indexes.append(False)
            else:
                active_indexes.append(True)
        new_alarm = create_alarm((last_index, last_index), times,
                                 alarm_base, criticality)
        alarms = [new_alarm]
    if not compound:
        dm.add_alarms(alarms)
    return active_indexes


def all_events_check(dm: DataManager, alarm_base: AllEventBase,
                     criticality: AlarmCriticality, earliest_time: datetime,
                     compound: bool) -> list[bool]:
    """
    Checks that all event bases in <alarm_base> have occurred, and returns appropriate
    Alarms, and a list of bools where each index i represents that the associated telemetry
    frame has an alarm active

    :param dm: The source of all data known to the program
    :param alarm_base: Defines events to check
    :param criticality: default criticality for the alarm base
    :param earliest_time: The earliest time from a set of the most recently added
    telemetry frames
    :param compound: If this algorithm is being called as part of a compound alarm
    :return: A list of all alarms that should be newly raised, and a list of bools
    where each index i represents that the associated telemetry frame has an alarm active
    """
    first_time, sequence = find_first_time(alarm_base, earliest_time)
    possible_events = alarm_base.event_bases
    telemetry_data = dm.get_telemetry_data(first_time, None, dm.tags)

    # iterate through each of the eventbases and get their list indicating where alarm conditions
    # where met
    inner_alarm_indexes = []
    for possible_event in possible_events:
        strategy = get_strategy(possible_event)
        alarm_indexes = strategy(dm, possible_event, criticality, earliest_time, True)
        inner_alarm_indexes.append(alarm_indexes)

    all_tags = dm.tags
    for tag in all_tags:
        any_tag = tag
        break
    times = list(telemetry_data.get_parameter_values(any_tag).keys())

    # now, iterate through the all previous lists and find where alarms were unanimously raised
    conds_met = []
    false_indexes = []
    for i in range(len(inner_alarm_indexes[0])):
        telemetry_time = times[i]
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
        new_alarm = create_alarm(alarm_index, times, alarm_base, criticality)
        alarms.append(new_alarm)
    alarm_frames = find_alarm_indexes(first_indexes, conds_met)
    if not compound:
        dm.add_alarms(alarms)
    return alarm_frames


def any_events_check(dm: DataManager, alarm_base: AnyEventBase,
                     criticality: AlarmCriticality, earliest_time: datetime,
                     compound: bool) -> list[bool]:
    """
    Checks that any of the event bases in <alarm_base> occurred, and returns a appropraite alarms,
    and a list of bools where each index i represents that the associated telemetry
    frame has an alarm active

    :param dm: The source of all data known to the program
    :param alarm_base: Defines events to check
    :param criticality: default criticality for the alarm base
    :param earliest_time: The earliest time from a set of the most recently added
    telemetry frames
    :param compound: If this algorithm is being called as part of a compound alarm
    :return: A list of all alarms that should be newly raised, and a list of bools
    where each index i represents that the associated telemetry frame has an alarm active
    """

    first_time, sequence = find_first_time(alarm_base, earliest_time)
    possible_events = alarm_base.event_bases
    telemetry_data = dm.get_telemetry_data(first_time, None, dm.tags)

    inner_alarm_indexes = []
    for possible_event in possible_events:
        strategy = get_strategy(possible_event)
        alarm_indexes = strategy(dm, possible_event, criticality, earliest_time, True)
        inner_alarm_indexes.append(alarm_indexes)

    all_tags = dm.tags
    for tag in all_tags:
        any_tag = tag
        break
    times = list(telemetry_data.get_parameter_values(any_tag).keys())

    # now, iterate through the all previous lists and find where any alarms was unanimously raised
    conds_met = []
    false_indexes = []
    for i in range(len(inner_alarm_indexes[0])):
        telemetry_time = times[i]
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
        new_alarm = create_alarm(alarm_index, times, alarm_base, criticality)
        alarms.append(new_alarm)
    alarm_frames = find_alarm_indexes(first_indexes, conds_met)
    if not compound:
        dm.add_alarms(alarms)
    return alarm_frames
