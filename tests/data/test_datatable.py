"""Unit tests for the datatable.

The methods tags, parameters, num_telemetry_frames, and get_telemetry_frame are directly tested.
The constructor and the method add_data are indirectly tested.
The methods from_config_file and add_data_from_file, due to requiring file I/O, are left untested.
"""

from datetime import datetime

import pandas as pd
import pytest

from astra.data.datatable import (
    ConfigData,
    DataTable,
    Parameter,
    Tag,
    TelemetryData,
    TelemetryFrame,
)

A3 = Tag('A3')
B1 = Tag('B1')
B4 = Tag('B4')
C1 = Tag('C1')


@pytest.fixture
def dt():
    datatable = DataTable(
        ConfigData(
            pd.DataFrame(
                {
                    'tag': ['A3', 'B1', 'B4', 'C1'],
                    'description': ['a monad', 'is a monoid', 'in the category', 'of endofunctors'],
                    'units': ['m', 'kg', 's', 'g'],
                    'conversion_factor': [1, 2, 3, 4],
                }
            )
        )
    )
    datatable.add_data(
        TelemetryData(
            pd.DataFrame(
                {
                    'EPOCH': [datetime(2011, 10, 24), datetime(2018, 3, 16), datetime(2014, 5, 2)],
                    'A3': [5, 3, 3],
                    'B1': [0, 0, 1],
                    'B4': [1, 0, 0],
                    'C1': [2, 4, 2],
                }
            )
        )
    )
    datatable.add_data(
        TelemetryData(
            pd.DataFrame(
                {
                    'EPOCH': [datetime(2022, 3, 25), datetime(2016, 6, 1)],
                    'A3': [5, 3],
                    'B1': [3, 1],
                    'B4': [0, 0],
                    'C1': [1, 3],
                }
            )
        )
    )
    return datatable


def test_tags(dt: DataTable):
    assert sorted(dt.tags) == [A3, B1, B4, C1]


def test_parameters(dt: DataTable):
    assert sorted(dt.parameters.items()) == sorted(
        {
            A3: Parameter(A3, 'a monad', 'm', 1),
            B1: Parameter(B1, 'is a monoid', 'kg', 2),
            B4: Parameter(B4, 'in the category', 's', 3),
            C1: Parameter(C1, 'of endofunctors', 'g', 4),
        }.items()
    )


def test_num_telemetry_frames(dt: DataTable):
    assert dt.num_telemetry_frames == 5


def test_get_telemetry_frame(dt: DataTable):
    assert dt.get_telemetry_frame(2) == TelemetryFrame(
        datetime(2016, 6, 1), {A3: 3, B1: 2, B4: 0, C1: 12}
    )


def test_get_telemetry_frame_negative(dt: DataTable):
    assert dt.get_telemetry_frame(-2) == TelemetryFrame(
        datetime(2018, 3, 16), {A3: 3, B1: 0, B4: 0, C1: 16}
    )


def test_get_telemetry_frame_out_of_bounds(dt: DataTable):
    with pytest.raises(IndexError):
        dt.get_telemetry_frame(6)
