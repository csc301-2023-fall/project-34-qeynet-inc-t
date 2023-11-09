"""
This file holds the view class that will be run in main.py
"""

from tkinter import filedialog, ttk, Tk, Label
from tkinter import Button, Entry, Frame, LabelFrame, Toplevel
from tkinter import CENTER, NO, END
from tkinter import StringVar
from tkinter.ttk import Treeview

from .view_model import DashboardViewModel
from .view_draw_functions import draw_frameview
from typing import List

from ..data.data_manager import DataManager


class View(Tk):
    """
    View class
    """
    dashboard_table: Treeview
    _dm: DataManager

    def __init__(self) -> None:
        """
        Init method for the view class
        When the view is initialized, all the frames and tables
        are loaded into the view
        """
        self._dm = DataManager.from_device_name('DEVICE')

        # Root frame of tkinter
        super().__init__()
        self.title("View Prototype")
        self.dashboard_view_model = DashboardViewModel()

        # tab widget
        tab_control = ttk.Notebook(self)

        # frames corresponding to each tab
        dashboard_frame = ttk.Frame(tab_control)
        tableview_frame = ttk.Frame(tab_control)
        graphview_frame = ttk.Frame(tab_control)
        frameview_frame = ttk.Frame(tab_control)

        # adding the tabs to the tab control
        tab_control.add(dashboard_frame, text='Dashboard')
        tab_control.add(tableview_frame, text='Table view')
        tab_control.add(graphview_frame, text='Graph view')
        tab_control.add(frameview_frame, text='Frame view')

        # packing tab control to make tabs visible
        tab_control.pack(expand=1, fill="both")

        # elements of dashboard_frame
        add_data_button = Button(dashboard_frame, text="Add data...", command=self.open_file)
        add_data_button.grid(sticky="W", row=0, column=0)

        self.start_time = StringVar()
        self.end_time = StringVar()

        dashboard_time_range_row = Frame(dashboard_frame)
        dashboard_time_range_row.grid(sticky='W', row=1, column=0)
        Label(dashboard_time_range_row, text='From').grid(row=0, column=0)
        Entry(dashboard_time_range_row, textvariable=self.start_time).grid(row=0, column=1)
        Label(dashboard_time_range_row, text='to').grid(row=0, column=2)
        Entry(dashboard_time_range_row, textvariable=self.end_time).grid(row=0, column=3)
        Button(dashboard_time_range_row, text='Update time',
               command=self.update_time).grid(row=0, column=4)

        self.dashboard_current_frame_number = 0
        self.dashboard_frame_navigation_text = StringVar()

        dashboard_frame_navigation_row = Frame(dashboard_frame)
        dashboard_frame_navigation_row.grid(sticky='W', row=2, column=0)
        Button(dashboard_frame_navigation_row, text='|<',
               command=self.first_frame).grid(row=0, column=0)
        Button(dashboard_frame_navigation_row, text='<',
               command=self.decrement_frame).grid(row=0, column=1)
        (Label(dashboard_frame_navigation_row, textvariable=self.dashboard_frame_navigation_text)
         .grid(row=0, column=2))
        Button(dashboard_frame_navigation_row, text='>',
               command=self.increment_frame).grid(row=0, column=3)
        Button(dashboard_frame_navigation_row, text='>|',
               command=self.last_frame).grid(row=0, column=4)

        # dashboard table
        style = ttk.Style()
        style.theme_use("clam")
        style.configure('Treeview.Heading', background='#ddd', font=('TkDefaultFont', 10, 'bold'))
        dashboard_table = ttk.Treeview(dashboard_frame, height=10, padding=3)
        self.dashboard_table = dashboard_table
        dashboard_table['columns'] = ("tag", "description", "value", "setpoint")
        dashboard_table.grid(sticky="W", row=10, column=0)
        dashboard_table.column("#0", width=0, stretch=NO)
        dashboard_table.column("tag", anchor=CENTER, width=80)
        dashboard_table.column("description", anchor=CENTER, width=100)
        dashboard_table.column("value", anchor=CENTER, width=80)
        dashboard_table.column("setpoint", anchor=CENTER, width=80)
        dashboard_table.heading("tag", text="Tag", anchor=CENTER, command=self.toggle_tag)
        dashboard_table.heading("description", text="Description", anchor=CENTER,
                                command=self.toggle_description)
        dashboard_table.heading("value", text="Value", anchor=CENTER, command=self.toggle_value)
        dashboard_table.heading("setpoint", text="Setpoint", anchor=CENTER)
        dashboard_table.bind('<Double-1>', self.double_click_table_row)

        # elements of tableview_frame
        tableview_table_frame = Frame(tableview_frame)
        tableview_table_frame.grid(sticky="W", row=0, column=0)

        dummy_label = Label(tableview_table_frame, text="<Data table>")
        dummy_label.pack()

        tableview_filters_frame = LabelFrame(tableview_frame, text="Filters on data")
        tableview_filters_frame.grid(sticky="W", row=1, column=0)

        dummy_label = Label(tableview_filters_frame, text="<Filters>")
        dummy_label.pack()

        # elements of graphview_frame
        graphview_graph_frame = Frame(graphview_frame)
        graphview_graph_frame.grid(sticky="W", row=0, column=0)

        dummy_label = Label(graphview_graph_frame, text="<Embeded MatPlotLib Graph>")
        dummy_label.pack()

        graphview_filters_frame = LabelFrame(graphview_frame, text="Filters")
        graphview_filters_frame.grid(sticky="W", row=1, column=0)

        dummy_label = Label(graphview_filters_frame, text="<Filters on data>")
        dummy_label.pack()

        # elements of frameview_frame

        # dummy values for now
        frameview_descriptions = [
            ["<Timestamp - <description for timestamp>", "<more info about timestamp"],
            ["<value for timestamp"],
            ["<parameter - <description>", "<More info>", "<More info>"],
            ["<value for timestamp"],
            ["<parameter - <description>", "<More info>", "<More info>"],
            ["<value for timestamp"],
            ["<parameter - <description>", "<More info>", "<More info>"]
        ]

        draw_frameview(frameview_frame, frameview_descriptions)

    def toggle_tag(self) -> None:
        """
        This method is the toggle action for the tag header
        in the dashboard table
        """
        self.dashboard_view_model.toggle_sort("TAG")
        self.refresh_table()

    def toggle_description(self) -> None:
        """
        This method is the toggle action for the description header
        in the dashboard table
        """
        self.dashboard_view_model.toggle_sort("DESCRIPTION")
        self.refresh_table()

    def toggle_value(self) -> None:
        """
        This method is the toggle action for the value header
        in the dashboard table
        """
        self.dashboard_view_model.toggle_sort("VALUE")
        self.refresh_table()

    def double_click_table_row(self, event) -> None:
        """
        This method specifies what happens if a double click were to happen
        in the dashboard table
        """
        curItem = self.dashboard_table.focus()

        region = self.dashboard_table.identify("region", event.x, event.y)
        if region != "heading":
            self.openNewWindow(self.dashboard_table.item(curItem)['values'])

    def refresh_table(self) -> None:
        """
        This method wipes the data from the dashboard table and re-inserts
        the new values
        """
        for item in self.dashboard_table.get_children():
            self.dashboard_table.delete(item)
        for item in self.dashboard_view_model.get_table_entries():
            self.dashboard_table.insert("", END, values=tuple(item))

    def openNewWindow(self, values: List[str]) -> None:
        """
        This method opens a new window to display one row of telemetry data

        Args:
            values (List[str]): the values to be displayed in the
                new window
        """
        newWindow = Toplevel(self)
        newWindow.title("New Window")
        newWindow.geometry("200x200")
        for column in values:
            Label(newWindow, text=column).pack()

    def open_file(self):
        """
        This method specifies what happens when the add data button
        is clicked
        """
        file = filedialog.askopenfilename()

        self.dashboard_view_model.load_file(self._dm, 'telemetry0.h5')
        self.refresh_table()

        self.dashboard_view_model.toggle_start_time(None)
        self.dashboard_view_model.toggle_end_time(None)
        self.dashboard_view_model.choose_frame(self._dm, 0)
        self.refresh_table()

    def update_time(self):
        # Dummy for testing in the extreme short term
        self.dashboard_view_model.toggle_start_time(None)
        self.dashboard_view_model.toggle_end_time(None)
        self.dashboard_view_model.choose_frame(self._dm, 0)
        self.refresh_table()

    def first_frame(self):
        self.dashboard_current_frame_number = 0
        self.dashboard_view_model.choose_frame(self._dm, 0)
        self.refresh_table()

    def last_frame(self):
        last = self.dashboard_view_model.get_num_frames() - 1
        self.dashboard_current_frame_number = last
        self.dashboard_view_model.choose_frame(self._dm, last)
        self.refresh_table()

    def decrement_frame(self):
        if self.dashboard_current_frame_number > 0:
            self.dashboard_current_frame_number -= 1
        index = self.dashboard_current_frame_number
        self.dashboard_view_model.choose_frame(self._dm, index)
        self.refresh_table()

    def increment_frame(self):
        last = self.dashboard_view_model.get_num_frames() - 1
        if self.dashboard_current_frame_number < last:
            self.dashboard_current_frame_number += 1
        index = self.dashboard_current_frame_number
        self.dashboard_view_model.choose_frame(self._dm, index)
        self.refresh_table()
