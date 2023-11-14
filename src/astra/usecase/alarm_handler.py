from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

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


class AlarmHandler(UseCaseHandler):
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
                return "Rate of Change"
            case StaticEventBase():
                return "Static"
            case ThresholdEventBase():
                return "Threshold"
            case SetpointEventBase():
                return "Setpoint"
            case SOEEventBase():
                return "Sequence of Events"
            case AllEventBase():
                return "All Events"
            case _:
                return "Any Events"

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
    def _determine_toggled(cls, alarm: Alarm, filter_args: AlarmsFilters,
                           priority: AlarmPriority) -> bool:
        """
        Uses <filter_args> to determine if <alarm> should be shown or not

        :param alarm: The alarm that should be enabled or disabled
        :param filter_args: Contains arguments that will determine if <alarm> is shown
        :param priority: The priortiy level of the associated <alarm>
        :return: true iff <alarm> should be shown
        """
        show = True
        # First, checking if it satisfies priority requirements
        show = priority in filter_args.priorities

        # Next, checking if it satisfies criticality arguments
        show = show and alarm.criticality in filter_args.criticalities

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
                if cls._determine_toggled(alarm, filter_args, priority):
                    shown.append(new_row)
                else:
                    removed.append(removed)

        return_table = TableReturn(shown, removed)
        return return_table

    @classmethod
    def update_data(cls, prev_data: TableReturn, filter_args: any, dm: DataManager = None) -> None:
        """
        Updates the previous data returned by get_data to apply any new filters

        :param prev_data: The data returned by the last call to cls.get_data
        :param filter_args: Describes all filters to apply to the table
        :param dm: Contains all data known to the program
        """
        for row in prev_data.table:
            alarm = row[9]
            if not cls._determine_toggled(alarm, filter_args, row[1]):
                prev_data.removed.append(row)
                prev_data.table.remove(row)
        for row in prev_data.removed:
            alarm = row[9]
            if cls._determine_toggled(alarm, filter_args, row[1]):
                prev_data.table.append(row)
                prev_data.removed.remove(row)
