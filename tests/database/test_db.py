import unittest
import os
from astra.data.database.db_initializer import (
    initialize_sqlite_db,
    Device,
)
from astra.data.database.db_manager import (
    get_device,
    device_exists,
    get_tags_for_device,
    get_alarm_base_info,
    get_tag_id_name,
    num_telemetry_frames,
    get_telemetry_data_by_index,
    get_telemetry_data_by_tag,
    get_device_data,
    delete_device,
)
from astra.data.telemetry_manager import read_telemetry
from astra.data.config_manager import read_config
from sqlalchemy.engine import Engine
import datetime


class TestInitializeSqliteDb(unittest.TestCase):
    """tests the initialize_sqlite_db function"""

    def test_initialize_sqlite_db(self):
        """tests the initialize_sqlite_db function"""

        actual = initialize_sqlite_db()
        self.assertIsInstance(actual, Engine)


class TestClass(unittest.TestCase):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    read_config("./test_files/test_config1.yaml")
    read_telemetry("./test_files/test_telemetry1.yaml")
    read_config("./test_files/test_config2.yaml")
    read_telemetry("./test_files/test_telemetry2.yaml")

    def test_get_device_exists(self):
        """tests the get_device function with a device that exists"""

        actual = get_device("test_config1")
        expected = Device(
            device_name="test_config1", device_description="Device V1."
        )

        self.assertIsInstance(actual, Device)
        self.assertEqual(expected.device_name, actual.device_name)
        self.assertEqual(expected.device_description, actual.device_description)

    def test_get_device_does_not_exist(self):
        """tests the get_device function with a device that does not exist"""

        actual = get_device("monad2")
        expected = None

        self.assertEqual(expected, actual)

    def test_device_exists(self):
        """tests the device_exists function with a device that exists"""

        actual = device_exists("test_config1")
        expected = True

        self.assertEqual(expected, actual)

    def test_device_does_not_exist(self):
        """tests the device_exists function with a device that does not exist"""

        actual = device_exists("monad2")
        expected = False

        self.assertEqual(expected, actual)

    def test_get_tags_for_device(self):
        """tests if get_tags_for_device returns the correct tags"""
        actual = get_tags_for_device("test_config1")
        expected = [
            (
                "e4",
                {
                    "description": "Pawn e2-e4",
                    "display_units": None,
                    "dtype": "bool",
                    "setpoint": True,
                },
            ),
            (
                "Nf3",
                {
                    "description": "Knight g1-f3",
                    "display_units": {
                        "constant": 0,
                        "description": "millimetres",
                        "multiplier": 1000,
                        "symbol": "mm",
                    },
                    "dtype": "float",
                    "setpoint": 1,
                },
            ),
            (
                "2e4",
                {
                    "description": "Pawn e2-2e4",
                    "display_units": None,
                    "dtype": "bool",
                    "setpoint": False,
                },
            ),
        ]

        self.assertEqual(expected, actual)

    def test_get_alarm_base_info(self):
        """tests if get_alarm_base_info returns the correct alarm base info"""
        actual = get_alarm_base_info("test_config1")
        expected = [
            (
                "WARNING",
                {
                    "tag": "a6",
                    "type": "rate_of_change",
                    "description": "rate of change alarm",
                    "persistence": 3,
                    "rate_of_fall_threshold": 1,
                    "rate_of_rise_threshold": 1,
                    "time_window": 1,
                },
            ),
            (
                "LOW",
                {
                    "tag": "Bb5",
                    "type": "static",
                    "description": "static alarm",
                    "persistence": 10,
                },
            ),
        ]

        self.assertEqual(expected, actual)

    def test_get_tag_id_name(self):
        """tests if get_tag_id_name returns the correct tag id name"""
        data = get_tag_id_name("test_config1")
        actual = [(tag_id, tag_name) for tag_id, tag_name in data]
        expected = [(3, "2e4"), (2, "Nf3"), (1, "e4")]

        self.assertEqual(expected, actual)

        data = get_tag_id_name("test_config2")
        actual = [(tag_id, tag_name) for tag_id, tag_name in data]
        expected = [(5, "2Nf3"), (4, "e4")]

        self.assertEqual(expected, actual)

    def test_num_telemetry_frames(self):
        """tests if num_telemetry_frames returns the correct number of frames"""
        # No time
        actual = num_telemetry_frames("test_config1", None, None)
        expected = 10

        self.assertEqual(expected, actual)

        actual = num_telemetry_frames("test_config2", None, None)
        expected = 10

        self.assertEqual(expected, actual)

        # Only start time
        actual = num_telemetry_frames(
            "test_config1", "2023-10-11 19:30:04.000000", None
        )
        expected = 6

        self.assertEqual(expected, actual)

        # Only end time
        actual = num_telemetry_frames(
            "test_config2", None, "2023-10-11 19:30:08.000000"
        )
        expected = 4

        self.assertEqual(expected, actual)

        # Both start and end time
        actual = num_telemetry_frames(
            "test_config2",
            "2023-10-11 19:30:03.000000",
            "2023-10-11 19:30:07.000000",
        )
        expected = 3

        self.assertEqual(expected, actual)

    def test_get_telemetry_data_by_index(self):
        """tests if get_telemetry_data_by_index returns the correct data"""
        # No time & No tags
        actual = get_telemetry_data_by_index(
            "test_config1", None, None, None, 4
        )
        expected = (
            [("Nf3", 466288.2692964514), ("e4", None), ("2e4", None)],
            datetime.datetime(2023, 10, 11, 19, 30, 4),
        )

        self.assertEqual(expected, actual)

        # Time & tags
        actual = get_telemetry_data_by_index(
            "test_config1",
            ("Nf3",),
            "2023-10-11 19:30:03.000000",
            "2023-10-11 19:30:07.000000",
            4,
        )
        expected = ([("Nf3", None)], datetime.datetime(2023, 10, 11, 19, 30, 7))

        self.assertEqual(expected, actual)

    def test_get_telemetry_data_by_tag(self):
        """tests if get_telemetry_data_by_tag returns the correct data"""
        # No time
        actual = get_telemetry_data_by_tag("test_config1", None, None, "Nf3")
        expected = [
            (467640.60634239786, datetime.datetime(2023, 10, 11, 19, 30)),
            (464240.2930270969, datetime.datetime(2023, 10, 11, 19, 30, 1)),
            (None, datetime.datetime(2023, 10, 11, 19, 30, 2)),
            (468158.34450224123, datetime.datetime(2023, 10, 11, 19, 30, 3)),
            (466288.2692964514, datetime.datetime(2023, 10, 11, 19, 30, 4)),
            (467752.1778316993, datetime.datetime(2023, 10, 11, 19, 30, 5)),
            (467034.82697615295, datetime.datetime(2023, 10, 11, 19, 30, 6)),
            (None, datetime.datetime(2023, 10, 11, 19, 30, 7)),
            (466026.0261241936, datetime.datetime(2023, 10, 11, 19, 30, 8)),
            (468285.01818524837, datetime.datetime(2023, 10, 11, 19, 30, 9)),
        ]

        self.assertEqual(expected, actual)

        # With time
        actual = get_telemetry_data_by_tag(
            "test_config1",
            "2023-10-11 19:30:08.000000",
            "2023-10-11 19:30:13.000000",
            "e4",
        )
        expected = [
            (0.0, datetime.datetime(2023, 10, 11, 19, 30, 8)),
            (0.0, datetime.datetime(2023, 10, 11, 19, 30, 9)),
        ]

        self.assertEqual(expected, actual)

    def test_get_device_data(self):
        """tests if get_device_data returns the correct device data"""
        actual = get_device_data()
        expected = [("test_config1", "Device V1."), ("test_config2", "Device V2.")]

        self.assertEqual(expected, actual)

    def test_delete_device(self):
        """tests if delete_device deletes the correct device"""
        delete_device("test_config1")
        actual = device_exists("test_config1")
        expected = False

        self.assertEqual(expected, actual)

        delete_device("test_config2")
        actual = device_exists("test_config2")
        expected = False

        self.assertEqual(expected, actual)

        # Re-add the devices
        read_config("./test_files/test_config1.yaml")
        read_telemetry("./test_files/test_telemetry1.yaml")
        read_config("./test_files/test_config2.yaml")
        read_telemetry("./test_files/test_telemetry2.yaml")


if __name__ == "__main__":
    unittest.main()
