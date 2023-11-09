"""This module defines the TelemetryData class, representing a collection of telemetry data."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property

from astra.data.database import db_manager
from astra.data.parameters import ParameterValue, Tag


class InternalDatabaseError(IOError):
    """Raised when objects read from the database are detected to violate internal invariants."""

    pass


@dataclass(frozen=True)
class TelemetryFrame:
    """All the telemetry data from a TelemetryData object for one timestamp."""

    time: datetime
    data: Mapping[Tag, ParameterValue]


class TelemetryData:
    """
    A collection of telemetry data, organized by timestamp and tag.

    Can be thought of as a lazy 2D array,
    with one row per telemetry frame and one column per parameter.

    All rows will have a timestamp between the start and end times.
    The columns will match the set of tags.
    """

    _device_name: str
    _start_time: datetime | None  # Unbounded if None
    _end_time: datetime | None  # Unbounded if None
    _tags: set[Tag]

    def __init__(
        self,
        device_name: str,
        start_time: datetime | None,
        end_time: datetime | None,
        tags: set[Tag],
    ):
        # Not meant to be instantiated directly. Instead, create via DataManager.get_telemetry_data.
        self._device_name = device_name
        self._start_time = start_time
        self._end_time = end_time
        self._tags = tags

    @cached_property
    def num_telemetry_frames(self) -> int:
        """Return the number of telemetry frames (rows) for this TelemetryData."""
        return db_manager.num_telemetry_frames(self._device_name, self._start_time, self._end_time)

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
        timestamp = db_manager.get_timestamp_by_index(
            self._device_name, self._start_time, self._end_time, index
        )
        data = db_manager.get_telemetry_data_by_timestamp(self._device_name, self._tags, timestamp)
        return TelemetryFrame(
            timestamp, {Tag(dbdata.tag.tag_name): dbdata.value for dbdata in data}
        )

    def get_parameter_values(self, tag: Tag) -> Mapping[datetime, ParameterValue]:
        """
        Return a column of this TelemetryData in the form of a timestamp->value mapping.

        :param tag:
            The tag for the parameter to get values for.

        :raise ValueError:
            If the tag isn't among the set of tags in this TelemetryData.

        :return:
            A mapping from timestamps to the values of the given parameter at those timestamps.
        """
        if tag not in self._tags:
            raise ValueError(f'got unexpected tag {tag}')
        data = db_manager.get_telemetry_data_by_tag(
            self._device_name, self._start_time, self._end_time, tag
        )
        return {dbdata.timestamp: dbdata.value for dbdata in data}
