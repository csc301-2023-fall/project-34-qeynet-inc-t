from astra.data.data_manager import DataManager
from astra.data.parameters import Parameter, ParameterValue, Tag
from astra.data.telemetry_data import TelemetryData


# Module defines a number of common operations across classes

def eval_param_value(tag_parameter: Parameter,
                     tag_data: ParameterValue | None) -> float | int | bool | None:
    """
    Converts the raw <parameter_data> into its true value using the
    parameter multiplier and constant

    :param tag_parameter: Parameter data for the relevant tag
    :param tag_data: The raw data in the telemetry frame
    :return: The converted parameter value
    """
    if tag_data is None:
        return None
    elif tag_parameter.display_units is None:
        return tag_data
    else:
        multiplier = tag_parameter.display_units.multiplier
        constant = tag_parameter.display_units.constant
        return tag_data * multiplier + constant


def get_tag_param_value(index: int, tag: Tag, td: TelemetryData) -> ParameterValue | None:
    """
    Extracts ParameterValue of <tag> in the <index>-th TelemetryFrame of TelemetryData

    :param index: The index of TelemetryData to access
    :param tag: The tag whose data is to be required
    :param td: The telemetry data to extract from
    :return: The ParameterValue of <tag> in <td> at index <index>
    """

    telemetry_frame = td.get_telemetry_frame(index)
    return telemetry_frame.data[tag]


def get_tag_params(tag: Tag, dm: DataManager) -> Parameter:
    """
    Returns the Parameter object associated with <tag>

    :param tag: The tag to get data associated to
    :param dm: The manager of all data in the program
    :return: The Parameter associated to <tag>
    """
    data_parameters = dm.parameters
    return data_parameters[tag]
