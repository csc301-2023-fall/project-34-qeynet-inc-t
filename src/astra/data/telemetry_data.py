"""This module defines the TelemetryData class, representing a collection of telemetry data."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING

from astra.data import export_manager
from astra.data.database import db_manager
from astra.data.parameters import ParameterValue, Tag

if TYPE_CHECKING:
    from astra.data.data_manager import DataManager


class InternalDatabaseError(IOError):
    """Raised when objects read from the database are detected to violate internal invariants."""

    pass


@dataclass(frozen=True)
class TelemetryFrame:
    """All the telemetry data from a TelemetryData object for one timestamp."""

    time: datetime
    data: Mapping[Tag, ParameterValue | None]


class TelemetryData:
    """
    A collection of telemetry data, organized by timestamp and tag.

    Can be thought of as a lazy 2D array,
    with one row per telemetry frame and one column per parameter.

    All rows will have a timestamp between the start and end times.
    The columns will match the set of tags.
    """

    _data_manager: 'DataManager'
    _start_time: datetime | None  # Unbounded if None
    _end_time: datetime | None  # Unbounded if None
    _tags: Iterable[Tag]

    def __init__(
        self,
        data_manager: 'DataManager',
        start_time: datetime | None,
        end_time: datetime | None,
        tags: Iterable[Tag],
    ):
        # Not meant to be instantiated directly. Instead, create via DataManager.get_telemetry_data.
        self._data_manager = data_manager
        self._start_time = start_time
        self._end_time = end_time
        self._tags = tags

    @property
    def tags(self) -> Iterable[Tag]:
        """The tags for this TelemetryData."""
        return self._tags

    def _convert_dtype(self, tag: Tag, value: float | None) -> ParameterValue:
        # Convert the float telemetry value from the database
        # to the correct type for the given parameter.
        if value is None:
            return None
        return self._data_manager.parameters[tag].dtype(value)

    @cached_property
    def num_telemetry_frames(self) -> int:
        """The number of telemetry frames (rows) for this TelemetryData."""
        return db_manager.num_telemetry_frames(
            self._data_manager.device_name, self._start_time, self._end_time
        )

    def timestamps(self, step: int = 1) -> Iterable[datetime]:
        """
        Get all the timestamps for this TelemetryData.

        :param step:
            When step=n, only get every nth timestamp. Only positive steps are supported.

        :raise ValueError:
            If step is zero or negative.

        :return:
            An iterable of timestamps.
        """
        if step <= 0:
            raise ValueError(f'timestamps step must be positive; got {step}')
        # With the current design, a tag is required to access lists of timestamps.
        # Just pick one from the list of tags for the device.
        # Requires there to be at least one tag in the device configuration file,
        # but does not require there to be at least one tag in the TelemetryData itself.
        tag = next(iter(self._data_manager.tags))
        return [
            timestamp
            for _, timestamp in db_manager.get_telemetry_data_by_tag(
                self._data_manager.device_name, self._start_time, self._end_time, tag, step
            )
        ]

    def get_telemetry_frame(self, index: int) -> TelemetryFrame:
        """
        Return the <index>th-oldest telemetry frame (row) for this TelemetryData.

        :param index:
            Acts as an index into an array of telemetry frames sorted by timestamp
            (older comes first). 0-indexed; negative indices have standard Python semantics.
            (An index of -1 corresponds to the newest telemetry frame.)

        :raise IndexError:
            If index is out of range. The index is in range if and only if
            -self.num_telemetry_frames <= index < self.num_telemetry_frames.

        :return:
            A TelemetryFrame with the appropriate timestamp and data.
        """
        if not (-self.num_telemetry_frames <= index < self.num_telemetry_frames):
            raise IndexError(f'telemetry frame index {index} out of range')
        if index < 0:
            index += self.num_telemetry_frames
        data, timestamp = db_manager.get_telemetry_data_by_index(
            self._data_manager.device_name, set(self.tags), self._start_time,
            self._end_time, index
        )
        return TelemetryFrame(
            timestamp,
            {Tag(tag_name): self._convert_dtype(Tag(tag_name), value) for tag_name, value in data},
        )

    def get_parameter_values(
        self, tag: Tag, step: int = 1
    ) -> Mapping[datetime, ParameterValue | None]:
        """
        Return a column of this TelemetryData in the form of a timestamp->value mapping.

        :param tag:
            The tag for the parameter to get values for.
        :param step:
            When step=n, only get every nth value. Only positive steps are supported.

        :raise ValueError:
            If the tag isn't among the set of tags in this TelemetryData.
            If step is zero or negative.

        :return:
            A mapping from timestamps to the values of the given parameter at those timestamps.
        """
        if tag not in self.tags:
            raise ValueError(f'got unexpected tag {tag}')
        if step <= 0:
            raise ValueError(f'get_parameter_values step must be positive; got {step}')
        data = db_manager.get_telemetry_data_by_tag(
            self._data_manager.device_name, self._start_time, self._end_time, tag, step
        )
        return {timestamp: self._convert_dtype(tag, value) for value, timestamp in data}

    def save_to_file(self, filename: str, step: int = 1) -> None:
        """
        Export this TelemetryData to a file.

        :param filename:
            The path to save to. The export format is determined based on the file extension.
        :param step:
            When step=n, only export every nth telemetry frame. Only positive steps are supported.

        :raise ValueError:
            If step is zero or negative.
        """
        if step <= 0:
            raise ValueError(f'save_to_file step must be positive; got {step}')
        export_manager.export_data(filename, self, step)
