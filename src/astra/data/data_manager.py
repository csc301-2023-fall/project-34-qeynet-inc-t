"""This module defines the DataManager, the main data access interface for the use case subteam."""
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Self

from astra.data import config_manager, dict_parsing, telemetry_manager
from astra.data.alarms import AlarmBase, AlarmCriticality, AlarmPriority, Alarm
from astra.data.database import db_manager
from astra.data.alarm_container import AlarmsContainer
from astra.data.dict_parsing import ParsingError
from astra.data.parameters import Parameter, Tag
from astra.data.telemetry_data import InternalDatabaseError, TelemetryData


@dataclass(frozen=True)
class Device:
    """The relevant metadata for a device."""

    name: str
    description: str


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

    @staticmethod
    def add_device(config_filename: str) -> None:
        """
        Add a device, specified by a configuration file, to the database.

        :param config_filename:
            The path to the configuration file.
        """
        config_manager.read_config(config_filename)

    @staticmethod
    def remove_device(device_name: str) -> None:
        """
        Remove a device and all of its associated data from the database.

        :param device_name:
            The name of the device to remove (metadata.device in the device configuration file).
        """
        db_manager.delete_device(device_name)

    @staticmethod
    def get_devices() -> Mapping[str, Device]:
        """:return: A name->metadata mapping for all devices in the database."""
        return {
            name: Device(name, description) for name, description in db_manager.get_device_data()
        }

    def __init__(self, device_name: str):
        """
        Construct a DataManager for the device with the given name.

        :param device_name:
            The name of the device (metadata.device in the device configuration file).

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
    def device_name(self) -> str:
        """The name of the device of this DataManager."""
        return self._device_name

    @property
    def tags(self) -> Iterable[Tag]:
        """All the tags for the device of this DataManager."""
        return self._parameters.keys()

    @property
    def parameters(self) -> Mapping[Tag, Parameter]:
        """Tag -> parameter mapping for the device of this DataManager."""
        return self._parameters

    @property
    def alarm_bases(self) -> Iterable[AlarmBase]:
        """The alarm bases for the device of this DataManager."""
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
        selected_tag_set = set(tags)
        device_tag_set = set(self.tags)
        if not (selected_tag_set <= device_tag_set):
            raise ValueError(f'got unexpected tags {selected_tag_set - device_tag_set}')
        return TelemetryData(self, start_time, end_time, tags)
