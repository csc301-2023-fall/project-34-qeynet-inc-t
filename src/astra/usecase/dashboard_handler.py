from .output_boundary import send_data
from .use_case_handlers import UseCaseHandler
from astra.data.datatable import DataTable

SORT = 'SORT'
TAG = 'TAG'
INDEX = 'INDEX'
DESCRIPTION = 'DESCRIPTION'
DESCENDING = '<'
DATA = 'DATA'
CONFIG = 'CONFIG'


class TableReturn:
    """A container for the output of get_data() and output_data() in
    DashBoardHandler

    :param columns: An ordered list of column names to be displayed
    :param timestamp: The timestamp of the currently shown telemetry frame
    :param table: an ordered list of lists containing data for each row
    :param removed: an unordered list of lists containing data for tags
    not currently shown
    """

    def __init__(self):
        self.columns = ['Tag', 'Description', 'Value']
        self.timestamp = None
        self.table = []
        self.removed = []


class DashboardHandler(UseCaseHandler):
    """DashboardHandler is a child class of UseCaseHandler that defines
    data filtering requested by the Telemetry Dashboard

    :param index: the telemetry frame to be shown in the dashboard
    :param sort: indicates what type of sort should be applied to which column.
    A tuple in the form (sort_type, sort_column), where sort_type is one
    of '>' or '<', and sort_column is one of <DATA> or <CONFIG>
    :param tags: a set of all tags that are shown in the dashboard
    """

    sort = None
    index = None
    tags = set()

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
    def _add_tags_to_output(cls, input_tags: set, return_data: TableReturn,
                            data: DataTable) -> None:
        """
        Adds tags from <input_tags> and their relevant data to <output_list>

        :param data: Contain all data stored by the program to date
        :param input_tags: a set of tags to be added to output_list
        :param return_data: The output container to add data to
        """
        telemetry_frame = data.get_telemetry_frame(cls.index)
        data_parameters = data.parameters
        data_tags = data.tags

        for tag in data_tags:
            tag_parameters = data_parameters[tag]
            tag_description = tag_parameters.description
            tag_data = telemetry_frame.data[tag]
            tag_value = str(tag_data) + " " + tag_parameters.units

            new_row = [tag, tag_description, tag_value]

            include_tag = tag in input_tags
            if include_tag:
                return_data.table.append(new_row)
            else:
                return_data.removed.append(tag)

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
    def get_data(cls, data: DataTable):
        """
        An implementation of get_data for the Telemetry Dashboard to create a
        data table pertaining to a single telemetry frame with data filtering
        requested by the user

        :param data: Contain all data stored by the program to date
        :return: An instance of TableReturn where the <table> attribute
        represents the ordered rows to be presented in the Telemetry Dashboard
        table, and removed represents all tags not shown presently

        PRECONDITIONS: <cls.index> is not None and <cls.tags> is not empty
        """

        telemetry_frame = data.get_telemetry_frame(cls.index)
        return_data = TableReturn()

        # First, creating each row for tags that should be included
        cls._add_tags_to_output(cls.tags, return_data, data)

        # Next, determine if any sorting was requested
        cls._sort_output(return_data)

        return_data.timestamp = telemetry_frame.timestamp

        send_data(return_data)
        return return_data

    @classmethod
    def update_data(cls, previous_table: TableReturn):
        """
        An implementation of update_data for the Telemetry Dashboard to update fields
        based on new sorting requests from the user

        :param previous_table: A representation of the current shown data in
        the Telemetry Dashboard

        PRECONDITIONS: <cls.tags> is not empty
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
        send_data(previous_table)