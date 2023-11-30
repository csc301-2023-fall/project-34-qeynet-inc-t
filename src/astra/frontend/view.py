"""
This file holds the main view class that will run after selecting a device to monitor
"""

import itertools
from tkinter import Frame
from tkinter import BOTH
from tkinter import ttk, Tk, Label

from astra.data.data_manager import DataManager
from .graphing_view import GraphingView
from .telemetry_view import TelemetryView
from .alarm_view import AlarmView


class View(Tk):
    """
    View class
    """
    _dm: DataManager

    def __init__(self, device_name: str) -> None:
        """
        Init method for the main view class
        When the view is initialized, all the frames and tables
        are loaded into the view

        :param device_name:
            The name of the device being monitored.
        """
        self._dm = DataManager.from_device_name(device_name)

        # Root frame of tkinter
        super().__init__()
        self.title(f'Astra - {device_name}')

        # tab widget
        tab_control = ttk.Notebook(self)

        # Get the screen size information, and fullscreen the app
        width = self.winfo_screenwidth()
        height = self.winfo_screenheight()

        self.telemetry_tab = TelemetryView(tab_control, height // 4, self._dm)
        telemetry_frame = self.telemetry_tab.overall_frame

        self.alarm_tab = AlarmView(tab_control, height // 4, self._dm)
        alarm_frame = self.alarm_tab.overall_frame

        self.graphing_tab = GraphingView(tab_control, height // 4, width, self._dm)
        graphing_frame = self.graphing_tab.overall_frame

        watchers = [
            self.telemetry_tab.construct_dashboard_table,
            self.alarm_tab.construct_alarms_table,
            self.update_alarm_banners,
        ]
        for watcher in watchers:
            self.alarm_tab.controller.install_alarm_watcher(self._dm, watcher)

        self.geometry('%dx%d' % (width, height))
        self.state('zoomed')

        # alarm banners
        alarm_banners_container = Frame(self)
        self.alarm_banners = [Label(alarm_banners_container, anchor='w') for i in range(6)]
        for alarm_banner in self.alarm_banners:
            alarm_banner.pack(fill=BOTH)
        alarm_banners_container.pack(fill=BOTH)

        # adding the tabs to the tab control
        tab_control.add(telemetry_frame, text='Telemetry')
        tab_control.add(alarm_frame, text='Alarm')
        tab_control.add(graphing_frame, text='Graphing')
        # packing tab control to make tabs visible
        tab_control.pack(expand=1, fill='both')

    def update_alarm_banners(self):
        """
        Method to update the alarms in the alarms banner
        """
        for alarm_banner, text in itertools.zip_longest(
                self.alarm_banners, self.alarm_tab.controller.get_alarm_banner()
        ):
            alarm_banner['text'] = text if text is not None else ''
