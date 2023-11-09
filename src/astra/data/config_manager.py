from yaml import safe_load

# import parameters
from astra.data.database.db_manager import (
    create_update_device,
    create_update_tag,
    create_update_alarm,
)
from astra.data.parameters import DisplayUnit, Parameter, Tag


def _read_config_yaml(filename: str) -> None:
    """
    Read in a yaml configuration file and parse it into a pandas dataframe.
    The data in the "alarm" column is temporarily removed to
    improve the readability of the dataframe.

    Args:
        filename (str): full path to the config file
    """
    with open(filename, "r") as yaml_file:
        config_contents = safe_load(yaml_file)
        metadata = config_contents["metadata"]
        dictionary_of_tags = config_contents["tags"]

        # create or update the device in database
        device = create_update_device(metadata)

        for tag_dict in dictionary_of_tags:
            # create or update the tags in database
            tag = list(tag_dict.keys())[0]
            create_update_tag(
                tag_name=tag, tag_parameter=tag_dict[tag], device_id=device
            )

        # create or update the alarms in database
        dictionary_of_alarms = config_contents["alarms"]
        create_update_alarm(dictionary_of_alarms, device_id=device)


def yaml_tag_parser(tag_dict: dict) -> dict:
    """
        A helper function for yaml reader that parse the tag
        data into a dictionary.

    Args:
        tag_data (dict): a dictionary that contains the tag data
                         (setpoint, dtype, display_units)

    Raises:
        ValueError: when the dtype is not int, float, or bool

    Returns:
        dict: a dictionary that contains the parsed tag data
    """
    tag_id = list(tag_dict.keys())[0]
    tag_data = tag_dict[tag_id]
    if tag_data["setpoint"] is not None:
        setpoint = tag_data["setpoint"]
    else:
        setpoint = None

    if tag_data["dtype"] == "int":
        dtype = int
    elif tag_data["dtype"] == "float":
        dtype = float
    elif tag_data["dtype"] == "bool":
        dtype = bool
    else:
        raise ValueError

    if tag_data["display_units"] is not None:
        display_units = DisplayUnit(
            description=tag_data["display_units"]["description"],
            symbol=tag_data["display_units"]["symbol"],
            multiplier=tag_data["display_units"]["multiplier"],
            constant=tag_data["display_units"]["constant"],
        )
    else:
        display_units = None

    return Parameter(
        tag=Tag(tag_id),
        description=tag_data["description"],
        dtype=dtype,
        setpoint=setpoint,
        display_units=display_units,
    )


# A dictionary that map file extensions to reader functions
_file_readers = {
    "yaml": _read_config_yaml
    # Add more file types and reader functions as needed
}


def read_config(filename: str) -> None:
    """
    Read in a configuration file with the given path and return
    it as a pandas dataframe.
    Raise ValueError when the type of the configuration is incorrect.

    Args:
        filename (str): full path to the config file
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
    read_config("database/DF71ZLMI9W.yaml")
    # read_config("test_config1.yaml")
    # read_config("test_config2.yaml")
    # read_config("test_config3.yaml")
