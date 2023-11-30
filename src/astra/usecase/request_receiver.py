
from abc import ABC, abstractmethod
from datetime import datetime
from queue import Queue
from threading import Thread
from typing import Any, Iterable
from .alarm_checker import check_alarms
from .use_case_handlers import TelemetryTableReturn, UseCaseHandler
from .dashboard_handler import DashboardHandler, TableReturn, DashboardFilters
from astra.data.data_manager import DataManager, AlarmsContainer
from ..data.parameters import Tag

VALID_SORTING_DIRECTIONS = {'>', '<'}
VALID_SORTING_COLUMNS = {'TAG', 'DESCRIPTION'}
DATA = 'DATA'
CONFIG = 'CONFIG'


class RequestReceiver(ABC):
    """
    RequestReceiver is an abstract class that defines the interface for front end data requests.
    """

    handler: UseCaseHandler

    @abstractmethod
    def create(self, dm: DataManager):
        """
        create is a method that creates a new data table.
        """
        pass

    @abstractmethod
    def update(self, previous_data: Any, dm: DataManager = None):
        """
        update is a method that updates the currently represented information
        """
        pass


class DashboardRequestReceiver(RequestReceiver):
    """
    DashboardRequestReceiver is a class that implements the RequestReceiver interface.
    It handles requests from the dashboard, such as creating the initial data table,
    updating the currently represented information, changing the index of the datatable
    that we are viewing, adding or removing a tag from the set of tags that we are viewing,
    and updating the sorting filter to be applied.
    """

    filters = DashboardFilters(None, None, None, None, None)
    handler = DashboardHandler()
    search_cache = dict()
    search_eviction = Queue()

    @classmethod
    def create(cls, dm: DataManager) -> TableReturn:
        """
        Create is a method that creates the initial data table,
        with all tags shown, no sorting applied and at the first index.

        :param model: The model of currently shown data
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
        return cls.handler.get_data(dm, cls.filters)

    @classmethod
    def update(cls, previous_data: TelemetryTableReturn, dm: DataManager | None = None):
        """
        update is a method that updates the currently represented information
        """
        cls.handler.update_data(previous_data, cls.filters)

    @classmethod
    def change_index(cls, index: int) -> bool:
        """
        change_index changes the index of the datatable
        that we are viewing. It returns True if it was successful and False otherwise.

        :param dm: The interface for getting all data known to the program
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
        :param previous_table: the previous table that was in the view.
        :returns: True if the tag was successfully added and False otherwise.
        """
        if cls.filters.tags is None:
            cls.filters.tags = set()

        # Determine if we can add the tag to the set of tags that we are viewing.
        tag_index = add.index(':')
        add_tag = add[:tag_index]
        if add_tag not in cls.filters.tags:
            cls.filters.tags.add(add_tag)
            return True
        else:
            # Tag was already in the set of tags that we are viewing.
            return False

    @classmethod
    def set_shown_tags(cls, tags: Iterable[str]):
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

        :param previous_table: The previous table that was in the view.
        :param remove: The tag that we want to remove from the set of tags that we are viewing.
        :return: True if the tag was successfully removed and False otherwise.
        """
        if cls.filters.tags is None:
            cls.filters.tags = set()

        # Determine if we can remove the tag from the set of tags that we are viewing.
        tag_index = remove.index(':')
        remove_tag = remove[:tag_index]
        if remove_tag in cls.filters.tags:
            cls.filters.tags.remove(remove_tag)
            return True
        else:
            return False  # Tag was not in the set of tags that we are viewing.

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
    def search_tags(cls, search: str, dm: DataManager) -> list[Tag]:
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


class DataRequestReceiver(RequestReceiver):
    """
    Receives new data files and updates our programs database accordingly.
    """

    file = None
    alarms = None

    @classmethod
    def set_filename(cls, file):
        cls.file = file

    @classmethod
    def get_alarms(cls) -> AlarmsContainer:
        return cls.alarms

    @classmethod
    def create(cls, dm: DataManager) -> DataManager:
        """
        create is a method that creates a new data table and returns it based
        on the filename provided.

        :param dm: The interface for getting all data known to the program
        """
        cls.alarms = dict()
        return dm.from_device_name(cls.file)

    @classmethod
    def update(cls, previous_data: DataManager, dm: DataManager = None) -> None:
        """
        update is a method that updates the database based on the filename provided.
        """
        if cls.alarms is None:
            cls.alarms = AlarmsContainer()

        earliest_time = previous_data.add_data_from_file(cls.file)

        checking_thread = Thread(target=check_alarms, args=[previous_data, earliest_time])
        checking_thread.start()
