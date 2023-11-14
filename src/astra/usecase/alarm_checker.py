from datetime import datetime
from threading import Thread
from .alarm_strategies import get_strategy, AlarmsContainer
from ..data.alarms import AlarmPriority, Alarm
from ..data.data_manager import DataManager


def check_alarms(dm: DataManager, alarms: dict[AlarmPriority, set[Alarm]],
                 earliest_time: datetime) -> None:
    """
    Goes through all possible alarms to check and, if any exists, adds them to <alarms>
    based on their criticality

    :param earliest_time:
    :param dm: The manager of all data known to the program
    :param alarms: The global variable storing all current alarms

    PRECONDITION: alarms has exactly 5 keys, the values of which are
    'WARNING', 'LOW', 'MEDIUM', HIGH', CRITICAL', all of which map to
    a list
    """

    threads = []
    alarm_bases = dm.alarm_bases
    for alarm_base in alarm_bases:
        base = alarm_base.event_base
        criticality = alarm_base.criticality

        strategy = get_strategy(base)
        alarm_container = AlarmsContainer(alarms)
        new_thread = Thread(target=strategy, args=[dm, base, criticality, earliest_time,
                                                   alarm_container])
        threads.append(new_thread)
        new_thread.start()


