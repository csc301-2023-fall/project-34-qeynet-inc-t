from typing import NewType
from astra.usecase.use_case_handlers import DashboardHandler, DataHandler
from astra.data.datatable import DataTable


INDEX = 'INDEX'
DATA = 'DATA'
CONFIG = 'CONFIG'

Tag = NewType('Tag', str)


def test_dashboard_no_filter():
    """
    A test case for the dashboard use case handler with no filters.
    We expect the full table to be returned.
    """

    # creates a datatable and adds data to it.
    datatable = DataTable()
    data_config = {DATA: 'telemetry0.csv', CONFIG: 'config0.csv'}
    DataHandler.get_data(data_config, datatable)

    # create a dashboard handler
    dashboard_handler = DashboardHandler()

    # create a dictionary of filters to use for demonstration purposes.
    filter_data = {
        Tag('A3'): (True,),
        Tag('B1'): (True,),
        Tag('B4'): (True,),
        Tag('C1'): (True,),
        INDEX: (0,),
    }

    expected = [
        ['A3', 'a monad', '3 cm'],
        ['B1', 'is a monoid', '1 L'],
        ['B4', 'in the category', '0 ft'],
        ['C1', 'of endofuntors', '2 C'],
        ['Tag', 'Description', 'Value']
    ]
    actual = dashboard_handler.get_data(filter_data, datatable)

    assert (
        actual[0:(len(actual) - 1)] == expected
    )


def test_dashboard_one_filter():
    """
    A test case for the dashboard use case handler with one filter.
    We expect a table with one column to removed be returned.
    """

    # creates a datatable and adds data to it.
    datatable = DataTable()
    data_config = {DATA: 'telemetry0.csv', CONFIG: 'config0.csv'}
    DataHandler.get_data(data_config, datatable)

    # create a dashboard handler
    dashboard_handler = DashboardHandler()

    # create a dictionary of filters to use for demonstration purposes.
    filter_data = {
        Tag('A3'): (False,),
        Tag('B1'): (True,),
        Tag('B4'): (True,),
        Tag('C1'): (True,),
        INDEX: (0,),
    }

    expected = [
        ['B1', 'is a monoid', '1 L'],
        ['B4', 'in the category', '0 ft'],
        ['C1', 'of endofuntors', '2 C'],
        ['Tag', 'Description', 'Value']
    ]
    actual = dashboard_handler.get_data(filter_data, datatable)

    assert (
        actual[0:(len(actual) - 1)] == expected
    )


def test_dashboard_all_filters():
    """
    A test case for the dashboard use case handler with every tag filtered.
    We expect an empty list to be returned.
    """

    # creates a datatable and adds data to it.
    datatable = DataTable()
    data_config = {DATA: 'telemetry0.csv', CONFIG: 'config0.csv'}
    DataHandler.get_data(data_config, datatable)

    # create a dashboard handler
    dashboard_handler = DashboardHandler()

    # create a dictionary of filters to use for demonstration purposes.
    filter_data = {
        Tag('A3'): (False,),
        Tag('B1'): (False,),
        Tag('B4'): (False,),
        Tag('C1'): (False,),
        INDEX: (0,),
    }

    # We expect an empty list to be returned, since all tags are filtered
    # out.
    expected = [['Tag', 'Description', 'Value']]
    actual = dashboard_handler.get_data(filter_data, datatable)

    assert (
        actual[0:(len(actual) - 1)] == expected
    )
