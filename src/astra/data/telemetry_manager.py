"""This module provides functionality for reading telemetry files."""

from datetime import datetime

import h5py
import yaml
import pandas as pd

from astra.data.database.db_manager import (
    get_device,
    engine,
    get_tag_id_name,
)
from astra.data.database.db_initializer import Device


def _read_telemetry_hdf5(filename: str) -> datetime:
    """
    Read in a hdf5 telemetry file and parse it into a pandas dataframe.
    The data in the "EPOCH" column is translated into human-readable
    datetime.
    The data is then written to the database.

    :param filename: full path to the telemetry file

    :return: earliest timestamp in the telemetry data
    """

    with h5py.File(filename, "r") as h5file:
        # get the device name
        telemetry_metadata = h5file["metadata"]
        device_name = telemetry_metadata.attrs["device"]
        device = get_device(device_name)
        if device:
            included_tags = set(h5file["telemetry"].keys())
            excluded_tags = {
                tag_name for _, tag_name in get_tag_id_name(device_name)
            } - included_tags
            [values_length] = {
                len(values) for values in h5file["telemetry"].values()
            }
            # get the telemetry data and use pandas to store it in a dataframe
            # use None for parameters not included in the telemetry file
            telemetry_data = pd.DataFrame(
                {
                    header: values
                    for header, values in h5file["telemetry"].items()
                }
                | {
                    tag_name: [None] * values_length
                    for tag_name in excluded_tags
                }
            )

            # write the data to database
            earliest_added_timestamp = _dataframe_to_database(
                telemetry_data, device
            )

            # return the earliest timestamp in the telemetry data
            return earliest_added_timestamp
        else:
            raise ValueError("Device does not exist in database")


def _read_telemetry_yaml(filename: str) -> datetime:
    """
    Read in a yaml telemetry file and store it in the database.

    :param filename: full path to the telemetry file

    :return: earliest timestamp in the telemetry data
    """
    with open(filename, "r") as yaml_file:
        # Load the yaml file and get the data
        config_contents = yaml.safe_load(yaml_file)
        metadata = config_contents["metadata"]
        telemetry_data = config_contents["telemetry"]
        device_name = metadata["device"]
        device = get_device(device_name)

        if device:
            included_tags = set(telemetry_data.keys())
            excluded_tags = {
                tag_name for _, tag_name in get_tag_id_name(device_name)
            } - included_tags
            [values_length] = {
                len(values) for values in telemetry_data.values()
            }
            # get the telemetry data and use pandas to store it in a dataframe
            # use None for parameters not included in the telemetry file
            telemetry_dataframe = pd.DataFrame(
                {header: values for header, values in telemetry_data.items()}
                | {
                    tag_name: [None] * values_length
                    for tag_name in excluded_tags
                }
            )

            # create a dataframe from the telemetry data
            earliest_added_timestamp = _dataframe_to_database(
                telemetry_dataframe, device
            )

            # return the earliest timestamp in the telemetry data
            return earliest_added_timestamp
        else:
            raise ValueError("Device does not exist in database")


# A dictionary that maps file extensions to reader functions
_file_readers = {
    "h5": _read_telemetry_hdf5,
    "yaml": _read_telemetry_yaml
    # Add more file types and reader functions as needed
}


def _dataframe_to_database(
    telemetry_data: pd.DataFrame, device: Device
) -> datetime:
    """Helper function: save data from a pandas dataframe to the database.

    :param telemetry_data: the telemetry data in the form of a pandas dataframe --
    should have an EPOCH column for timestamps and one column for each parameter

    :return: earliest timestamp in the telemetry data
    """
    # convert EPOCH to datetime
    telemetry_data["timestamp"] = pd.to_datetime(
        telemetry_data["EPOCH"], unit="s"
    )
    telemetry_data = telemetry_data.drop(columns=["EPOCH"])
    earliest_added_timestamp = min(telemetry_data["timestamp"])

    # convert the dataframe to long format for database insertion
    telemetry_data = pd.melt(
        telemetry_data, id_vars=["timestamp"], value_name="value"
    )
    telemetry_data.rename(columns={"variable": "tag_name"}, inplace=True)

    # map tag_name to tag_id
    tag_id_map = {}
    tag_id_name = get_tag_id_name(device.device_name)
    for tag_id, tag_name in tag_id_name:
        tag_id_map[tag_name] = tag_id
    telemetry_data["tag_id"] = telemetry_data["tag_name"].map(tag_id_map)
    telemetry_data = telemetry_data.drop(columns=["tag_name"])

    # add last_modified column with the current time
    telemetry_data["last_modified"] = datetime.now()

    # write the data to database
    telemetry_data.to_sql(
        name="Data",
        con=engine,
        if_exists="append",
        index=False,
        method="multi",
    )

    return earliest_added_timestamp


def read_telemetry(filename: str) -> datetime:
    """
    Read in a telemetry file with the given path and save the telemetry data in the database.

    :param filename: full path to the telemetry file

    :raise ValueError: when the type of the telemetry is incorrect

    :return: earliest timestamp in the telemetry data
    """
    file_extension = filename.split(".")[-1]
    reader_func = _file_readers.get(file_extension)

    if reader_func is not None:
        return reader_func(filename)
    else:
        keys = ""
        for key in _file_readers.keys():
            keys += "." + key + ", "
        raise ValueError(f"File has an unexpected type. Expected {keys[:-2]}")


if __name__ == "__main__":
    read_telemetry("database/DF71ZLMI9W_2023-10-11_15-30-00.h5")
