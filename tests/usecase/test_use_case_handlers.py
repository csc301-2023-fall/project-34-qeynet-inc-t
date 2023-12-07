import queue
from astra.usecase.dashboard_handler import DashboardHandler

"""
config = pd.DataFrame(
    {
        'tag': ['A3', 'B1', 'B4', 'C1'],
        'description': ['a monad', 'is a monoid', 'in the category', 'of endofunctors'],
        'dtype': ['int', 'float', 'bool', 'int'],
        'setpoint': [3, 1.0, False, None],
        'units': [
            DisplayUnit('metre', 'm', 1, 0),
            DisplayUnit('gram', 'g', 1000, 0),
            None,
            DisplayUnit('second', 's', 1, 0)
        ]
    }
)

telemetry_0 = pd.DataFrame(
    {
        'EPOCH': [datetime(2011, 10, 24), datetime(2018, 3, 16), datetime(2014, 5, 2)],
        'A3': [5, 3, 3],
        'B1': [0.0, 0.0, 1.0],
        'B4': [True, False, False],
        'C1': [2, 4, 2],
    }
)

telemetry_1 = pd.DataFrame(
    {
        'EPOCH': [datetime(2022, 3, 25), datetime(2016, 6, 1)],
        'A3': [5, 3],
        'B1': [3.0, 1.0],
        'B4': [False, False],
        'C1': [1, 3],
    }
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
    telemetry_0.get('EPOCH')[0],  # use the earliest date
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

    A test case for the dashboard use case handler with no filters.
    We expect the full table to be returned.

    # creates a data manager and adds data to it.
    data = DataManager.from_device_name(DEVICE)
    start_time = data.add_data_from_file(telemetry_file)

    # creates a datatable and adds data to it and retrieves the data.
    DashboardHandler.set_index(0)
    DashboardHandler.set_shown_tag(data.tags)
    DashboardHandler.set_start_time(start_time)
    DashboardHandler.set_end_time(None)
    actual = DashboardHandler.get_data(data)

    # Avoid alias of the table object.
    expected = copy(tablereturn)

    assert (
            actual == expected
    )


@pytest.mark.parametrize('telemetry_file, tablereturn', [(MOCKTELEMETRY0, MOCKTABLE0),
                                                         (MOCKTELEMETRY1, MOCKTABLE1)])
def test_dashboard_one_filter(telemetry_file: str, tablereturn: TableReturn):

    A test case for the dashboard use case handler with one filter.
    We expect a table with one column removed be returned.


    data = DataManager.from_device_name(DEVICE)
    start_time = data.add_data_from_file(telemetry_file)

    # creates a datatable and adds data to it and retrieves the data.
    DashboardHandler.set_index(0)
    DashboardHandler.set_shown_tag(data.tags)
    DashboardHandler.set_start_time(start_time)
    DashboardHandler.set_end_time(None)
    actual = DashboardHandler.get_data(data)

    # remove a tag from the display and update it.
    DashboardHandler.remove_shown_tag('A3')

    DashboardHandler.update_data(actual)

    # avoid alias of the table object.
    expected = copy(tablereturn)

    # remove the first row from the table.
    expected.removed = [tablereturn.table[0][:]]
    expected.table = tablereturn.table[1:]

    assert (
            actual == expected
    )


@pytest.mark.parametrize('telemetry_file, tablereturn', [(MOCKTELEMETRY0, MOCKTABLE0),
                                                         (MOCKTELEMETRY1, MOCKTABLE1)])
def test_dashboard_all_filters(telemetry_file: str, tablereturn: TableReturn):

    A test case for the dashboard use case handler with every tag filtered.
    We expect an empty list to be returned.

    data = DataManager.from_device_name(DEVICE)
    start_time = data.add_data_from_file(telemetry_file)

    # creates a datatable and adds data to it and retrieves the data.
    DashboardHandler.set_index(0)
    DashboardHandler.set_shown_tag(data.tags)
    DashboardHandler.set_start_time(start_time)
    DashboardHandler.set_end_time(None)
    actual = DashboardHandler.get_data(data)

    # remove the tags from the display and update between each.
    DashboardHandler.remove_shown_tag('A3')
    DashboardHandler.update_data(actual)
    DashboardHandler.remove_shown_tag('B1')
    DashboardHandler.update_data(actual)
    DashboardHandler.remove_shown_tag('B4')
    DashboardHandler.update_data(actual)
    DashboardHandler.remove_shown_tag('C1')
    DashboardHandler.update_data(actual)

    # avoid alias of the table object.
    expected = copy(tablereturn)

    # remove all rows from the table.
    expected.removed = tablereturn.table
    expected.table = []

    assert (
            actual == expected
    )
"""


def test_search_tags_default_empty_cache():
    "Simply testing the algorithm returns all tags and does not change cache"
    tags = ['abcde', 'abc', 'a', 'bc', 'fgh', 'lm', 'ae']
    cache = dict()
    cache[''] = tags.copy()
    eviction = queue.Queue()

    check = DashboardHandler.search_tags('', cache, eviction)
    assert check == tags
    assert cache == {'': tags}


def test_search_tags_default_one_cache():
    """Testing that searching for the empty string exclusively returns
    all tags and does not modify the cache"""
    tags = ['abcde', 'abc', 'a', 'bc', 'fgh', 'lm', 'ae']
    cache = dict()
    cache[''] = tags.copy()
    cache['abcde'] = ['abcde']
    eviction = queue.Queue()

    check = DashboardHandler.search_tags('', cache, eviction)
    assert check == tags
    assert cache == {'': tags, 'abcde': ['abcde']}


def test_search_tags_new_search():
    """Testing that searching for a new string that has a match in tags
    returns a subset of tags and modifies cache and eviction"""
    tags = ['abcde', 'abc', 'a', 'bc', 'fgh', 'lm', 'ae']
    cache = dict()
    cache[''] = tags.copy()
    eviction = queue.Queue()

    check = DashboardHandler.search_tags('abcde', cache, eviction)
    assert check == ['abcde']
    assert cache == {'': tags, 'abcde': ['abcde']}
    assert eviction.get() == 'abcde'


def test_search_tags_no_duplicates():
    """Testing that when we search an exactly cached string, neither cache nor eviction
    is modified"""
    tags = ['abcde', 'abc', 'a', 'bc', 'fgh', 'lm', 'ae']
    cache = dict()
    cache[''] = tags.copy()
    eviction = queue.Queue()

    DashboardHandler.search_tags('abcde', cache, eviction)
    check = DashboardHandler.search_tags('abcde', cache, eviction)
    assert check == ['abcde']
    assert cache == {'': tags, 'abcde': ['abcde']}
    assert eviction.get() == 'abcde'
    assert eviction.empty()


def test_search_tags_eviction():
    """Testing that once 20 searches occur, the next search evicts the oldest search option
    from both the cache and queue"""
    tags = ['abcde', 'abc', 'a', 'bc', 'fgh', 'lm', 'ae']
    cache = dict()
    cache[''] = tags.copy()
    eviction = queue.Queue()

    for i in range(200):
        search = 'a' * (i + 1)
        DashboardHandler.search_tags(search, cache, eviction)

    check = DashboardHandler.search_tags('t', cache, eviction)
    assert check == []
    assert len(cache) == 201
    # The function already evicted 'a', so 'aa' should be the next one
    assert eviction.get() == 'aa'
