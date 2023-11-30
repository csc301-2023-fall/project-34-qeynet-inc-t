"""
This file holds the view that is used for the telemetry tab
"""

from datetime import datetime
from tkinter import Button, Frame, Toplevel, Event
from tkinter import CENTER, NO, END
from tkinter import StringVar
from tkinter import filedialog, messagebox, ttk, Label

from astra.data.data_manager import DataManager
from astra.frontend.timerange_input import OperationControl, TimerangeInput
from .tag_searcher import TagSearcher
from ..usecase.request_receiver import DashboardRequestReceiver, DataRequestReceiver


class TelemetryView:
    def __init__(self, frame: ttk.Notebook, num_rows: int, dm: DataManager):
        self.dm = dm
        self.overall_frame = Frame(frame)
        self.controller = DashboardRequestReceiver()
        self.data_controller = DataRequestReceiver()

        for i in range(num_rows):
            self.overall_frame.grid_rowconfigure(i, weight=1)

        self.overall_frame.grid_columnconfigure(0, weight=1)
        self.overall_frame.grid_columnconfigure(1, weight=2)

        self.dashboard_searcher = TagSearcher(num_rows, self.overall_frame, self.dm,
                                              self.dashboard_searcher_update)

        add_data_button = Button(self.overall_frame, text='Add data...', command=self.open_file)
        add_data_button.grid(sticky='W', row=0, column=1)

        TimerangeInput(
            self.overall_frame, 'Time range', self.update_dashboard_times
        ).grid(sticky='W', row=1, column=1)

        self.dashboard_current_frame_number = 0
        self.navigation_text = StringVar(value='Frame --- at ---')

        self.navigation_row_outside = Frame(self.overall_frame)
        self.navigation_row_outside.grid(sticky='ew', row=2, column=1, pady=(10, 0))
        self.navigation_row = Frame(self.navigation_row_outside)
        self.navigation_row.pack(expand=False)
        Button(self.navigation_row, text='|<',
               command=self.first_frame).grid(sticky='w', row=0, column=0)
        Button(self.navigation_row, text='<',
               command=self.decrement_frame).grid(sticky='w', row=0, column=1)
        (Label(self.navigation_row, textvariable=self.navigation_text)
         .grid(sticky='ew', row=0, column=2))
        Button(self.navigation_row, text='>',
               command=self.increment_frame).grid(sticky='e', row=0, column=3)
        Button(self.navigation_row, text='>|',
               command=self.last_frame).grid(sticky='e', row=0, column=4)

        # dashboard table
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview.Heading', background='#ddd', font=('TkDefaultFont', 10, 'bold'))
        dashboard_table = ttk.Treeview(self.overall_frame, height=10, padding=3)
        dashboard_table_scroll = ttk.Scrollbar(self.overall_frame, orient='vertical',
                                               command=dashboard_table.yview)
        dashboard_table.configure(yscrollcommand=dashboard_table_scroll.set)
        dashboard_table_scroll.grid(sticky='NS', row=4, column=2, rowspan=num_rows - 5)
        self.dashboard_table = dashboard_table
        dashboard_table['columns'] = ('tag', 'description', 'value', 'setpoint', 'units', 'alarm')
        dashboard_table.grid(sticky='NSEW', row=4, column=1, rowspan=num_rows - 5)
        dashboard_table.column('#0', width=0, stretch=NO)
        dashboard_table.column('tag', anchor=CENTER, width=80)
        dashboard_table.column('description', anchor=CENTER, width=100)
        dashboard_table.column('value', anchor=CENTER, width=80)
        dashboard_table.column('setpoint', anchor=CENTER, width=80)
        dashboard_table.column('units', anchor=CENTER, width=80)
        dashboard_table.column('alarm', anchor=CENTER, width=80)
        dashboard_table.heading('tag', text='Tag ▲', anchor=CENTER, command=self.toggle_tag)
        dashboard_table.heading('description', text='Description ●', anchor=CENTER,
                                command=self.toggle_description)
        dashboard_table.heading('value', text='Value', anchor=CENTER)
        dashboard_table.heading('setpoint', text='Setpoint', anchor=CENTER)
        dashboard_table.heading('units', text='Units', anchor=CENTER)
        dashboard_table.heading('alarm', text='Alarm', anchor=CENTER)
        dashboard_table.bind('<Double-1>', self.double_click_dashboard_table_row)

        dashboard_table.bind('<Up>', self.move_row_up)
        dashboard_table.bind('<Down>', self.move_row_down)

        self.data_controller.set_data_manager(self.dm)

        if self.data_controller.data_exists():
            self.controller.create(self.dm)

            self.controller.change_index(0)
            self.controller.toggle_sort('TAG')
            self.controller.create(self.dm)
            self.refresh_data_table()

            self.dashboard_searcher.update_searched_tags()
            self.dashboard_searcher.select_all_tags()

    def toggle_tag(self) -> None:
        """
        This method is the toggle action for the tag header
        in the dashboard table
        """
        if self.data_controller.data_exists():
            ascending = self.controller.toggle_sort('TAG')
            if ascending:
                self.dashboard_table.heading('tag', text='Tag ▲')
                self.dashboard_table.heading('description', text='Description ●')
            else:
                self.dashboard_table.heading('tag', text='Tag ▼')
                self.dashboard_table.heading('description', text='Description ●')
            self.controller.update()
            self.refresh_data_table()

    def toggle_description(self) -> None:
        """
        This method is the toggle action for the description header
        in the dashboard table
        """
        if self.data_controller.data_exists():
            ascending = self.controller.toggle_sort('DESCRIPTION')
            if ascending:
                self.dashboard_table.heading('description', text='Description ▲')
                self.dashboard_table.heading('tag', text='Tag ●')
            else:
                self.dashboard_table.heading('description', text='Description ▼')
                self.dashboard_table.heading('tag', text='Tag ●')
            self.controller.update()
            self.refresh_data_table()

    def double_click_dashboard_table_row(self, event) -> None:
        """
        This method specifies what happens if a double click were to happen
        in the dashboard table
        """
        cur_item = self.dashboard_table.focus()

        region = self.dashboard_table.identify('region', event.x, event.y)
        if cur_item and region != 'heading':
            self.open_telemetry_popup(self.dashboard_table.item(cur_item)['values'])

    def refresh_data_table(self) -> None:
        """
        This method wipes the data from the dashboard table and re-inserts
        the new values
        """
        self.change_frame_navigation_text()
        for item in self.dashboard_table.get_children():
            self.dashboard_table.delete(item)
        for item in self.controller.get_table_entries():
            self.dashboard_table.insert('', END, values=tuple(item))

    def construct_dashboard_table(self):
        self.controller.create(self.dm)
        self.refresh_data_table()

    def open_telemetry_popup(self, values: list[str]) -> None:
        """
        This method opens a new window to display one row of telemetry data

        Args:
            values (list[str]): the values to be displayed in the
                new window
        """
        new_window = Toplevel(self.overall_frame)
        new_window.title('Telemetry information')
        new_window.geometry('200x200')
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
            self.data_controller.set_filename(file)
            self.data_controller.update()
            self.controller.create(self.dm)
        except Exception as e:
            messagebox.showerror(title='Cannot read telemetry', message=f'{type(e).__name__}: {e}')
            return

        self.refresh_data_table()

        self.dashboard_searcher.update_searched_tags()

    def update_dashboard_times(
            self, start_time: datetime | None, end_time: datetime | None
    ) -> OperationControl:
        if self.dm.get_telemetry_data(start_time, end_time, {}).num_telemetry_frames == 0:
            messagebox.showinfo(
                title='No telemetry frames',
                message='The chosen time range does not have any telemetry frames.'
            )
            return OperationControl.CANCEL
        self.controller.set_start_time(start_time)
        self.controller.set_end_time(end_time)
        self.dashboard_current_frame_number = 0
        self.controller.change_index(0)
        self.controller.create(self.dm)
        self.change_frame_navigation_text()

        self.refresh_data_table()
        return OperationControl.CONTINUE

    def first_frame(self):
        if self.controller.get_num_frames() == 0:
            return
        self.dashboard_current_frame_number = 0
        self.controller.change_index(0)
        self.controller.create(self.dm)
        self.refresh_data_table()

    def last_frame(self):
        if self.controller.get_num_frames() == 0:
            return
        last = self.controller.get_num_frames() - 1
        self.dashboard_current_frame_number = last
        self.controller.change_index(last)
        self.controller.create(self.dm)
        self.refresh_data_table()

    def decrement_frame(self):
        if self.controller.get_num_frames() == 0:
            return
        if self.dashboard_current_frame_number > 0:
            self.dashboard_current_frame_number -= 1
        index = self.dashboard_current_frame_number
        self.controller.change_index(index)
        self.controller.create(self.dm)
        self.refresh_data_table()

    def increment_frame(self):
        if self.controller.get_num_frames() == 0:
            return
        last = self.controller.get_num_frames() - 1
        if self.dashboard_current_frame_number < last:
            self.dashboard_current_frame_number += 1
        index = self.dashboard_current_frame_number
        self.controller.change_index(index)
        self.controller.create(self.dm)
        self.refresh_data_table()

    def move_row_up(self, event: Event):
        focus_item = self.dashboard_table.focus()

        region = self.dashboard_table.identify('region', event.x, event.y)
        if focus_item and region != 'heading':
            focus_row = self.dashboard_table.selection()
            index = self.dashboard_table.index(focus_item)

            if len(focus_row) == 1 and index > 0:
                self.dashboard_table.move(focus_row[0],
                                          self.dashboard_table.parent(focus_row[0]), index - 1)

                # Workaround for selection skipping where we previously were
                prev_row = self.dashboard_table.get_children()[index]
                self.dashboard_table.focus(prev_row)
                self.dashboard_table.selection_set(prev_row)

    def move_row_down(self, event: Event):
        focus_item = self.dashboard_table.focus()

        region = self.dashboard_table.identify('region', event.x, event.y)
        if focus_item and region != 'heading':
            focus_row = self.dashboard_table.selection()
            index = self.dashboard_table.index(focus_item)

            if len(focus_row) == 1 and index < len(self.dashboard_table.get_children()):
                self.dashboard_table.move(focus_row[0],
                                          self.dashboard_table.parent(focus_row[0]), index + 1)

                # Workaround for selection skipping where we previously were
                prev_row = self.dashboard_table.get_children()[index]
                self.dashboard_table.focus(prev_row)
                self.dashboard_table.selection_set(prev_row)

    def change_frame_navigation_text(self):
        curr = self.dashboard_current_frame_number + 1
        total = self.controller.get_num_frames()
        time = self.controller.get_time()
        self.navigation_text.set(
            f'Frame {curr}/{total} at {time}'
        )

    def dashboard_searcher_update(self):
        # Convert to list to enforce ordering
        selected_tags = list(self.dashboard_searcher.selected_tags)
        self.controller.set_shown_tags(selected_tags)
        self.controller.update()
        self.refresh_data_table()
