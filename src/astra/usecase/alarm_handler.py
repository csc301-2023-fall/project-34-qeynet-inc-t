from dataclasses import dataclass
from datetime import datetime
from queue import Queue
from typing import Iterable, Any

from astra.data.alarms import (AlarmPriority, AlarmCriticality, RateOfChangeEventBase, Alarm,
                               StaticEventBase, ThresholdEventBase, SetpointEventBase,
                               SOEEventBase, AllEventBase, EventBase, AnyEventBase)
from astra.data.data_manager import DataManager
from astra.data.parameters import Tag
from astra.usecase.use_case_handlers import UseCaseHandler, TableReturn

PRIORITY = 'PRIORITY'
CRITICALITY = 'CRITICALITY'
TYPE = 'TYPE'
REGISTERED_DATE = 'REGISTERED_DATE'
CONFIRMED_DATE = 'CONFIRMED_DATE'
UNACKNOWLEDGED = 'UA'
DESCENDING = '>'
VALID_SORTING_COLUMNS = ['ID', 'PRIORITY', 'CRITICALITY', 'REGISTERED', 'CONFIRMED', 'TYPE']


class LimitedSlotAlarms:
    """
    Contains all alarms to be shown in the banner at the top of the screen

    :param _slots: A dict of priority queues
    :param _priorities: an ordered list of keys in _slots, where elements are ordered by descending importance
    """
    _slots: dict[str, Queue]
    _priorities: list[str]

    @classmethod
    def __init__(cls):
        cls._priorities = ['n', 'o']
        new_queue = Queue(3)
        old_queue = Queue(3)
        cls._slots = {'n': new_queue, 'o': old_queue}

    @classmethod
    def get_all(cls) -> list[str]:
        """
        Compacts all data amongst <cls._slots> into one list in a readable format

        :return: An ordered list of data compiled from <cls._slots>
        """
        all_items = []
        for slot_type in cls._priorities:
            age_q = cls._slots[slot_type]
            q_items = age_q.queue

            new_items = list(q_items)
            new_items.sort()

            all_items += new_items
        return all_items

    @classmethod
    def insert_into_new(cls, alarm: Alarm) -> None:
        """
        Inserts information about <alarm> into the new alarms queue in <cls._slots>. If the queue
        exceeds its intended size, remove the oldest element in the queue

        :param alarm: The alarm to insert into the banner slots
        """
        cls._slots['n'].put(alarm)

    @classmethod
    def insert_into_old(cls, alarm: Alarm) -> None:
        """
        Inserts information about <alarm> into the old alarms queue in <cls._slots>. If the queue
        exceeds its intended size, remove the oldest element in the queue

        :param alarm: The alarm to insert into the banner slots
        """
        cls._slots['o'].put(alarm)


@dataclass
class AlarmsFilters:
    """
    A container for all the filters that can be applied in the alarm dashboard.

    :param sort: indicates what type of sort should be applied to which column.
    A tuple in the form (sort_type, sort_column), where sort_type is one
    of '>' or '<', and
    sort_column is one of: {PRIORITY, CRITICALITY, TYPE, REGISTERED_DATE, CONFIRMED_DATE}
    :param priorities: A set of all priorities to be shown in the table.
    :param criticalities: A set of all criticalities to be shown in the table.
    :param types: A set of all types to be shown in the table.
    :param registered_start_time: the first time of alarms being registered. Is less than
    end_time
    :param registered_end_time: the last time of alarms being registered to be examined
    :param confirmed_start_time: the first time of alarms being confirmed. Is less than
    end_time
    :param confirmed_end_time: the last time of alarms being confirmed to be examined
    :param new: whether only unacknowledged alarms should solely be seen

    All of the above parameters may be None iff they have never been set before
    """

    sort: tuple[str, str] | None
    priorities: set[AlarmPriority] | None
    criticalities: set[AlarmCriticality] | None
    types: Iterable[str] | None
    registered_start_time: datetime | None
    registered_end_time: datetime | None
    confirmed_start_time: datetime | None
    confirmed_end_time: datetime | None
    new: bool


class AlarmsHandler(UseCaseHandler):
    @staticmethod
    def _get_alarm_type(alarm: Alarm) -> str:
        """
        Returns the string representation of the underlying EventBase of <alarm>

        :param alarm: The alarm to examine
        :return: A string representation of the alarm type
        """
        base = alarm.event.base
        match base:
            case RateOfChangeEventBase():
                return 'RATE_OF_CHANGE'
            case StaticEventBase():
                return 'STATIC'
            case ThresholdEventBase():
                return 'THRESHOLD'
            case SetpointEventBase():
                return 'SETPOINT'
            case SOEEventBase():
                return 'SOE'
            case AllEventBase():
                return 'L_AND'
            case _:
                return 'L_OR'

    @classmethod
    def _get_relevant_tags(cls, event_base: EventBase) -> list[Tag]:
        """
        Takes an event base and outputs a list of all relevant tags to the base

        :param event_base: The event base to examine
        :return: A list of all relevant tags to the base
        """
        if type(event_base) is not AllEventBase \
                and type(event_base) is not AnyEventBase \
                and type(event_base) is not SOEEventBase:
            return [event_base.tag]
        else:
            all_tags = []
            for inner_event_base in event_base.event_bases:
                all_tags += cls._get_relevant_tags(inner_event_base)
            return all_tags

    @classmethod
    def _determine_toggled(cls, alarm: Alarm, filter_args: AlarmsFilters) -> bool:
        """
        Uses <filter_args> to determine if <alarm> should be shown or not

        :param alarm: The alarm that should be enabled or disabled
        :param filter_args: Contains arguments that will determine if <alarm> is shown
        :return: true iff <alarm> should be shown
        """
        show = True
        # First, checking if it satisfies priority requirements
        show = alarm.priority.name in filter_args.priorities

        # Next, checking if it satisfies criticality arguments
        show = show and alarm.criticality.name in filter_args.criticalities

        # Checking if the alarm type matches
        show = show and cls._get_alarm_type(alarm) in filter_args.types

        # Now we need to make sure the alarm fits in the time parameters
        alarm_confirm_time = alarm.event.confirm_time
        alarm_register_time = alarm.event.confirm_time
        if filter_args.confirmed_start_time is not None:
            compare_time = filter_args.registered_start_time
            show = show and alarm_confirm_time > compare_time

        if filter_args.confirmed_end_time is not None:
            compare_time = filter_args.registered_end_time
            show = show and alarm_confirm_time < compare_time

        if filter_args.registered_start_time is not None:
            register_time = filter_args.registered_start_time
            show = show and alarm_register_time > register_time

        if filter_args.registered_start_time is not None:
            register_time = filter_args.registered_start_time
            show = show and alarm_register_time < register_time

        # Finally, checking if we only show unacknowledged alarms
        if filter_args.new:
            show = show and alarm.acknowledgement == UNACKNOWLEDGED
        return show

    @classmethod
    def _sort_output(cls, return_data: TableReturn, sort: tuple[str, str]):
        """
        sorts the <table> field of return_data based on <sort>

        :param return_data: the output container to sort data from
        :param sort: defines how output should be sorted

        PRECONDITION: The values of sort satisfy the docstrings of the sort field in
        AlarmsFilters
        """
        if sort is not None:
            # Determining which column to sort by
            key_index = 0
            for i in range(len(VALID_SORTING_COLUMNS)):
                if sort[1] == VALID_SORTING_COLUMNS[i]:
                    key_index = i
                    break

            # By default, sorting occurs by ascending values, so a case is
            # needed to check if it should occur by descending order
            reverse = False
            if sort[0] == DESCENDING:
                reverse = True

            return_data.table = sorted(return_data.table,
                                       key=lambda x: x[key_index],
                                       reverse=reverse)

    @classmethod
    def _extract_alarm_data(cls, alarm: Alarm, priority: AlarmPriority) -> list:
        """
        Takes an Alarm and constructs a list of ordered data to be output in a table

        :param alarm: The alarm to construct data from
        :param priority: The priority of the associated <alarm>
        :return: A list in the form of [<alarm> id, <alarm> priority, <alarm> criticality,
        <alarm> register time, <alarm> confirm time, <alarm> type, <alarm> description, and the
        alarm itself
        """
        alarm_id = alarm.event.id
        alarm_priority = priority
        alarm_criticality = alarm.criticality
        alarm_register_time = alarm.event.register_time
        alarm_confirm_time = alarm.event.confirm_time
        alarm_type = cls._get_alarm_type(alarm)
        alarm_tags = cls._get_relevant_tags(alarm.event.base)
        alarm_description = alarm.event.description

        new_row = [alarm_id, alarm_priority, alarm_criticality, alarm_register_time,
                   alarm_confirm_time, alarm_type, alarm_tags, alarm_description, alarm]
        return new_row

    @classmethod
    def get_data(cls, dm: dict[AlarmPriority, set[Alarm]], filter_args: AlarmsFilters) \
            -> TableReturn:
        """
        Using the current data structure of alarms, packs all data stored by the alarms into
        an easily accessible format

        :param dm: Contains all alarms known to the program
        :param filter_args: Describes all filters to apply to the filter
        :return: A container for all data to be shown by the table
        """
        shown = []
        removed = []
        for priority in dm:
            for alarm in dm[priority]:
                new_row = cls._extract_alarm_data(alarm, priority)
                if cls._determine_toggled(alarm, filter_args):
                    shown.append(new_row)
                else:
                    removed.append(new_row)

        return_table = TableReturn(shown, removed)
        return return_table

    @classmethod
    def update_data(cls, prev_data: TableReturn, filter_args: AlarmsFilters,
                    dm: DataManager = None) -> None:
        """
        Updates the previous data returned by get_data to apply any new filters

        :param prev_data: The data returned by the last call to cls.get_data
        :param filter_args: Describes all filters to apply to the table
        :param dm: Contains all data known to the program
        """
        new_table = []
        new_removed = []

        for row in prev_data.table:
            alarm = row[8]
            if not cls._determine_toggled(alarm, filter_args):
                new_removed.append(row)
            else:
                new_table.append(row)
        for row in prev_data.removed:
            alarm = row[8]
            if cls._determine_toggled(alarm, filter_args):
                new_table.append(row)
            else:
                new_removed.append(row)

        prev_data.table = new_table
        prev_data.removed = new_removed
        cls._sort_output(prev_data, filter_args.sort)
