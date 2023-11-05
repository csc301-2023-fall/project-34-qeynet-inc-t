from typing import Any
from .use_case_handlers import UseCaseHandler
from src.storage.datatable import DataTable


class FrontendRequestReceiver:
    """
    FrontendRequestreceiver is a class that receives requests from the
    frontend and passes them to the use case handlers.

    Attributes:
        handler (UseCaseHandler): The use case handler that will process the
        requests.

    Methods:
        receive(filter_data: dict[str, tuple[bool]], data: DataTable):
            Accepts a dictionary for filtering and a DataTable and passes it to
            the use case handler to process it.
    """

    handler: UseCaseHandler

    def __init__(self, handler: UseCaseHandler):
        self.handler = handler

    def receive(self, filter_data: dict[Any, tuple[Any]], data: DataTable):
        """
        Accepts a dictionary for filtering and a DataTable and passes it to
        the use case handler to process it.

        Args:
            filter_data (dict[str, tuple[str]])
                A dictionary where keys are the column names and values are
                tuples containing booleans that choose which columns are kept.
                Ex: {'A3': (True)}, this will keep the 'A3' column.
            data (DataTable): The data that will be processed.
        """

        return self.handler.get_data(filter_data, data)
