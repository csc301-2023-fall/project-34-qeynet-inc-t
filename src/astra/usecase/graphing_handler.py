from dataclasses import dataclass
from datetime import datetime
from copy import deepcopy
from typing import Mapping
from astra.data.data_manager import DataManager
from astra.data.parameters import ParameterValue, Tag
from astra.data.telemetry_data import TelemetryData
from .use_case_handlers import UseCaseHandler

DATETIME_FORMAT = "%d/%m/%Y, %H:%M:%S"


@dataclass
class GraphingData:
    """
    A container for data needed by the fronted to graph the requested tags. For each tag,
    the length of their times and values lists must be the same.

    :param shown_tags: A dictionary where each key is a tag, and each value is a tuple of lists.
    the first list is a list of strings representing times and the second is a list of values at
    those times for that tag. These lists must be the same length.
    :param curr_telemetry_data: The telemetry data that was used to create the <shown_tags>. It is
    used to correctly filter data when it is requested without accessing the database each time.
    """

    # The list of strings is a list of dates, formatted as <DATETIME_FORMAT>
    shown_tags: dict[Tag, tuple[list[str], list[ParameterValue | None]]]
    curr_telemetry_data: TelemetryData


@dataclass
class GraphingFilters:
    """
    A container for all the data required by the graphing handler.

    :param shown_tags: a set of tags that should be shown on the graph.
    :param start_time: the earliest time that values for each tag are from.
    :param end_time: the latest time that values for each tag are from.
    :param interval: The number of frams between each value in the list of values.
    """

    shown_tags: set[Tag]
    start_time: datetime | None
    end_time: datetime | None


class GraphingHandler(UseCaseHandler):
    """
    GraphingHandler is a implementation of UseCaseHandler for the graphing tab.
    It takes care of acquiring and formatting data needed by the graphing tab.
    """

    @classmethod
    def get_data(cls, dm: DataManager, filter_args: GraphingFilters) -> GraphingData:
        """
        get_data is a method that accesses the database to get the initial data needed to
        make a graph. Then, it fills out and returns a GraphingData object.

        :param dm: All data stored in the program.
        :param filter_args: Contains all information on filters to be applied
        :return: A GraphingData object containing the data needed to graph the requested tags.
        """
        # get the data from the database
        telemetry_data = dm.get_telemetry_data(
            None, None, dm.tags)

        # initialize the graphing data, with all data from the database
        graphing_data = GraphingData({}, telemetry_data)

        # filter the graphing data by mutating it.
        cls._filter_graphing_data(graphing_data, filter_args)

        return graphing_data

    @classmethod
    def update_data(cls, prev_data: GraphingData,
                    filter_args: GraphingFilters, dm: DataManager = None) -> None:
        """
        update_data is a method that updates the currently represented information,
        by modifying <prev_data> to match the current filters. Note, this method
        will not add new data from the database.

        :param prev_data: The representation of the current state of displayed data
        :param filter_args: Contains all information on filters to be applied
        :param dm: Contains all data stored by the program to date
        """
        cls._filter_graphing_data(prev_data, filter_args)

    @classmethod
    def export_graph_to_file(cls, filter_args: GraphingFilters,
                             dm: DataManager, file_name: str) -> None:
        """
        export_graph_to_file is a method that exports the graph to a file.

        :param prev_data: The representation of the current state of displayed data
        :param file_name: The name of the file to export the graph to.
        """
        telemetry_data = dm.get_telemetry_data(filter_args.start_time,
                                               filter_args.end_time,
                                               filter_args.shown_tags)

        interval = 1

        telemetry_data.save_to_file(file_name, interval)

    @classmethod
    def _initialize_graphing_data(cls, telemetry_data: TelemetryData) -> GraphingData:
        """
        fill_in_data is a method that fills in the data in <graphing_data> with
        the data in <telemetry_data>.

        :param telemetry_data: The tags and timeframes that will be used to fill in
        the data.
        :return: A GraphingData object containing the data needed to graph the requested tags.
        """

        graphing_data = GraphingData({}, {})

        # Loop through each tag in the data and add its times and values to the graphing data
        for tag in telemetry_data.tags:
            graphing_data.all_tags_values[tag] = ([], [])
            curr_tag_times = graphing_data.all_tags_values[tag][0]
            cur_tag_values = graphing_data.all_tags_values[tag][1]

            interval = 1

            tag_values = telemetry_data.get_parameter_values(tag, interval)

            # Loop through each time in the tag and add it to the graphing data, so long as
            # the value exists at that time (it is not None)
            cls._add_tag_values(tag_values, curr_tag_times, cur_tag_values)

        # Make a deep copy of the all_tags_values to be used as the shown_tags since they
        # have not been filtered yet
        graphing_data.shown_tags = deepcopy(graphing_data.all_tags_values)

        return graphing_data

    @classmethod
    def _add_tag_values(cls, tag_values: Mapping[datetime, ParameterValue | None],
                        curr_tag_times: list[str],
                        cur_tag_values: list[ParameterValue]) -> None:
        """
        add_tag_values is a method that adds the values in <tag_values> to the
        graphing data, so long as the value exists at that time (it is not None)

        :param tag_values: The values that will be added to the graphing data.
        :param curr_tag_times: The list of times to append to.
        :param cur_tag_values: The list of values to append to.

        Note: This method mutates <curr_tag_times> and <cur_tag_values>, and returns with
        len(curr_tag_times) == len(cur_tag_values).

        PRECONDITION: The keys in <tag_values> are sorted in chronological order.
        """
        for time in tag_values:
            value = tag_values[time]
            # In the case that a value at a time is None, we do not add it to the graphing data.
            if value is not None:
                curr_tag_times.append(time.strftime(DATETIME_FORMAT))
                cur_tag_values.append(value)

    # @classmethod
    # def _filter_graphing_data(cls, graphing_data: GraphingData,
    #                           filter_args: GraphingFilters) -> None:
    #     """
    #     filter_graphing_data is a method that filters the data in <graphing_data> based on
    #     <filter_args>. This is done by mutating <graphing_data>.

    #     :param graphing_data: The data that will be filtered by mutating it.
    #     :param filter_args: Contains all information on filters to be applied.
    #     """
    #     for tag in graphing_data.all_tags_values:

    #         # Filter out any tags that are not in <filter_args.shown_tags> but in the graphing data.
    #         if (tag not in filter_args.shown_tags) and (tag in graphing_data.shown_tags):
    #             del graphing_data.shown_tags[tag]

    #         # Add in any tags that need to be in <graping_data.shown_tags> but are not
    #         elif (tag in filter_args.shown_tags) and (tag not in graphing_data.shown_tags):

    #             # get the times and values for the tag
    #             curr_tag_dates = graphing_data.all_tags_values[tag][0]
    #             curr_tag_values = graphing_data.all_tags_values[tag][1]

    #             # Add the tag and its values to shown tags.
    #             graphing_data.shown_tags[tag] = (
    #                 curr_tag_dates.copy(), curr_tag_values.copy())

    #     # Filter out any times that are not within the start and end times
    #     cls._filter_times(
    #         graphing_data, filter_args.start_time, filter_args.end_time)

    @classmethod
    def _filter_graphing_data(cls, graphing_data: GraphingData,
                              filter_args: GraphingFilters) -> None:
        """
        _filter_graphing_data is a method that filters the <graphing_data> based on <filter_args>.
        This is done by mutating <graphing_data.shown_tags>.

        :param graphing_data: The data that will be filtered by mutating it.
        :param filter_args: Contains all information on filters to be applied.
        """
        telemetry_data = graphing_data.curr_telemetry_data

        times_list = list(telemetry_data.timestamps())

        min_index, max_index = cls._filter_times(times_list, filter_args.start_time,
                                                 filter_args.end_time)

        # Format the times to strings. Within the indices give by _filter_times.
        formatted_times_list = [time.strftime(DATETIME_FORMAT)
                                for time in times_list[min_index: max_index+1]]

        # Remove all tags before looking through the filter to get only the required tags
        graphing_data.shown_tags.clear()

        # If the max and min index are the same, there are no values within the time_frame.
        if min_index == max_index:
            return None

        # Loop through the <filter_args> to find which tags we must add to the data.
        for tag in filter_args.shown_tags:
            # Since the list of times correspond to the values, we can take the same slice of both.
            parameter_values = telemetry_data.get_parameter_values(tag, 1)
            curr_values = list(parameter_values.values())[min_index: max_index+1]

            graphing_data.shown_tags[tag] = (formatted_times_list,
                                             curr_values)

    # @classmethod
    # def _filter_times(cls, graphing_data: GraphingData,
    #                   start_time: datetime | None,
    #                   end_time: datetime | None) -> None:
    #     """
    #     This method will filter out any times that are not within the start and end times, by
    #     mutating the <shown_tags> parameter.

    #     :param graphing: The graphing data containing the list of times that will be filtered.
    #     The list of time must be the same length as the list of values, and sorted in chronological
    #     order.
    #     :param start_time: The datetime that is the earliest time that values for each tag
    #     are from.
    #     :param end_time: The datetime that is the latest time that values for each tag are from.
    #     """
    #     for tag in graphing_data.shown_tags:
    #         times_list = graphing_data.shown_tags[tag][0]
    #         values_list = graphing_data.shown_tags[tag][1]

    #         min_index = cls._find_min_index(times_list, start_time)
    #         max_index = cls._find_max_index(times_list, end_time)

    #         # determine if there are atleast some values that are within the start and end times
    #         if min_index == len(times_list) - 1:
    #             del graphing_data.shown_tags[tag]
    #         elif max_index == 0:
    #             del graphing_data.shown_tags[tag]
    #         else:
    #             # there are values within the start and end times, so we keep the tag, but slice
    #             # the list.
    #             graphing_data.shown_tags[tag] = (times_list[min_index:max_index+1],
    #                                              values_list[min_index:max_index+1])

    @classmethod
    def _filter_times(cls, times_list: list[datetime],
                      start_time: datetime | None, end_time: datetime | None) -> tuple[int, int]:
        """
        This method returns a tuple of ints representing indices that give a slice
        of the <times_list> where all times in it are >= <start_time> and <= <end_time>.

        :param imtes_list: The list of times in chronological order that we need the slice of, which
        is between the <start_time> and <end_time>.
        :param start_time: The datetime that is the earliest time that values for each tag
        are from.
        :param end_time: The datetime that is the latest time that values for each tag are from.
        """
        return (cls._find_min_index(times_list, start_time),
                cls._find_max_index(times_list, end_time))

    @staticmethod
    def _find_min_index(times_list: list[datetime], start_time: datetime | None) -> int:
        """
        Returns an int representing the first index in <times_list>
        that is >= <start_time>. If <start_time> is None, then it will return 0. (no minimum time)

        :param times_list: A list of times that you want the min_index for
        :param start_time: The minimum for values at and after the <min_index>

        Precondition: times_list is sorted chronologically and there are no duplicate times
        """
        if start_time is None:
            return 0

        curr_min = 0
        curr_max = len(times_list) - 1

        while curr_max >= curr_min:

            index = (curr_max + curr_min)//2

            if times_list[index] == start_time:
                return index

            elif times_list[index] > start_time:
                curr_max = index - 1

            elif times_list[index] < start_time:
                curr_min = index + 1

        # In the case that the loop ends, curr_min will be the index of the first time
        # that is after <start_time>.
        return curr_min

    @staticmethod
    def _find_max_index(times_list: list[datetime], end_time: datetime | None) -> int:
        """
        Returns an int representing the last index in <times_list>
        that is <= <end_time>. If <end_time> is None, then it
        will return the last index. (no maximum time)

        :param times_list: A list of times that you want the max_index for
        :param end_time: The maximum for values at and before the <max_index>

        Precondition: times_list is sorted chronologically and there are no duplicate times
        """
        if end_time is None:
            return len(times_list) - 1

        curr_min = 0
        curr_max = len(times_list) - 1

        while curr_max >= curr_min:

            index = (curr_max + curr_min)//2

            if times_list[index] == end_time:
                return index

            elif times_list[index] > end_time:
                curr_max = index - 1

            elif times_list[index] < end_time:
                curr_min = index + 1

        # In the case that the loop ends, curr_max will be the index of the last time
        # that is before <end_time>.
        return curr_max

    # @classmethod
    # def _find_min_index(cls, times_list: list[str], start_time: datetime | None) -> int:
    #     """
    #     This method will find the index of the first time in <times_list> that is after or equal to
    #     <start_time>. If <start_time> is None, then it will return 0. (no minimum time)

    #     :param times_list: The list of times that will be searched.
    #     :param start_time: The datetime that is the earliest time that values for each tag
    #     are from.
    #     :return: The index of the first time in <times_list> that is after <start_time>.
    #     """
    #     if start_time is None:
    #         return 0
    #     else:
    #         # Iterate through the list of times, and return the index of the first time that is
    #         # after or equal to <start_time>
    #         for i in range(len(times_list)):
    #             if datetime.strptime(times_list[i], DATETIME_FORMAT) >= start_time:
    #                 return i
    #         return len(times_list) - 1

    # @classmethod
    # def _find_max_index(cls, times_list: list[str], end_time: datetime | None) -> int:
    #     """
    #     This method will find the index of the first time in <times_list> that is after or equal to
    #     <start_time>. If <start_time> is None, then it will return 0. (no minimum time)

    #     :param times_list: The list of times that will be searched.
    #     :param end_time: The datetime that is the latest time that values for each tag
    #     are from.
    #     :return: The index of the last time in <times_list> that is before <end_time>.
    #     """
    #     if end_time is None:
    #         return len(times_list) - 1
    #     else:
    #         # Iterate through the list of times backwards and return the index of
    #         # the first time that is before or equal to <end_time>.
    #         for i in range(len(times_list)-1, -1, -1):
    #             if datetime.strptime(times_list[i], DATETIME_FORMAT) <= end_time:
    #                 return i
    #         return 0
