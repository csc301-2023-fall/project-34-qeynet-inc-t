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

    handler = GraphingHandler()
    filters = GraphingFilters(set(), None, None)

    @classmethod
    def create(cls, dm: DataManager) -> GraphingData:
        """
        Create is a method that returns the initial data needed to make a graph.

        :param dm: Contains all data stored by the program to date.
        """

        return cls.handler.get_data(dm, cls.filters)

    @classmethod
    def update(cls, previous_data: GraphingData, dm: DataManager = None) -> None:
        """
        update is a method that updates the currently represented information,
        by mutating the data in <previous_data> to match the current filters.
        """

        cls.handler.update_data(previous_data, cls.filters, dm)

    @classmethod
    def set_start_date(cls, start_time: datetime) -> None:
        """
        Sets the start date of the graph by updating the filters.

        :param start_time: The new start date of the graph.
        """

        cls.filters.start_time = start_time

    @classmethod
    def set_end_date(cls, end_time: datetime) -> None:
        """
        Sets the end date of the graph by updating the filters.

        :param end_time: The new end date of the graph.
        """

        cls.filters.end_time = end_time

    @classmethod
    def set_shown_tags(cls, tags: set[str]) -> None:
        """
        Sets the entire set of shown tags by updating the filters.

        :param tags: The set of tags to be shown.
        """

        # convert <tags> to Tag objects
        tag_tags = {Tag(tag) for tag in tags}
        cls.filters.shown_tags = tag_tags

    @classmethod
    def remove_shown_tag(cls, tag: str) -> None:
        """
        Removes a tag from the set of shown tags by updating the filters.

        :param tags: The name of the tag to be removed.
        """

        if tag in cls.filters.shown_tags:
            cls.filters.shown_tags.remove(Tag(tag))

    @classmethod
    def add_shown_tag(cls, tag: str) -> None:
        """
        Adds a tag to the set of shown tags by updating the filters.

        :param tags: The name of the tag to be added.
        """

        cls.filters.shown_tags.add(Tag(tag))

    @classmethod
    def export_graph_to_file(cls, filter_args: GraphingFilters,
                             dm: DataManager, filename: str) -> None:
        """
        Exports the graph to a file.

        :param filename: The path to save to. The export format is
        determined based on the file extension.
        :param data: The data to be exported.
        """

        cls.handler.export_graph_to_file(filter_args, dm, filename)
