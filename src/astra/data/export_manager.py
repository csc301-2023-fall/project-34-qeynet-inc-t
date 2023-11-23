"""This module takes care of exporting telemetry data to a file."""

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from astra.data.telemetry_data import TelemetryData


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
    telemetry_data: 'TelemetryData',
    step: int,
) -> None:
    """
    Export telemetry data to a file, determining the format from the file extension.

    For now, raise ValueError for unexpected file extensions.

    Exported data is currently unconverted (multiplier and constant not applied).

    :param filename:
        The path to save to.
    :param telemetry_data:
        The telemetry data to export.
    :param step:
        When step=n, only export every nth telemetry frame. Only positive steps are supported.
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
    tag = next(iter(telemetry_data.tags))
    timestamps = list(telemetry_data.get_parameter_values(tag).keys())

    df = pd.DataFrame(index=timestamps)
    for tag in telemetry_data.tags:
        df[tag] = telemetry_data.get_parameter_values(tag, step).values()

    exporter(filename, df)
