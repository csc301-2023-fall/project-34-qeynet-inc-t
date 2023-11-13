import queue
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Iterable
from .use_case_handlers import UseCaseHandler
from .dashboard_handler import DashboardHandler, TableReturn, DashboardFilters
from astra.data.data_manager import DataManager
from ..data.alarms import Alarm, AlarmPriority
from ..data.parameters import Tag
from .alarm_checker import check_alarms

DATA = 'DATA'
CONFIG = 'CONFIG'
WARNING = 'WARNING'
LOW = 'LOW'
MEDIUM = 'MEDIUM'
HIGH = 'HIGH'
CRITICAL = 'CRITICAL'


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

    filters = None
    handler = DashboardHandler
    search_cache: dict[str: list[Tag]]
    search_eviction: queue

    @classmethod
    def __init__(cls):
        cls.handler = DashboardHandler()
        cls.filters = DashboardFilters(None, None, None, None, None)
        cls.search_cache = dict()
        cls.search_eviction = queue.Queue()

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
        cls.filters.tags = all_tags

        if len(cls.search_cache) == 0:
            cls.search_cache[''] = all_tags

        # Set the index to the first index by default.
        if cls.filters.index is None:
            cls.filters.index = 0

        # Create the initial table.
        return cls.handler.get_data(dm, cls.filters)

    @classmethod
    def update(cls, previous_data: TableReturn, dm: DataManager = None):
        """
        update is a method that updates the currently represented information
        """
        cls.handler.update_data(previous_data, cls.filters)

    @classmethod
    def change_index(cls, index: int) -> bool:
        """
        change_index changes the index of the datatable
        that we are viewing.
        It returns True if it was successful and False otherwise.
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
        that we are viewing.
        It returns True if it was successful and False otherwise.
        :param add: the tag that we want to add to the set of tags that we are viewing.
        :param previous_table: the previous table that was in the view.
        :returns: True if the tag was successfully added and False otherwise.
        """

        # Determine if we can add the tag to the set of tags that we are viewing.
        if add not in cls.filters.tags:
            cls.filters.tags.append(add)
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
        cls.filters.tags = tags

    @classmethod
    def remove_shown_tag(cls, remove: str) -> bool:
        """
        Remove a tag from the set of tags that we are viewing.
        It returns True if it was successful and False otherwise.
        :param previous_table: The previous table that was in the view.
        :param remove: The tag that we want to remove from the set of tags that we are viewing.
        :return: True if the tag was successfully removed and False otherwise.
        """
        # Determine if we can remove the tag from the set of tags that we are viewing.
        if remove in cls.filters.tags:
            cls.filters.tags.remove(remove)
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
        :param previous_table: the previous table that was in the view.
        :returns: True if the sorting filter was successfully updated and False otherwise.
        """
        valid_sorting_directions = {'>', '<'}
        valid_columns = {DATA, CONFIG}

        # Determine if the sorting filter is valid.
        if sort[0] not in valid_sorting_directions:
            return False
        if sort[1] not in valid_columns:
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
    def search_tags(cls, search: str) -> list[Tag]:
        """
        Finds all tags in <cls.filters.tags> where <search> is a substring

        :param search: The substring to search for
        :return: A list of all satisfying tags
        """
        if len(cls.search_cache) == 0:
            return []
        return cls.handler.search_tags(search, cls.search_cache, cls.search_eviction)


class AlarmsRequestReceiver(RequestReceiver):
    """
    AlarmsRequestReceiver is a class that implements the RequestReceiver interface.
    It handles requests from the alarms tab, such as creating the initial data table,
    updating the currently represented information, changing the index of the datatable
    that we are viewing, adding or removing a tag from the set of tags that we are viewing,
    and updating the sorting filter to be applied.
    """

    # TODO move to its own module.

    filters = None
    handler = AlarmsHandler

    @classmethod
    def __init__(cls):
        cls.handler = DashboardHandler()
        cls.filters = AlarmsFilters(None, None, None, None, None, None, None)
        # maybe make this inherit from dashboard filters
        # Im assuming the alarms filter will have:
        # (sort, index, priority, criticality, alarm_type, start_time, end_time)

    # TODO new type for the return.
    @classmethod
    def create(cls, dm: DataManager) -> TableReturn:
        """
        Create is a method that creates the initial data table,
        with all priorities/types/criticalities shown, no sorting applied and at the first index.
        :param model: The model of currently shown data
        :param dm: Contains all data stored by the program to date.
        """

        criticalities = [WARNING, LOW, MEDIUM, HIGH, CRITICAL]
        priorities = [WARNING, LOW, MEDIUM, HIGH, CRITICAL]

        # add all priorities and criticalities to the shown priorities and criticalities by default
        cls.filters.criticalities = criticalities
        cls.filters.priorities = priorities

        # get all alarm types from dm
        all_types = []  # TODO figure out how to get all alarm types from dm

        # Add all types to the shown types by default.
        cls.filters.types = all_types

        # Set the index to the first index by default.
        if cls.filters.index is None:
            cls.filters.index = 0

        # Create the initial table.
        return cls.handler.get_data(dm, cls.filters)

    # TODO new type for the previous_data
    @classmethod
    def update(cls, previous_data: TableReturn, dm: DataManager = None):
        """
        update is a method that updates the currently represented information
        """
        cls.handler.update_data(previous_data, cls.filters)

    @classmethod
    def change_index(cls, index: int) -> bool:
        """
        change_index changes the index of the datatable
        that we are viewing.
        It returns True if it was successful and False otherwise.
        :param dm: The interface for getting all data known to the program
        :param index: the index of the datatable that we want to change to.
        :returns: True if the index was successfully changed and False otherwise.
        """

        cls.filters.index = index

    @classmethod
    def add_shown_priority(cls, add: str) -> bool:
        """
        add_shown_priority is a method that adds a priority to the set of priorities
        that we are viewing.
        It returns True if it was successful and False otherwise.
        :param add: the priority that we want to add to the set of priorities that we are viewing.
        :param previous_table: the previous table that was in the view.
        :returns: True if the priority was successfully added and False otherwise.
        """

        # Determine if we can add the priority to the set of priorities that we are viewing.
        if add not in cls.filters.priorities:
            cls.filters.priorities.append(add)
            return True
        else:
            # Priority was already in the set of priorities that we are viewing.
            return False

    @classmethod
    def add_shown_criticality(cls, add: str) -> bool:
        """
        add_shown_criticality is a method that adds a criticality to the set of criticalities
        that we are viewing.
        It returns True if it was successful and False otherwise.
        :param add: the criticality that we want to add to the set of criticalities that we 
        are viewing.
        :param previous_table: the previous table that was in the view.
        :returns: True if the criticality was successfully added and False otherwise.
        """

        # Determine if we can add the criticality to the set of criticalities that we are viewing.
        if add not in cls.filters.criticailities:
            cls.filters.criticalities.append(add)
            return True
        else:
            # Criticality was already in the set of criticalities that we are viewing.
            return False

    @classmethod
    def add_shown_type(cls, add: str) -> bool:
        """
        add_shown_type is a method that adds a type to the set of types
        that we are viewing.
        It returns True if it was successful and False otherwise.
        :param add: the type that we want to add to the set of types that we are viewing.
        :param previous_table: the previous table that was in the view.
        :returns: True if the type was successfully added and False otherwise.
        """

        # Determine if we can add the type to the set of types that we are viewing.
        if add not in cls.filters.types:
            cls.filters.types.append(add)
            return True
        else:
            # Type was already in the set of types that we are viewing.
            return False

    @classmethod
    def set_shown_priorities(cls, priorities: Iterable[Tag]):
        """
        Sets <cls.filters.priorities> to the set of priorities to be shown

        PRECONDITION: <priority> is an element of <cls.filters.priorities>

        :param priorities: a set of priorities to show
        """
        cls.filters.priorities = priorities

    @classmethod
    def set_shown_criticalities(cls, criticalities: Iterable[Tag]):
        """
        Sets <cls.filters.criticalities> to the set of criticalities to be shown

        PRECONDITION: <criticality> is an element of <cls.filters.criticalities>

        :param criticalities: a set of criticalities to show
        """
        cls.filters.criticalities = criticalities

    @classmethod
    def set_shown_types(cls, types: Iterable[Tag]):
        """
        Sets <cls.filters.types> to the set of types to be shown

        PRECONDITION: <type> is an element of <cls.filters.types>

        :param types: a set of types to show
        """
        cls.filters.types = types

    @classmethod
    def remove_shown_priority(cls, remove: str) -> bool:
        """
        Remove a priority from the set of priorities that we are viewing.
        It returns True if it was successful and False otherwise.
        :param previous_table: The previous table that was in the view.
        :param remove: The priority that we want to remove from the set of priorities that 
        we are viewing.
        :return: True if the priority was successfully removed and False otherwise.
        """
        # Determine if we can remove the priority from the set of priorities that we are viewing.
        if remove in cls.filters.priorities:
            cls.filters.priorities.remove(remove)
            return True
        else:
            # Priority was not in the set of priorities that we are viewing.
            return False

    @classmethod
    def remove_shown_criticality(cls, remove: str) -> bool:
        """
        Remove a criticality from the set of criticalities that we are viewing.
        It returns True if it was successful and False otherwise.
        :param previous_table: The previous table that was in the view.
        :param remove: The criticality that we want to remove from the set of criticalities that
        we are viewing.
        :return: True if the criticality was successfully removed and False otherwise.
        """
        # Determine if we can remove the criticality from the set of criticalities that
        # we are viewing.
        if remove in cls.filters.criticalities:
            cls.filters.criticalities.remove(remove)
            return True
        else:
            # Criticality was not in the set of criticalities that we are viewing.
            return False

    @classmethod
    def remove_shown_type(cls, remove: str) -> bool:
        """
        Remove a type from the set of types that we are viewing.
        It returns True if it was successful and False otherwise.
        :param previous_table: The previous table that was in the view.
        :param remove: The type that we want to remove from the set of types that we are viewing.
        :return: True if the type was successfully removed and False otherwise.
        """
        # Determine if we can remove the type from the set of types that we are viewing.
        if remove in cls.filters.types:
            cls.filters.types.remove(remove)
            return True
        else:
            # Type was not in the set of types that we are viewing.
            return False

    @classmethod
    def update_sort(cls, sort: tuple[str, str]) -> bool:
        """
        Updates the sorting filter to be applied.
        It returns True if the sorting filter was successfully applied and False otherwise.
        :param sort: the first value in the tuple for this key will
             be either ">", indicating sorting by increasing values,
             and "<" indicating sorting by decreasing values. The second
             value will indicate the name of the column to sort by.
        :param previous_table: the previous table that was in the view.
        :returns: True if the sorting filter was successfully updated and False otherwise.
        """
        valid_sorting_directions = {'>', '<'}
        valid_columns = []  # TODO figure out what columns we have

        # Determine if the sorting filter is valid.
        if sort[0] not in valid_sorting_directions:
            return False
        if sort[1] not in valid_columns:
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
    def get_alarms(cls) -> dict[AlarmPriority: set[Alarm]]:
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
        earliest_time = previous_data.add_data_from_file(cls.file)
        check_alarms(previous_data, cls.alarms, earliest_time)
