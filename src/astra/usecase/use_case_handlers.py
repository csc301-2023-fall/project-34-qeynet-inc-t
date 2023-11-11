from abc import ABC, abstractmethod
from typing import Any
from astra.data.data_manager import DataManager


class UseCaseHandler(ABC):
    """
    UseCaseHandler is an abstract class that defines the interface for the use
    case handlers.

    Methods:
        get_data(self, filter_data: dict[str, tuple[bool]], data: DataTable):
            Accepts a dictionary for filtering and processes the data
            accordingly.
    """

    @abstractmethod
    def get_data(self, dm: DataManager, filter_args: any):
        """
        get_data is a method that processes the data according to determined
        filters by each child class

        :param dm: The data that will be processed.
        :param filter_args: Contains all information on filters to be applied
        """
        pass

    @abstractmethod
    def update_data(self, prev_data: Any, filter_args: any, dm: DataManager = None):
        """
        update_data is a method that updates the currently represented information

        :param dm: Contains all data stored by the program to date
        :param filter_args: Contains all information on filters to be applied
        :param prev_data: The representation of the current state of displayed data
        determined by each child class
        """
        pass
