from dataclasses import dataclass
from datetime import datetime
from .use_case_handlers import UseCaseHandler
from astra.data.data_manager import DataManager
from astra.data.telemetry_data import TelemetryData
from astra.data.parameters import Parameter, ParameterValue

SORT = 'SORT'
TAG = 'TAG'
INDEX = 'INDEX'
DESCRIPTION = 'DESCRIPTION'
DESCENDING = '<'
DATA = 'DATA'
CONFIG = 'CONFIG'


@dataclass
class TableReturn:
    """A container for the output of get_data() and output_data() in
    DashBoardHandler

    :param columns: An ordered list of column names to be displayed
    :param timestamp: The timestamp of the currently shown telemetry frame
    :param table: an ordered list of lists containing data for each row
    :param removed: an unordered list of lists containing data for tags
    not currently shown
    """
    timestamp: datetime
    table: list[list[str]]
    removed: list[list[str]]
    frame_quantity: int


class DashboardHandler(UseCaseHandler):
    """DashboardHandler is a child class of UseCaseHandler that defines
    data filtering requested by the Telemetry Dashboard

    :param index: the telemetry frame to be shown in the dashboard
    :param sort: indicates what type of sort should be applied to which column.
    A tuple in the form (sort_type, sort_column), where sort_type is one
    of '>' or '<', and sort_column is one of <DATA> or <CONFIG>
    :param tags: a set of all tags that are shown in the dashboard
    :param start_time: the first time of telemetry frames to examined
    :param end_time: the last time of telemetry frames to be examined
    """

    sort = None
    index = None
    tags = set()
    start_time = None
    end_time = None

    @classmethod
    def set_index(cls, index: int):
        """
        Updates the index to be shown in the Telemetry Dashboard

        PRECONDITION: <index> refers to a valid index of telemetry frames

        :param index: the value for this key will be a tuple storing an
             integer indicating the index of the telemetry frame to view
        """
        cls.index = index

    @classmethod
    def set_sort(cls, sort: tuple[str, str]):
        """
        Updates the sorting filter to be applied

        PRECONDITION: in <sort>

        :param sort: the first value in the tuple for this key will
             be either ">", indicating sorting by increasing values,
             and "<" indicating sorting by decreasing values. The second
             value will indicate the name of the column to sort by.
        """

        cls.sort = sort

    @classmethod
    def add_shown_tag(cls, tag: str):
        """
        Adds <tag> to the set of tags to be shown

        PRECONDITION: <tag> is an element of <cls.tags>

        :param tag: the tag name to be added
        """
        cls.tags.add(tag)

    @classmethod
    def set_shown_tag(cls, tags: str):
        """
        sets <tags> to the set of tags to be shown

        PRECONDITION: <tag> is an element of <cls.tags>

        :param tags: a set of tags to show
        """
        cls.tags = tags

    @classmethod
    def remove_shown_tag(cls, tag: str):
        """
        Removes <tag> from the set of tags to be shown

        PRECONDITION: <tag> is an element of <cls.tags>

        :param tag: the tag name to be removed
        """
        cls.tags.remove(tag)

    @classmethod
    def set_start_time(cls, start_time: datetime):
        """
        Modifies <cls.start_time> to be equal to <start_time>

        :param start_time: the datetime to be set
        """
        cls.start_time = start_time

    @classmethod
    def set_end_time(cls, end_time: datetime):
        """
        Modifies <cls.end_time> to be equal to <end_time>

        :param end_time: the datetime to be set
        """
        cls.end_time = end_time

    @classmethod
    def _eval_param_value(cls, tag_parameter: Parameter,
                          tag_data: ParameterValue) -> float | int | bool | None:
        """
        Converts the raw <parameter_data> into its true value using the
        parameter multiplier and constant

        :param tag_parameter: Parameter data for the relevant tag
        :param tag_data: The raw data in the telemetry frame
        :return: The converted parameter value
        """
        if type(tag_data) is bool or tag_data is None:
            return tag_data
        else:
            multiplier = tag_parameter.display_units.multiplier
            constant = tag_parameter.display_units.constant
            return tag_data * multiplier + constant

    @classmethod
    def _add_rows_to_output(cls, input_tags: set, dm: DataManager, td: TelemetryData,
                            timestamp: datetime) -> tuple[list[list[str]], list[list[str]]]:
        """
        Adds tags from <input_tags> and their relevant data to <output_list>

        :param dm: Contain all data stored by the program to date
        :param input_tags: a set of tags to be added to output_list
        :return A tuple of two 2D lists. The first contains an ordered list
        of tag data to be shown to the user, the other an unordered list of
        tag data to not yet be shown to the user
        """

        data_parameters = dm.parameters
        data_tags = dm.tags

        include = []
        removed = []

        for tag in data_tags:

            tag_parameters = data_parameters[tag]
            tag_description = tag_parameters.description

            # creating the string for the tag value
            raw_tag_data = td.get_parameter_values(tag)
            raw_timestamp_data = raw_tag_data[timestamp]
            tag_data = cls._eval_param_value(tag_parameters, raw_timestamp_data)

            # creating the string for the tag setpoint value
            raw_tag_setpoint_value = tag_parameters.setpoint
            tag_setpoint_value = cls._eval_param_value(
                tag_parameters, raw_tag_setpoint_value)

            if type(tag_data) is bool:
                tag_value = f'{tag_data}'
                tag_setpoint = f'{tag_setpoint_value}'
            elif raw_tag_setpoint_value is None:
                unit_symbol = tag_parameters.display_units.symbol
                tag_value = f'{tag_data} {unit_symbol}'
                tag_setpoint = f'{tag_setpoint_value}'
            else:
                unit_symbol = tag_parameters.display_units.symbol
                tag_value = f'{tag_data} {unit_symbol}'
                tag_setpoint = f'{tag_setpoint_value} {unit_symbol}'

            include_tag = tag in input_tags
            if include_tag:
                include.append([tag, tag_description, tag_value, tag_setpoint])
            else:
                removed.append([tag, tag_description, tag_value, tag_setpoint])
        return include, removed

    @classmethod
    def _sort_output(cls, return_data: TableReturn):
        """
        sorts the <table> field of return_data based on cls.sort

        :param return_data: the output container to sort data from
        """
        if cls.sort is not None:
            # Determining which column to sort by
            if cls.sort[1] == TAG:
                key_index = 0
            else:
                # This case indicates sorting should occur by description
                key_index = 1

            # By default, sorting occurs by ascending values, so a case is
            # needed to check if it should occur by descending order
            reverse = False
            if cls.sort[0] == DESCENDING:
                reverse = True

            return_data.table = sorted(return_data.table,
                                       key=lambda x: x[key_index],
                                       reverse=reverse)

    @classmethod
    def get_data(cls, dm: DataManager):
        """
        An implementation of get_data for the Telemetry Dashboard to create a
        data table pertaining to a single telemetry frame with data filtering
        requested by the user

        :param model: The model of currently shown data
        :param dm: Contain all data stored by the program to date
        :return: An instance of TableReturn where the <table> attribute
        represents the ordered rows to be presented in the Telemetry Dashboard
        table, and removed represents all tags not shown presently

        PRECONDITIONS: <cls.index> is not None, and <cls.tags> is not empty
        """

        telemetry_data = dm.get_telemetry_data(
            cls.start_time, cls.end_time, cls.tags)
        telemetry_frame = telemetry_data.get_telemetry_frame(cls.index)

        # First, all the return data
        timestamp = telemetry_frame.time
        include, remove = cls._add_rows_to_output(cls.tags, dm, telemetry_data, timestamp)
        frame_quantity = telemetry_data.num_telemetry_frames

        return_data = TableReturn(timestamp, include, remove, frame_quantity)

        # Next, determine if any sorting was requested
        cls._sort_output(return_data)

        return return_data

    @classmethod
    def update_data(cls, previous_table: TableReturn):
        """
        An implementation of update_data for the Telemetry Dashboard to update fields
        based on new sorting requests from the user

        :param previous_table: A representation of the current shown data in
        the Telemetry Dashboard
        """

        # Technically inefficient, but far better than re-building every time.
        # Potential choice for optimization if needed
        if len(previous_table.table) < len(cls.tags):
            # Indicates some tag from <previous_table.removed> needs to be shown
            for i in range(len(previous_table.removed)):
                removed_row = previous_table.removed[i]
                if removed_row[0] in cls.tags:
                    previous_table.removed.remove(removed_row)
                    previous_table.table.append(removed_row)
                    break
        elif len(previous_table.table) > len(cls.tags):
            # Indicates some tag from <previous_table.table> needs to be removed
            for i in range(len(previous_table.table)):
                removed_row = previous_table.table[i]
                if removed_row[0] not in cls.tags:
                    previous_table.removed.append(removed_row)
                    previous_table.table.remove(removed_row)
                    break

        cls._sort_output(previous_table)
