from datetime import datetime
from typing import Iterable

from .alarm_strategies import AlarmsContainer
from .use_case_handlers import TableReturn
from .alarm_handler import AlarmHandler, AlarmsFilters  # , ReturnType
from .request_receiver import RequestReceiver
from astra.data.data_manager import DataManager
from ..data.alarms import AlarmPriority, AlarmCriticality

VALID_SORTING_DIRECTIONS = {'>', '<'}
VALID_SORTING_COLUMNS = ['ID', 'PRIORITY', 'CRITICALITY', 'REGISTERED', 'CONFIRMED', 'TYPE']
RATE_OF_CHANGE = 'RATE_OF_CHANGE'
STATIC = 'STATIC'
THRESHOLD = 'THRESHOLD'
SETPOINT = 'SETPOINT'
SOE = 'SOE'
L_AND = 'L_AND'  # LOGICAL AND
L_OR = 'L_OR'  # LOGICAL OR


class AlarmsRequestReceiver(RequestReceiver):
    """
    AlarmsRequestReceiver is a class that implements the RequestReceiver interface.
    It handles requests from the alarms tab, such as creating the initial data table,
    updating the currently represented information, changing the index of the datatable
    that we are viewing, adding or removing priorities, criticalities or types
    from the sets of them that we are viewing, and updating the sorting filter to be applied.
    """

    filters = None
    handler = AlarmHandler

    @classmethod
    def __init__(cls):
        cls.handler = AlarmHandler()
        cls.filters = AlarmsFilters(None, None, None, None, None, None, None, None, False)
        # maybe make this inherit from dashboard filters
        # Im assuming the alarms filter will have:
        # (sort, index, priority, criticality, alarm_type, start_time, end_time)

    @classmethod
    def create(cls, dm: AlarmsContainer) -> TableReturn:
        """
        Create is a method that creates the initial data table,
        with all priorities/types/criticalities shown, no sorting applied and at the first index.

        :param model: The model of currently shown data
        :param dm: Contains all data stored by the program to date.
        """

        criticalities = [AlarmCriticality.WARNING, AlarmCriticality.LOW,
                         AlarmCriticality.MEDIUM, AlarmCriticality.HIGH, AlarmCriticality.CRITICAL]
        priorities = [AlarmPriority.WARNING, AlarmPriority.LOW,
                      AlarmPriority.MEDIUM, AlarmPriority.HIGH, AlarmPriority.CRITICAL]

        # add all priorities and criticalities to the shown priorities and criticalities by default
        cls.filters.criticalities = criticalities
        cls.filters.priorities = priorities

        # get all alarm types from dm
        all_types = [RATE_OF_CHANGE, STATIC, THRESHOLD, SETPOINT, SOE, L_AND, L_OR]

        # Add all types to the shown types by default.
        cls.filters.types = all_types

        # Create the initial table.
        return cls.handler.get_data(dm.get_alarms(), cls.filters)

    @classmethod
    def update(cls, previous_data: TableReturn, dm: DataManager = None):
        """
        update is a method that updates the currently represented information

        :param previous_data: The previous table that was in the view and we want to update.
        :param dm: Contains all data stored by the program to date.
        """
        cls.handler.update_data(previous_data, cls.filters)

    @classmethod
    def add_shown_priority(cls, add: str) -> bool:
        """
        add_shown_priority is a method that adds a priority to the set of priorities
        that we are viewing. It returns True if it was successful and False otherwise.

        :param add: the priority that we want to add to the set of priorities that we are viewing.
        :returns: True if the priority was successfully added and False otherwise.
        """

        # Determine if we can add the priority to the set of priorities that we are viewing.
        if add not in cls.filters.priorities:
            cls.filters.priorities.append(add)
            return True
        else:
            # Priority was already in the set of priorities that we are viewing.
            return False

    @classmethod
    def add_shown_criticality(cls, add: str) -> bool:
        """
        add_shown_criticality is a method that adds a criticality to the set of criticalities
        that we are viewing. It returns True if it was successful and False otherwise.

        :param add: the criticality that we want to add to the set of criticalities that we
        are viewing.
        :returns: True if the criticality was successfully added and False otherwise.
        """

        # Determine if we can add the criticality to the set of criticalities that we are viewing.
        if add not in cls.filters.criticailities:
            cls.filters.criticalities.append(add)
            return True
        else:
            # Criticality was already in the set of criticalities that we are viewing.
            return False

    @classmethod
    def add_shown_type(cls, add: str) -> bool:
        """
        add_shown_type is a method that adds a type to the set of types that we are viewing.
        It returns True if it was successful and False otherwise.

        :param add: the type that we want to add to the set of types that we are viewing.
        :returns: True if the type was successfully added and False otherwise.
        """

        # Determine if we can add the type to the set of types that we are viewing.
        if add not in cls.filters.types:
            cls.filters.types.append(add)
            return True
        else:
            # Type was already in the set of types that we are viewing.
            return False

    @classmethod
    def set_shown_priorities(cls, priorities: Iterable[AlarmPriority]):
        """
        Sets <cls.filters.priorities> to the set of priorities to be shown

        PRECONDITION: <priority> is an element of <cls.filters.priorities>

        :param priorities: a set of priorities to show
        """
        cls.filters.priorities = priorities

    @classmethod
    def set_shown_criticalities(cls, criticalities: Iterable[AlarmCriticality]):
        """
        Sets <cls.filters.criticalities> to the set of criticalities to be shown

        PRECONDITION: <criticality> is an element of <cls.filters.criticalities>

        :param criticalities: a set of criticalities to show
        """
        cls.filters.criticalities = criticalities

    @classmethod
    def set_shown_types(cls, types: Iterable[str]):
        """
        Sets <cls.filters.types> to the set of types to be shown

        PRECONDITION: <type> is an element of <cls.filters.types>

        :param types: a set of types to show
        """
        cls.filters.types = types

    @classmethod
    def remove_shown_priority(cls, remove: str) -> bool:
        """
        Remove a priority from the set of priorities that we are viewing.
        It returns True if it was successful and False otherwise.

        :param remove: The priority that we want to remove from the set of priorities that
        we are viewing.
        :return: True if the priority was successfully removed and False otherwise.
        """
        # Determine if we can remove the priority from the set of priorities that we are viewing.
        if remove in cls.filters.priorities:
            cls.filters.priorities.remove(remove)
            return True
        else:
            # Priority was not in the set of priorities that we are viewing.
            return False

    @classmethod
    def remove_shown_criticality(cls, remove: str) -> bool:
        """
        Remove a criticality from the set of criticalities that we are viewing.
        It returns True if it was successful and False otherwise.

        :param remove: The criticality that we want to remove from the set of criticalities that
        we are viewing.
        :return: True if the criticality was successfully removed and False otherwise.
        """
        # Determine if we can remove the criticality from the set of criticalities that
        # we are viewing.
        if remove in cls.filters.criticalities:
            cls.filters.criticalities.remove(remove)
            return True
        else:
            # Criticality was not in the set of criticalities that we are viewing.
            return False

    @classmethod
    def remove_shown_type(cls, remove: str) -> bool:
        """
        Remove a type from the set of types that we are viewing.
        It returns True if it was successful and False otherwise.

        :param remove: The type that we want to remove from the set of types that we are viewing.
        :return: True if the type was successfully removed and False otherwise.
        """
        # Determine if we can remove the type from the set of types that we are viewing.
        if remove in cls.filters.types:
            cls.filters.types.remove(remove)
            return True
        else:
            # Type was not in the set of types that we are viewing.
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
    def set_start_time(cls, start_time: datetime):
        """
        Modifies <cls.filters.start_time> to be equal to <start_time>

        :param start_time: the datetime to be set
        """
        cls.filters.start_time = start_time

    @classmethod
    def set_end_time(cls, end_time: datetime):
        """
        Modifies <cls.filters.end_time> to be equal to <end_time>

        :param end_time: the datetime to be set
        """
        cls.filters.end_time = end_time
