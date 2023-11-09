"""
File that holds the dummy Model Class
"""

import datetime
from typing import Any

from astra.data.data_manager import DataManager
from astra.usecase.request_receiver import RequestReceiver


class Model:
    """
    Dummy class currently representing the backend
    """

    data = None
    request_receiver = None

    def __init__(self, request_receiver: RequestReceiver) -> None:
        """
        Initialize to some random telemetry data
        """
        self.request_receiver = request_receiver

    def receive_new_data(self, dm: DataManager) -> Any:
        self.data = self.request_receiver.create(dm)

    def receive_updates(self) -> None:
        """
        A method that simulates the functionality of the backend
        Since our data is fixed, we sort by hand each input case
        """
        self.request_receiver.update(self.data)

    def get_data(self) -> Any:
        """
        Getter method to return whatever's in the data
        """
        return self.data

    def set_data(self, data: Any):
        """
        Setter method for data. Since the model is used by all viewmodels,
        accept any form of data as input and assume they will be known by the
        using function(s)
        :param data: The new data to represent the current model
        """
        self.data = data
