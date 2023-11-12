import datetime
import unittest
from astra.usecase.alarm_strategies import *


class MyTestCase(unittest.TestCase):
    def test_find_first_time_no_persistence(self):
        """Tests that when a basic eventbase with no persistence is provided, the base earliest
        time is returned, and the sequence of time to check is correctly indicated as 0"""
        basic_event = EventBase(None, "")
        earliest = datetime.now()

        actual = find_first_time(basic_event, earliest)
        expected = (earliest, 0)

        self.assertEqual(actual, expected)

    def test_find_first_time_persistence(self):
        """Tests that when a basic eventbase with persistence is provided, the correct values
        are returned"""
        basic_event = EventBase(50, "")
        earliest = datetime.now()

        actual = find_first_time(basic_event, earliest)
        expected = (earliest - timedelta(seconds=50), 50)

        self.assertEqual(actual, expected)

    def test_find_first_time_actual_eventbase(self):
        """Tests that find_earliest_time works when providing a child class of
        eventbase"""
        child_event = StaticEventBase(10, "", "")
        earliest = datetime.now()
        actual = find_first_time(child_event, earliest)
        expected = (earliest - timedelta(seconds=10), 10)

        self.assertEqual(actual, expected)

    def test_persistence_check_one_index_no_period(self):
        """Tests that if there's only one telemetry frame that satisfies alarm
        conditions, and no persistence check is to be applied, an index is returned"""
        conditions = [(True, datetime.now())]
        persistence = 0
        false_indexes = []

        actual = persistence_check(conditions, persistence, false_indexes)
        expected = [0]

        self.assertEqual(actual, expected)

    def test_find_alarm_indexes_one_index_(self):
        """Tests that in the previous test case's conditions, the index of the only frame is
        returned in a list"""
        first_indexes = [0]
        conditions = [(True, datetime.now())]

        actual = find_alarm_indexes(first_indexes, conditions)
        expected = [True]

        self.assertEqual(actual, expected)

    def test_persistence_check_one_index_period(self):
        """Tests that if there's only one telemetry frame that satisfies alarm
        conditions, and a persistence check is to be applied, no index is returned"""
        conditions = [(True, datetime.now())]
        persistence = 10
        false_indexes = []

        actual = persistence_check(conditions, persistence, false_indexes)
        expected = []

        self.assertEqual(actual, expected)

    def test_find_alarm_indexes_check_one_index_period(self):
        """Tests that in the previous test case's conditions, no index is returned"""
        first_indexes = []
        conditions = [(True, datetime.now())]

        actual = find_alarm_indexes(first_indexes, conditions)
        expected = [False]

        self.assertEqual(actual, expected)

    def test_persistence_check_multi_index_alarm(self):
        """Basic test where theres multiple telemetry frames, and the persistence condition is
        satisfied, an alarm is raised"""
        conditions = [(True, datetime.now() - timedelta(seconds=60)),
                      (True, datetime.now() - timedelta(seconds=50)),
                      (True, datetime.now() - timedelta(seconds=10))]
        persistence = 30
        false_indexes = []

        actual = persistence_check(conditions, persistence, false_indexes)
        expected = [0]

        self.assertEqual(actual, expected)

    def test_find_alarm_indexes_multi_index_alarm(self):
        """Tests that in the previous test case's conditions, all indexes are returned"""
        first_indexes = [0, 1, 2]
        conditions = [(True, datetime.now() - timedelta(seconds=60)),
                      (True, datetime.now() - timedelta(seconds=50)),
                      (True, datetime.now() - timedelta(seconds=10))]

        actual = find_alarm_indexes(first_indexes, conditions)
        expected = [True, True, True]

        self.assertEqual(actual, expected)

    def test_persistence_check_multi_index_no_alarm(self):
        """Basic test where theres multiple telemetry frames, and the persistence condition is
        not satisfied, no alarm is raised"""
        conditions = [(True, datetime.now() - timedelta(seconds=60)),
                      (True, datetime.now() - timedelta(seconds=50)),
                      (True, datetime.now() - timedelta(seconds=10))]
        persistence = 500
        false_indexes = []

        actual = persistence_check(conditions, persistence, false_indexes)
        expected = []

        self.assertEqual(actual, expected)

    def test_find_alarm_indexes_multi_index_no_alarm(self):
        """Tests that in the previous test case's conditions, all indexes are false"""
        first_indexes = []
        conditions = [(True, datetime.now() - timedelta(seconds=60)),
                      (True, datetime.now() - timedelta(seconds=50)),
                      (True, datetime.now() - timedelta(seconds=10))]

        actual = find_alarm_indexes(first_indexes, conditions)
        expected = [False, False, False]

        self.assertEqual(actual, expected)

    def test_persistence_check_one_false_start_alarm(self):
        """Tests that if there's only multiple telemetry frames, only one that does
        not meet alarm conditions at the start, and an alarm should be raised overall, the correct
        value is returned"""
        conditions = [(False, datetime.now() - timedelta(seconds=60)),
                      (True, datetime.now() - timedelta(seconds=50)),
                      (True, datetime.now() - timedelta(seconds=10))]
        persistence = 30
        false_indexes = [0]

        actual = persistence_check(conditions, persistence, false_indexes)
        expected = [1]

        self.assertEqual(actual, expected)

    def test_find_alarm_one_false_start_alarm(self):
        """Tests that in the previous test case's conditions, all indexes after the
        false entry are True"""
        first_indexes = [1, 2]
        conditions = [(False, datetime.now() - timedelta(seconds=60)),
                      (True, datetime.now() - timedelta(seconds=50)),
                      (True, datetime.now() - timedelta(seconds=10))]

        actual = find_alarm_indexes(first_indexes, conditions)
        expected = [False, True, True]

        self.assertEqual(actual, expected)

    def test_persistence_check_one_false_start_no_alarm(self):
        """Tests that if there's only multiple telemetry frames, only one that does
        not meet alarm conditions at the start, and no alarm should be raised overall,
        the correct value is returned"""
        conditions = [(False, datetime.now() - timedelta(seconds=60)),
                      (True, datetime.now() - timedelta(seconds=50)),
                      (True, datetime.now() - timedelta(seconds=40))]
        persistence = 30
        false_indexes = [0]

        actual = persistence_check(conditions, persistence, false_indexes)
        expected = []

        self.assertEqual(actual, expected)

    def test_find_alarm_one_false_start_no_alarm(self):
        """Tests that in the previous test case's conditions, all indexes are false"""
        first_indexes = []
        conditions = [(False, datetime.now() - timedelta(seconds=60)),
                      (True, datetime.now() - timedelta(seconds=50)),
                      (True, datetime.now() - timedelta(seconds=10))]

        actual = find_alarm_indexes(first_indexes, conditions)
        expected = [False, False, False]

        self.assertEqual(actual, expected)

    def test_persistence_check_one_false_end_alarm(self):
        """Tests that if there's only multiple telemetry frames, only one that does
        not meet alarm conditions at the end, and an alarm should be raised overall, the correct
        value is returned"""
        conditions = [(True, datetime.now() - timedelta(seconds=60)),
                      (True, datetime.now() - timedelta(seconds=20)),
                      (False, datetime.now() - timedelta(seconds=10))]
        persistence = 30
        false_indexes = [2]

        actual = persistence_check(conditions, persistence, false_indexes)
        expected = [0]

        self.assertEqual(actual, expected)

    def test_find_alarm_one_false_end_alarm(self):
        """Tests that in the previous test case's conditions, all but the last index
        is true"""
        first_indexes = [0, 1]
        conditions = [(True, datetime.now() - timedelta(seconds=60)),
                      (True, datetime.now() - timedelta(seconds=20)),
                      (False, datetime.now() - timedelta(seconds=10))]

        actual = find_alarm_indexes(first_indexes, conditions)
        expected = [True, True, False]

        self.assertEqual(actual, expected)

    def test_persistence_check_one_false_end_no_alarm(self):
        """Tests that if there's only multiple telemetry frames, only one that does
        not meet alarm conditions at the end, and no alarm should be raised overall,
        the correct value is returned"""
        conditions = [(True, datetime.now() - timedelta(seconds=60)),
                      (True, datetime.now() - timedelta(seconds=50)),
                      (False, datetime.now() - timedelta(seconds=40))]
        persistence = 30
        false_indexes = [0]

        actual = persistence_check(conditions, persistence, false_indexes)
        expected = []

        self.assertEqual(actual, expected)

    def test_find_alarm_one_false_end_no_alarm(self):
        """Tests that in the previous test case's conditions, no index is true"""
        first_indexes = []
        conditions = [(True, datetime.now() - timedelta(seconds=60)),
                      (True, datetime.now() - timedelta(seconds=50)),
                      (False, datetime.now() - timedelta(seconds=40))]

        actual = find_alarm_indexes(first_indexes, conditions)
        expected = [False, False, False]

        self.assertEqual(actual, expected)

    def test_persistence_check_one_false_middle_alarm(self):
        """Tests that if there's only multiple telemetry frames, only one that does
        not meet alarm conditions in the middle, multiple alarms can be raised"""
        conditions = [(True, datetime.now() - timedelta(seconds=120)),
                      (True, datetime.now() - timedelta(seconds=50)),
                      (False, datetime.now() - timedelta(seconds=60)),
                      (True, datetime.now() - timedelta(seconds=40)),
                      (True, datetime.now() - timedelta(seconds=5))]
        persistence = 30
        false_indexes = [2]

        actual = persistence_check(conditions, persistence, false_indexes)
        expected = [0, 3]

        self.assertEqual(actual, expected)

    def test_find_alarm_indexes_check_one_false_middle_alarm(self):
        """Tests that in the previous test case, only element 2 is false"""
        first_indexes = [0, 1, 3, 4]
        conditions = [(True, datetime.now() - timedelta(seconds=120)),
                      (True, datetime.now() - timedelta(seconds=50)),
                      (False, datetime.now() - timedelta(seconds=60)),
                      (True, datetime.now() - timedelta(seconds=40)),
                      (True, datetime.now() - timedelta(seconds=5))]

        actual = find_alarm_indexes(first_indexes, conditions)
        expected = [True, True, False, True, True]

        self.assertEqual(actual, expected)

    def test_persistence_check_one_false_middle_no_alarm(self):
        """Tests that if there's only multiple telemetry frames, only one that does
        not meet alarm conditions in the middle, multiple alarms are not raised
        when persistence checks all failed"""
        conditions = [(True, datetime.now() - timedelta(seconds=120)),
                      (True, datetime.now() - timedelta(seconds=50)),
                      (False, datetime.now() - timedelta(seconds=60)),
                      (True, datetime.now() - timedelta(seconds=40)),
                      (True, datetime.now() - timedelta(seconds=5))]
        persistence = 500
        false_indexes = [2]

        actual = persistence_check(conditions, persistence, false_indexes)
        expected = []

        self.assertEqual(actual, expected)

    def test_find_alarm_indexes_one_false_middle_no_alarm(self):
        """Tests that in the previous test case, all indexes are false"""
        persistence = 500
        false_indexes = [2]
        conditions = [(True, datetime.now() - timedelta(seconds=120)),
                      (True, datetime.now() - timedelta(seconds=50)),
                      (False, datetime.now() - timedelta(seconds=60)),
                      (True, datetime.now() - timedelta(seconds=40)),
                      (True, datetime.now() - timedelta(seconds=5))]

        first_indexes = persistence_check(conditions, persistence, false_indexes)


        actual = find_alarm_indexes(first_indexes, conditions)
        expected = [False, False, False, False, False]

        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
