"""This module takes care of exporting telemetry data to a file."""

from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path

import pandas as pd

from astra.data.database import db_manager
from astra.data.parameters import Parameter, ParameterValue, Tag


def _convert_dtype(parameter: Parameter, value: float | None) -> ParameterValue:
    # Convert the float telemetry value from the database
    # to the correct type for the given parameter.
    # Modified from TelemetryData.
    if value is None:
        return None
    return parameter.dtype(value)


# Exporter DataFrame input format:
# - Timestamp datetime indices for rows.
# - Each tag has its own column.


def _export_data_csv(filename: str, df: pd.DataFrame):
    # Export the data from the dataframe to the file with the given filename.
    # Currently uses TIME as the column header for timestamps.
    df.to_csv(filename, index_label='TIME')


_file_extension_to_exporter: Mapping[str, Callable[[str, pd.DataFrame], None]] = {
    '.csv': _export_data_csv
}


def export_data(
        filename: str,
        device_name: str,
        start_time: datetime | None,
        end_time: datetime | None,
        parameters: Mapping[Tag, Parameter],
        step: int
) -> None:
    """
    Export data to a file, determining the format from the file extension.

    For now, raise ValueError for unexpected file extensions.

    Exported data is currently unconverted (multiplier and constant not applied).

    :param filename:
        The path to save to.
    :param device_name:
        The name of the device to export data for.
    :param start_time:
        Earliest allowed time for a telemetry frame in the exported data.
        Use None to indicate that arbitrarily old telemetry frames are allowed.
    :param end_time:
        Latest allowed time for a telemetry frame in the exported data.
        Use None to indicate that arbitrarily new telemetry frames are allowed.
    :param parameters:
        A tag->parameter mapping with the tags that will be included in the exported data.
    :param step:
        When step=n, only export every nth value. Only positive steps are supported.

    Preconditions:
        parameters is nonempty and only contains entries associated with the device.
        step > 0.
    """
    file_extension = Path(filename).suffix
    try:
        exporter = _file_extension_to_exporter[file_extension]
    except KeyError:
        raise ValueError(
            f'unexpected file extension {repr(file_extension)} -- '
            f'supported file extensions are: {', '.join(_file_extension_to_exporter.keys())}'
        )

    # With the current design, a tag is required to access lists of timestamps.
    tag = next(iter(parameters.keys()))
    timestamps = [timestamp for _, timestamp in db_manager.get_telemetry_data_by_tag(
        device_name, start_time, end_time, tag, step
    )]

    df = pd.DataFrame(index=timestamps)
    for tag, parameter in parameters.items():
        df[tag] = [
            _convert_dtype(parameter, value) for value, _ in db_manager.get_telemetry_data_by_tag(
                device_name, start_time, end_time, tag, step
            )
        ]

    exporter(filename, df)
