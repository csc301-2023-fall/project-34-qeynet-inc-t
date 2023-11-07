from datetime import datetime
import pytest
from astra.data.data_manager import (
    DataManager,
    telemetry_0,
    telemetry_1,
)

from astra.usecase.dashboard_handler import (
    TableReturn,
    DashboardHandler
)

MOCKTELEMETRY0 = 'telemetry0.h5'
MOCKTELEMETRY1 = 'telemetry1.h5'
DEVICE = 'DEVICE'


@pytest.fixture
def data0():
    datamanager = DataManager.from_device_name(DEVICE)
    start_time = datamanager.add_data_from_file(MOCKTELEMETRY0)

    # Uses data from telemetry0.h5
    telemetry_table = [
        ['A3', 'a monad', '5 m', '3'],
        ['B1', 'is a monoid', '0.0 g', '1.0'],
        ['B4', 'in the category', 'True', 'False'],
        ['C1', 'of endofuntors', '2 s', 'None']
    ]

    table = TableReturn(
        telemetry_0.get('EPOCH')[0],
        telemetry_table,
        [],
        3
    )

    return datamanager, start_time, table


@pytest.fixture
def data1():
    datamanager = DataManager.from_device_name(DEVICE)
    start_time = datamanager.add_data_from_file(MOCKTELEMETRY1)

    # Uses data from telemetry1.h5
    telemetry_table = [
        ['A3', 'a monad', '5 m', '3'],
        ['B1', 'is a monoid', '3000.0 g', '1.0'],
        ['B4', 'in the category', 'False', 'False'],
        ['C1', 'of endofuntors', '1 s', 'None']
    ]

    table = TableReturn(
        telemetry_1.get('EPOCH')[0],
        telemetry_table,
        [],
        2
    )

    return datamanager, start_time, table


@pytest.mark.parametrize('data,start_time,tablereturn', [data0, data1])
def test_dashboard_no_filter(data: DataManager, start_time: datetime, table: TableReturn):
    """
    A test case for the dashboard use case handler with no filters.
    We expect the full table to be returned.
    """

    # creates a datatable and adds data to it and retrieves the data.
    DashboardHandler.set_index(0)
    DashboardHandler.set_shown_tag(data.tags)
    DashboardHandler.set_start_time(start_time)
    DashboardHandler.set_end_time(None)
    actual = DashboardHandler.get_data(data)

    expected = table

    assert (
        actual == expected
    )


@pytest.mark.parametrize('data,start_time,tablereturn', [data0, data1])
def test_dashboard_one_filter(data: DataManager, start_time: datetime, table: TableReturn):
    """
    A test case for the dashboard use case handler with one filter.
    We expect a table with one column removed be returned.
    """

    # creates a datatable and adds data to it and retrieves the data.
    DashboardHandler.set_index(0)
    DashboardHandler.set_shown_tag(data.tags)
    DashboardHandler.set_start_time(start_time)
    DashboardHandler.set_end_time(None)

    # remove a tag from the display.
    DashboardHandler.remove_shown_tag('A3')

    actual = DashboardHandler.get_data(data)

    expected = table
    expected.table = table.table[1:]

    assert (
        actual == expected
    )


@pytest.mark.parametrize('data,start_time,tablereturn', [data0, data1])
def test_dashboard_all_filters(data: DataManager, start_time: datetime, table: TableReturn):
    """
    A test case for the dashboard use case handler with every tag filtered.
    We expect an empty list to be returned.
    """

    # creates a datatable and adds data to it and retrieves the data.
    DashboardHandler.set_index(0)
    DashboardHandler.set_shown_tag(data.tags)
    DashboardHandler.set_start_time(start_time)
    DashboardHandler.set_end_time(None)

    # remove the tags from the display.
    DashboardHandler.remove_shown_tag('A3')
    DashboardHandler.remove_shown_tag('B1')
    DashboardHandler.remove_shown_tag('B4')
    DashboardHandler.remove_shown_tag('C1')

    actual = DashboardHandler.get_data(data)

    expected = table
    expected.table = table.table[len(table.table):]

    assert (
        actual == expected
    )
