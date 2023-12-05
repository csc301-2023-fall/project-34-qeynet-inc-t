from datetime import datetime
from threading import Thread, Condition
from .alarm_strategies import get_strategy
from ..data.data_manager import DataManager


def check_alarms(dm: DataManager,
                 earliest_time: datetime) -> None:
    """
    Goes through all possible alarm bases to check, and calls the appropriate
    strategy to evaluate them

    This should only be called once new telemetry data is added to the system

    :param dm: Contains all data known to the program
    :param earliest_time: Details the earliest timestamp amongst newly added telemetry frames
    """

    alarm_bases = dm.alarm_bases

    # condition variable allows us to make a notification once all strategies have completed
    cv = Condition()
    threads = []

    for alarm_base in alarm_bases:
        # The base and criticality were seperated due to how things worked previously. This would
        # be a good and simple thing to refactor
        base = alarm_base.event_base
        criticality = alarm_base.criticality

        # Acquiring the correct strategy for the event base then running it in a new thread
        strategy = get_strategy(base)
        new_thread = Thread(target=strategy, args=[dm, base, criticality, earliest_time, False, cv])

        new_thread.start()
        threads.append(new_thread)
    wait_for_children(dm, cv, threads)


def wait_for_children(dm: DataManager, cv: Condition, threads: list[Thread]) -> None:
    """
    Waits for all threads in <threads> to be completed, then notifies the alarm container that
    all alarm bases have been evaluated

    :param dm: Contains all data known to the program
    :param cv: The condition variable each thread in <threads> has to track thread completion
    :param threads: Contains all child threads of this process
    """

    thread_active = check_alive(threads)

    with cv:
        # Simple loop to check if any child thread is alive and block if so
        while thread_active:
            # Note: this idea might be doable with a semaphore? My only concern is if the child
            # threads don't acquire a semaphore before this thread, then it won't work
            cv.wait()
            thread_active = check_alive(threads)
    dm.alarms.observer.notify_watchers()


def check_alive(threads: list[Thread]) -> bool:
    """
    Checks if any thread in <threads> is alive and returns an appropriate boolean

    :param threads: The list of threads to check
    """

    thread_active = False
    for thread in threads:
        if thread.is_alive():
            thread_active = True
            return thread_active
    return thread_active
