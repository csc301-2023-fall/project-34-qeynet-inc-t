from dataclasses import dataclass
from datetime import datetime
from typing import NewType
from astra.data.data_manager import DataManager
from astra.data.parameters import ParameterValue, Tag
from use_case_handlers import UseCaseHandler


@dataclass
class GraphingData:
    """
    A container for data needed by the fronted to graph the requested tags.

    :param shown_tags: A dictionary where each key is a tag, and each value it a tuple of lists.
    the first list is a list of times and the second is a list of values at those times for
    that tag.
    :param removed_tags: The same as <shown_tags> but for tags that have
    been removed from the graph. We keep this data so that we can add the tag back
    to the graph without accessing the database each time.
    """

    shown_tags: dict[Tag, tuple[list[datetime], list[ParameterValue]]]
    removed_tags: dict[Tag, tuple[list[datetime], list[ParameterValue]]]


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
    # maybe left to fronted as they can simply take every n-th value from the list.
    interval: int


class GraphingHandler(UseCaseHandler):

    @classmethod
    def get_data(cls, dm: DataManager, filter_args: GraphingFilters) -> GraphingData:
        """
        get_data is a method that processes the data according to determined
        filters by <filter_args>.

        :param dm: All data stored in the program.
        :param filter_args: Contains all information on filters to be applied
        :return: A GraphingData object containing the data needed to graph the requested tags.
        """
        graphing_data = GraphingData({}, {})
        telemetry_data = dm.get_telemetry_data(
            filter_args.start_time, filter_args.end_time, filter_args.tags)
        telemetry_frame = telemetry_data.get_telemetry_frame(filter_args.index)
        
        
        return GraphingData({}, {})

    @classmethod
    def update_data(cls, prev_data: GraphingData,
                    filter_args: GraphingFilters, dm: DataManager = None) -> None:
        """
        update_data is a method that updates the currently represented information,
        by modifying <prev_data> to match the current filters.
        
        :param prev_data: The representation of the current state of displayed data
        :param filter_args: Contains all information on filters to be applied
        :param dm: Contains all data stored by the program to date
        """
        pass
