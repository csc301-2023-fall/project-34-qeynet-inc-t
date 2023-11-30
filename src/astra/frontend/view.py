"""
This file holds the main view class that will run after selecting a device to monitor
"""

import itertools
from datetime import datetime
from tkinter import Button, Entry, Frame, Toplevel, Event
from tkinter import CENTER, BOTTOM, NO, END, BOTH
from tkinter import StringVar
from tkinter import filedialog, messagebox, ttk, Tk, Label
from tkinter.ttk import Treeview

from astra.data.data_manager import DataManager
from astra.frontend.timerange_input import OperationControl, TimerangeInput
from .graphing_view import GraphingView
from .telemetry_view import TelemetryView
from .alarm_view import AlarmView
from .tag_searcher import TagSearcher, AlarmTagSearcher
from .view_model import DashboardViewModel, AlarmsViewModel
from ..data.alarms import Alarm


class View(Tk):
    """
    View class
    """
    dashboard_table: Treeview
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

        alarm_watchers = []

        self.telemetry_tab = TelemetryView(tab_control, height // 4, self._dm)
        telemetry_frame = self.telemetry_tab.overall_frame

        self.alarm_tab = AlarmView(tab_control, height // 4, self._dm, alarm_watchers)
        alarm_frame = self.alarm_tab.overall_frame

        self.graphing_tab = GraphingView(tab_control, height // 4, width, self._dm)
        graphing_frame = self.graphing_tab.overall_frame

        watchers = [
            self.alarm_tab.construct_alarms_table,
            self.telemetry_tab.construct_dashboard_table,
            self.update_alarm_banners,
        ]

        # Mutate the alarms watcher so it can notify the telemetry tab
        for watcher in watchers:
            alarm_watchers.append(watcher)

        # This is required for the alarms banner
        self.alarms_view_model = AlarmsViewModel(self._dm, watchers)

        self.geometry("%dx%d" % (width, height))
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
        tab_control.add(graphing_frame, text="Graphing")
        # packing tab control to make tabs visible
        tab_control.pack(expand=1, fill="both")

    def update_alarm_banners(self):
        for alarm_banner, text in itertools.zip_longest(
                self.alarm_banners, self.alarms_view_model.get_alarm_banners()
        ):
            alarm_banner['text'] = text if text is not None else ''
