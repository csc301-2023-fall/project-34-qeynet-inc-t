from .alarm_strategies import *


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

    alarm_bases = dm.alarm_bases
    for alarm_base in alarm_bases:
        base = alarm_base.event_base
        criticality = alarm_base.criticality

        strategy = get_strategy(base)
        alarm = strategy(dm, base, criticality, earliest_time)
        if alarm is not None:
            criticality = alarm.criticality
            priority = dm.alarm_priority_matrix[timedelta(seconds=0)][criticality]

            if priority in alarms:
                alarms[priority].add(alarm)
            else:
                alarm[priority] = {alarm}
