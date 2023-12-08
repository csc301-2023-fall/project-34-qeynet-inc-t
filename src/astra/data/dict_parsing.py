"""
This module provides tools and functions for parsing JSON/YAML-like dicts into objects.

Although one could semi-elegantly parse and validate things using match-case,
that doesn't allow for very good error messages when parsing fails.
This (admittedly somewhat overengineered, though fun to write) module serves the purpose of
removing some of the agony associated with parsing things in a more imperative way.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from types import NoneType, UnionType
from typing import Any, Never

from astra.data.alarms import (
    AlarmBase,
    AlarmCriticality,
    EventBase,
    RateOfChangeEventBase,
    StaticEventBase,
    ThresholdEventBase,
    SetpointEventBase,
    SOEEventBase,
    AllEventBase,
    AnyEventBase,
)
from astra.data.parameters import DisplayUnit, Parameter, Tag


# Define ParameterValue here as a UnionType to work around some mypy thing
ParameterValue: UnionType = bool | int | float


class ParsingError(Exception):
    """Raised for all expected errors in the data format during parsing."""

    pass


@dataclass(frozen=True)
class Path:
    """A list of indices/keys for getting a certain value out of a nested list/dict structure."""

    base: str
    elements: list[int | str]

    def add(self, element: int | str) -> 'Path':
        """
        Append an index/key to a path.

        :param element:
            The index or key to append.

        :return:
            A new path with the index/key appended.
        """
        return Path(self.base, self.elements + [element])

    def __str__(self):
        """
        Format this path in a human-readable way.

        Current format looks something like: base[index0].key0[index1][index2].key1.key2
        """
        return self.base + ''.join(
            (f'[{element}]' if isinstance(element, int) else f'.{element}')
            for element in self.elements
        )


def _format_type(t: type | UnionType) -> str:
    # Stringify types in a nice way.
    return repr('None' if t is NoneType else t.__name__ if isinstance(t, type) else str(t))


def _check_type(path: Path, value: object, expected_type: type | UnionType) -> Any:
    # Return the value unchanged if it is of the expected type and raise an error otherwise.
    if isinstance(value, expected_type):
        return value
    else:
        raise ParsingError(
            f'expected {path} to have type {_format_type(expected_type)}, '
            f'got {_format_type(type(value))}'
        )


def _raise_expected_values_error(path: Path, value: str, expected_values: list[str]) -> Never:
    # Raise an error where a value is not in a list of expected values.
    raise ParsingError(f'expected {path} to be one of {expected_values}, got {repr(value)}')


def _convert_to_pathed(path: Path, value: Any) -> Any:
    # Convert lists and dicts into their pathed equivalents, using the given path.
    # Leave all other values unchanged.
    if isinstance(value, list):
        return PathedList(path, value)
    elif isinstance(value, dict):
        return PathedDict(path, value)
    else:
        return value


class PathedList:
    """A list equipped with a path."""

    _path: Path
    _list: list

    def __init__(self, path: Path, value: object):
        """
        Construct a PathedList.

        :param path:
            The path for the PathedList.
        :param value:
            The underlying list for the PathedList, validated as a list during runtime.

        :raise ParsingError:
            If value is not a list.
        """
        self._path = path
        self._list = _check_type(path, value, list)

    @property
    def path(self) -> Path:
        """The path for this PathedList."""
        return self._path

    def iter(self, expected_type: type | UnionType, expected_length: int | None) -> Iterator[Any]:
        """
        Iterate over the list, checking that values are of the right type and converting as needed.

        :param expected_type:
            The expected type of each value.
        :param expected_length:
            The expected length of the list, or None for a list of any size.

        :raise ParsingError:
            If any value is of the incorrect type, or the length of the overall list is incorrect.

        :return:
            An iterator of values -- for lists/dicts, PathedLists/PathedDicts;
            for everything else, values of the expected type.
        """
        if expected_length is not None and len(self._list) != expected_length:
            raise ParsingError(
                f'expected {self._path} to have {expected_length} elements, got {len(self._list)}'
            )
        for i, value in enumerate(self._list):
            child_path = self._path.add(i)
            yield _convert_to_pathed(child_path, _check_type(child_path, value, expected_type))

    def tuple_iter(self, expected_types: list[type | UnionType]) -> Iterator[Any]:
        """
        Iterate over the list with a heterogeneous list of expected types.

        :param expected_types:
            The expected types of the values.

        :raise ParsingError:
            If any value is of the incorrect type,
            or the length of the overall list does not match the length of the expected types.

        :return:
            An iterator of values -- for lists/dicts, PathedLists/PathedDicts;
            for everything else, values of the expected type.
        """
        if len(self._list) != len(expected_types):
            raise ParsingError(
                f'expected {self._path} to have {len(expected_types)} elements, '
                f'got {len(self._list)}'
            )
        for i, (value, expected_type) in enumerate(zip(self._list, expected_types)):
            child_path = self._path.add(i)
            yield _convert_to_pathed(child_path, _check_type(child_path, value, expected_type))


class PathedDict:
    """A dictionary equipped with a path."""

    _path: Path
    _dict: dict

    def __init__(self, path: Path, value: object):
        """
        Construct a PathedDict.

        :param path:
            The path for the PathedDict.
        :param value:
            The underlying dict for the PathedDict, validated as a dict during runtime.

        :raise ParsingError:
            If value is not a dict.
        """
        self._path = path
        self._dict = _check_type(path, value, dict)

    @property
    def path(self) -> Path:
        """The path for this PathedDict."""
        return self._path

    def get(self, key: str, expected_type: type | UnionType) -> Any:
        """
        Get value by key, checking that the value is of the right type and converting as needed.

        :param key:
            The key for the value.
        :param expected_type:
            The expected type of the value.

        :raise ParsingError:
            If the key is absent or the value is of the incorrect type.

        :return:
            The value for the given key -- for lists/dicts, a PathedList/PathedDict;
            for everything else, a value of the expected type.
        """
        try:
            value = self._dict[key]
        except KeyError:
            raise ParsingError(f'{self._path} is missing key {repr(key)}')
        child_path = self._path.add(key)
        return _convert_to_pathed(child_path, _check_type(child_path, value, expected_type))


def parse_parameter(tag: Tag, value: object) -> Parameter:
    """
    Parse the input into a Parameter object.

    :param tag:
        The tag for the Parameter object.
    :param value:
        The input (should be a dict) to parse.

    :raise ParsingError:
        If parsing fails because of missing keys or incorrect types/values.

    :return:
        The input, parsed into a Parameter object.
    """
    parameter_dict = PathedDict(Path('<tag>', []), value)
    parameter_description = parameter_dict.get('description', str)
    dtype_string = parameter_dict.get('dtype', str)
    try:
        dtype = {'bool': bool, 'int': int, 'float': float}[dtype_string]
    except KeyError:
        _raise_expected_values_error(
            parameter_dict.path.add('dtype'), dtype_string, ['bool', 'int', 'float']
        )
    setpoint = parameter_dict.get('setpoint', ParameterValue | None)
    units_dict = parameter_dict.get('display_units', dict | None)
    if units_dict is not None:
        units_description = units_dict.get('description', str)
        symbol = units_dict.get('symbol', str)
        multiplier = units_dict.get('multiplier', int | float)
        constant = units_dict.get('constant', int | float)
        display_units = DisplayUnit(units_description, symbol, multiplier, constant)
    else:
        display_units = None
    return Parameter(tag, parameter_description, dtype, setpoint, display_units)


def _parse_event_base(event_dict: PathedDict) -> EventBase:
    # Parse the input into an EventBase.
    persistence = event_dict.get('persistence', int | float | None)
    description = event_dict.get('description', str)
    event_type = event_dict.get('type', str)
    match event_type:
        case 'rate_of_change':
            return RateOfChangeEventBase(
                persistence,
                description,
                Tag(event_dict.get('tag', str)),
                event_dict.get('rate_of_fall_threshold', int | float | None),
                event_dict.get('rate_of_rise_threshold', int | float | None),
                event_dict.get('time_window', int | float),
            )
        case 'static':
            return StaticEventBase(persistence, description, Tag(event_dict.get('tag', str)))
        case 'threshold':
            return ThresholdEventBase(
                persistence,
                description,
                Tag(event_dict.get('tag', str)),
                event_dict.get('lower_threshold', int | float | None),
                event_dict.get('upper_threshold', int | float | None),
            )
        case 'setpoint':
            return SetpointEventBase(
                persistence,
                description,
                Tag(event_dict.get('tag', str)),
                event_dict.get('setpoint', ParameterValue),
            )
        case 'sequence_of_events':
            event_bases = [
                _parse_event_base(inner_event_dict)
                for inner_event_dict in event_dict.get('events', list).iter(dict, None)
            ]
            intervals = []
            for interval_tuple in event_dict.get('intervals', list).iter(
                list, len(event_bases) - 1
            ):
                min_interval, max_interval = interval_tuple.tuple_iter(
                    [int | float, int | float | None]
                )
                intervals.append((min_interval, max_interval))
            return SOEEventBase(persistence, description, event_bases, intervals)
        case 'logical_and':
            return AllEventBase(
                persistence,
                description,
                [
                    _parse_event_base(inner_event_dict)
                    for inner_event_dict in event_dict.get('events', list).iter(dict, None)
                ],
            )
        case 'logical_or':
            return AnyEventBase(
                persistence,
                description,
                [
                    _parse_event_base(inner_event_dict)
                    for inner_event_dict in event_dict.get('events', list).iter(dict, None)
                ],
            )
        case _:
            _raise_expected_values_error(
                event_dict.path.add('type'),
                event_type,
                [
                    'rate_of_change',
                    'static',
                    'threshold',
                    'setpoint',
                    'sequence_of_events',
                    'logical_and',
                    'logical_or',
                ],
            )


def parse_alarm_base(criticality_string: str, value: object) -> AlarmBase:
    """
    Parse the input into an AlarmBase.

    :param criticality_string:
        The criticality for the AlarmBase.
    :param value:
        The input (should be a dict) to parse.

    :raise ParsingError:
        If parsing fails because of missing keys or incorrect types/values.

    :return:
        The input, parsed into an AlarmBase.
    """
    try:
        criticality = AlarmCriticality(criticality_string)
    except ValueError:
        _raise_expected_values_error(
            Path('<alarm>', ['criticality']),
            criticality_string,
            [criticality.value for criticality in AlarmCriticality],
        )
    event_dict = PathedDict(Path('<alarm>', ['event']), value)
    event_base = _parse_event_base(event_dict)
    return AlarmBase(event_base, criticality)
