from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Iterable

from .use_case_handlers import UseCaseHandler
from .dashboard_handler import DashboardHandler, TableReturn
from astra.data.data_manager import DataManager
from ..data.parameters import Tag


# Not sure if this is necessary anymore, request receivers should just be some modules?


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
    def update(self, previous_data: Any):
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

    # TODO what is the type of the table that we are receiving?
    # TODO where do we send the data.

    handler = DashboardHandler

    def __init__(self):
        self.handler = DashboardHandler()

    @classmethod
    def create(cls, dm: DataManager) -> TableReturn:
        """
        create is a method that creates the initial data table,
        with all tags shown, no sorting applied and at the first index.
        :param model: The model of currently shown data
        :param dm: Contains all data stored by the program to date.
        """

        all_tags = dm.tags

        # Add all tags to the shown tags by default.
        cls.handler.set_shown_tag(all_tags)

        # Set the index to the first index by default.
        cls.handler.set_index(0)

        # Create the initial table.
        return cls.handler.get_data(dm)

    @classmethod
    def update(cls, previous_data: TableReturn):
        """
        update is a method that updates the currently represented information
        """
        cls.handler.update_data(previous_data)

    @classmethod
    def change_index(cls, index: int) -> bool:
        """
        change_index changes the index of the datatable
        that we are viewing and then updates the view.
        It returns True if it was successful and False otherwise.
        :param dm: The interface for getting all data known to the program
        :param index: the index of the datatable that we want to change to.
        :returns: True if the index was successfully changed and False otherwise.
        """

        # Liam's Note: due to change in interface, i've removed the index check

        cls.handler.set_index(index)

        # Determine if we can update the view without issues.
        if cls.handler.tags is None:
            return False
        return True

    @classmethod
    def add_shown_tag(cls, add: str) -> bool:
        """
        add_shown_tag is a method that adds a tag to the set of tags
        that we are viewing and then updates the view.
        It returns True if it was successful and False otherwise.
        :param add: the tag that we want to add to the set of tags that we are viewing.
        :param previous_table: the previous table that was in the view.
        :returns: True if the tag was successfully added and False otherwise.
        """

        # Determine if we can add the tag to the set of tags that we are viewing.
        if add not in cls.handler.tags:
            cls.handler.add_shown_tag(add)
            return True
        else:
            return False  # Tag was already in the set of tags that we are viewing.

    @classmethod
    def set_shown_tags(cls, tags: Iterable[Tag]):
        """
        sets <tags> to the set of tags to be shown

        PRECONDITION: <tag> is an element of <cls.tags>

        :param tags: a set of tags to show
        """
        cls.handler.set_shown_tag(tags)

    @classmethod
    def remove_shown_tag(cls, remove: str) -> bool:
        """
        Remove a tag from the set of tags that we are viewing and update the view.
        It returns True if it was successful and False otherwise.
        :param previous_table: The previous table that was in the view.
        :param remove: The tag that we want to remove from the set of tags that we are viewing.
        :return: True if the tag was successfully removed and False otherwise.
        """
        # Determine if we can remove the tag from the set of tags that we are viewing.
        if remove in cls.handler.tags:
            cls.handler.remove_shown_tag(remove)
            return True
        else:
            return False  # Tag was not in the set of tags that we are viewing.

    @classmethod
    def update_sort(cls, sort: tuple[str, str]) -> bool:
        """
        Updates the sorting filter to be applied
        It returns True if the sorting filter was successfully applied and False otherwise.
        :param sort: the first value in the tuple for this key will
             be either ">", indicating sorting by increasing values,
             and "<" indicating sorting by decreasing values. The second
             value will indicate the name of the column to sort by.
        :param previous_table: the previous table that was in the view.
        :returns: True if the sorting filter was successfully updated and False otherwise.
        """
        valid_sorting_directions = {'>', '<'}
        valid_columns = {'TAG', 'DESCRIPTION'}  # TODO confirm this

        # Determine if the sorting filter is valid.
        if sort[0] not in valid_sorting_directions:
            return False
        if sort[1] not in valid_columns:
            return False

        # both if statements failed, so the filter is valid.
        cls.handler.set_sort(sort)
        return True

    @classmethod
    def set_start_time(cls, start_time: datetime):
        """
        Modifies <cls.start_time> to be equal to <start_time>

        :param start_time: the datetime to be set
        """
        cls.handler.set_start_time(start_time)

    @classmethod
    def set_end_time(cls, end_time: datetime):
        """
        Modifies <cls.end_time> to be equal to <end_time>

        :param end_time: the datetime to be set
        """
        cls.handler.set_end_time(end_time)


class DataRequestReceiver(RequestReceiver):
    """
    Receives new data files and updates our programs database accordingly.
    """

    file = None

    @classmethod
    def set_filename(cls, file):
        cls.file = file

    @classmethod
    def create(cls, dm: DataManager) -> DataManager:
        """
        create is a method that creates a new data table and returns it based
        on the filename provided.
        :param model: The model of currently shown data
        :param dm:
        :param device_name: the name of the file to create the data table from.
        """
        return dm.from_device_name(cls.file)

    @classmethod
    def update(cls, previous_data: DataManager) -> None:
        """
        update is a method that updates the database based on the filename provided.
        """
        previous_data.add_data_from_file(cls.file)
