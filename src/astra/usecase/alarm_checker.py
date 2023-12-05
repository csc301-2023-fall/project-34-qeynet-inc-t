from datetime import datetime
from threading import Thread, Condition
from .alarm_strategies import get_strategy
from ..data.data_manager import DataManager


def check_alarms(dm: DataManager,
                 earliest_time: datetime) -> None:
    """
    Goes through all possible alarms to check and, if any exists, adds them to <alarms>
    based on their criticality

    :param earliest_time:
    :param dm: The manager of all data known to the program
    """

    alarm_bases = dm.alarm_bases
    cv = Condition()
    threads = []

    for alarm_base in alarm_bases:
        base = alarm_base.event_base
        criticality = alarm_base.criticality

        strategy = get_strategy(base)
        new_thread = Thread(target=strategy, args=[dm, base, criticality, earliest_time, False, cv])
        new_thread.start()
        threads.append(new_thread)
    wait_for_children(dm, cv, threads)


def wait_for_children(dm: DataManager, cv: Condition, threads: list[Thread]) -> None:
    """
    Waits for all child threads to be completed, then notifies the alarm container that
    all tasks are done

    :param dm: Container of the alarm container
    :param cv: The condition variable to track child completion
    :param threads: Contains all child threads of this process
    """
    thread_active = check_alive(threads)

    with cv:
        while thread_active:
            # Note: this idea might be doable with a semaphore? My only concern is if the child
            # threads don't acquire a semaphore before this thread, then it won't work
            cv.wait()
            thread_active = check_alive(threads)
    dm.alarms.observer.notify_watchers()


def check_alive(threads: list[Thread]) -> bool:
    """
    Checks if any thread in <threds> is alive and returns an appropriate boolean

    :param threads: The list of threads to check
    """
    thread_active = False
    for thread in threads:
        if thread.is_alive():
            thread_active = True
            return thread_active
    return thread_active
