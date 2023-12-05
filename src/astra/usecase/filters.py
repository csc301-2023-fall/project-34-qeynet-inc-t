from dataclasses import dataclass
from datetime import datetime

from astra.data.alarms import AlarmPriority, AlarmCriticality
from astra.data.parameters import Tag


@dataclass
class Filters:
    """
    A basic container class that will be the parent of all filters actually used bt each handler

    :param tags: A set of all tags to be shown
    """
    tags: set[Tag] | None


@dataclass
class DashboardFilters(Filters):
    """
    A container for all the filters that can be applied in the telemetry dashboard

    :param index: the telemetry frame to be shown in the dashboard.
    :param sort: indicates what type of sort should be applied to which column.
    A tuple in the form (sort_type, sort_column), where sort_type is one
    of '>' or '<', and sort_column is one of <DATA> or <CONFIG>
    :param start_time: the first time of telemetry frames to examined. Is less than
    end_time
    :param end_time: the last time of telemetry frames to be examined

    All of the above parameters may be None iff they have never been set before
    """

    sort: tuple[str, str] | None
    index: int | None
    start_time: datetime | None
    end_time: datetime | None


@dataclass
class AlarmsFilters(Filters):
    """
    A container for all the filters that can be applied in the alarm dashboard.

    :param sort: indicates what type of sort should be applied to which column.
    A tuple in the form (sort_type, sort_column), where sort_type is one
    of '>' or '<', and
    sort_column is one of: {PRIORITY, CRITICALITY, TYPE, REGISTERED_DATE, CONFIRMED_DATE}
    :param priorities: A set of all priorities to be shown in the table.
    :param criticalities: A set of all criticalities to be shown in the table.
    :param types: A set of all types to be shown in the table.
    :param registered_start_time: the first time of alarms being registered. Is less than
    end_time
    :param registered_end_time: the last time of alarms being registered to be examined
    :param confirmed_start_time: the first time of alarms being confirmed. Is less than
    end_time
    :param confirmed_end_time: the last time of alarms being confirmed to be examined
    :param new: whether only unacknowledged alarms should solely be seen

    All of the above parameters may be None iff they have never been set before
    """

    sort: tuple[str, str] | None
    priorities: set[AlarmPriority] | None
    criticalities: set[AlarmCriticality] | None
    types: set[str] | None
    registered_start_time: datetime | None
    registered_end_time: datetime | None
    confirmed_start_time: datetime | None
    confirmed_end_time: datetime | None
    new: bool


@dataclass
class GraphingFilters(Filters):
    """
    A container for all the data required by the graphing handler.

    :param start_time: the earliest time that values for each tag are from.
    :param end_time: the latest time that values for each tag are from.
    :param interval: The number of frams between each value in the list of values.
    """

    start_time: datetime | None
    end_time: datetime | None
