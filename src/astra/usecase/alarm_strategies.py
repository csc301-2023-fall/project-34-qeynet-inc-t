from itertools import pairwise
from math import inf
from threading import Condition

from astra.data.alarms import (EventID, Alarm, EventBase, RateOfChangeEventBase,
                               StaticEventBase, ThresholdEventBase, SetpointEventBase,
                               SOEEventBase, AllEventBase, AlarmCriticality, Event, AnyEventBase)
from astra.data.data_manager import DataManager
from typing import Callable, Mapping
from astra.data.parameters import Tag, ParameterValue
from astra.data.telemetry_data import TelemetryData
from datetime import timedelta, datetime

UNACKNOWLEDGED = False
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


def running_average_at_time(data: Mapping[datetime, ParameterValue | None], times: list[datetime],
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
                         compound: bool, cv: Condition) -> list[bool]:
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
    :param cv: Used to notify completion of this task
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

    curr_running_average = 0.0
    if len(times) > 0:
        prev_running_average = running_average_at_time(tag_values, times,
                                                       times[0], alarm_base.time_window)
    else:
        prev_running_average = 0.0
    # Calculate the rate of change for each time window, and add the appropriate
    # number to the list.
    for start_date in times[1:-1]:

        # ROC is found by subtracting the previous running average from the current one.
        curr_running_average = running_average_at_time(tag_values, times,
                                                       start_date, alarm_base.time_window)
        curr_roc = curr_running_average - prev_running_average

        if (rate_of_rise_threshold is not None) and (curr_roc > rate_of_rise_threshold):
            rising_or_falling_list.append(1)
        elif (rate_of_fall_threshold is not None) and (-1 * curr_roc > rate_of_fall_threshold):
            rising_or_falling_list.append(-1)
        else:
            rising_or_falling_list.append(0)

        prev_running_average = curr_running_average

    # Now we create one list for rising and for falling alarms, and check for persistence.
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

    # Now we create the appropriate alarms.
    for index in rising_persistence:
        new_alarm = create_alarm(index, times, alarm_base, criticality)
        alarms.append(new_alarm)

    for index in falling_persistence:
        new_alarm = create_alarm(index, times, alarm_base, criticality)
        alarms.append(new_alarm)

    if not compound:
        dm.add_alarms(alarms)

    with cv:
        cv.notify()
        return all_alarm_frames


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
                 compound: bool, cv: Condition) -> list[bool]:
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
    :param cv: Used to notify completion of this task
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

    with cv:
        cv.notify()
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
                    compound: bool, cv: Condition) -> list[bool]:
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
    :param cv: Used to notify completion of this task
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

        with cv:
            cv.notify()
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
                   compound: bool, cv: Condition) -> list[bool]:
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
    :param cv: Used to notify completion of this task
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

    with cv:
        cv.notify()
        return alarm_frames


def forward_checking_propagator(first_events: list[tuple[int, datetime]],
                                second_events: list[tuple[int, datetime]],
                                window_duration: tuple[float, float | None]) \
        -> list[tuple[int, datetime]]:
    """
    Returns a modification of <second_events> of elements where the datetime element occurs
    in a specified time windows

    :param first_events: The list of all events to check time windows after
    :param second_events: The list of all events to compare time window it started in
    :param window_duration: Specifies time windows that need to occur between events
    """
    satisfying_events = []
    for second_event in second_events:
        for first_event in first_events:
            lower_threshold = first_event[1] + timedelta(seconds=window_duration[0])
            if window_duration[1] is not None:
                upper_threshold = first_event[1] + timedelta(seconds=window_duration[1])
            else:
                # If upper threshold is None, we need a time that's guaranteed to be greater than
                # any second event time
                upper_threshold = first_events[-1][1] + timedelta(seconds=10)

            if lower_threshold < second_event[1] < upper_threshold:
                satisfying_events.append(second_event)
                break
    return satisfying_events


def get_smallest_domain(events: list[list[tuple[int, datetime]]]) -> int:
    """
    Returns the index of the event with the smallest remaining domain values

    :param events: A list of all events to check
    :return: The index of the event with the smallest domain
    """

    smallest_size = inf
    smallest_index = -1
    for i in range(len(events)):
        event = events[i]
        # Skipping already assigned events
        if type(event) is list:
            event_size = len(event)
            if event_size < smallest_size:
                smallest_size = event_size
                smallest_index = i
    return smallest_index


def backtracking_search(events: list[tuple[int, datetime] | list[tuple[int, datetime]]],
                        end_events: list[tuple[int, datetime] | list[tuple[int, datetime]]],
                        time_window: list[tuple[float, float | None]]) \
        -> list[int]:
    """
    Employs the backtracking search algorithm to find a sequence of events where each sequential
    event occurs within <time_window> of one another

    Note: the inputs should probably just be their own class, i'll make the change time permitting

    :param events: An ordered list of all events to check through
    :param end_events: A list of the last index an event
    occurred corresponding to each event in <events>
    :param time_window: The window of time where each sequential event must occur within
    :return: A list of the first and last index in the sequence of events
    """
    # Using the MRV heuristic to speed up the search
    chosen_domain = get_smallest_domain(events[:len(events) - 1])
    if chosen_domain == -1:
        # indicates solution was found
        return [events[0][0], end_events[-1][-1][0]]

    first_event = end_events[chosen_domain]
    second_event = events[chosen_domain + 1]

    events[chosen_domain + 1] = forward_checking_propagator(first_event, second_event,
                                                            time_window[chosen_domain])
    if not events[chosen_domain + 1]:
        return []
    else:
        new_events = events.copy()
        new_end_events = end_events.copy()
        for i in range(len(events[chosen_domain])):
            event = events[chosen_domain][i]
            new_events[chosen_domain] = event

            new_end_events[chosen_domain] = end_events[i]
            return backtracking_search(new_events, new_end_events, time_window)


def sequence_of_events_check(dm: DataManager, alarm_base: SOEEventBase,
                             criticality: AlarmCriticality, earliest_time: datetime,
                             compound: bool, cv: Condition) -> list[bool]:
    """
    Checks that the alarms described in <alarm_base> were all raised and persisted,
    and occured within the appropriate time window in correct sequential order.

    :param dm: The source of all data known to the program
    :param alarm_base: Defines events to check
    :param criticality: default criticality for the alarm base
    :param earliest_time: The earliest time from a set of the most recently added
    telemetry frames
    :param compound: If this algorithm is being called as part of a compound alarm
    :param cv: Used to notify completion of this task
    :return: A list of all alarms that should be newly raised, and a list of bools
    where each index i represents that the associated telemetry frame has an alarm active
    """
    first_time, sequence = find_first_time(alarm_base, earliest_time)
    possible_events = alarm_base.event_bases
    telemetry_data = dm.get_telemetry_data(first_time, None, dm.tags)

    # iterate through each of the eventbases and get their list indicating where alarm conditions
    # where met
    first_indexes = []
    last_indexes = []

    all_tags = dm.tags
    for tag in all_tags:
        any_tag = tag
        break
    times = list(telemetry_data.get_parameter_values(any_tag).keys())
    for possible_event in possible_events:
        strategy = get_strategy(possible_event)
        inner_alarm_indexes = strategy(dm, possible_event, criticality, earliest_time, True, Condition())

        if not inner_alarm_indexes:
            with cv:
                cv.notify()
                return [False] * len(times)

        # Cleansing the data to find all the first alarm indices and their associated timestamp
        inner_first_indexes = []
        inner_last_indexes = []
        active_alarm = False
        for i in range(len(inner_alarm_indexes)):
            if inner_alarm_indexes[i] and not active_alarm:
                inner_first_indexes.append((i, times[i]))
                active_alarm = True
            if not inner_alarm_indexes[i] and active_alarm:
                inner_last_indexes.append((i, times[i]))
                active_alarm = False

        if active_alarm:
            last_index = len(inner_alarm_indexes) - 1
            inner_last_indexes.append((last_index, times[last_index]))
        first_indexes.append(inner_first_indexes)
        last_indexes.append(inner_last_indexes)

    sequence_of_events = backtracking_search(first_indexes, last_indexes, alarm_base.intervals)

    if not sequence_of_events:
        with cv:
            cv.notify()
            return [False] * len(times)
    else:
        first_index = sequence_of_events[0]
        last_index = sequence_of_events[1]

        alarm_indexes = ([False] * first_index + [True] * (last_index - first_index) +
                         [False] * (len(times) - last_index - 1))

        new_alarm = create_alarm((first_index, last_index), times, alarm_base, criticality)

        if not compound:
            dm.add_alarms([new_alarm])

        with cv:
            cv.notify()
            return alarm_indexes


def all_events_check(dm: DataManager, alarm_base: AllEventBase,
                     criticality: AlarmCriticality, earliest_time: datetime,
                     compound: bool, cv: Condition) -> list[bool]:
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
    :param cv: Used to notify completion of this task
    :return: A list of all alarms that should be newly raised, and a list of bools
    where each index i represents that the associated telemetry frame has an alarm active
    """
    first_time, sequence = find_first_time(alarm_base, earliest_time)
    possible_events = alarm_base.event_bases
    telemetry_data = dm.get_telemetry_data(first_time, None, dm.tags)

    # iterate through each of the eventbases and get their list indicating where alarm conditions
    # where met

    alarm_indexes = []
    taken_indices = set()
    alarm_data = set()

    all_tags = dm.tags
    for tag in all_tags:
        any_tag = tag
        break
    times = list(telemetry_data.get_parameter_values(any_tag).keys())

    for possible_event in possible_events:
        strategy = get_strategy(possible_event)
        inner_alarm_indexes = strategy(dm, possible_event, criticality, earliest_time, True, Condition())

        if not alarm_indexes:
            alarm_indexes = inner_alarm_indexes
        # Check through returned indices to find where alarms should exist
        active_alarm = False

        for i in range(len(inner_alarm_indexes)):
            alarm_indexes[i] = alarm_indexes[i] and inner_alarm_indexes[i]
            if alarm_indexes[i]:
                # Verifying that we havent already indicated an alarm is active in this frame and
                # that not previously raised alarm overlaps with this one
                if not active_alarm and i not in taken_indices:
                    new_alarm_data = (i, i)
                    active_alarm = True
                    alarm_data.add(new_alarm_data)
                taken_indices.add(i)
            elif active_alarm:
                active_alarm = False

        if True not in alarm_indexes:
            return_val = [False] * len(inner_alarm_indexes)
            with cv:
                cv.notify()
                return return_val

    alarms = []
    for alarm in alarm_data:
        new_alarm = create_alarm(alarm, times, alarm_base, criticality)
        alarms.append(new_alarm)

    if not compound:
        dm.add_alarms(alarms)

    with cv:
        cv.notify()
        return alarm_indexes


def any_events_check(dm: DataManager, alarm_base: AnyEventBase,
                     criticality: AlarmCriticality, earliest_time: datetime,
                     compound: bool, cv: Condition) -> list[bool]:
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
    :param cv: Used to notify completion of this task
    :return: A list of all alarms that should be newly raised, and a list of bools
    where each index i represents that the associated telemetry frame has an alarm active
    """

    first_time, sequence = find_first_time(alarm_base, earliest_time)
    possible_events = alarm_base.event_bases
    telemetry_data = dm.get_telemetry_data(first_time, None, dm.tags)

    all_tags = dm.tags
    for tag in all_tags:
        any_tag = tag
        break
    times = list(telemetry_data.get_parameter_values(any_tag).keys())

    alarm_indexes = []
    taken_indices = set()
    alarm_data = set()
    for possible_event in possible_events:
        strategy = get_strategy(possible_event)
        inner_alarm_indexes = strategy(dm, possible_event, criticality, earliest_time, True, Condition())

        if not alarm_indexes:
            alarm_indexes = inner_alarm_indexes

        # Check through returned indices to find where alarms should exist
        active_alarm = False
        for i in range(len(inner_alarm_indexes)):
            alarm_indexes[i] = alarm_indexes[i] or inner_alarm_indexes[i]
            if inner_alarm_indexes[i]:
                # Verifying that we havent already indicated an alarm is active in this frame and
                # that not previously raised alarm overlaps with this one
                if not active_alarm and i not in taken_indices:
                    new_alarm_data = (i, i)
                    active_alarm = True
                    alarm_data.add(new_alarm_data)
                # If we already have an active alarm but an alarm is indicated for this frame
                # the existing one is superseded but the current one
                elif active_alarm and (i, i) in alarm_data:
                    alarm_data.remove((i, i))
                taken_indices.add(i)
            elif active_alarm:
                active_alarm = False

    alarms = []
    for alarm in alarm_data:
        new_alarm = create_alarm(alarm, times, alarm_base, criticality)
        alarms.append(new_alarm)

    if not compound:
        dm.add_alarms(alarms)

    with cv:
        cv.notify()
        return alarm_indexes
