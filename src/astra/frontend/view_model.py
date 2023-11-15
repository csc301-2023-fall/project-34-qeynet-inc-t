"""
File that contains the view models needed for the view

For this deliverable, it just contains the view model for the dashboard
"""

from .model import Model
import datetime
from typing import List, Iterable

from ..data.data_manager import DataManager
from ..data.parameters import Tag
from ..usecase.dashboard_handler import TableReturn
from ..usecase.request_receiver import DashboardRequestReceiver, DataRequestReceiver


class DashboardViewModel:
    """
    Dashboard view model
    """

    _sorting: List[int]
    _time: datetime.datetime
    _table_entries: List[list]
    _num_frames: int

    def __init__(self) -> None:
        """
        Initializes the view model
        """
        self.model = Model(DashboardRequestReceiver())
        self._sorting = [1, 1]
        self._table_entries = []
        self._time = None
        self._num_frames = 0

    def get_table_entries(self) -> List[list]:
        """
        Getter method to return the entries in the table

        Table entries are stores as a list of lists

        Returns:
            List[list]: list of table entries
        """
        return self._table_entries

    def get_time(self) -> datetime.datetime:
        """
        Getter method to return the time from

        Returns:
            datetime.datetime: datetime object representing
                the time of the frame data
        """
        return self._time

    def get_num_frames(self) -> int:
        return self._num_frames

    def toggle_sort(self, heading: str) -> None:
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

        if heading == "TAG":
            self._sorting[0] *= -1
            sort_value = self._sorting[0]
        else:
            self._sorting[1] *= -1
            sort_value = self._sorting[1]

        if sort_value == 1:
            # ascending
            self.model.request_receiver.update_sort(('>', heading))
        elif sort_value == -1:
            # descending
            self.model.request_receiver.update_sort(('<', heading))

        self.model.receive_updates()
        self.update_table_entries()

    def toggle_tag(self, tags: Iterable[Tag]) -> None:
        self.model.request_receiver.set_shown_tags(tags)

    def toggle_start_time(self, start: datetime) -> None:
        self.model.request_receiver.set_start_time(start)

    def toggle_end_time(self, end: datetime) -> None:
        self.model.request_receiver.set_end_time(end)

    def choose_frame(self, dm: DataManager, index: int) -> None:
        self.model.request_receiver.change_index(index)
        self.model.receive_new_data(dm)
        self.update_table_entries()

    def update_table_entries(self) -> None:
        """
        Updates the table entires to be the same as
        what is in the model
        """
        self._table_entries = []
        table_data: TableReturn
        table_data = self.model.get_data()

        self._time = table_data.timestamp
        self._num_frames = table_data.frame_quantity
        self._table_entries = table_data.table

    def load_file(self, dm: DataManager, file: str):
        """
        This method has yet to be fully implemented
        Currently it just asks the view_model to update itself to
        simulate a file being loaded

        Args:
            file: the filepath of the telemetry file
            :param file:
            :param dm:
        """
        data_receiver = DataRequestReceiver
        data_receiver.set_filename(file)
        data_receiver.update(dm)
