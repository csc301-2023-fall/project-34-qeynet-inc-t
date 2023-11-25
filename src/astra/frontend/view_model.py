"""
File that contains the view models needed for the view

For this deliverable, it just contains the view model for the dashboard
"""

from .model import Model
import datetime
from typing import List

from ..data.data_manager import DataManager
from ..data.parameters import Tag
from ..usecase.use_case_handlers import TableReturn
from ..usecase.request_receiver import DashboardRequestReceiver, DataRequestReceiver
from ..usecase.alarms_request_receiver import AlarmsRequestReceiver

DASHBOARD_HEADINGS = ['TAG', 'DESCRIPTION']
ALARM_HEADINGS = ['ID', 'PRIORITY', 'CRITICALITY', 'REGISTERED', 'CONFIRMED', 'TYPE']


class DashboardViewModel:
    """
    Dashboard view model
    """

    _sorting: List[int]
    _time: datetime.datetime
    _table_entries: List[list]
    _num_frames: int
    _tag_list: List[Tag]
    _toggled_tags: List[Tag]

    _data_reciever: DataRequestReceiver

    def __init__(self) -> None:
        """
        Initializes the view model
        """
        self.model = Model(DashboardRequestReceiver())
        self._sorting = [-1, 1]
        self._table_entries = []
        self._time = None
        self._num_frames = 0
        self._tag_list = []
        self._toggled_tags = []

        self._data_reciever = None

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

    def toggle_sort(self, heading: str) -> bool:
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
        for i in range(len(DASHBOARD_HEADINGS)):
            check_heading = DASHBOARD_HEADINGS[i]
            if heading == check_heading:
                self._sorting[i] *= -1
                sort_value = self._sorting[0]
            else:
                self._sorting[i] = 1

        if sort_value == 1:
            # ascending
            self.model.request_receiver.update_sort(('>', heading))
        elif sort_value == -1:
            # descending
            self.model.request_receiver.update_sort(('<', heading))

        self.model.receive_updates()
        self.update_table_entries()
        return sort_value == 1

    # def toggle_tag(self, tags: Iterable[Tag]) -> None:
    #     self.model.request_receiver.set_shown_tags(tags)

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
        Loads a telemetry file for the data for the datatable

        Args:
            file: the filepath of the telemetry file
            :param file:
            :param dm:
        """
        self._data_reciever = DataRequestReceiver
        self._data_reciever.set_filename(file)
        self._data_reciever.update(dm)
        self.model.receive_new_data(dm)

    def search_tags(self, search: str):
        self._tag_list = self.model.request_receiver.search_tags(search)

    def get_tag_list(self):
        to_return = []
        for tag in self._tag_list:
            to_return.append(tag)
        return to_return

    def get_toggled_tags(self):
        return self._toggled_tags

    def toggle_tag(self, tag: Tag):
        # Case 1: untoggle the tag
        if tag in self._toggled_tags:
            self._toggled_tags.remove(tag)
            self.model.request_receiver.remove_shown_tag(tag)
        # Otherwise, toggle the tag
        else:
            self._toggled_tags.append(tag)
            self.model.request_receiver.add_shown_tag(tag)
        # In either case, refresh the table entries

        self.model.receive_updates()
        self.update_table_entries()

    def get_alarms(self):
        return self._data_reciever.get_alarms()


class AlarmsViewModel:
    """
    Alarms view model
    """

    model: Model
    _new: bool
    _sorting: List[int]
    _priorities: set[Tag]
    _criticalities: set[Tag]
    _types: set[Tag]
    _time: datetime.datetime
    _table_entries: List[list]

    def __init__(self, dm: DataManager, watchers: List[callable]) -> None:
        """
        Initializes the view model
        """
        self.model = Model(AlarmsRequestReceiver())
        self._sorting = [1, 1, 1, 1, 1, 1]
        self._priorities = {'WARNING', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}
        self._criticalities = {'WARNING', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}
        self._types = {'RATE_OF_CHANGE', 'STATIC', 'THRESHOLD', 'SETPOINT', 'SOE', 'L_AND', 'L_OR'}
        self._table_entries = []
        self._time = None

        self.model.request_receiver.set_shown_priorities(self._priorities)
        self.model.request_receiver.set_shown_criticalities(self._criticalities)
        self.model.request_receiver.set_shown_types(self._types)
        self.model.request_receiver.update_sort(('<', 'ID'))
        self._new = False

        for watcher in watchers:
            self.model.request_receiver.install_alarm_watcher(dm, watcher)

    def load_file(self, dm: DataManager, file: str):
        """
        Loads a telemetry file for its alarms for the alarm table

        Args:
            file: the filepath of the telemetry file
            :param file:
            :param dm:
        """

        data_receiver = DataRequestReceiver
        data_receiver.set_filename(file)
        data_receiver.update(dm)
        self.model.receive_new_data(dm)

    def get_table_entries(self) -> List[list]:
        """
        Getter method to return the entries in the table

        Table entries are stores as a list of lists

        Returns:
            List[list]: list of table entries
        """
        return self._table_entries

    def get_tag_list(self):
        return self._priorities, self._criticalities, self._types

    def update_table_entries(self) -> None:
        """
        Updates the table entires to be the same as
        what is in the model
        """
        self._table_entries = []
        table_data: TableReturn
        table_data = self.model.get_data()

        if table_data is not None:
            self._table_entries = table_data.table

    def toggle_all(self) -> None:
        self.model.request_receiver.set_shown_priorities(self._priorities)
        self.model.request_receiver.set_shown_criticalities(self._criticalities)
        self.model.request_receiver.set_shown_types(self._types)
        self.model.receive_updates()
        self.update_table_entries()

    def toggle_sort(self, heading: Tag) -> bool:
        """
        Method for toggling sorting on a specific heading
        The headings include (for now):
        - TAG
        - PRIORITY
        - CRITICALITY
        - REGISTERED
        - CONFIRMED
        - TYPE
        This method will ask the model to sort the data
        according to which heading was toggled

        Args:
            heading (str): string representing which heading was toggled
        """

        for i in range(len(ALARM_HEADINGS)):
            check_heading = ALARM_HEADINGS[i]
            if check_heading == heading:
                self._sorting[i] *= -1
                sort_value = self._sorting[i] * (heading == check_heading)
            else:
                self._sorting[i] = 1

        if sort_value == 1:
            # ascending
            self.model.request_receiver.update_sort(('<', heading))
        elif sort_value == -1:
            # descending
            self.model.request_receiver.update_sort(('>', heading))

        self.model.receive_updates()
        self.update_table_entries()
        return sort_value == 1

    def toggle_new(self):
        """
        Method for toggling whether alarms should only be shown if they are acknowledged
        or not
        """
        self._new = not self._new
        self.model.request_receiver.toggle_new_only()
        self.model.receive_updates()
        self.update_table_entries()

    def toggle_priority(self, tag: Tag):
        """
        Method for toggling filtering of specific priority
        The headings include (for now):
        - WARNING
        - LOW
        - MEDIUM
        - HIGH
        - CRITICAL
        This method will ask the model to sort the data
        according to which heading was toggled

        Args:
            heading (str): string representing which heading was toggled
        """
        if tag not in self._priorities:
            self._priorities.add(tag)
        else:
            self._priorities.remove(tag)

        self.model.request_receiver.set_shown_priorities(self._priorities)
        self.model.receive_updates()
        self.update_table_entries()

    def toggle_criticality(self, tag: Tag):
        """
        Method for toggling filtering of specific criticality
        The headings include (for now):
        - WARNING
        - LOW
        - MEDIUM
        - HIGH
        - CRITICAL
        This method will ask the model to sort the data
        according to which heading was toggled

        Args:
            heading (str): string representing which heading was toggled
        """
        if tag not in self._criticalities:
            self._criticalities.add(tag)
        else:
            self._criticalities.remove(tag)

        self.model.request_receiver.set_shown_criticalities(self._criticalities)
        self.model.receive_updates()
        self.update_table_entries()

    def toggle_type(self, tag: Tag):
        """
        Method for toggling filtering of specific criticality
        The headings include (for now):
        - RATE-OF-CHANGE
        - STATIC
        - THRESHOLD
        - SETPOINT
        - SOE
        - LOGICAL
        This method will ask the model to sort the data
        according to which heading was toggled

        Args:
            heading (str): string representing which heading was toggled
        """
        if tag not in self._types:
            self._types.add(tag)
        else:
            self._types.remove(tag)

        self.model.request_receiver.set_shown_types(self._types)
        self.model.receive_updates()
        self.update_table_entries()

    def get_priorities(self):
        return self._priorities

    def get_criticalities(self):
        return self._criticalities

    def get_types(self):
        return self._types

    def get_new(self) -> bool:
        return self._new
