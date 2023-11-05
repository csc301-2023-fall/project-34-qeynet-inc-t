from typing import Any
from .use_case_handlers import UseCaseHandler
from src.storage.datatable import DataTable

DATA = 'DATA'
CONFIG = 'CONFIG'


class DataHandler(UseCaseHandler):
    """DataHandler is a child class of UseCaseHandler that handles
    data managing operations defined by the user
    """

    file: str

    @classmethod
    def get_data(cls, data: DataTable):
        """
        An implementation of get_data that focuses on adding
        initial data to the table

        PRECONDITIONS: <file> is not None
        """
        data = DataTable.from_config_file(cls.file)


    @classmethod
    def get_data(cls, data: DataTable):
        """
        An implementation of get_data that focuses on adding
        initial data to the table

        PRECONDITIONS: <file> is not None
        """
        data = DataTable.from_config_file(cls.file)
