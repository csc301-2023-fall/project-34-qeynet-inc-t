import h5py
import pandas as pd
from database.db_manager import (
    get_device,
    engine,
    get_tag_id_name,
)
from datetime import datetime


def _read_telemetry_hdf5(filename: str) -> datetime:
    """
    Read in a hdf5 telemetry file and parse it into a pandas dataframe.
    The data in the "EPOCH" column is translated into human-readable
    datetime.

    Args:
        filename (str): full path to the telemetry file
    """

    with h5py.File(filename, "r") as h5file:
        # get the device name
        telemetry_metadata = h5file["metadata"]
        device_name = telemetry_metadata.attrs["device"]
        device = get_device(device_name)
        if device:
            # get the telemetry data and use pandas to store it in a dataframe
            telemetry_data = pd.DataFrame(
                {
                    header: values
                    for header, values in h5file["telemetry"].items()
                }
            )

            # convert EPOCH to datetime
            telemetry_data["timestamp"] = pd.to_datetime(
                telemetry_data["EPOCH"], unit="s"
            )
            telemetry_data = telemetry_data.drop(columns=["EPOCH"])
            earliest_added_timestamp = min(telemetry_data["timestamp"])

            # convert the dataframe to long format for database insertion
            telemetry_data = pd.melt(
                telemetry_data, id_vars="timestamp", value_name="value"
            )
            telemetry_data.rename(
                columns={"variable": "tag_name"}, inplace=True
            )

            # map tag_name to tag_id
            tag_id_map = {}
            tag_id_name = get_tag_id_name(device.device_name)
            for tag_id, tag_name in tag_id_name:
                tag_id_map[tag_name] = tag_id
            telemetry_data["tag_id"] = telemetry_data["tag_name"].map(
                tag_id_map
            )
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
        else:
            raise ValueError("Device does not exist in database")


# A dictionary that map file extensions to reader functions
_file_readers = {
    "h5": _read_telemetry_hdf5
    # Add more file types and reader functions as needed
}


def read_telemetry(filename: str) -> datetime:
    """
    Read in a telemetry file with the given path and return
    it as a pandas dataframe.
    Raise ValueError when the type of the telemetry is incorrect.

    Args:
        filename (str): full path to the telemetry file
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
