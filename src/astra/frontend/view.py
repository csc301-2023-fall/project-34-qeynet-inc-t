"""
This file holds the view class that will be run in main.py
"""

import pathlib
import sys
from datetime import datetime
from tkinter import Button, Entry, Frame, LabelFrame, Toplevel
from tkinter import CENTER, NO, END
from tkinter import StringVar
from tkinter import filedialog, messagebox, ttk, Tk, Label
from tkinter.ttk import Treeview

from astra.data import config_manager
from astra.data.data_manager import DataManager
from .view_draw_functions import draw_frameview
from .view_model import DashboardViewModel
from ..data.parameters import Tag

config_path = filedialog.askopenfilename(title='Select config file')
if not config_path:
    sys.exit()
try:
    config_manager.read_config(config_path)
except Exception as e:
    messagebox.showerror(title='Cannot read config', message=f'{type(e).__name__}: {e}')
    sys.exit(1)
device_name = pathlib.Path(config_path).stem


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
        self._dm = DataManager.from_device_name(device_name)

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
        self.dashboard_search_bar = StringVar()

        filter_tags = Frame(dashboard_frame)
        filter_tags.config(background='#fff')
        filter_tags.grid(sticky='W', row=0, column=0, rowspan=20)
        Label(filter_tags, text="Parameters to display", background='#fff').grid(row=0, column=0, columnspan=2)
        Label(filter_tags, text="Search", background='#fff').grid(row=1, column=0)
        Entry(filter_tags, textvariable=self.dashboard_search_bar).grid(row=1, column=1)
        self.dashboard_search_bar.trace_add("write", self.search_bar_change)
        (Button(filter_tags, text="Check all search results",
                wraplength=80, command=self.update_time).grid(row=2, column=0, rowspan=2)) # TODO
        (Button(filter_tags, text="Uncheck all search results",
                wraplength=80, command=self.update_time).grid(row=2, column=1, rowspan=2)) # TODO
        tag_table = ttk.Treeview(filter_tags, height=12, show='tree')
        self.tag_table = tag_table
        tag_table['columns'] = ("tag")
        tag_table.column("#0", width=0, stretch=NO)
        tag_table.column("tag")
        tag_table.grid(row=4, column=0, columnspan=2)
        tag_table.bind('<ButtonRelease-1>', self.toggle_tag_table_row)

        add_data_button = Button(dashboard_frame, text="Add data...", command=self.open_file)
        add_data_button.grid(sticky="W", row=0, column=1)

        self.start_time = StringVar()
        self.end_time = StringVar()

        dashboard_time_range_row = Frame(dashboard_frame)
        dashboard_time_range_row.grid(sticky='W', row=1, column=1)
        Label(dashboard_time_range_row, text='From').grid(row=0, column=0)
        Entry(dashboard_time_range_row, textvariable=self.start_time).grid(row=0, column=1)
        Label(dashboard_time_range_row, text='to').grid(row=0, column=2)
        Entry(dashboard_time_range_row, textvariable=self.end_time).grid(row=0, column=3)
        Button(dashboard_time_range_row, text='Update time',
               command=self.update_time).grid(row=0, column=4)

        self.dashboard_current_frame_number = 0
        self.dashboard_frame_navigation_text = StringVar(value='Frame --- at ---')

        dashboard_frame_navigation_row = Frame(dashboard_frame)
        dashboard_frame_navigation_row.grid(sticky='W', row=2, column=1)
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
        dashboard_table.grid(sticky="W", row=10, column=1)
        dashboard_table.column("#0", width=0, stretch=NO)
        dashboard_table.column("tag", anchor=CENTER, width=80)
        dashboard_table.column("description", anchor=CENTER, width=100)
        dashboard_table.column("value", anchor=CENTER, width=80)
        dashboard_table.column("setpoint", anchor=CENTER, width=80)
        dashboard_table.heading("tag", text="Tag", anchor=CENTER, command=self.toggle_tag)
        dashboard_table.heading("description", text="Description", anchor=CENTER,
                                command=self.toggle_description)
        dashboard_table.heading("value", text="Value", anchor=CENTER)
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

        if self._dm.get_telemetry_data(None, None, {}).num_telemetry_frames > 0:
            self.dashboard_view_model.toggle_start_time(None)
            self.dashboard_view_model.toggle_end_time(None)
            self.dashboard_view_model.choose_frame(self._dm, 0)
            self.refresh_table()

    def toggle_tag(self) -> None:
        """
        This method is the toggle action for the tag header
        in the dashboard table
        """
        if self._dm.get_telemetry_data(None, None, {}).num_telemetry_frames > 0:
            self.dashboard_view_model.toggle_sort("TAG")
            self.refresh_table()

    def toggle_description(self) -> None:
        """
        This method is the toggle action for the description header
        in the dashboard table
        """
        if self._dm.get_telemetry_data(None, None, {}).num_telemetry_frames > 0:
            self.dashboard_view_model.toggle_sort("DESCRIPTION")
            self.refresh_table()

    def double_click_table_row(self, event) -> None:
        """
        This method specifies what happens if a double click were to happen
        in the dashboard table
        """
        if self._dm.get_telemetry_data(None, None, {}).num_telemetry_frames > 0:
            cur_item = self.dashboard_table.focus()

            region = self.dashboard_table.identify("region", event.x, event.y)
            if region != "heading":
                self.open_new_window(self.dashboard_table.item(cur_item)['values'])

    def refresh_table(self) -> None:
        """
        This method wipes the data from the dashboard table and re-inserts
        the new values
        """
        self.change_frame_navigation_text()
        for item in self.dashboard_table.get_children():
            self.dashboard_table.delete(item)
        for item in self.dashboard_view_model.get_table_entries():
            self.dashboard_table.insert("", END, values=tuple(item))

    def open_new_window(self, values: list[str]) -> None:
        """
        This method opens a new window to display one row of telemetry data

        Args:
            values (list[str]): the values to be displayed in the
                new window
        """
        new_window = Toplevel(self)
        new_window.title("New Window")
        new_window.geometry("200x200")
        for column in values:
            Label(new_window, text=column).pack()

    def open_file(self):
        """
        This method specifies what happens when the add data button
        is clicked
        """
        file = filedialog.askopenfilename(title='Select telemetry file')

        if not file:
            return

        try:
            self.dashboard_view_model.load_file(self._dm, file)
        except Exception as e:
            messagebox.showerror(title='Cannot read telemetry', message=f'{type(e).__name__}: {e}')
            return
        self.refresh_table()

        self.dashboard_view_model.toggle_start_time(None)
        self.dashboard_view_model.toggle_end_time(None)
        self.dashboard_view_model.choose_frame(self._dm, 0)
        self.refresh_table()

    def update_time(self):
        input_start_time = self.start_time.get()
        input_end_time = self.end_time.get()
        if input_start_time:
            try:
                start_time = datetime.strptime(input_start_time, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                messagebox.showwarning(
                    title='Invalid start time',
                    message=(
                        'Start time must either be empty or a valid datetime in the format '
                        'YYYY-MM-DD hh:mm:ss.'
                    )
                )
                return
        else:
            start_time = None
        if input_end_time:
            try:
                end_time = datetime.strptime(input_end_time, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                messagebox.showwarning(
                    title='Invalid end time',
                    message=(
                        'End time must either be empty or a valid datetime in the format '
                        'YYYY-MM-DD hh:mm:ss.'
                    )
                )
                return
        else:
            end_time = None
        if self._dm.get_telemetry_data(start_time, end_time, {}).num_telemetry_frames == 0:
            messagebox.showinfo(
                title='No telemetry frames',
                message='The chosen time range does not have any telemetry frames.'
            )
            return
        self.dashboard_view_model.toggle_start_time(start_time)
        self.dashboard_view_model.toggle_end_time(end_time)
        self.dashboard_current_frame_number = 0
        self.dashboard_view_model.choose_frame(self._dm, 0)
        self.refresh_table()

    def first_frame(self):
        if self.dashboard_view_model.get_num_frames() == 0:
            return
        self.dashboard_current_frame_number = 0
        self.dashboard_view_model.choose_frame(self._dm, 0)
        self.refresh_table()

    def last_frame(self):
        if self.dashboard_view_model.get_num_frames() == 0:
            return
        last = self.dashboard_view_model.get_num_frames() - 1
        self.dashboard_current_frame_number = last
        self.dashboard_view_model.choose_frame(self._dm, last)
        self.refresh_table()

    def decrement_frame(self):
        if self.dashboard_view_model.get_num_frames() == 0:
            return
        if self.dashboard_current_frame_number > 0:
            self.dashboard_current_frame_number -= 1
        index = self.dashboard_current_frame_number
        self.dashboard_view_model.choose_frame(self._dm, index)
        self.refresh_table()

    def increment_frame(self):
        if self.dashboard_view_model.get_num_frames() == 0:
            return
        last = self.dashboard_view_model.get_num_frames() - 1
        if self.dashboard_current_frame_number < last:
            self.dashboard_current_frame_number += 1
        index = self.dashboard_current_frame_number
        self.dashboard_view_model.choose_frame(self._dm, index)
        self.refresh_table()

    def change_frame_navigation_text(self):
        curr = self.dashboard_current_frame_number + 1
        total = self.dashboard_view_model.get_num_frames()
        time = self.dashboard_view_model.get_time()
        self.dashboard_frame_navigation_text.set(
            f"Frame {curr}/{total} at {time}"
        )

    def update_searched_tags(self):
        for tag in self.tag_table.get_children():
            self.tag_table.delete(tag)
        for tag in self.dashboard_view_model.get_tag_list():
            check = " "
            if tag in self.dashboard_view_model.get_toggled_tags():
                check = "x"
            self.tag_table.insert("", END, value=(f"[{check}] {tag}",))

    def search_bar_change(self, *args):
        del args
        self.dashboard_view_model.search_tags(self.dashboard_search_bar.get())
        self.update_searched_tags()

    def toggle_tag_table_row(self, event):
        cur_item = self.tag_table.focus()
        try:
            tag_str = self.tag_table.item(cur_item)['values'][0][4:]
        except IndexError:
            # Do nothing
            return
        tag = Tag(tag_str)
        self.dashboard_view_model.toggle_tag(tag)
        self.update_searched_tags()
        self.refresh_table()

