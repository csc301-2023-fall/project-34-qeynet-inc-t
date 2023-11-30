from dataclasses import dataclass
from datetime import datetime
from astra.data.telemetry_data import TelemetryData


@dataclass
class TableReturn:
    """A container for the output of get_data() and output_data() in
    of certain UseCaseHandlers


    :param table: an ordered list of lists containing data for each row
    :param removed: an unordered list of lists containing data for tags
    not currently shown
    """
    table: list[list]
    removed: list[list]


@dataclass
class TelemetryTableReturn(TableReturn):
    """
    An extension of TableReturn describing more details about the table

    :param frame_quantity: The number of shown frames
    :param timestamp: The timestamp of the currently shown telemetry frame
    :param td: The telemetry data previously examined
    """
    frame_quantity: int
    timestamp: datetime
    td: TelemetryData
