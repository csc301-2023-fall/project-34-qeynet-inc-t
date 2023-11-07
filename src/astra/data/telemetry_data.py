from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from astra.data.parameters import ParameterValue, Tag


@dataclass(frozen=True)
class TelemetryFrame:
    time: datetime
    data: Mapping[Tag, ParameterValue]


class TelemetryData:
    _telemetry_data: pd.DataFrame

    def __init__(self, telemetry_data, start_time, end_time, tags):
        time_filter = telemetry_data['EPOCH'] == telemetry_data['EPOCH']
        if start_time is not None:
            time_filter &= start_time <= telemetry_data['EPOCH']
        if end_time is not None:
            time_filter &= telemetry_data['EPOCH'] <= end_time
        self._telemetry_data = telemetry_data[tags][time_filter]

    @property
    def num_telemetry_frames(self) -> int:
        return len(self._telemetry_data)

    def get_telemetry_frame(self, index: int) -> TelemetryFrame:
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
            tag: value
            for tag, value in unscaled_data.items()
        }
        return TelemetryFrame(pd.to_datetime(timestamp, unit='s'), data)

    def get_parameter_values(self, tag: Tag) -> Mapping[datetime, ParameterValue]:
        telemetry_frames = [
            self.get_telemetry_frame(index) for index in range(self.num_telemetry_frames)
        ]
        return {frame.time: frame.data[tag] for frame in telemetry_frames}
