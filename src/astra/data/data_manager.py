"""This module defines the DataManager, the main data access interface for the use case subteam."""
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta
from queue import Queue
from threading import Lock, Timer
from typing import Self, Callable, Dict, List

from astra.data import dict_parsing, telemetry_manager
from astra.data.alarms import AlarmBase, AlarmCriticality, AlarmPriority, Alarm
from astra.data.database import db_manager
from astra.data.dict_parsing import ParsingError
from astra.data.parameters import Parameter, Tag
from astra.data.telemetry_data import InternalDatabaseError, TelemetryData

NEW_QUEUE_KEY = 'n'
MAX_QUEUE_SIZE = 3
ACKNOWLEDGED = False


class AlarmObserver:
    """
    Observes the state of the global alarms container and notifies interested
    parties whenever an update occurs

    :param watchers: A list of functions to call on any update to the alarm container
    :param mutex: Synchronization tool as many threads may notify watchers of updates
    """
    watchers_added = []
    watchers_modified = []
    _mutex = Lock()

    @classmethod
    def __int__(cls):
        cls.watchers_added = []
        cls.watchers_modified = []
        cls._mutex = Lock()

    @classmethod
    def add_watcher_adding(cls, watcher: Callable):
        """
        Adds a new function to call on alarm container receiving new data

        :param watcher: The new function to call
        """
        cls.watchers_added.append(watcher)

    @classmethod
    def add_watcher_modifying(cls, watcher: Callable):
        """
        Adds a new function to call on alarm container elements being modified

        :param watcher: The new function to call
        """
        cls.watchers_modified.append(watcher)

    @classmethod
    def notify_watchers_added(cls) -> None:
        """
        Calls all functions that wish to be called on container receiving new data
        """
        with cls._mutex:
            for watcher in cls.watchers_added:
                watcher()

    @classmethod
    def notify_watchers_added_modified(cls, alarm) -> None:
        """
        Calls all functions that should be notified on a container item being modified
        """
        with cls._mutex:
            for watcher in cls.watchers_modified:
                watcher(alarm)


class AlarmsContainer:
    """
    A container for a global alarms dict that utilizes locking for multithreading

    :param alarms: The actual dictionary of alarms held
    :param mutex: A lock used for mutating cls.alarms
    :param observer: An Observer to monitor the state of the container
    """
    observer: AlarmObserver
    alarms: dict[str, list[Alarm] | Queue]
    mutex: Lock

    @classmethod
    def __init__(cls):
        cls.alarms = {AlarmPriority.WARNING.name: [], AlarmPriority.LOW.name: [],
                      AlarmPriority.MEDIUM.name: [], AlarmPriority.HIGH.name: [],
                      AlarmPriority.CRITICAL.name: [], NEW_QUEUE_KEY: Queue()}
        cls.mutex = Lock()
        cls.observer = AlarmObserver()

    @classmethod
    def get_alarms(cls) -> dict[str, list[Alarm] | Queue]:
        """
        Returns a shallow copy of <cls.alarms>

        :return: A copy of <cls.alarms>
        """
        with cls.mutex:
            return cls.alarms.copy()

    @classmethod
    def add_alarms(cls, alarms: list[Alarm],
                   apm: Mapping[timedelta, Mapping[AlarmCriticality, AlarmPriority]]) -> None:
        """
        Updates the alarms global variable after acquiring the lock for it

        :param dm: Holds information of data criticality and priority
        :param apm: Maps information on alarms to correct priority level
        :param alarms: The set of alarms to add to <cls.alarms>
        """
        new_alarms = []
        times = [0, 5, 15, 30]
        timer_vals = []
        alarms.sort(reverse=True)
        if alarms:
            # First, add the new alarms to the alarms structure
            # Because the alarms structure is used in a number of threads, we lock here
            with cls.mutex:
                for alarm in alarms:
                    criticality = alarm.criticality
                    alarm_timer_vals = []

                    # Find the closest timeframe from 0, 5, 15, and 30 minutes from when the
                    # alarm was created to when it was actually confirmed
                    for i in range(1, len(times)):
                        time = times[i]
                        endpoint_time = alarm.event.confirm_time + timedelta(minutes=time)

                        # indicates an endpoint has already been found, so we add every following
                        # timer endpoint
                        if alarm_timer_vals:
                            alarm_timer_vals.append(endpoint_time - alarm.event.creation_time)

                        # Case for the first timer interval the alarm has not yet reached
                        if alarm.event.creation_time < endpoint_time and not alarm_timer_vals:
                            priority_name = apm[timedelta(minutes=times[i - 1])][criticality]
                            priority = AlarmPriority(priority_name)
                            cls.alarms[priority].append(alarm)
                            alarm.priority = priority
                            new_alarms.append([alarm, priority])

                            remaining_time = endpoint_time - alarm.event.creation_time
                            alarm_timer_vals.append(remaining_time)

                    # Case where the alarm was confirmed at least 30 minutes ago already
                    if not alarm_timer_vals:
                        priority = apm[timedelta(minutes=30)][criticality]
                        cls.alarms[priority.name].append(alarm)

                        cls.alarms[NEW_QUEUE_KEY].put(alarm)
                        if cls.alarms[NEW_QUEUE_KEY].qsize() > MAX_QUEUE_SIZE:
                            cls.alarms[NEW_QUEUE_KEY].get()

                        new_alarms.append([alarm, priority])
                    timer_vals.append(alarm_timer_vals)

            # Now that the state of the alarms container has been update, notify watchers
            cls.observer.notify_watchers_added()

            # Now, we need to create a timer thread for each alarm
            for i in range(len(new_alarms)):
                alarm = new_alarms[i]
                associated_times = timer_vals[i]

                for associated_time in associated_times:
                    # Because <associated_times> is a subset of <times>, we need to offset
                    # the index well later use into it
                    time_interval = len(times) - len(associated_times) + i

                    new_timer = Timer(associated_time.seconds, cls._update_priority,
                                      args=[alarm, timedelta(minutes=times[time_interval]), apm])
                    new_timer.start()

    @classmethod
    def _update_priority(cls, alarm_data: list[Alarm, AlarmPriority], time: timedelta,
                         apm: Mapping[timedelta, Mapping[AlarmCriticality, AlarmPriority]]) -> None:
        """
        Uses the alarm priority matrix with <time> to place <alarm> in the correct priority bin
        NOTE: we pass a list, and not a tuple, as we need to mutate said list

        :param alarm_data: contains the current priority of the alarm and the alarm itself
        :param time: Time elapsed since the alarm came into effect
        :param apm: Maps information on alarms to correct priority level
        """

        with cls.mutex:
            new_priority = apm[time][alarm_data[0].criticality]
            cls.alarms[alarm_data[1]].remove(alarm_data[0])
            cls.alarms[new_priority].append(alarm_data[0])
            alarm_data[0].priority = new_priority
            alarm_data[1] = new_priority
        # TODO temp
        cls.observer.notify_watchers_added()

    @classmethod
    def acknowledge_alarm(cls, alarm: Alarm) -> None:
        """
        Removes the requested alarm in <cls.alarms>

        :param alarm: The alarm to remove from the container

        PRECONDITION: <alarm> is in <cls.alarms>
        """
        with cls.mutex:
            # Note: because the alarm container should store every known alarm, this mutation
            # should work
            alarm.acknowledgement = ACKNOWLEDGED
        cls.observer.notify_watchers_added_modified(alarm)

    @classmethod
    def remove_alarm(cls, alarm: Alarm) -> None:
        """
        Removes the requested alarm in

        :param alarm:
        :return:
        """
        with cls.mutex:
            for priority in cls.alarms:
                if priority != NEW_QUEUE_KEY and alarm in cls.alarms[priority]:
                    # Note: We don't consider the queue of new alarms, since by the time
                    # the alarm can be removed, it's already be taken out of the queue
                    cls.alarms[priority].remove(alarm)
        cls.observer.notify_watchers_added_modified(alarm)


class DataManager:
    """
    An object that facilitates file/database I/O for a session of the program.

    A single DataManager object represents the information relating to a single device.
    Almost all reading/writing to the filesystem will be done through
    either this class or the related TelemetryData class.
    """

    _device_name: str
    _parameters: dict[Tag, Parameter]
    _alarm_bases: list[AlarmBase]
    _alarm_container: AlarmsContainer

    def __init__(self, device_name: str):
        """
        Construct a DataManager for the device with the given name.

        :param device_name:
            The name of the device (metadata.device in the device configuration file)

        :raise ValueError:
            If there is no device with the given name.
        :raise IOError:
            If there are internal problems with construction.
        """
        device = db_manager.get_device(device_name)
        if device is None:
            raise ValueError(f'there is no device with name {device_name}')
        self._device_name = device_name
        self._parameters = {
            Tag(tag_name): DataManager._parse_parameter_dict(tag_name, parameter_dict)
            for tag_name, parameter_dict in db_manager.get_tags_for_device(device_name)
        }
        self._alarm_bases = [
            DataManager._parse_alarm_dict(criticality, event_dict)
            for criticality, event_dict in db_manager.get_alarm_base_info(device_name)
        ]
        self._alarm_container = AlarmsContainer()

    @staticmethod
    def _parse_parameter_dict(tag_name: str, parameter_info: object) -> Parameter:
        # Return a Parameter based on the given tag name and parameter information.
        # Raise InternalDatabaseError if the dict cannot be parsed.
        try:
            return dict_parsing.parse_parameter(Tag(tag_name), parameter_info)
        except ParsingError as e:
            raise InternalDatabaseError(f'failed to parse database tag {tag_name}: {e}')

    @staticmethod
    def _parse_alarm_dict(criticality: str, event_info: object) -> AlarmBase:
        # Return an AlarmBase based on the given criticality and event information.
        # Raise InternalDatabaseError if the dict cannot be parsed.
        try:
            return dict_parsing.parse_alarm_base(criticality, event_info)
        except ParsingError as e:
            raise InternalDatabaseError(f'failed to parse database alarm base: {e}')

    @classmethod
    def from_device_name(cls, device_name: str) -> Self:
        """Same as the standard constructor -- retained for historical reasons."""
        return cls(device_name)

    @property
    def tags(self) -> Iterable[Tag]:
        """Iterable of tags for the device of this DataManager."""
        return self._parameters.keys()

    @property
    def parameters(self) -> Mapping[Tag, Parameter]:
        """Tag -> parameter mapping for the device of this DataManager."""
        return self._parameters

    @property
    def alarm_bases(self) -> Iterable[AlarmBase]:
        return self._alarm_bases

    @property
    def alarms(self) -> AlarmsContainer:
        return self._alarm_container

    def add_alarms(self, alarms: list[Alarm]) -> None:
        """
        Updates the alarms global variable after acquiring the lock for it

        :param dm: Holds information of data criticality and priority
        :param alarms: The set of alarms to add to <cls.alarms>
        """
        self._alarm_container.add_alarms(alarms, self.alarm_priority_matrix)

    @property
    def alarm_priority_matrix(self) -> Mapping[timedelta, Mapping[AlarmCriticality, AlarmPriority]]:
        """
        Data to facilitate turning alarm criticality and time since alarm into alarm priority.

        The outer mapping has keys sorted in descending order. The final key is a timedelta of zero.
        The key to select is the first/largest key less than or equal to the time since alarm.
        """
        # Hardcode for now -- replace with a file read later.
        w, l, m, h, c = AlarmCriticality
        # fmt: off
        return dict(reversed([
            (timedelta(minutes=0), {w: w, l: l, m: l, h: m, c: c}),  # noqa E251
            (timedelta(minutes=5), {w: w, l: l, m: m, h: h, c: c}),  # noqa E251
            (timedelta(minutes=15), {w: w, l: l, m: m, h: h, c: c}),
            (timedelta(minutes=30), {w: w, l: m, m: h, h: c, c: c}),
        ]))
        # fmt: on

    @staticmethod
    def add_data(filename: str) -> datetime:
        """
        Read in a telemetry file.

        The device is determined based on the metadata in the file.

        :param filename:
            The path to the telemetry file.

        :return:
            The time of the earliest read-in telemetry frame (to facilitate alarm checking).
        """
        return telemetry_manager.read_telemetry(filename)

    add_data_from_file = add_data  # Alias for historical reasons

    def get_telemetry_data(
            self, start_time: datetime | None, end_time: datetime | None, tags: Iterable[Tag]
    ) -> TelemetryData:
        """
        Give access to a collection of telemetry data for the device of this DataManager.

        :param start_time:
            Earliest allowed time for a telemetry frame in the returned TelemetryData.
            Use None to indicate that arbitrarily old telemetry frames are allowed.
        :param end_time:
            Latest allowed time for a telemetry frame in the returned TelemetryData.
            Use None to indicate that arbitrarily new telemetry frames are allowed.
        :param tags:
            The tags that will be included in the returned TelemetryData.
            Must be a subset of the tags for the device of this DataManager.

        :raise ValueError:
            If tags is not a subset of the tags for the device of this DataManager.

        :return:
            A TelemetryData object for this DataManager's device and the given time range and tags.
        """
        tags = set(tags)
        device_tags = set(self.tags)
        if not (tags <= device_tags):
            raise ValueError(f'got unexpected tags {tags - device_tags}')
        subset_parameters = {
            tag: parameter for tag, parameter in self.parameters.items() if tag in tags
        }
        return TelemetryData(self._device_name, start_time, end_time, subset_parameters)
