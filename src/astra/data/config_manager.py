import pandas as pd
from yaml import load, FullLoader
from pandas import DataFrame
from typing import NewType

# Define NewType
ConfigData = NewType('ConfigData', DataFrame)


def _read_config_yaml(filename: str) -> ConfigData:
    """
    Read in a yaml configuration file and parse it into a pandas dataframe.
    The data in the "alarm" column is temporarily removed to
    improve the readability of the dataframe.

    Args:
        filename (str): full path to the config file

    Returns:
        DataFrame: parsed config file as pandas dataframe
    """
    with open(filename, 'r') as yaml_file:
        configdata_yaml = load(yaml_file, Loader=FullLoader)
        config_dataframe = (
            pd.DataFrame.from_dict(configdata_yaml)
            .drop('alarm')
            .transpose()
            .reset_index(names='tag')
        )
        return ConfigData(config_dataframe)


# A dictionary that map file extensions to reader functions
_file_readers = {
    'yaml': _read_config_yaml
    # Add more file types and reader functions as needed
}


def read_config(filename: str) -> ConfigData:
    """
    Read in a configuration file with the given path and return
    it as a pandas dataframe.
    Raise ValueError when the type of the configuration is incorrect.

    Args:
        filename (str): full path to the config file

    Returns:
        DataFrame: parsed config file as pandas dataframe
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
