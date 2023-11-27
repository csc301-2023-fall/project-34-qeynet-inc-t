from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, NewType
from astra.data.data_manager import DataManager
from astra.data.parameters import ParameterValue, Tag
from astra.data.telemetry_data import TelemetryData
from use_case_handlers import UseCaseHandler

DATETIME_FORMAT = "%d/%m/%Y, %H:%M:%S"


@dataclass
class GraphingData:
    """
    A container for data needed by the fronted to graph the requested tags. For each tag,
    the length of their times and values lists must be the same.

    :param shown_tags: A dictionary where each key is a tag, and each value is a tuple of lists.
    the first list is a list of strings representing times and the second is a list of values at
    those times for that tag. These lists must be the same length.
    :param all_tags_values: The same format as shown_tags. However, this dictionary contains
    contains all possible data for each tag, not just the data that is currently shown on the
    graph. This is used to update the graph when the user changes the tags that are shown.
    """

    # The list of strings is a list of dates, formatted as <DATETIME_FORMAT>
    shown_tags: dict[Tag, tuple[list[str], list[ParameterValue]]]
    all_tags_values: dict[Tag, tuple[list[str], list[ParameterValue]]]


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
            filter_args.start_time, filter_args.end_time, filter_args.shown_tags)

        # initialize the graphing data, with all data from the database
        graphing_data = cls._initialize_graphing_data(telemetry_data)

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
            graphing_data.shown_tags[tag] = ([], [])
            curr_tag_times = graphing_data.shown_tags[tag][0]
            cur_tag_values = graphing_data.shown_tags[tag][1]

            interval = 1

            tag_values = telemetry_data.get_parameter_values(tag, interval)

            # Loop through each time in the tag and add it to the graphing data, so long as
            # the value exists at that time (it is not None)
            cls._add_tag_values(tag_values, curr_tag_times, cur_tag_values)
        
        graphing_data.all_tags_values = graphing_data.shown_tags.copy()

        return graphing_data

    def _add_tag_values(tag_values: Mapping[datetime, ParameterValue | None],
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

    @classmethod
    def _filter_graphing_data(cls, graphing_data: GraphingData,
                              filter_args: GraphingFilters) -> None:
        """
        filter_graphing_data is a method that filters the data in <graphing_data> based on
        <filter_args>. This is done by mutating <graphing_data>.

        :param graphing_data: The data that will be filtered by mutating it.
        :param filter_args: Contains all information on filters to be applied.
        """
        for tag in GraphingData:
            
            
            # Filter out any times that are not within the start and end times
            cls._filter_times(graphing_data, filter_args.start_time, filter_args.end_time)
