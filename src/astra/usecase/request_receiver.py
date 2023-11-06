from abc import ABC, abstractmethod
from .use_case_handlers import UseCaseHandler
from dashboard_handler import DashboardHandler, TableReturn
from astra.data.datatable import DataTable
from output_boundary import send_data

# Not sure if this is necessary anymore, request receivers should just be some modules?


class RequestReceiver(ABC):
    """
    RequestReceiver is an abstract class that defines the interface for front end data requests.
    """

    handler: UseCaseHandler

    @abstractmethod
    def create(self):
        """
        create is a method that creates a new data table.
        """
        pass

    @abstractmethod
    def update(self):
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

    @staticmethod
    def create(data: DataTable) -> None:
        """
        create is a method that creates the initial data table,
        with all tags shown, no sorting applied and at the first index.
        :param data: Contains all data stored by the program to date.
        """

        all_tags = DataTable.tags

        # Add all tags to the shown tags by default.
        for tag in all_tags:
            DashboardHandler.add_shown_tag(tag)

        # Set the index to the first index by default.
        DashboardHandler.set_index(0)

        # Create the initial table.
        DashboardHandler.get_data(data)

    @staticmethod
    def update():
        """
        update is a method that updates the currently represented information
        """
        pass

    @staticmethod
    def change_index(data: DataTable, index: int) -> bool:
        """
        change_index changes the index of the datatable
        that we are viewing and then updates the view.
        It returns True if it was successful and False otherwise.
        :param index: the index of the datatable that we want to change to.
        :returns: True if the index was successfully changed and False otherwise.
        """

        # Check if we have a valid index.
        if abs(index) > data.num_telemetry_frames:
            return False

        DashboardHandler.set_index(index)

        # Determine if we can update the view without issues.
        if DashboardHandler.tags is None:
            return False

        send_data(DashboardHandler.get_data(data))
        return True

    @staticmethod
    def add_shown_tag(previous_table: TableReturn, add: str) -> bool:
        """
        add_shown_tag is a method that adds a tag to the set of tags
        that we are viewing and then updates the view.
        It returns True if it was successful and False otherwise.
        :param add: the tag that we want to add to the set of tags that we are viewing.
        :param previous_table: the previous table that was in the view.
        :returns: True if the tag was successfully added and False otherwise.
        """

        # Determine if we can add the tag to the set of tags that we are viewing.
        if add not in DashboardHandler.tags:
            DashboardHandler.add_shown_tag(add)
            DashboardHandler.update_data(previous_table)
            return True
        else:
            return False  # Tag was already in the set of tags that we are viewing.

    @staticmethod
    def remove_shown_tag(previous_table: TableReturn, remove: str) -> bool:
        """
        Remove a tag from the set of tags that we are viewing and update the view.
        It returns True if it was successful and False otherwise.
        :param previous_table: The previous table that was in the view.
        :param remove: The tag that we want to remove from the set of tags that we are viewing.
        :return: True if the tag was successfully removed and False otherwise.
        """
        # Determine if we can remove the tag from the set of tags that we are viewing.
        if remove in DashboardHandler.tags:
            DashboardHandler.remove_shown_tag(remove)
            DashboardHandler.update_data(previous_table)
            return True
        else:
            return False  # Tag was not in the set of tags that we are viewing.

    @staticmethod
    def update_sort(previous_table: TableReturn, sort: tuple[str, str]) -> bool:
        """
        Updates the sorting filter to be applied, and then updates the view.
        It returns True if the sorting filter was successfully applied and False otherwise.
        :param sort: the first value in the tuple for this key will
             be either ">", indicating sorting by increasing values,
             and "<" indicating sorting by decreasing values. The second
             value will indicate the name of the column to sort by.
        :param previous_table: the previous table that was in the view.
        :returns: True if the sorting filter was successfully updated and False otherwise.
        """
        valid_sorting_directions = {'>', '<'}
        valid_columns = {'tag', 'description'}  # TODO confirm this

        # Determine if the sorting filter is valid.
        if sort[0] not in valid_sorting_directions:
            return False
        if sort[1] not in valid_columns:
            return False

        # both if statements failed, so the filter is valid.
        DashboardHandler.set_sort(sort)
        DashboardHandler.update_data(previous_table)
        return True


class DataRequestReceiver(RequestReceiver):
    """
    Receives new data files and updates our programs database accordingly.
    """

    def create(filename: str, table: DataTable) -> DataTable:
        """
        create is a method that creates a new data table and returns it based
        on the filename provided.
        :param filename: the name of the file to create the data table from.
        """
        return table.from_config_file(filename)

    def update(filename: str, table: DataTable) -> None:
        """
        update is a method that updates the database based on the filename provided.
        """
        table.add_data_from_file(filename)
