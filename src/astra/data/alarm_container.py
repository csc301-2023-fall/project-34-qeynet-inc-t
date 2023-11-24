from datetime import timedelta
from queue import Queue
from threading import Lock, Timer
from typing import Callable, Mapping

from astra.data.alarms import AlarmPriority, Alarm, AlarmCriticality

NEW_QUEUE_KEY = 'n'
MAX_QUEUE_SIZE = 3
ACKNOWLEDGED = False


class AlarmObserver:
    """
    Observes the state of the global alarms container and notifies interested
    parties whenever an update occurs

    :param watchers: A list of functions to call on any update to the alarm container
    :param mutex: Synchronization tool as many threads may notify watchers of updates
    """
    watchers = []
    _mutex = Lock()

    @classmethod
    def __int__(cls):
        cls.watchers = []
        cls._mutex = Lock()

    @classmethod
    def add_watcher(cls, watcher: Callable):
        """
        Adds a new function to call on alarm container being updated

        :param watcher: The new function to call
        """
        cls.watchers.append(watcher)

    @classmethod
    def notify_watchers(cls) -> None:
        """
        Calls all functions that wish to be called on container being updated
        """
        with cls._mutex:
            for watcher in cls.watchers:
                watcher()


class AlarmsContainer:
    """
    A container for a global alarms dict that utilizes locking for multithreading

    :param alarms: The actual dictionary of alarms held
    :param mutex: A lock used for mutating cls.alarms
    :param observer: An Observer to monitor the state of the container
    """
    observer: AlarmObserver
    alarms: dict[str, list[Alarm] | Queue]
    mutex: Lock

    @classmethod
    def __init__(cls):
        cls.alarms = {AlarmPriority.WARNING.name: [], AlarmPriority.LOW.name: [],
                      AlarmPriority.MEDIUM.name: [], AlarmPriority.HIGH.name: [],
                      AlarmPriority.CRITICAL.name: [], NEW_QUEUE_KEY: Queue()}
        cls.mutex = Lock()
        cls.observer = AlarmObserver()

    @classmethod
    def get_alarms(cls) -> dict[str, list[Alarm] | Queue]:
        """
        Returns a shallow copy of <cls.alarms>

        :return: A copy of <cls.alarms>
        """
        with cls.mutex:
            return cls.alarms.copy()

    @classmethod
    def add_alarms(cls, alarms: list[Alarm],
                   apm: Mapping[timedelta, Mapping[AlarmCriticality, AlarmPriority]]) -> None:
        """
        Updates the alarms global variable after acquiring the lock for it

        :param dm: Holds information of data criticality and priority
        :param apm: Maps information on alarms to correct priority level
        :param alarms: The set of alarms to add to <cls.alarms>
        """
        new_alarms = []
        times = [0, 5, 15, 30]
        timer_vals = []
        alarms.sort(reverse=True)
        if alarms:
            # First, add the new alarms to the alarms structure
            # Because the alarms structure is used in a number of threads, we lock here
            with cls.mutex:
                for alarm in alarms:
                    criticality = alarm.criticality
                    alarm_timer_vals = []

                    # Find the closest timeframe from 0, 5, 15, and 30 minutes from when the
                    # alarm was created to when it was actually confirmed
                    for i in range(1, len(times)):
                        time = times[i]
                        endpoint_time = alarm.event.confirm_time + timedelta(minutes=time)

                        # indicates an endpoint has already been found, so we add every following
                        # timer endpoint
                        if alarm_timer_vals:
                            alarm_timer_vals.append(endpoint_time - alarm.event.creation_time)

                        # Case for the first timer interval the alarm has not yet reached
                        if alarm.event.creation_time < endpoint_time and not alarm_timer_vals:
                            priority_name = apm[timedelta(minutes=times[i - 1])][criticality]
                            priority = AlarmPriority(priority_name)
                            cls.alarms[priority].append(alarm)
                            alarm.priority = priority
                            new_alarms.append([alarm, priority])

                            remaining_time = endpoint_time - alarm.event.creation_time
                            alarm_timer_vals.append(remaining_time)

                    # Case where the alarm was confirmed at least 30 minutes ago already
                    if not alarm_timer_vals:
                        priority = apm[timedelta(minutes=30)][criticality]
                        cls.alarms[priority.name].append(alarm)

                        cls.alarms[NEW_QUEUE_KEY].put(alarm)
                        if cls.alarms[NEW_QUEUE_KEY].qsize() > MAX_QUEUE_SIZE:
                            cls.alarms[NEW_QUEUE_KEY].get()

                        new_alarms.append([alarm, priority])
                    timer_vals.append(alarm_timer_vals)

            # Now that the state of the alarms container has been update, notify watchers
            cls.observer.notify_watchers()

            # Now, we need to create a timer thread for each alarm
            for i in range(len(new_alarms)):
                alarm = new_alarms[i]
                associated_times = timer_vals[i]

                for associated_time in associated_times:
                    # Because <associated_times> is a subset of <times>, we need to offset
                    # the index well later use into it
                    time_interval = len(times) - len(associated_times) + i

                    new_timer = Timer(associated_time.seconds, cls._update_priority,
                                      args=[alarm, timedelta(minutes=times[time_interval]), apm])
                    new_timer.start()

    @classmethod
    def _update_priority(cls, alarm_data: list[Alarm, AlarmPriority], time: timedelta,
                         apm: Mapping[timedelta, Mapping[AlarmCriticality, AlarmPriority]]) -> None:
        """
        Uses the alarm priority matrix with <time> to place <alarm> in the correct priority bin
        NOTE: we pass a list, and not a tuple, as we need to mutate said list

        :param alarm_data: contains the current priority of the alarm and the alarm itself
        :param time: Time elapsed since the alarm came into effect
        :param apm: Maps information on alarms to correct priority level
        """

        with cls.mutex:
            new_priority = apm[time][alarm_data[0].criticality]
            cls.alarms[alarm_data[1]].remove(alarm_data[0])
            cls.alarms[new_priority].append(alarm_data[0])
            alarm_data[0].priority = new_priority
            alarm_data[1] = new_priority
        # Because of the nature of priorities, we need to notify both modification observers
        # and addition observers
        cls.observer.notify_watchers()

    @classmethod
    def acknowledge_alarm(cls, alarm: Alarm) -> None:
        """
        Removes the requested alarm in <cls.alarms>

        :param alarm: The alarm to remove from the container

        PRECONDITION: <alarm> is in <cls.alarms>
        """
        with cls.mutex:
            # Note: because the alarm container should store every known alarm, this mutation
            # should work
            alarm.acknowledgement = ACKNOWLEDGED
        cls.observer.notify_watchers()

    @classmethod
    def remove_alarm(cls, alarm: Alarm) -> None:
        """
        Removes the requested alarm in

        :param alarm:
        :return:
        """
        with cls.mutex:
            for priority in cls.alarms:
                if priority != NEW_QUEUE_KEY and alarm in cls.alarms[priority]:
                    # Note: We don't consider the queue of new alarms, since by the time
                    # the alarm can be removed, it's already be taken out of the queue
                    cls.alarms[priority].remove(alarm)
        cls.observer.notify_watchers()
