from astra.data.alarms import (AlarmPriority, RateOfChangeEventBase, Alarm,
                               StaticEventBase, ThresholdEventBase, SetpointEventBase,
                               SOEEventBase, AllEventBase)
from astra.data.data_manager import DataManager
from astra.usecase.filters import AlarmsFilters
from astra.usecase.table_return import TableReturn

PRIORITY = 'PRIORITY'
CRITICALITY = 'CRITICALITY'
TYPE = 'TYPE'
REGISTERED_DATE = 'REGISTERED_DATE'
CONFIRMED_DATE = 'CONFIRMED_DATE'
DESCENDING = '>'
PRIORITIES = [AlarmPriority.WARNING.name, AlarmPriority.LOW.name, AlarmPriority.MEDIUM.name,
              AlarmPriority.HIGH.name, AlarmPriority.CRITICAL.name]
VALID_SORTING_COLUMNS = ['ID', 'PRIORITY', 'CRITICALITY', 'REGISTERED', 'CONFIRMED', 'TYPE']
NEW_QUEUE_KEY = 'n'
OLD_QUEUE_KEY = 'o'
NEW_PREFIX = "[NEW] "
MAX_BANNER_SIZE = 6
MAX_NEW_SIZE = 3
MAX_OLD_SIZE = 3


class AlarmBanner:
    """
    Stores alarms to be shown in the banner at the top of the screen according to acknowledgement

    :param _slots: Maps constant strings to the appropriate alarms list
    :type: dict[str, list[Alarm]]

    :param _priorities: an ordered list of keys in _slots, where elements are ordered by
    descending importance
    :type: list[str]
    """

    _slots = {NEW_QUEUE_KEY: [], OLD_QUEUE_KEY: []}  # type: dict[str, list[Alarm]]
    _priorities = [NEW_QUEUE_KEY, OLD_QUEUE_KEY]

    @staticmethod
    def create_banner_string(alarm: Alarm) -> str:
        """Creates an appropriate string for the banner provided an alarm

        :param alarm: The alarm to detail in the returned string
        :return A representation of the alarm for the banner
        """
        priority_str = (f"{alarm.priority.name[0] + alarm.priority.name[1:].lower()}"
                        f"-priority alarm ")
        num_str = f'(#{alarm.event.id}): '
        desc_str = alarm.event.description
        return priority_str + num_str + desc_str

    @classmethod
    def get_all(cls) -> list[str]:
        """
        Determines which alarms should be shown in the banners and returns an ordered list
        of strings to display

        Currently, uses the following criteria to determine what should be shown:
            1. 3 new alarms and 3 old alarms should be shown. If there are less than 3 of either,
            the other may take its place
            2. In each age bracket, we use the highest priority to determine which should be shown

        :return: An ordered list of strings to show in the banner
        """

        all_items: list[str] = []

        # Note: while this implementation may seem slow, due to the nature of alarms
        # being rare and banner slots being limited, speed should not be an issue
        new_q = cls._slots[NEW_QUEUE_KEY]
        new_q_items = new_q.copy()
        new_q_items.sort(reverse=True)
        old_q = cls._slots[OLD_QUEUE_KEY]

        # We want to reserve 3 slots for old alarms, but if there's less than 3 old alarms,
        # populate the banner with more new ones
        old_q_size = len(old_q)
        if old_q_size > MAX_NEW_SIZE:
            max_new = MAX_NEW_SIZE
        else:
            max_new = MAX_BANNER_SIZE - old_q_size

        # Getting and formatting strings for the top priority new alarms
        i = 0
        while i < len(new_q_items) and len(all_items) < max_new:
            item = new_q_items[i]
            new_str = NEW_PREFIX + cls.create_banner_string(item)
            all_items.append(new_str)
            i += 1

        # Getting and formatting strings for the top priority old alarms
        i = 0
        old_q_items = old_q.copy()
        old_q_items.sort(reverse=True)

        # We run a while loop over the size of <all_items> to ensure the
        # banner is as populated as possible
        while len(all_items) < MAX_BANNER_SIZE:
            item = old_q_items[i]
            old_str = cls.create_banner_string(item)
            all_items.append(old_str)
            i += 1

        return all_items

    @classmethod
    def insert_into_new(cls, alarm: Alarm) -> None:
        """
        Inserts <alarm> into the new alarms queue in <cls._slots>

        :param alarm: The alarm to insert into the new alarms queue
        """
        new_q = cls._slots[NEW_QUEUE_KEY]
        new_q.append(alarm)

    @classmethod
    def insert_into_old(cls, alarm: Alarm) -> None:
        """
        Moves <alarm> from the new alarms list and into the old alarms list

        :param alarm: The alarm to insert into the old banner slots

        PRECONDITION: <alarm> is in <cls._slots[NEW_QUEUE_KEY]>
        """
        old_q = cls._slots[OLD_QUEUE_KEY]
        new_q = cls._slots[NEW_QUEUE_KEY]

        new_q.remove(alarm)
        old_q.append(alarm)

    @classmethod
    def remove_alarm_from_banner(cls, alarm: Alarm) -> None:
        """
        Removes <alarm> from the appropriate queue

        :param alarm: The alarm to remove from any banner slots

        PRECONDITION: <alarm> is in one list in <cls._slots>
        """
        if alarm.acknowledged:
            old_q = cls._slots[OLD_QUEUE_KEY]
            old_q.remove(alarm)
        else:
            new_q = cls._slots[NEW_QUEUE_KEY]
            new_q.remove(alarm)


class AlarmsHandler:
    """
    Processes requests of the program when it comes to displaying alarm information

    :param banner_container: Data structure to determine what information to store in the
    alarm banner at the top of the screen
    :type: AlarmBanner
    """

    banner_container = AlarmBanner()

    @staticmethod
    def _get_alarm_type(alarm: Alarm) -> str:
        """
        Returns the string representation of the underlying EventBase of <alarm>

        NOTE: This is a pretty bad code smell. It will work--and if there are no further alarm
        types to add then this is fine enough--but this should be refactored.

        :param alarm: The alarm to extract a type from
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
    def _determine_toggled(cls, alarm: Alarm, filter_args: AlarmsFilters) -> bool:
        """
        Uses <filter_args> to determine if <alarm> should be shown or not

        :param alarm: The alarm that should be enabled or disabled
        :param filter_args: Contains arguments that will determine if <alarm> is shown
        :return: true iff <alarm> should be shown
        """

        # First, checking if it satisfies priority requirements

        show: bool = True
        show = alarm.priority.name in filter_args.priorities

        # Next, checking if it satisfies criticality arguments
        show = show and alarm.criticality.name in filter_args.criticalities

        # Checking if the alarm type matches
        if filter_args.types is not None:
            show = show and cls._get_alarm_type(alarm) in filter_args.types

        # Checking if the tag of the alarm is requested to be shown
        if filter_args.tags is not None:
            relevant_tags = set(alarm.event.base.tags)
            show = show and len(relevant_tags.difference(filter_args.tags)) == 0

        # Now we need to make sure the alarm fits in the time parameters
        alarm_confirm_time = alarm.event.confirm_time
        alarm_register_time = alarm.event.confirm_time

        compare_time = filter_args.confirmed_start_time
        show = show and alarm_confirm_time >= compare_time

        compare_time = filter_args.confirmed_end_time
        show = show and alarm_confirm_time <= compare_time

        register_time = filter_args.registered_start_time
        show = show and alarm_register_time >= register_time

        register_time = filter_args.registered_end_time
        show = show and alarm_register_time <= register_time

        # Finally, checking if we only show unacknowledged alarms
        if filter_args.new:
            show = show and not alarm.acknowledged
        return show

    @classmethod
    def _sort_output(cls, return_data: TableReturn, sort: tuple[str, str]):
        """
        sorts the <table> field of return_data based on <sort>

        :param return_data: the output container to sort data from
        :param sort: indicates what type of sort should be applied to which column.
        A tuple in the form (sort_type, sort_column), where <sort_type> is one
        of '>' or '<', and <sort_column> is in VALID_SORTING_COLUMNS.
        """

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
                                   key=lambda x: (x[key_index], x[0]),
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
        alarm_tags = alarm.event.base.tags
        tag_string = ''
        for tag in alarm_tags:
            tag_string += tag + ' '

        alarm_description = alarm.event.description

        new_row = [alarm_id, alarm_priority, alarm_criticality, alarm_register_time,
                   alarm_confirm_time, alarm_type, tag_string, alarm_description, alarm]
        return new_row

    @classmethod
    def get_data(cls, dm: DataManager,
                 filter_args: AlarmsFilters) -> TableReturn:
        """
        Using the current data structure of alarms, packs all data stored by the alarms into
        an easily accessible format

        :param dm: Contains all data known to the program
        :param filter_args: Describes all filters to apply to the filter
        :return: A container for all data to be shown by the table
        """
        shown = []
        removed = []

        alarms_container = dm.alarms
        alarms = alarms_container.get_alarms()

        # simply iterating through all alarms and extracting their data then adding it into
        # the appropriate list from those defined above
        for priority in PRIORITIES:
            for alarm in alarms[priority]:
                new_row = cls._extract_alarm_data(alarm, AlarmPriority(priority))
                if cls._determine_toggled(alarm, filter_args):
                    shown.append(new_row)
                else:
                    removed.append(new_row)

        # emptying the queue of new alarms to inform the alarm banner of their presence
        while alarms_container.new_alarms.qsize() > 0:
            next_item = alarms_container.new_alarms.get()
            cls.banner_container.insert_into_new(next_item)

        return_table = TableReturn(shown, removed)
        if filter_args.sort is not None:
            cls._sort_output(return_table, filter_args.sort)

        return return_table

    @classmethod
    def update_data(cls, prev_data: TableReturn, filter_args: AlarmsFilters) -> None:
        """
        Updates the previous data returned by get_data to apply any new filters or sort

        :param prev_data: The data returned by the last call to cls.get_data
        :param filter_args: Describes all filters to apply to the table
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

        if filter_args.sort is not None:
            cls._sort_output(prev_data, filter_args.sort)

    @classmethod
    def acknowledge_alarm(cls, alarm: Alarm, dm: DataManager) -> None:
        """
        Sets the provided <alarm> have its acknowledgment attribute set to ACKNOWLEDGED

        :param alarm: The alarm whose acknowledgment needs to be modified
        :param dm: Stores all data known to the program
        """
        # Note: While it should be possible to mutate the alarm straight from here,
        # the alarm container needs to do it to enforce that modifying elements of the container
        # is critical code among threads

        alarm_container = dm.alarms
        cls.banner_container.insert_into_old(alarm)
        alarm_container.acknowledge_alarm(alarm)

        # No need to update the table directly from here, as the alarm observer in the container
        # will do it for us

    @classmethod
    def remove_alarm(cls, alarm: Alarm, dm: DataManager) -> None:
        """
        Removes <alarm> from the alarm container in <dm>

        :param alarm: The alarm to remove
        :param dm: Stores the global alarm container
        """
        # Note: While it should be possible to mutate the alarm straight from here,
        # the alarm container needs to do it to enforce that modifying elements of the container
        # is critical code among threads

        alarm_container = dm.alarms
        cls.banner_container.remove_alarm_from_banner(alarm)
        alarm_container.remove_alarm(alarm)

    @classmethod
    def get_banner_elems(cls) -> list[str]:
        """Interfacing method for <cls.banner_container.get_all()>"""
        return cls.banner_container.get_all()
