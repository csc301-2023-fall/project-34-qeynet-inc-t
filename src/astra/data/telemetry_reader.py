import pandas as pd
import h5py
from pandas import DataFrame
from typing import NewType

# Define NewType
TelemetryData = NewType('TelemetryData', DataFrame)


def _read_telemetry_hdf5(filename: str) -> TelemetryData:
    """
    Read in a hdf5 telemetry file and parse it into a pandas dataframe.
    The data in the "EPOCH" column is translated into human-readable
    datetime.

    Args:
        filename (str): full path to the telemetry file

    Returns:
        DataFrame: parsed telemetry file as pandas dataframe
    """

    with h5py.File(filename, 'r') as h5file:
        telemetry_dataframe = pd.DataFrame(
            {header: values for header, values in h5file['Data'].items()}
        )
        telemetry_dataframe['EPOCH'] = pd.to_datetime(telemetry_dataframe['EPOCH'], unit='s')
        return TelemetryData(telemetry_dataframe)


# A dictionary that map file extensions to reader functions
_file_readers = {
    'h5': _read_telemetry_hdf5
    # Add more file types and reader functions as needed
}


def read_telemetry(filename: str) -> TelemetryData:
    """
    Read in a telemetry file with the given path and return
    it as a pandas dataframe.
    Raise ValueError when the type of the telemetry is incorrect.

    Args:
        filename (str): full path to the telemetry file

    Returns:
        DataFrame: parsed telemetry file as pandas dataframe
    """
    file_extension = filename.split('.')[-1]
    reader_func = _file_readers.get(file_extension)

    if reader_func is not None:
        return reader_func(filename)
    else:
        keys = ''
        for key in _file_readers.keys():
            keys += '.' + key + ', '
        raise ValueError(f'File has an unexpected type. Expected {keys[:-2]}')
