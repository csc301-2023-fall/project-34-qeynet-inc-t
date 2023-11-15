"""This module defines the DataManager, the main data access interface for the use case subteam."""
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta
from threading import Lock
from typing import Self

from astra.data import dict_parsing, telemetry_manager
from astra.data.alarms import AlarmBase, AlarmCriticality, AlarmPriority, Alarm
from astra.data.database import db_manager
from astra.data.dict_parsing import ParsingError
from astra.data.parameters import Parameter, Tag
from astra.data.telemetry_data import InternalDatabaseError, TelemetryData


class AlarmsContainer:
    """
    A container for a global alarms dict that utilizes locking for multithreading

    :param alarms: The actual dictionary of alarms held
    :param mutex: A lock used for mutating cls.alarms
    """
    alarms: dict[AlarmPriority, list[Alarm]] = None
    mutex = None

    @classmethod
    def __init__(cls):
        cls.alarms = defaultdict(lambda: [])
        cls.mutex = Lock()

    @classmethod
    def get_alarms(cls) -> dict[AlarmPriority, list[Alarm]]:
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
        # TODO: set priority correctly based on time elapsed since alarm
        new_alarms = []
        if alarms:
            # First, add the new alarms to the alarms structure
            # Because the alarms structure is used in a number of threads, we lock here
            with cls.mutex:
                for alarm in alarms:
                    criticality = alarm.criticality
                    priority = apm[timedelta(seconds=0)][criticality]
                    cls.alarms[priority].append(alarm)
                    new_alarms.append((priority, alarm))

            # Release the mutex as we are no longer using the alarms container
            # Now, we need to create a timer thread for each alarm

    def _update_priority(self, alarm: Alarm, time: timedelta) -> None:
        """
        Uses the alarm priority matrix with <time> to place <alarm> in the correct priority bin

        :param alarm: The alarm to check priority on
        :param time: Time elapsed since the alarm came into effect
        """

        with self.mutex:
            new_priority = self.alarm_priority_matrix[time][alarm.criticality]
            self.alarms[new_priority].append(alarm)

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
