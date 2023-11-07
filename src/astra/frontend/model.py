"""
File that holds the dummy Model Class
"""

import datetime
from typing import Dict, List


class Model:
    """
    Dummy class currently representing the backend
    """

    def __init__(self) -> None:
        """
        Initialize to some random telemetry data
        """
        self.data = [
            ['A3', 'b monad', '3 cm'],
            ['B4', 'ain the category', '0 ft'],
            ['C1', 'of endofuntors', '2 C'],
            ['Tag', 'Description', 'Value'],
            [datetime.datetime(2023, 10, 16, 17, 4, 31, 866600)]
        ]

    def receive(self, filter_data: Dict[any, tuple], data: any) -> List[list]:
        """
        A method that simulates the functionality of the backend
        Since our data is fixed, we sort by hand each input case
        """
        if filter_data['SORT'] == ('<', 'TAG'):
            self.data = [
                ['A3', 'b monad', '3 cm'],
                ['B4', 'ain the category', '0 ft'],
                ['C1', 'of endofuntors', '2 C'],
                ['Tag', 'Description', 'Value'],
                [datetime.datetime(2023, 10, 16, 17, 4, 31, 866600)]
            ]
        elif filter_data['SORT'] == ('>', 'TAG'):
            self.data = [
                ['C1', 'of endofuntors', '2 C'],
                ['B4', 'ain the category', '0 ft'],
                ['A3', 'b monad', '3 cm'],
                ['Tag', 'Description', 'Value'],
                [datetime.datetime(2023, 10, 16, 17, 4, 31, 866600)]
            ]
        elif filter_data['SORT'] == ('<', 'DESCRIPTION'):
            self.data = [
                ['B4', 'ain the category', '0 ft'],
                ['A3', 'b monad', '3 cm'],
                ['C1', 'of endofuntors', '2 C'],
                ['Tag', 'Description', 'Value'],
                [datetime.datetime(2023, 10, 16, 17, 4, 31, 866600)]
            ]
        elif filter_data['SORT'] == ('>', 'DESCRIPTION'):
            self.data = [
                ['C1', 'of endofuntors', '2 C'],
                ['A3', 'b monad', '3 cm'],
                ['B4', 'ain the category', '0 ft'],
                ['Tag', 'Description', 'Value'],
                [datetime.datetime(2023, 10, 16, 17, 4, 31, 866600)]
            ]
        elif filter_data['SORT'] == ('<', 'VALUE'):
            self.data = [
                ['B4', 'ain the category', '0 ft'],
                ['C1', 'of endofuntors', '2 C'],
                ['A3', 'b monad', '3 cm'],
                ['Tag', 'Description', 'Value'],
                [datetime.datetime(2023, 10, 16, 17, 4, 31, 866600)]
            ]
        elif filter_data['SORT'] == ('>', 'VALUE'):
            self.data = [
                ['A3', 'b monad', '3 cm'],
                ['C1', 'of endofuntors', '2 C'],
                ['B4', 'ain the category', '0 ft'],
                ['Tag', 'Description', 'Value'],
                [datetime.datetime(2023, 10, 16, 17, 4, 31, 866600)]
            ]

        return self.data

    def get_data(self) -> List[list]:
        """
        Getter method to return whatever's in the data
        """
        return self.data
