from queue import Queue
from typing import Iterable

from astra.data.alarms import (
    Alarm,
    AlarmCriticality,
)

from .filters import DashboardFilters
from .table_return import TableReturn, TelemetryTableReturn
from astra.data.data_manager import DataManager
from astra.data.telemetry_data import TelemetryFrame
from astra.data.parameters import ParameterValue, Tag
from .utils import eval_param_value

SORT = 'SORT'
TAG = 'TAG'
INDEX = 'INDEX'
DESCRIPTION = 'DESCRIPTION'
DESCENDING = '<'
DATA = 'DATA'
CONFIG = 'CONFIG'
ROUNDING_DECMIALS = 2
# For now, this choice is somewhat arbitrary
CACHE_SIZE = 200


class DashboardHandler:
    """DashboardHandler is a child class of UseCaseHandler that defines
    data filtering requested by the Telemetry Dashboard
    """

    @staticmethod
    def search_tags(search: str, cache: dict[str, Iterable[str]], eviction: Queue) \
            -> Iterable[str]:
        """
        Finds any tag where their tag name or description matches <tag> and returns them

        :param search: The substring to search for
        :param cache: Stores CACHE_SIZE + 1 keys, where each key matches a previous <search>
        value and maps to a list of all tags where <search> is a substring. Also maps ""
        to all tags for the current device. Is mutated by this function
        :param eviction: Stores the order in which keys were added to the cache in case
        eviction is neccessary
        :return: A list of all tags where <search> is a substring
        """
        # First, finding the closest matching search value in the cache
        closest = ''
        max_len = 0
        for prev_search in cache:
            if prev_search in search and len(prev_search) > max_len:
                closest = prev_search
                max_len = len(prev_search)

        # If search request is already in the cache
        if closest == search:
            return cache[search]

        # Search request is not already in the cache, so we perform the search on the closest
        # option
        matching = []
        for tag in cache[closest]:
            lower_tag = tag.lower()
            lower_search = search.lower()
            if lower_search in lower_tag:
                matching.append(tag)
        if search != "":
            cache[search] = matching
            eviction.put(search)

        # evicting from the cache if needed
        if len(cache) == CACHE_SIZE + 2:
            remove = eviction.get()
            cache.pop(remove)
        return matching

    @classmethod
    def _format_param_value(cls, tag_data: ParameterValue | None) -> str:
        """
        Formats the <tag_data> for viewing in the telemetry dashboard

        :param tag_data: The (converted) data to format
        :return: A string with the appropriate formatting
        """
        if tag_data is None:
            return '-'
        return f'{round(tag_data, ROUNDING_DECMIALS)}'

    @classmethod
    def _format_alarm_data(cls, alarm: Alarm | None) -> str:
        """
        Gets the relevant data from <alarm> and formats it for display in the telemetry dashboard.

        :param alarm: the alarm to get data from
        :return: a string that contains alarm data formatted for display in the telemetry dashboard.
        """

        if alarm is None:
            return '-'
        else:
            eventbase_description = alarm.event.base.description
            return f'{alarm.priority}: {eventbase_description}'

    @classmethod
    def _tag_to_alarms(cls, tags: list[Tag],
                       alarms: dict[str, list[Alarm]]) -> dict[Tag, Alarm]:
        """
        Finds and returns the highest priority alarm for each Tag in <tags, for use in
        displaying some alarm data in the telemetry dashboard.

        :param tags: The list of tags to find alarms for
        :param alarms: The alarms to search through
        :return: A dictionary mapping each tag to its highest priority alarm
        """

        tag_to_alarms = {}
        # List of priorities in order from highest to lowest priority
        priorities = [AlarmCriticality.CRITICAL, AlarmCriticality.HIGH,
                      AlarmCriticality.MEDIUM, AlarmCriticality.LOW, AlarmCriticality.WARNING]
        available_tags = tags.copy()

        # loop over each priority starting from the highest.
        for priority in priorities:
            alarms_at_this_prio = alarms[priority.value]

            # loop over each alarm at this priority and get their related tags
            for alarm in alarms_at_this_prio:
                tags_for_this_alarm = alarm.event.base.tags

                # If we haven't already seen this tag at a higher priority, add it to the dict along
                # with the related alarm.
                for tag in tags_for_this_alarm:

                    if tag in available_tags:
                        tag_to_alarms[tag] = alarm
                        available_tags.remove(tag)

        return tag_to_alarms

    @classmethod
    def _add_rows_to_output(cls, input_tags: Iterable[Tag], dm: DataManager, tf: TelemetryFrame) \
            -> tuple[list[list[str]], list[list[str]]]:
        """
        Adds tags from <input_tags> and their relevant data to <output_list>

        :param dm: Contain all data stored by the program to date
        :param input_tags: a set of tags to be added to output_list
        :return A tuple of two 2D lists. The first contains an ordered list
        of tag data to be shown to the user, the other an unordered list of
        tag data to not yet be shown to the user
        """

        data_parameters = dm.parameters
        data_tags = dm.tags
        data_alarms = dm.alarms.get_alarms()
        tag_to_alarms = cls._tag_to_alarms(list(data_tags), data_alarms)

        include = []
        removed = []

        for tag in data_tags:

            tag_parameters = data_parameters[tag]
            tag_description = tag_parameters.description
            # None if no alarm for this tag
            tag_alarm = tag_to_alarms.get(tag, None)

            # creating the string for the tag value
            raw_timestamp_data = tf.data[tag]
            tag_data = eval_param_value(tag_parameters, raw_timestamp_data)

            # creating the string for the tag setpoint value
            raw_tag_setpoint_value = tag_parameters.setpoint
            tag_setpoint_value = eval_param_value(
                tag_parameters, raw_tag_setpoint_value)

            # creating strings for relevant tag data
            tag_value = cls._format_param_value(tag_data)
            tag_setpoint = cls._format_param_value(tag_setpoint_value)

            # creating strings for unit of measurement of each tag
            if tag_parameters.display_units is None:
                tag_units = "-"
            else:
                tag_units = tag_parameters.display_units.symbol

            # creating strings for the highest priority alarm associated with the tag
            tag_alarm_data = cls._format_alarm_data(tag_alarm)

            include_tag = tag in input_tags
            if include_tag:
                include.append([tag, tag_description, tag_value, tag_setpoint, tag_units,
                                tag_alarm_data])
            else:
                removed.append([tag, tag_description, tag_value, tag_setpoint, tag_units,
                                tag_alarm_data])
        return include, removed

    @classmethod
    def _sort_output(cls, return_data: TableReturn, sort: tuple[str, str]):
        """
        sorts the <table> field of return_data based on <sort>

        :param return_data: the output container to sort data from
        :param sort: defines how output should be sorted

        PRECONDITION: The values of sort satisfy the docstrings of the sort field in
        DashboardFilters
        """
        if sort is not None:
            # Determining which column to sort by
            if sort[1] == TAG:
                key_index = 0
            else:
                # This case indicates sorting should occur by description
                key_index = 1

            # By default, sorting occurs by ascending values, so a case is
            # needed to check if it should occur by descending order
            reverse = False
            if sort[0] == DESCENDING:
                reverse = True

            return_data.table = sorted(return_data.table,
                                       key=lambda x: x[key_index],
                                       reverse=reverse)

    @classmethod
    def get_data(cls, dm: DataManager, filter_args: DashboardFilters):
        """
        Creates a data table pertaining to a single telemetry frame with data filtering
        requested by the user

        :param dm: Contains all data stored by the program to date
        :param filter_args: Defines all filters to be applied
        :return: An instance of TableReturn where the <table> attribute
        represents the ordered rows to be presented in the Telemetry Dashboard
        table, and removed represents all tags not shown presently

        PRECONDITIONS: <cls.index> is not None, and <cls.tags> is not empty
        """

        telemetry_data = dm.get_telemetry_data(
            filter_args.start_time, filter_args.end_time, dm.tags)
        telemetry_frame = telemetry_data.get_telemetry_frame(filter_args.index)

        # First, all the return data
        timestamp = telemetry_frame.time

        include, remove = cls._add_rows_to_output(
            filter_args.tags, dm,
            telemetry_frame)
        frame_quantity = telemetry_data.num_telemetry_frames

        return_data = TelemetryTableReturn(include, remove, frame_quantity, timestamp,
                                           telemetry_data)

        # Next, determine if any sorting was requested
        cls._sort_output(return_data, filter_args.sort)

        return return_data

    @classmethod
    def update_data(cls, previous_table: TelemetryTableReturn, filter_args: DashboardFilters):
        """
        Updates the currently shown table based on new filter or sort requests from the user

        :param filter_args: Defines all filters to be applied
        :param previous_table: A representation of the current shown data in
        the Telemetry Dashboard
        """

        # Technically inefficient, but far better than re-building every time.
        # Potential choice for optimization if needed
        new_table = previous_table.table.copy()
        new_removed = previous_table.removed.copy()

        if filter_args.tags is not None:
            tags = filter_args.tags
            if len(previous_table.table) < len(tags):
                # Indicates some tag from <previous_table.removed> needs to be shown
                for i in range(len(previous_table.removed)):
                    removed_row = previous_table.removed[i]
                    if removed_row[0] in tags:
                        new_removed.remove(removed_row)
                        new_table.append(removed_row)
            elif len(previous_table.table) > len(tags):
                # Indicates some tag from <previous_table.table> needs to be removed
                for i in range(len(previous_table.table)):
                    removed_row = previous_table.table[i]
                    if removed_row[0] not in tags:
                        new_removed.append(removed_row)
                        new_table.remove(removed_row)
        previous_table.table = new_table
        previous_table.removed = new_removed
        cls._sort_output(previous_table, filter_args.sort)

        previous_table.frame_quantity = previous_table.td.num_telemetry_frames
