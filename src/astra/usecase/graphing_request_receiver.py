from datetime import datetime
from astra.data.data_manager import DataManager
from astra.data.parameters import Tag
from .graphing_handler import GraphingData, GraphingHandler, GraphingFilters
from .request_receiver import RequestReceiver


class GraphingRequestReceiver(RequestReceiver):
    """
    GraphingRequestReceiver is a class that implements the RequestReceiver interface.
    It handles requests from the graphing tab, such as getting the data requested to create a graph,
    updating the currently represented data, changing the timeframe of the graph
    that we are viewing, or adding and removing tags.

    Note that the client is responsible for calling update() after modifying the filters.
    """

    handler: GraphingHandler
    filters: GraphingFilters

    def __init__(self) -> None:
        self.handler = GraphingHandler()
        self.filters = GraphingFilters(set(), None, None, 1)

    @classmethod
    def create(cls, dm: DataManager) -> GraphingData:
        return cls.handler.get_data(dm, cls.filters)

    @classmethod
    def update(cls, previous_data: GraphingData, dm: DataManager = None) -> None:
        cls.handler.update_data(dm, previous_data, cls.filters)

    @classmethod
    def set_start_date(cls, start_date: datetime) -> None:
        cls.filters.start_date = start_date

    @classmethod
    def set_end_date(cls, end_date: datetime) -> None:
        cls.filters.end_date = end_date

    @classmethod
    def set_shown_tags(cls, tags: set[str]) -> None:

        # convert <tags> to Tag objects
        tag_tags = {Tag(tag) for tag in tags}
        cls.filters.shown_tags = tag_tags

    @classmethod
    def remove_shown_tag(cls, tag: str) -> None:
        if tag in cls.filters.shown_tags:
            cls.filters.shown_tags.remove(Tag(tag))

    @classmethod
    def add_shown_tag(cls, tag: str) -> None:

        cls.filters.shown_tags.add(Tag(tag))
