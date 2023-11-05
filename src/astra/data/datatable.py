"""This module defines the interface between the data and use case sections of Astra's backend."""

__all__ = ['ConfigData', 'DataTable', 'Parameter', 'Tag', 'TelemetryData', 'TelemetryFrame']

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, NewType, Self

import pandas as pd

from . import config_manager
from . import telemetry_reader
from .config_manager import ConfigData
from .telemetry_reader import TelemetryData

Tag = NewType('Tag', str)


@dataclass(frozen=True)
class Parameter:
    """A type of telemetry data (value not included)."""

    tag: Tag
    description: str
    units: str
    conversion_factor: float | None


@dataclass(frozen=True)
class TelemetryFrame:
    """A collection of data corresponding to a single point in time.

    Units for each piece of data are given by the parameter
    corresponding to the tag for the piece of data.
    All data has already been pre-multiplied by the appropriate conversion factor.
    """

    timestamp: datetime
    data: Mapping[Tag, Any]


class DataTable:
    """A table that holds telemetry data that conforms to a given configuration.

    The telemetry data can be thought of as a list of telemetry frames,
    with each frame having a timestamp and a tag -> data map,
    where the tags in the map correspond to parameters as specified by the configuration.
    """

    _config_data: ConfigData
    _telemetry_data: TelemetryData

    def __init__(self, config_data: ConfigData):
        """Construct a DataTable from configuration data.

        The resulting table will have the given configuration, and will be empty of telemetry data.
        """
        self._config_data = ConfigData(
            config_data[['tag', 'description', 'units', 'conversion_factor']]
        )
        self._telemetry_data = TelemetryData(pd.DataFrame())

    @classmethod
    def from_config_file(cls, filename: str) -> Self:
        """Construct a DataTable with configuration data from a file."""
        return cls(config_manager.read_config(filename))

    def add_data(self, new_data: TelemetryData) -> None:
        """Add new telemetry data to this DataTable.

        Currently assumes no restrictions on timestamps.
        The implementation may change later for efficiency reasons.
        """
        self._telemetry_data = TelemetryData(
            pd.concat([self._telemetry_data, new_data]).sort_values(by='EPOCH', ignore_index=True)
        )

    def add_data_from_file(self, filename: str) -> None:
        """Add new telemetry data from a file to this DataTable."""
        self.add_data(telemetry_reader.read_telemetry(filename))

    @property
    def tags(self) -> Iterable[Tag]:
        """Return the tags in the configuration for this DataTable."""
        return list(self._config_data['tag'])

    @property
    def parameters(self) -> Mapping[Tag, Parameter]:
        """Return a tag -> parameter map based on the configuration for this DataTable."""
        return {
            tag: Parameter(tag, description, units, conversion_factor)
            for tag, description, units, conversion_factor in self._config_data.itertuples(
                index=False
            )
        }

    @property
    def num_telemetry_frames(self) -> int:
        """Return the number of telemetry frames currently in this DataTable."""
        return len(self._telemetry_data)

    def get_telemetry_frame(self, index: int) -> TelemetryFrame:
        """Index into the telemetry data (sorted in ascending order according to timestamp).

        Given an integer index n, return the telemetry frame with the nth oldest timestamp.
        Negative indices are supported, and work in standard Python fashion
        (so an index of -1 would give the most recent telemetry frame by timestamp).
        Raise an IndexError if the index is out of range.
        """
        try:
            telemetry_row = self._telemetry_data.iloc[index]
        except IndexError:
            raise IndexError('telemetry data index out of range') from None
        match telemetry_row.to_dict():
            case {'EPOCH': timestamp, **unscaled_data}:
                pass
            case _:
                raise RuntimeError('telemetry data lacks an EPOCH column')
        data = {
            tag: _apply_conversion_factor(value, self.parameters[tag].conversion_factor)
            for tag, value in unscaled_data.items()
        }
        return TelemetryFrame(pd.to_datetime(timestamp, unit='s'), data)


def _apply_conversion_factor(value: Any, conversion_factor: float | None) -> Any:
    return value if conversion_factor is None else value * conversion_factor
