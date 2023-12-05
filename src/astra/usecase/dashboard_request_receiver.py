from datetime import datetime
from queue import Queue
from typing import Iterable

from astra.data.data_manager import DataManager
from astra.data.parameters import Tag
from astra.usecase.dashboard_handler import DashboardHandler
from astra.usecase.filters import DashboardFilters
from astra.usecase.request_receiver import RequestReceiver
from astra.usecase.table_return import TableReturn

VALID_SORTING_DIRECTIONS = {'>', '<'}
VALID_SORTING_COLUMNS = {'TAG', 'DESCRIPTION'}
DATA = 'DATA'
CONFIG = 'CONFIG'
DASHBOARD_HEADINGS = ['TAG', 'DESCRIPTION']


class DashboardRequestReceiver(RequestReceiver):
    """
    DashboardRequestReceiver is a class that implements the RequestReceiver interface.
    It handles requests from the dashboard, such as creating the initial data table,
    updating the currently represented information, changing the index of the datatable
    that we are viewing, adding or removing a tag from the set of tags that we are viewing,
    and updating the sorting filter to be applied.
    """

    filters = DashboardFilters(set(), (">", "TAG"),
                               0, datetime.min, datetime.max)
    handler = DashboardHandler()
    search_cache: dict[str, Iterable[str]] = dict()
    search_eviction: Queue[str] = Queue()
    _sorting = [-1, 1]
    previous_data = None

    @classmethod
    def create(cls, dm: DataManager) -> TableReturn:
        """
        Create is a method that creates the initial data table,
        with all tags shown, no sorting applied and at the first index.

        :param dm: Contains all data stored by the program to date.
        """

        all_tags = dm.tags

        # Add all tags to the shown tags by default.
        if cls.filters.tags is None:
            cls.filters.tags = set(all_tags)

        # Set the index to the first index by default.
        if cls.filters.index is None:
            cls.filters.index = 0

        # Create the initial table.
        cls.previous_data = cls.handler.get_data(dm, cls.filters)
        return cls.previous_data

    @classmethod
    def update(cls):
        """
        update is a method that updates the currently represented information
        """
        if cls.previous_data is not None:
            cls.handler.update_data(cls.previous_data, cls.filters)

    @classmethod
    def change_index(cls, index: int) -> bool:
        """
        change_index changes the index of the datatable
        that we are viewing. It returns True if it was successful and False otherwise.

        :param index: the index of the datatable that we want to change to.
        :returns: True if the index was successfully changed and False otherwise.
        """

        cls.filters.index = index

        # Determine if we can update the view without issues.
        if cls.filters.tags is None:
            return False
        return True

    @classmethod
    def add_shown_tag(cls, add: str) -> bool:
        """
        add_shown_tag is a method that adds a tag to the set of tags
        that we are viewing. It returns True if it was successful and False otherwise.

        :param add: the tag that we want to add to the set of tags that we are viewing.
        :returns: True if the tag was successfully added and False otherwise.
        """
        if cls.filters.tags is None:
            cls.filters.tags = set()

        # Determine if we can add the tag to the set of tags that we are viewing.
        tag_index = add.index(':')
        add_tag = add[:tag_index]
        if add_tag not in cls.filters.tags:
            cls.filters.tags.add(Tag(add_tag))
            return True
        else:
            # Tag was already in the set of tags that we are viewing.
            return False

    @classmethod
    def set_shown_tags(cls, tags: Iterable[Tag]):
        """
        Sets <cls.filters.tags> to the set of tags to be shown

        PRECONDITION: <tag> is an element of <cls.filters.tags>

        :param tags: a set of tags to show
        """
        cls.filters.tags = set(tags)

    @classmethod
    def remove_shown_tag(cls, remove: str) -> bool:
        """
        Remove a tag from the set of tags that we are viewing.
        It returns True if it was successful and False otherwise.

        :param remove: The tag that we want to remove from the set of tags that we are viewing.
        :return: True if the tag was successfully removed and False otherwise.
        """
        if cls.filters.tags is None:
            cls.filters.tags = set()

        # Determine if we can remove the tag from the set of tags that we are viewing.
        tag_index = remove.index(':')
        remove_tag = remove[:tag_index]
        if remove_tag in cls.filters.tags:
            cls.filters.tags.remove(Tag(remove_tag))
            return True
        else:
            return False  # Tag was not in the set of tags that we are viewing.

    @classmethod
    def toggle_sort(cls, heading: str) -> bool:
        """
        Method for toggling sorting on a specific heading
        The headings include (for now):
        - TAG
        - DESCRIPTION
        This method will ask the model to sort the data
        according to which heading was toggled

        Args:
            heading (str): string representing which heading was toggled
        """
        sort_value = -1
        for i in range(len(DASHBOARD_HEADINGS)):
            check_heading = DASHBOARD_HEADINGS[i]
            if heading == check_heading:
                cls._sorting[i] *= -1
                sort_value = cls._sorting[i]
            else:
                cls._sorting[i] = 1

        if sort_value == 1:
            # ascending
            cls.update_sort(('>', heading))
        elif sort_value == -1:
            # descending
            cls.update_sort(('<', heading))
        return sort_value == 1

    @classmethod
    def update_sort(cls, sort: tuple[str, str]) -> bool:
        """
        Updates the sorting filter to be applied.
        It returns True if the sorting filter was successfully applied and False otherwise.

        :param sort: the first value in the tuple for this key will
             be either ">", indicating sorting by increasing values,
             and "<" indicating sorting by decreasing values. The second
             value will indicate the name of the column to sort by.
        :returns: True if the sorting filter was successfully updated and False otherwise.
        """

        # Determine if the sorting filter is valid.
        if sort[0] not in VALID_SORTING_DIRECTIONS:
            return False
        if sort[1] not in VALID_SORTING_COLUMNS:
            return False

        # both if statements failed, so the filter is valid.
        cls.filters.sort = sort
        return True

    @classmethod
    def set_start_time(cls, start_time: datetime):
        """
        Modifies <cls.filters.start_time> to be equal to <start_time>

        :param start_time: the datetime to be set
        """
        cls.filters.start_time = start_time

    @classmethod
    def set_end_time(cls, end_time: datetime):
        """
        Modifies <cls.filters.end_time> to be equal to <end_time>

        :param end_time: the datetime to be set
        """
        cls.filters.end_time = end_time

    @classmethod
    def search_tags(cls, search: str, dm: DataManager) -> Iterable[str]:
        """
        Finds all tags in <cls.filters.tags> where <search> is a substring

        :param search: The substring to search for
        :param dm: The source of all data known to the program
        :return: A list of all satisfying tags
        """
        all_tags = dm.tags
        if len(cls.search_cache) == 0:
            all_params = dm.parameters
            tag_strs = []
            for tag in all_tags:
                param = all_params[tag]
                tag_strs.append(tag + ": " + param.description)
            tag_strs.sort()
            cls.search_cache[''] = tag_strs

        return cls.handler.search_tags(search, cls.search_cache, cls.search_eviction)

    @classmethod
    def get_num_frames(cls) -> int:
        """
        Returns the number of frames from the last call to <cls.create> or <cls.update>

        :return: The number of telemetry frames in consideration
        """
        if cls.previous_data is not None:
            return cls.previous_data.frame_quantity
        else:
            return 0

    @classmethod
    def get_time(cls) -> datetime | None:
        """
        Returns the time of the currently examined frame

        :return: The time of the currently examined frame, or None if no data is in the telemetry dashboard
        """
        if cls.previous_data is not None:
            return cls.previous_data.timestamp
        return None

    @classmethod
    def load_file(cls, file: str, dm: DataManager) -> None:
        """
        Adds a telemetry file to the database

        :param dm: Stores all data known to the program
        :param file: The file storing data to add
        """

    @classmethod
    def get_table_entries(cls) -> list[list] | None:
        """
        Returns the table entries from the previous call to <create> or <update>

        :return: the table entries from the previous call to <create> or <update>
        """
        if cls.previous_data is None:
            return None
        else:
            return cls.previous_data.table
