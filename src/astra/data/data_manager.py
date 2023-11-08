"""This module defines the DataManager, the main data access interface for the use case subteam."""
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Self

from astra.data import telemetry_reader
from astra.data.database import db_manager
from astra.data.database.db_initializer import Tag as DBTag
from astra.data.parameters import DisplayUnit, Parameter, Tag
from astra.data.telemetry_data import InternalDatabaseError, TelemetryData


class DataManager:
    """
    An object that facilitates file/database I/O for a session of the program.

    A single DataManager object represents the information relating to a single device.
    Almost all reading/writing to the filesystem will be done through
    either this class or the related TelemetryData class.
    """

    _device_name: str
    _parameters: dict[Tag, Parameter]

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
        device_tags = db_manager.get_tags_for_device(device_name)
        self._parameters = {
            Tag(dbtag.tag_name): DataManager._parameter_from_dbtag(dbtag) for dbtag in device_tags
        }

    @staticmethod
    def _parameter_from_dbtag(dbtag: DBTag) -> Parameter:
        # Return a Parameter from the given database tag object.
        # Raise DataCorruptionError if the tag_parameter field
        # does not contain data in the correct format.
        match dbtag.tag_parameter:
            case {
                'description': str(description),
                'dtype': 'bool' | 'int' | 'float' as dtype_string,
                'setpoint': bool() | int() | float() | None as setpoint,
                'display_units': dict() | None as display_units_dict,
            }:
                pass
            case _:
                raise InternalDatabaseError(
                    f'could not retrieve configuration for tag {dbtag.tag_name}'
                )
        dtype = {'bool': bool, 'int': int, 'float': float}[dtype_string]
        match display_units_dict:
            case {
                'description': str(units_description),
                'symbol': str(units_symbol),
                'multiplier': int() | float() as units_multiplier,
                'constant': int() | float() as units_constant,
            }:
                display_units = DisplayUnit(
                    units_description, units_symbol, units_multiplier, units_constant
                )
            case None:
                display_units = None
            case _:
                raise InternalDatabaseError(
                    f'could not retrieve configuration for tag {dbtag.tag_name}'
                )
        return Parameter(Tag(dbtag.tag_name), description, dtype, setpoint, display_units)

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
        return telemetry_reader.read_telemetry(filename)

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
        return TelemetryData(self._device_name, start_time, end_time, tags)
