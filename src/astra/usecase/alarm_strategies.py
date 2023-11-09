import datetime

from astra.data.alarms import *
from astra.data.data_manager import DataManager
from .alarm_checker import get_strategy
from .utils import eval_param_value, get_tag_param_value, get_tag_params
from typing import Callable, Iterable
from astra.data.telemetry_data import TelemetryData


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

def create_alarm(event_base: EventBase, id: int, time: datetime, description: str,
                 criticality: AlarmCriticality) -> Alarm:
    """
    Creates and returns an Alarm with the given attributes.

    :param event_base: The event base for the alarm.
    :param id: The id to give the event that triggered the alarm.
    :param time: The time at which the event occured.
    :param description: The description of the event that triggered the alarm.
    :param criticality: The criticality of this alarm.
    :return: An Alarm with the given attributes.
    """

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


def repeat_checker(td: TelemetryData, tag: Tag) -> list[tuple[bool, datetime]]:
    """
    Checks all the frames in <td> and returns a list of tuples where each tuple 
    contains a boolean indicating if the value of <tag> is the same as the previous
    frame, and the datetime associated with the frame.

    :param td: The relevant telemetry data to check.
    :return: A list of tuples where each tuple contains a boolean indicating if the value of
    <tag> is the same as the previous frame, and the datetime associated with the frame.
    """

    num_frames = td.num_telemetry_frames
    sequences_of_static = []
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

    return sequences_of_static


def static_check(dm: DataManager, alarm_base: StaticEventBase,
                 criticality: AlarmCriticality, new_id: int,
                 earliest_time: datetime) -> Alarm | None:
    """
    Checks if in the telemetry frames with times in the range
    (<earliest_time> - <alarm_base.persistence> -> present), there exists
    a sequence lasting <alarm_base.persistence> seconds where <alarm_base.tag> reported
    the same value. Returns an appropriate Alarm if the check is satisfied

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

    # Check which frames share the same value as the previous frame.
    cond_met = repeat_checker(telemetry_data, tag)

    first_index = forward_checking(cond_met, sequence)
    if first_index == -1:
        return None
    relevant_frame = telemetry_data.get_telemetry_frame(first_index)
    timestamp = relevant_frame.time
    description = "static alarm triggered"

    return create_alarm(alarm_base, new_id, timestamp, description, criticality)


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

    first_time, sequence = find_first_time(alarm_base, earliest_time)
    tag = alarm_base.tag
    telemetry_data = dm.get_telemetry_data(first_time, None, [tag])

    setpoint = alarm_base.setpoint

    # Checking which frames have tag values at setpoint and indicating it in <cond_met> in order
    cond_met = check_conds(telemetry_data, tag, setpoint_cond, [setpoint])

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

    possible_events = alarm_base.event_bases
    first_alarm_time = None

    # iterate through each of the eventbases and check if all of them were triggered.
    for possible_event in possible_events:
        strategy = get_strategy(possible_event)
        alarm = strategy(dm, possible_event, criticality,
                         new_id, earliest_time)

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
    return create_alarm(alarm_base, new_id, first_alarm_time,
                        description, criticality)


def any_events_check(dm: DataManager, alarm_base: AnyEventBase,
                     criticality: AlarmCriticality, new_id: int,
                     earliest_time: datetime) -> Alarm | None:
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
            description = 'Any alarm was triggered with the following description: '
            + alarm.event.description + '.'

            return create_alarm(alarm_base, new_id, alarm.event.time, description, criticality)

    # If we exit the loop without returning, no alarm triggered, so the 'anyevent' did not happen.
    return None


def xor_events_check(dm: DataManager, alarm_base: XOREventBase,
                     criticality: AlarmCriticality, new_id: int,
                     earliest_time: datetime) -> Alarm | None:
    """
    Checks that only one of the event bases in <alarm_base> occurred, and returns an appropriate
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
    current_alarm = None

    # iterate through each of the eventbases and check if any of them are triggered.
    for eventbase in eventbases:
        strategy = get_strategy(eventbase)
        alarm = strategy(dm, eventbase, criticality, new_id, earliest_time)

        # Determine if any of the alarms are triggered.
        if alarm is not None:
            # Determine if an alarm was triggered previously.
            if current_alarm is None:
                # No other alarm has been triggered, so we create one.

                # Create a description for the alarm. #TODO Finalize the description.
                description = 'A XOR alarm was triggered with the following description: '
                + alarm.event.description + '.'
                current_alarm = create_alarm(alarm_base, new_id, alarm.event.time,
                                             description, criticality)

            else:
                # If we have already found an alarm and we find another, we return None.
                return None

        # reset the alarm to None
        alarm = None

    # When we exit the loop, current_alarm will be None if no alarm was triggered.
    # Or it will be the one alarm that was triggered.
    return current_alarm


def not_events_check(dm: DataManager, alarm_base: NotEventBase,
                     criticality: AlarmCriticality, new_id: int,
                     earliest_time: datetime) -> Alarm | None:
    """
    Checks that none event bases in <alarm_base> have occurred, and returns an appropriate
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

    strategy = get_strategy(alarm_base)
    alarm = strategy(dm, alarm_base, criticality,
                     new_id, earliest_time)

    # Determine if the alarm was triggered.
    if alarm is not None:
        return None
    else:
        # If the alarm did not trigger we create and return a 'not-alarm'.
        description = 'None of the events were triggered.'
        return create_alarm(alarm_base, new_id, earliest_time, description, criticality)
