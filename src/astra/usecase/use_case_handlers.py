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
    def get_data(self, dm: DataManager):
        """
        get_data is a method that processes the data according to determined
        filters by each child class

        :param model: The model of currently shown data
        :param dm: The data that will be processed.
        """
        pass

    @abstractmethod
    def update_data(self, prev_data: Any):
        """
        update_data is a method that updates the currently represented information

        :param prev_data: The representation of the current state of displayed data
        determined by each child class
        """
        pass
