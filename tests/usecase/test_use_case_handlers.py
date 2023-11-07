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

# Creating a mock data for the test cases.
MOCKTELEMETRY0 = 'telemetry0.h5'
MOCKTABLELIST0 = [
    ['A3', 'a monad', '5 m', '3 m'],
    ['B1', 'is a monoid', '0.0 g', '1000.0 g'],
    ['B4', 'in the category', 'True', 'False'],
    ['C1', 'of endofunctors', '2 s', 'None']
]
MOCKTABLE0 = TableReturn(
    telemetry_0.get('EPOCH')[0],
    MOCKTABLELIST0,
    [],
    3
)

# Creating the mock telemetry data frame for the second file.
MOCKTELEMETRY1 = 'telemetry1.h5'
MOCKTABLELIST1 = [
    ['A3', 'a monad', '3 m', '3 m'],
    ['B1', 'is a monoid', '1000.0 g', '1000.0 g'],
    ['B4', 'in the category', 'False', 'False'],
    ['C1', 'of endofunctors', '3 s', 'None']
]
MOCKTABLE1 = TableReturn(
    telemetry_1.get('EPOCH')[1],  # earliest date
    MOCKTABLELIST1,
    [],
    2
)
DEVICE = 'DEVICE'


@pytest.mark.parametrize('telemetry_file, tablereturn', [(MOCKTELEMETRY0, MOCKTABLE0),
                                                         (MOCKTELEMETRY1, MOCKTABLE1)])
def test_dashboard_no_filter(telemetry_file: str, tablereturn: TableReturn):
    """
    A test case for the dashboard use case handler with no filters.
    We expect the full table to be returned.
    """
    data = DataManager.from_device_name(DEVICE)
    start_time = data.add_data_from_file(telemetry_file)

    # creates a datatable and adds data to it and retrieves the data.
    DashboardHandler.set_index(0)
    DashboardHandler.set_shown_tag(data.tags)
    DashboardHandler.set_start_time(start_time)
    DashboardHandler.set_end_time(None)
    actual = DashboardHandler.get_data(data)

    expected = tablereturn

    assert (
        actual == expected
    )


@pytest.mark.parametrize('telemetry_file, tablereturn', [(MOCKTELEMETRY0, MOCKTABLE0),
                                                         (MOCKTELEMETRY1, MOCKTABLE1)])
def test_dashboard_one_filter(telemetry_file: str, tablereturn: TableReturn):
    """
    A test case for the dashboard use case handler with one filter.
    We expect a table with one column removed be returned.
    """

    data = DataManager.from_device_name(DEVICE)
    start_time = data.add_data_from_file(telemetry_file)

    # creates a datatable and adds data to it and retrieves the data.
    DashboardHandler.set_index(0)
    DashboardHandler.set_shown_tag(data.tags)
    DashboardHandler.set_start_time(start_time)
    DashboardHandler.set_end_time(None)
    actual = DashboardHandler.get_data(data)

    # remove a tag from the display.
    DashboardHandler.remove_shown_tag('A3')

    DashboardHandler.update_data(actual)

    expected = tablereturn
    expected.removed = [tablereturn.table[0]]
    expected.table = tablereturn.table[1:]

    assert (
        actual == expected
    )


# @pytest.mark.parametrize('telemetry_file, tablereturn', [(MOCKTELEMETRY0, MOCKTABLE0),
#                                                          (MOCKTELEMETRY1, MOCKTABLE1)])
# def test_dashboard_all_filters(telemetry_file: str, tablereturn: TableReturn):
#     """
#     A test case for the dashboard use case handler with every tag filtered.
#     We expect an empty list to be returned.
#     """

#     data = DataManager.from_device_name(DEVICE)
#     start_time = data.add_data_from_file(telemetry_file)

#     # creates a datatable and adds data to it and retrieves the data.
#     DashboardHandler.set_index(0)
#     DashboardHandler.set_shown_tag(data.tags)
#     DashboardHandler.set_start_time(start_time)
#     DashboardHandler.set_end_time(None)

#     # remove the tags from the display.
#     DashboardHandler.remove_shown_tag('A3')
#     DashboardHandler.remove_shown_tag('B1')
#     DashboardHandler.remove_shown_tag('B4')
#     DashboardHandler.remove_shown_tag('C1')

#     actual = DashboardHandler.get_data(data)

#     expected = tablereturn
#     expected.table = tablereturn.table[len(tablereturn.table):]

#     assert (
#         actual == expected
#     )
