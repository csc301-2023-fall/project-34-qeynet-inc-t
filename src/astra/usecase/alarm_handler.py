from dataclasses import dataclass
from typing import Iterable
from datetime import datetime

from astra.data.alarms import AlarmPriority, AlarmCriticality

PRIORITY = 'PRIORITY'
CRITICALITY = 'CRITICALITY'
TYPE = 'TYPE'
REGISTERED_DATE = 'REGISTERED_DATE'
CONFIRMED_DATE = 'CONFIRMED_DATE'



@dataclass
class AlarmsFilters:
    """
    A container for all the filters that can be applied in the alarm dashboard.

    :param index: the page of data to be shown in the view.
    :param sort: indicates what type of sort should be applied to which column.
    A tuple in the form (sort_type, sort_column), where sort_type is one
    of '>' or '<', and
    sort_column is one of: {PRIORITY, CRITICALITY, TYPE, REGISTERED_DATE, CONFIRMED_DATE}
    :param priority: A set of all priorities to be shown in the table.
    :param criticality: A set of all criticalities to be shown in the table.
    :param Types: A set of all types to be shown in the table.
    :param start_time: the first time of telemetry frames to examined. Is less than
    end_time
    :param end_time: the last time of telemetry frames to be examined

    All of the above parameters may be None iff they have never been set before
    """

    sort: tuple[str, str] | None
    index: int | None
    priorities: Iterable[AlarmPriority] | None
    criticalities: Iterable[AlarmCriticality] | None
    types: Iterable[str] | None 
    start_time: datetime | None
    end_time: datetime | None
