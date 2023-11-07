from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Self

import pandas as pd

from parameters import DisplayUnit, Parameter, Tag
from telemetry_data import TelemetryData
from alarms import AlarmBase

config = pd.DataFrame(
    {
        'tag': ['A3', 'B1', 'B4', 'C1'],
        'description': ['a monad', 'is a monoid', 'in the category', 'of endofunctors'],
        'dtype': ['int', 'float', 'bool', 'int'],
        'setpoint': [3, 1.0, False, None],
        'units': [
            DisplayUnit('metre', 'm', 1, 0),
            DisplayUnit('gram', 'g', 1000, 0),
            None,
            DisplayUnit('second', 's', 1, 0)
        ]
    }
)


telemetry_0 = pd.DataFrame(
    {
        'EPOCH': [datetime(2011, 10, 24), datetime(2018, 3, 16), datetime(2014, 5, 2)],
        'A3': [5, 3, 3],
        'B1': [0.0, 0.0, 1.0],
        'B4': [True, False, False],
        'C1': [2, 4, 2],
    }
)

telemetry_1 = pd.DataFrame(
    {
        'EPOCH': [datetime(2022, 3, 25), datetime(2016, 6, 1)],
        'A3': [5, 3],
        'B1': [3.0, 1.0],
        'B4': [False, False],
        'C1': [1, 3],
    }
)


# All file IO methods raise IOError upon any failure that we should be handling.

class DataManager:
    _config_data: pd.DataFrame
    _telemetry_data: pd.DataFrame
    _telemetry_files: list[str]

    def __init__(self, config_data: pd.DataFrame):
        self._config_data = config_data[[
            'tag', 'description', 'dtype', 'setpoint', 'units'
        ]]
        self._telemetry_data = pd.DataFrame()
        self._telemetry_files = []

    @classmethod
    def from_device_name(cls, device_name: str) -> Self:
        if device_name == 'DEVICE':
            return cls(config)
        else:
            raise FileNotFoundError(f"Couldn't find device with name {device_name}")

    @property
    def tags(self) -> Iterable[Tag]:
        return list(self._config_data['tag'])

    @property
    def parameters(self) -> Mapping[Tag, Parameter]:
        return {
            tag: Parameter(tag, desc, dtype, setp, units)
            for tag, desc, dtype, setp, units in self._config_data.itertuples(
                index=False
            )
        }

    def add_data(self, new_data: pd.DataFrame) -> None:
        """Add new telemetry data to this DataTable.

        Currently assumes no restrictions on timestamps.
        The implementation may change later for efficiency reasons.
        """
        self._telemetry_data = pd.concat(
            [self._telemetry_data, new_data]
        ).sort_values(by='EPOCH', ignore_index=True)

    # Returns the time of the earliest added telemetry frame.
    def add_data_from_file(self, filename: str) -> datetime:
        if filename in self._telemetry_files:
            raise IOError(f'Already added telemetry file {filename}')
        self._telemetry_files.append(filename)
        try:
            df = {'telemetry0.h5': telemetry_0, 'telemetry1.h5': telemetry_1}[filename]
        except KeyError:
            raise FileNotFoundError(f"Couldn't find telemetry file {filename}")
        self.add_data(df)
        if 'telemetry1.h5' in self._telemetry_files:
            return datetime(2022, 3, 25)
        else:
            return datetime(2018, 3, 16)

    # Will likely need some way to only get every nth value for graphing over long timespans.
    def get_telemetry_data(
            self, start_time: datetime, end_time: datetime, tags: Iterable[Tag]
    ) -> TelemetryData:
        return TelemetryData(self._telemetry_data, start_time, end_time, ['EPOCH'] + list(tags))
