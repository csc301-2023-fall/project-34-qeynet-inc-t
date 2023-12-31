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
    filters = GraphingFilters(set(), datetime.min, datetime.max)

    @classmethod
    def create(cls, dm: DataManager) -> GraphingData:
        """
        Create is a method that returns the initial data needed to make a graph.

        :param dm: Contains all data stored by the program to date.
        """
        cls.previous_data = cls.handler.get_data(dm, cls.filters)
        return cls.previous_data

    @classmethod
    def update(cls) -> None:
        """
        update is a method that updates the currently represented information,
        by mutating the data in <cls.previous_data> to match the current filters
        given in <cls.filters>.
        """

        cls.handler.update_data(cls.previous_data, cls.filters)

    @classmethod
    def set_start_date(cls, start_date: datetime) -> None:
        """
        Sets the start date of the graph by updating <cls.filters>.

        :param start_date: The new start date of the graph.
        """

        cls.filters.start_time = start_date

    @classmethod
    def set_end_date(cls, end_date: datetime) -> None:
        """
        Sets the end date of the graph by updating >cls.filters>.

        :param end_date: The new end date of the graph.
        """

        cls.filters.end_time = end_date

    @classmethod
    def add_shown_tag(cls, tag: str) -> None:
        """
        Adds a single tag to the set of shown tags by updating <cls.filters>.

        :param tag: The name of the tag to be added.
        """

        cls.filters.tags.add(Tag(tag))

    @classmethod
    def set_shown_tags(cls, tags: set[str]) -> None:
        """
        Sets the entire set of shown tags at once by updating <cls.filters>.

        :param tags: The set of tags to be shown.
        """

        # convert <tags> to Tag objects
        tag_tags = {Tag(tag) for tag in tags}
        cls.filters.tags = tag_tags

    @classmethod
    def remove_shown_tag(cls, tag: str) -> None:
        """
        Removes a tag from the set of shown tags by updating <cls.filters>.

        :param tag: The name of the tag to be removed.
        """

        if tag in cls.filters.tags:
            cls.filters.tags.remove(Tag(tag))

    @classmethod
    def export_data_to_file(cls, filename: str) -> None:
        """
        Exports the current telemetry data to a file. The export format is
        determined based on the file extension in the <filename>.

        :param filename: The path to save to.
        """

        cls.handler.export_data_to_file(cls.previous_data, filename)
