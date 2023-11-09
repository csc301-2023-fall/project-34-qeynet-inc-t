"""
File that contains the view models needed for the view

For this deliverable, it just contains the view model for the dashboard
"""

from .model import Model
import datetime
from typing import List


class DashboardViewModel:
    """
    Dashboard view model
    """

    _sorting: List[int]
    _time: datetime.datetime
    _table_entries: List[list]

    def __init__(self) -> None:
        """
        Initializes the view model
        """
        self.model = Model()
        self._sorting = [1, 1, 1]
        self._table_entries = []
        self._time = None

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

    def toggle_sort(self, heading: str) -> None:
        """
        Method for toggling sorting on a specific heading
        The headings include (for now):
        - TAG
        - DESCRIPTION
        - VALUE
        This method will ask the model to sort the data
        according to which heading was toggled

        Args:
            heading (str): string representing which heading was toggled
        """
        sort_value = 0
        if heading == "TAG":
            self._sorting[0] *= -1
            sort_value = self._sorting[0]
        elif heading == "DESCRIPTION":
            self._sorting[1] *= -1
            sort_value = self._sorting[1]
        else:
            self._sorting[2] *= -1
            sort_value = self._sorting[2]

        filter_data = {'A3': (True,), 'B1': (False,), 'B4': (True,), 'C1': (True,), 'INDEX': (0, )}
        if sort_value == 1:
            filter_data['SORT'] = ('>', heading)
        elif sort_value == -1:
            filter_data['SORT'] = ('<', heading)

        self.model.receive(filter_data=filter_data, data=None)
        self.update_table_entries()

    def update_table_entries(self) -> None:
        """
        Updates the table entires to be the same as
        what is in the model
        """
        self._table_entries = []
        for row in self.model.get_data():
            if row == ['Tag', 'Description', 'Value']:
                continue
            elif len(row) < 3:
                self._time = row
            else:
                self._table_entries.append(row)

    def load_file(self, file):
        """
        This method has yet to be fully implemented
        Currently it just asks the view_model to update itself to
        simulate a file being loaded

        Args:
            file: the filepath of the telemetry file
        """
        self.update_table_entries()
