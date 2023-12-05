from datetime import datetime
from typing import Callable

from .table_return import TableReturn
from .alarm_handler import AlarmsHandler, AlarmsFilters
from .request_receiver import RequestReceiver
from astra.data.data_manager import DataManager
from ..data.alarms import AlarmCriticality, AlarmPriority, Alarm
from ..data.parameters import Tag

VALID_SORTING_DIRECTIONS = {'>', '<'}
VALID_SORTING_COLUMNS = ['ID', 'PRIORITY', 'CRITICALITY', 'REGISTERED', 'CONFIRMED', 'TYPE']
ALARM_HEADINGS = ['ID', 'PRIORITY', 'CRITICALITY', 'REGISTERED', 'CONFIRMED', 'TYPE']
RATE_OF_CHANGE = 'RATE_OF_CHANGE'
STATIC = 'STATIC'
THRESHOLD = 'THRESHOLD'
SETPOINT = 'SETPOINT'
SOE = 'SOE'
L_AND = 'L_AND'  # LOGICAL AND
L_OR = 'L_OR'  # LOGICAL OR

CRITICALITIES = {AlarmCriticality.WARNING.name, AlarmCriticality.LOW.name,
                 AlarmCriticality.MEDIUM.name, AlarmCriticality.HIGH.name,
                 AlarmCriticality.CRITICAL.name}
PRIORITIES = {AlarmPriority.WARNING.name, AlarmPriority.LOW.name,
              AlarmPriority.MEDIUM.name, AlarmPriority.HIGH.name,
              AlarmPriority.CRITICAL.name}
ALL_TYPES = {RATE_OF_CHANGE, STATIC, THRESHOLD, SETPOINT, SOE, L_AND, L_OR}


class AlarmsRequestReceiver(RequestReceiver):
    """
    Handles requests relating to displaying alarms, such as creating the initial alarm table,
    updating the currently represented information, adding or removing priorities,
    criticalities or types from the sets of them that we are viewing,
    and updating the sorting filter to be applied.

    :param filters: Container class for all filters to apply to the table
    :type: AlarmsFilters

    :param handler: THe class that actually processes requests made by this request receiver
    :type: AlarmsHandler

    :param previous_data: Stores the return value of the previous call to <cls.create>
    :type: TableReturn

    :param _sorting: Tracks which direction each row should be sorted by
    :type: list[int]

    :param _new: Tracks if only new alarms should be shown
    :type: bool

    :param _priorities: Stores the priorities currently being shown
    :type: set[str]

    :param _criticalities: Stores the criticalities currently being shown
    :type: set[str]

    :param _types: Stores the types currently being shown
    :type: set[str]
    """

    filters = AlarmsFilters({Tag("")}, None, CRITICALITIES, PRIORITIES, ALL_TYPES, datetime.min,
                            datetime.max, datetime.min, datetime.max, False)
    handler = AlarmsHandler()
    previous_data = TableReturn([], [])
    _sorting = [-1, 1, 1, 1, 1, 1]
    _new = False
    _priorities = {'WARNING', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}
    _criticalities = {'WARNING', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}
    _types = {'RATE_OF_CHANGE', 'STATIC', 'THRESHOLD', 'SETPOINT', 'SOE', 'L_AND', 'L_OR'}

    @classmethod
    def create(cls, dm: DataManager) -> TableReturn:
        """
        Creates a table of data using all alarms and applies any relevant filters or sorts

        :param dm: Contains all data stored by the program to date.
        """
        if "" in cls.filters.tags:
            # Since the filter tags list needs to be provided externally via the DataManager, a
            # special case needs to be made to update the filter tags
            cls.filters.tags = set(dm.tags)

        # Create the initial table.
        cls.previous_data = cls.handler.get_data(dm, cls.filters)
        return cls.previous_data

    @classmethod
    def update(cls):
        """
        Updates the current data in the table to represent changes to filters or sorting
        """

        cls.handler.update_data(cls.previous_data, cls.filters)

    @classmethod
    def set_shown_tags(cls, tags: set[Tag]):
        """
        Setter method for <cls.filters.tags>
        """
        cls.filters.tags = tags

    @classmethod
    def add_shown_priority(cls, add: str) -> bool:
        """
        Adds an alarm priority to the set of priorities that we are viewing.
        It returns True if it was successful and False otherwise.

        :param add: the priority that we want to add to the set of priorities that we are viewing.
        :returns: True iff the priority was successfully added
        """

        # Determine if we can add <add> to the set of priorities that we are viewing.
        if add not in cls.filters.priorities:
            cls.filters.priorities.add(add)
            return True
        else:
            # <add> was already in the set of priorities that we are viewing.
            return False

    @classmethod
    def add_shown_criticality(cls, add: AlarmCriticality) -> bool:
        """
        Adds a criticality to the set of criticalities that we are viewing. Returns True iff
        it was successful

        :param add: the criticality that we want to add to the set of criticalities that we
        are viewing.
        :returns: True iff the criticality was successfully added
        """

        # Determine if we can add <add> to the set of criticalities that we are viewing.
        if add not in cls.filters.criticalities:
            cls.filters.criticalities.add(add.name)
            return True
        else:
            # <add> was already in the set of criticalities that we are viewing.
            return False

    @classmethod
    def add_shown_type(cls, add: str) -> bool:
        """
        add_shown_type is a method that adds a type to the set of types that we are viewing.
        It returns True if it was successful and False otherwise.

        :param add: the type that we want to add to the set of types that we are viewing.
        :returns: True if the type was successfully added and False otherwise.
        """

        # Make sure that the set of types that we are viewing is not None.
        if cls.filters.types is None:
            cls.filters.types = set()

        # Determine if we can add the type to the set of types that we are viewing.
        if add not in cls.filters.types:
            cls.filters.types.add(add)
            return True
        else:
            # Type was already in the set of types that we are viewing.
            return False

    @classmethod
    def toggle_sort(cls, heading: str) -> bool:
        """
        Method for toggling sorting on a specific heading
        The headings include:
        - TAG
        - PRIORITY
        - CRITICALITY
        - REGISTERED
        - CONFIRMED
        - TYPE
        This method will filter the data according to which heading was toggled

        :param heading: the sort name that was toggled
        """
        sort_value = 1
        for i in range(len(ALARM_HEADINGS)):
            check_heading = ALARM_HEADINGS[i]
            if check_heading == heading:
                cls._sorting[i] *= -1
                sort_value = cls._sorting[i] * (heading == check_heading)
            else:
                cls._sorting[i] = 1

        if sort_value == 1:
            # ascending
            cls.update_sort(('<', heading))
        elif sort_value == -1:
            # descending
            cls.update_sort(('>', heading))

        return sort_value == 1

    @classmethod
    def toggle_priority(cls, tag: Tag):
        """
        Method for toggling filtering of specific priority
        The headings include:
        - WARNING
        - LOW
        - MEDIUM
        - HIGH
        - CRITICAL
        This method will filter the data according to which heading was toggled

        :param tag: The priority name to toggle on/off
        """
        if tag not in cls._priorities:
            cls._priorities.add(tag)
        else:
            cls._priorities.remove(tag)

        cls.set_shown_priorities(cls._priorities)
        cls.update()

    @classmethod
    def toggle_criticality(cls, tag: Tag):
        """
        Method for toggling filtering of specific criticality
        The headings include:
        - WARNING
        - LOW
        - MEDIUM
        - HIGH
        - CRITICAL
        This method will filter the data according to which heading was toggled

        :param tag: string representing which criticality was toggled
        """
        if tag not in cls._criticalities:
            cls._criticalities.add(tag)
        else:
            cls._criticalities.remove(tag)

        cls.set_shown_criticalities(cls._criticalities)
        cls.update()

    @classmethod
    def toggle_type(cls, tag: Tag):
        """
        Method for toggling filtering of specific criticality
        The headings include:
        - RATE-OF-CHANGE
        - STATIC
        - THRESHOLD
        - SETPOINT
        - SOE
        - LOGICAL
        This method will filter the data according to which heading was toggled

        :param tag: string representing which type of alarm was toggled
        """

        if tag not in cls._types:
            cls._types.add(tag)
        else:
            cls._types.remove(tag)

        cls.set_shown_types(cls._types)
        cls.update()

    @classmethod
    def toggle_all(cls) -> None:
        """
        Resets all non-parameter filters to their default options. That is,
        all alarms of different acknowledgement levels, priorities, criticalities, and types are
        shown
        """

        cls.set_new_alarms(False)
        cls.set_shown_priorities(cls._priorities)
        cls.set_shown_criticalities(cls._criticalities)
        cls.set_shown_types(cls._types)

    @classmethod
    def set_shown_priorities(cls, priorities: set[str]):
        """
        Setter method for <cls.filters.priorities>
        """

        cls.filters.priorities = priorities

    @classmethod
    def set_shown_criticalities(cls, criticalities: set[str]):
        """
        Setter method for <cls.filters.criticalities>
        """

        cls.filters.criticalities = criticalities

    @classmethod
    def set_shown_types(cls, types: set[str]):
        """
        Setter method for <cls.filters.types>
        """
        cls.filters.types = types

    @classmethod
    def remove_shown_priority(cls, remove: AlarmPriority) -> bool:
        """
        Remove a priority from the set of priorities that we are viewing.
        It returns True if it was successful and False otherwise.

        :param remove: The priority that we want to remove from the set of priorities that
        we are viewing.
        :return: True if the priority was successfully removed and False otherwise.
        """

        # Make sure that the set of priorities that we are viewing is not None.
        if cls.filters.priorities is None:
            cls.filters.priorities = set()

        # Determine if we can remove <remove> from the set of priorities that we are viewing.
        if remove in cls.filters.priorities:
            cls.filters.priorities.remove(remove.name)
            return True
        else:
            # <remove> was not in the set of priorities that we are viewing.
            return False

    @classmethod
    def remove_shown_criticality(cls, remove: AlarmCriticality) -> bool:
        """
        Remove a criticality from the set of criticalities that we are viewing.
        It returns True if it was successful and False otherwise.

        :param remove: The criticality that we want to remove from the set of criticalities that
        we are viewing.
        :return: True if the criticality was successfully removed and False otherwise.
        """

        # Make sure that the set of criticalities that we are viewing is not None.
        if cls.filters.criticalities is None:
            cls.filters.criticalities = set()

        # Determine if we can remove <remove> from the set of criticalities that we are viewing.
        if remove in cls.filters.criticalities:
            cls.filters.criticalities.remove(remove.name)
            return True
        else:
            # <remove> was not in the set of criticalities that we are viewing.
            return False

    @classmethod
    def remove_shown_type(cls, remove: str) -> bool:
        """
        Remove a type from the set of types that we are viewing.
        It returns True if it was successful and False otherwise.

        :param remove: The type that we want to remove from the set of types that we are viewing.
        :return: True if the type was successfully removed and False otherwise.
        """

        # Make sure that the set of types that we are viewing is not None.
        if cls.filters.types is None:
            cls.filters.types = set()

        # Determine if we can remove <remove> from the set of types that we are viewing.
        if remove in cls.filters.types:
            cls.filters.types.remove(remove)
            return True
        else:
            # <remove> was not in the set of types that we are viewing.
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
        :returns: True if the sorting filter was successfully updated and False otherwise.
        """

        # Determine if the sorting filter is valid.
        if sort[0] not in VALID_SORTING_DIRECTIONS:
            return False
        if sort[1] not in VALID_SORTING_COLUMNS:
            return False

        # both if statements failed, so the filter is valid.
        cls.filters.sort = sort
        return True

    @classmethod
    def set_registered_start_time(cls, start_time: datetime):
        """
        setter method for <cls.filters.confirmed_start_time>
        """

        cls.filters.registered_start_time = start_time

    @classmethod
    def set_registered_end_time(cls, end_time: datetime):
        """
        setter method for <cls.filters.registered_end_time>
        """

        cls.filters.registered_end_time = end_time

    @classmethod
    def set_confirmed_start_time(cls, start_time: datetime):
        """
        setter method for <cls.filters.confirmed_start_time>
        """

        cls.filters.confirmed_start_time = start_time

    @classmethod
    def set_confirmed_end_time(cls, end_time: datetime):
        """
        setter method for <cls.filters.confirmed_end_time>
        """

        cls.filters.confirmed_end_time = end_time

    @classmethod
    def set_new_alarms(cls, new: bool):
        """
        setter method for <cls.filters.new>
        """

        cls.filters.new = new

    @classmethod
    def toggle_new_only(cls) -> None:
        """
        Switches the boolean value of <cls.filters.new>
        """

        cls.filters.new = not cls.filters.new

    @classmethod
    def acknowledge_alarm(cls, alarm: Alarm, dm: DataManager) -> None:
        """
        Sets the provided <alarm> have its acknowledgment attribute set to ACKNOWLEDGED

        :param alarm: The alarm whose acknowledgment needs to be modified
        :param dm: Stores all data known to the program
        """

        cls.handler.acknowledge_alarm(alarm, dm)

    @classmethod
    def remove_alarm(cls, alarm: Alarm, dm: DataManager) -> None:
        """
        Interfacing method to remove an alarm from <dm>

        :param alarm: The alarm to remove
        :param dm: The holder of the global alarm container
        """

        cls.handler.remove_alarm(alarm, dm)

    @classmethod
    def get_alarm_banner(cls) -> list[str]:
        """
        Returns a list of strings in order to show in the alarm banners
        """

        return cls.handler.get_banner_elems()

    @classmethod
    def install_alarm_watcher(cls, dm: DataManager, watcher: Callable) -> None:
        """
        An interfacing function for the alarm container to install a watcher function
        """

        dm.alarms.observer.add_watcher(watcher)

    @classmethod
    def get_table_entries(cls) -> list[list]:
        """
        getter method for the data to actually be shown in the alarms table
        """

        return cls.previous_data.table

    @classmethod
    def get_new(cls) -> bool:
        """
        getter method for whether only unacknowledged alarms should be shown or not
        """

        return cls.filters.new

    @classmethod
    def get_priorities(cls):
        """
        getter method for the priorities currently shown
        """

        return cls._priorities

    @classmethod
    def get_criticalities(cls):
        """
        getter method for the criticalities currently shown
        """

        return cls._criticalities

    @classmethod
    def get_types(cls):
        """
        getter method for the types of alarms shown
        """

        return cls._types
