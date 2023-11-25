from dataclasses import dataclass
from datetime import datetime
from typing import NewType
from astra.data.parameters import ParameterValue, Tag
from use_case_handlers import UseCaseHandler

@dataclass
class GraphingData:
    """
    A container for data needed by the fronted to graph the requested tags.
    """
    
    dict[tag, tuple[tuple[datetime, ParameterValue]]]
    # dictionary where each key is a tag, and each value is a tuple of length-2 tuples
    # which contain a date and value to be graphed that correspond to that tag.

@dataclass
class GraphingFilters:
    """
    A container for all the data required by the graphing handler.

    :param shown_tags: a dictionary mapping each tag to a list of values that are
    the value of that tag in order beginning at <start_date> and ending at <end_date>.
    :param shown_tags: a list of tags that are currently shown on the graph.
    :param removed_tags: a list of tags that are currently not shown on the graph.
    :param start_date: the earliest time that values for each tag are from.
    :param end_date: the latest time that values for each tag are from.
    :param interval: ?????.
    """

    shown_tags: list[Tag]
    start_date: datetime | None
    end_date: datetime | None
    # maybe left to fronted as they can simply take every n-th value from the list.
    interval: int


class GraphingHandler(UseCaseHandler):
    pass
