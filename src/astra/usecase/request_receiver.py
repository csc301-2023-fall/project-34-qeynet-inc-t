from abc import ABC, abstractmethod
from threading import Thread
from typing import Any, Mapping
from .alarm_checker import check_alarms
from astra.data.data_manager import DataManager, Device


class RequestReceiver(ABC):
    """
    RequestReceiver is an abstract class that defines the interface for front end data processing
    requests.

    :param previous_data: Stores the data last returned by the <create> function
    :type: Any
    """
    previous_data: Any

    @abstractmethod
    def create(self, dm: DataManager):
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


class DataRequestReceiver(RequestReceiver):
    """
    Receives new data files and updates our programs database accordingly.

    :param file: A file to read from for requests
    :type: str

    :param previous_data: stores data manager last returned by this class' <create> function
    :type: DataManager
    """

    file: str = ""
    previous_data: DataManager | None = None

    @classmethod
    def set_filename(cls, file):
        """
        setter method for <cls.file>
        """
        cls.file = file

    @classmethod
    def create(cls, dm: DataManager) -> DataManager:
        """
        create is a method that creates a new data table and returns it based
        on the filename provided.

        :param dm: The interface for getting all data known to the program
        """
        cls.previous_data = dm.from_device_name(cls.file)
        return cls.previous_data

    @classmethod
    def update(cls) -> None:
        """
        update is a method that updates the database based on the filename provided.
        """

        if cls.previous_data is not None:
            dm = cls.previous_data
            filename = cls.file
            earliest_time = dm.add_data_from_file(filename)

            checking_thread = Thread(target=check_alarms, args=[cls.previous_data, earliest_time])
            checking_thread.start()

    @classmethod
    def data_exists(cls) -> bool:
        """
        Determines if the data manager has any stored data in it

        :return: True iff some telemetry data has been input to the DataManager
        """

        if cls.previous_data is not None:
            return cls.previous_data.get_telemetry_data(None, None, {}).num_telemetry_frames > 0
        return False

    @classmethod
    def set_data_manager(cls, dm: DataManager) -> None:
        """
        setter method for <cls.previous_data>
        """
        cls.previous_data = dm

    @staticmethod
    def add_device(config_path: str) -> None:
        """
        Interfacing method for adding devices to the data manager

        :param config_path: The path to the config file to construct a device from
        """
        DataManager.add_device(config_path)

    @staticmethod
    def get_devices() -> Mapping[str, Device]:
        """
        Interfacing method for getting the name of all devices from the
        data manager
        """
        return DataManager.get_devices()

    @staticmethod
    def remove_device(device_name: str) -> None:
        """
        Interfacing method for remove devices from the data manager

        :param device_name: The device to remove from the data manager
        """
        DataManager.remove_device(device_name)
