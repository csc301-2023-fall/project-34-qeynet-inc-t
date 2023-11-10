import datetime
from datetime import datetime

from astra.data.alarms import *
from astra.data.data_manager import DataManager
from .alarm_checker import get_strategy
from .utils import eval_param_value, get_tag_param_value, get_tag_params
from typing import Callable, Iterable, Tuple, List
from astra.data.telemetry_data import TelemetryData

next_id = EventID(0)

# TODO: if alarm descriptions are "formulaic", extract helper method for making alarms from list


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
        subtract_time = datetime.timedelta(seconds=0)
        sequence = 0
    else:
        subtract_time = datetime.timedelta(seconds=alarm_base.persistence)
        sequence = alarm_base.persistence

    # Getting all Telemetry Frames associated with the relevant timeframe
    first_time = earliest_time - subtract_time
    return first_time, sequence


def create_alarm(event_base: EventBase, time: datetime, description: str,
                 criticality: AlarmCriticality) -> Alarm:
    """
    Creates and returns an Alarm with the given attributes.

    :param event_base: The event base for the alarm.
    :param time: The time at which the event occured.
    :param description: The description of the event that triggered the alarm.
    :param criticality: The criticality of this alarm.
    :return: An Alarm with the given attributes.
    """
    global next_id

    event = Event(event_base, next_id, time, description)
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

        # Note: I believe we don't need to convert to true value because both sides of
        # comparison would be applied the same transformation anyway
        raw_parameter_value = get_tag_param_value(i, tag, td)
        cond_frame_met = condition(raw_parameter_value, comparison)

        cond_met.append((cond_frame_met, telemetry_frame.time))
        if not cond_frame_met:
            false_index.append(i)
    return cond_met, false_index


def persistence_check(tuples: list[tuple[bool, datetime]], persistence,
                      false_indexes: list[int]) -> list[int]:
    """
    Checks if there exists any sequence of booleans amongst tuples in <tuples>
    where all booleans are true and associated datetimes are every datetime in
    <tuples> within the range of (first datetime in the sequence + persistence seconds)
    
    :param tuples: Contains tuples indicating whether an alarm condition was
    met, and the time associated with the telemetry frame 
    :param persistence: How much time in seconds the alarm condition must be met for
    :param false_indexes: Lists all indexes in <tuples> where the first element is false
    :return: The first index in the all sequences satisfying the persistence check. Returns
    -1 if no such sequence exists
    
    PRECONDITION: <tuples> is sorted by ascending datetime
    """
    if len(false_indexes) == 0:
        # Indicates that we have all trues, hence we only need to check if the period of time
        # is long enough
        first_time = tuples[0][1]
        last_time = tuples[len(tuples) - 1][1]
        if last_time - first_time >= persistence:
            return [0]
        return []
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

            if first_index < last_index:
                first_time = tuples[first_index][1]
                last_time = tuples[last_index][1]
                if last_time - first_time >= persistence:
                    times.append(first_index)
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
    i = 1

    # First frame is vacuously a sequence of static values
    sequences_of_static.append((True, td.get_telemetry_frame(0).time))

    # Iterate over each frame and add a true value to the list if the value is the same as the
    # previous one.
    for i in range(1, num_frames):
        curr_frame = td.get_telemetry_frame(i)
        curr_value = get_tag_param_value(i, tag, td)
        last_value = get_tag_param_value(i - 1, tag, td)

        if curr_value == last_value:
            sequences_of_static.append((True, curr_frame.time))
        else:
            sequences_of_static.append((False, curr_frame.time))
            false_index.append(i)

    return sequences_of_static, false_index


def static_check(dm: DataManager, alarm_base: StaticEventBase,
                 criticality: AlarmCriticality, earliest_time: datetime) \
        -> (list[Alarm], list[tuple[datetime, bool]]):
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
    :return:  A list of all alarms that should be newly raised, and tuple
    where each i-th element refers to the i-th telemetry frame in the appropriate
    timeframe, where the first element indicates if the alarm condition was met, and
    the second indicates the associated time
    """

    # Calculating the range of time that needs to be checked
    first_time, sequence = find_first_time(alarm_base, earliest_time)

    # Getting all Telemetry Frames associated with the relevant timeframe
    tag = alarm_base.tag
    telemetry_data = dm.get_telemetry_data(first_time, None, [tag])

    # Check which frames share the same value as the previous frame.
    cond_met, false_indexes = repeat_checker(telemetry_data, tag)

    alarm_indexes = persistence_check(cond_met, sequence, false_indexes)
    if not alarm_indexes:
        return [], cond_met
    alarms = []
    for index in alarm_indexes:
        relevant_frame = telemetry_data.get_telemetry_frame(index)
        timestamp = relevant_frame.time
        description = "static alarm triggered"
        new_alarm = create_alarm(alarm_base, timestamp, description, criticality)
        alarms.append(new_alarm)

    return alarms, cond_met


def threshold_check(dm: DataManager, alarm_base: ThresholdEventBase,
                    criticality: AlarmCriticality, earliest_time: datetime) \
        -> (list[Alarm], list[tuple[datetime, bool]]):
    ...


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
        -> (list[Alarm], list[tuple[datetime, bool]]):
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
    :return: A list of all alarms that should be newly raised, and tuple
    where each i-th element refers to the i-th telemetry frame in the appropriate
    timeframe, where the first element indicates if the alarm condition was met, and
    the second indicates the associated time
    """

    first_time, sequence = find_first_time(alarm_base, earliest_time)
    tag = alarm_base.tag
    telemetry_data = dm.get_telemetry_data(first_time, None, [tag])

    setpoint = alarm_base.setpoint

    # Checking which frames have tag values at setpoint and indicating it in <cond_met> in order
    cond_met, false_indexes = check_conds(telemetry_data, tag, setpoint_cond, [setpoint])

    first_indexes = persistence_check(cond_met, sequence, false_indexes)
    if not first_indexes:
        return [], cond_met
    alarms = []
    for index in first_indexes:
        relevant_frame = telemetry_data.get_telemetry_frame(index)
        timestamp = relevant_frame.time
        description = "setpoint value recorded"
        new_alarm = create_alarm(alarm_base, timestamp, description, criticality)
        alarms.append(new_alarm)
    return alarms, cond_met


def sequence_of_events_check(dm: DataManager, alarm_base: SOEEventBase,
                             criticality: AlarmCriticality, earliest_time: datetime) \
        -> (list[Alarm], list[tuple[datetime, bool]]):
    ...


def all_events_check(dm: DataManager, alarm_base: AllEventBase,
                     criticality: AlarmCriticality, earliest_time: datetime) \
        -> (list[Alarm], list[tuple[datetime, bool]]):
    """
    Checks that all event bases in <alarm_base> have occurred, and returns an appropriate
    Alarm. Otherwise, returns None.

    :param dm: The source of all data known to the program
    :param alarm_base: Defines events to check
    :param criticality: default criticality for the alarm base
    :param earliest_time: The earliest time from a set of the most recently added
    telemetry frames
    :return: An Alarm containing all data about the recent event, or None if the check
    is not satisfied
    """

    possible_events = alarm_base.event_bases
    first_alarm_time = None

    # iterate through each of the eventbases and check if all of them were triggered.
    for possible_event in possible_events:
        strategy = get_strategy(possible_event)
        alarm = strategy(dm, possible_event, criticality, earliest_time)

        # Determine if any of the alarms were not triggered.
        # If so, the event failed and we return None.
        if alarm is None:
            return None
        else:
            # Track the first event to happen to return its time.
            # TODO clarify if this is the correct time.
            if first_alarm_time is None:
                first_alarm_time = alarm.event.time
            else:
                first_alarm_time = min(first_alarm_time, alarm.event.time)

    # If we exit the if, all events occured so we create and return an alarm.
    # TODO Finalize the description.
    description = 'All events were triggered.'
    return create_alarm(alarm_base, first_alarm_time, description, criticality)


def any_events_check(dm: DataManager, alarm_base: AnyEventBase,
                     criticality: AlarmCriticality, new_id: int,
                     earliest_time: datetime) -> (list[Alarm], list[tuple[datetime, bool]]):
    """
    Checks that any of the event bases in <alarm_base> occurred, and returns an appropriate
    Alarm. Otherwise, returns None.

    :param dm: The source of all data known to the program
    :param alarm_base: Defines events to check
    :param criticality: default criticality for the alarm base
    :param new_id: the id to assign a potential new alarm
    :param earliest_time: The earliest time from a set of the most recently added
    telemetry frames
    :return: An Alarm containing all data about the recent event, or None if the check
    is not satisfied
    """

    eventbases = alarm_base.event_bases

    # iterate through each of the eventbases and check if any of them are triggered.
    for eventbase in eventbases:
        strategy = get_strategy(eventbase)
        alarm = strategy(dm, eventbase, criticality, new_id, earliest_time)

        # Determine if any of the alarms are triggered. If so, we create and return an alarm for it.
        if alarm is not None:
            # Create a description for the alarm. #TODO Finalize the description.
            description = (f'Any alarm was triggered with the following description: '
                           f'{alarm.event.description}.')
            return create_alarm(alarm_base, alarm.event.time, description, criticality)

    # If we exit the loop without returning, no alarm triggered, so the 'anyevent' did not happen.
    return None
