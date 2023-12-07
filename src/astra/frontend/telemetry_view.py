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
from ..usecase.dashboard_request_receiver import DashboardRequestReceiver
from ..usecase.request_receiver import DataRequestReceiver


class TelemetryView:
    """Contains the GUI elements of the Telemetry Dashboard"""

    def __init__(self, frame: ttk.Notebook, num_rows: int, dm: DataManager):
        """
        Initializes all GUI elements of the telemetry dashboard

        :param frame: The notebook of tabs which this view should be inserted into
        :param num_rows: Used for scaling to fullscreen
        :param dm: Contains all data known to the program
        """
        self.dm = dm
        self.overall_frame = Frame(frame)
        self.controller = DashboardRequestReceiver()
        self.data_controller = DataRequestReceiver()

        # Configuring row/column weightings
        for i in range(num_rows):
            self.overall_frame.grid_rowconfigure(i, weight=1)

        self.overall_frame.grid_columnconfigure(0, weight=1)
        self.overall_frame.grid_columnconfigure(1, weight=2)

        # Configuring search widget
        self.dashboard_searcher = TagSearcher(num_rows, self.overall_frame, self.dm,
                                              self.dashboard_searcher_update)

        # Configuring button to add new data
        add_data_button = Button(self.overall_frame, text='Add data...', command=self._open_file)
        add_data_button.grid(sticky='W', row=0, column=1)

        # Configuring timerange input for changing available telemetry frames
        TimerangeInput(
            self.overall_frame, 'Time range', self._update_dashboard_times
        ).grid(sticky='W', row=1, column=1)

        self.dashboard_current_frame_number = 0
        self.navigation_text = StringVar(value='Frame --- at ---')

        # Configuring column header for changing telemetry frame and seeing current frame
        # information
        self.navigation_row_outside = Frame(self.overall_frame)
        self.navigation_row_outside.grid(sticky='ew', row=2, column=1, pady=(10, 0))
        self.navigation_row = Frame(self.navigation_row_outside)
        self.navigation_row.pack(expand=False)
        Button(self.navigation_row, text='|<',
               command=self._first_frame).grid(sticky='w', row=0, column=0)
        Button(self.navigation_row, text='<',
               command=self._decrement_frame).grid(sticky='w', row=0, column=1)
        (Label(self.navigation_row, textvariable=self.navigation_text)
         .grid(sticky='ew', row=0, column=2))
        Button(self.navigation_row, text='>',
               command=self._increment_frame).grid(sticky='e', row=0, column=3)
        Button(self.navigation_row, text='>|',
               command=self._last_frame).grid(sticky='e', row=0, column=4)

        # Configuring dashboard table
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
        dashboard_table.heading('tag', text='Tag ▼', anchor=CENTER, command=self._toggle_tag)
        dashboard_table.heading('description', text='Description ●', anchor=CENTER,
                                command=self._toggle_description)
        dashboard_table.heading('value', text='Value', anchor=CENTER)
        dashboard_table.heading('setpoint', text='Setpoint', anchor=CENTER)
        dashboard_table.heading('units', text='Units', anchor=CENTER)
        dashboard_table.heading('alarm', text='Alarm', anchor=CENTER)
        dashboard_table.bind('<Double-1>', self._double_click_dashboard_table_row)

        dashboard_table.bind('<Up>', self._move_row_up)
        dashboard_table.bind('<Down>', self._move_row_down)

        self.data_controller.set_data_manager(self.dm)
        self._toggle_tag()
        self.dashboard_searcher.update_searched_tags()

        if self.data_controller.data_exists():
            self.controller.create(self.dm)

            self.controller.change_index(0)
            self.controller.create(self.dm)
            self._refresh_data_table()

            self.dashboard_searcher.select_all_tags()

    def _toggle_tag(self) -> None:
        """
        Defines what occurs when the "tag" table header is clicked
        """
        ascending = self.controller.toggle_sort('TAG')
        if ascending:
            self.dashboard_table.heading('tag', text='Tag ▲')
            self.dashboard_table.heading('description', text='Description ●')
        else:
            self.dashboard_table.heading('tag', text='Tag ▼')
            self.dashboard_table.heading('description', text='Description ●')
        self.controller.update()
        self._refresh_data_table()

    def _toggle_description(self) -> None:
        """
        Defines what occurs when the "Description" table header is clicked
        """
        ascending = self.controller.toggle_sort('DESCRIPTION')
        if ascending:
            self.dashboard_table.heading('description', text='Description ▲')
            self.dashboard_table.heading('tag', text='Tag ●')
        else:
            self.dashboard_table.heading('description', text='Description ▼')
            self.dashboard_table.heading('tag', text='Tag ●')
        self.controller.update()
        self._refresh_data_table()

    def _double_click_dashboard_table_row(self, event) -> None:
        """
        This method specifies what happens if a double click were to happen
        in the dashboard table
        """
        cur_item = self.dashboard_table.focus()

        region = self.dashboard_table.identify('region', event.x, event.y)
        if cur_item and region != 'heading':
            self._open_telemetry_popup(self.dashboard_table.item(cur_item)['values'])

    def _refresh_data_table(self) -> None:
        """
        This method wipes the data from the dashboard table and re-inserts
        the new values
        """
        if self.controller.get_table_entries() is not None:
            self._change_frame_navigation_text()
            for item in self.dashboard_table.get_children():
                self.dashboard_table.delete(item)
            for item in self.controller.get_table_entries():
                self.dashboard_table.insert('', END, values=tuple(item))

    def construct_dashboard_table(self) -> None:
        """
        Makes a request to obtain all data pertaining to the current telemetry frame and
        reconstructs the shown data table
        """
        self.controller.create(self.dm)
        self._refresh_data_table()

    def _open_telemetry_popup(self, values: list[str]) -> None:
        """
        This method opens a new window to display one row of telemetry data

        :params: values (list[str]): the values to be displayed in the
        new window
        """
        new_window = Toplevel(self.overall_frame)
        new_window.title('Telemetry information')
        new_window.geometry('200x200')
        for column in values:
            Label(new_window, text=column).pack()

    def _open_file(self) -> None:
        """
        This method specifies what happens when the add data button
        is clicked
        """
        file = filedialog.askopenfilename(title='Select telemetry file')

        if not file:
            return

        try:
            # Uses the input file and makes a request to insert new data
            self.data_controller.set_filename(file)
            self.data_controller.update()
            self.controller.create(self.dm)
        except Exception as e:
            messagebox.showerror(title='Cannot read telemetry', message=f'{type(e).__name__}: {e}')
            return

        self._refresh_data_table()

        self.dashboard_searcher.update_searched_tags()

    def _update_dashboard_times(
            self, start_time: datetime | None, end_time: datetime | None
    ) -> OperationControl:
        """

        :param start_time: The minimum requested time for telemetry frames
        :param end_time: The maximum requested time for telemetry frames
        :return: An operation code indicating how to proceed
        """
        if self.dm.get_telemetry_data(start_time, end_time, {}).num_telemetry_frames == 0:
            messagebox.showinfo(
                title='No telemetry frames',
                message='The chosen time range does not have any telemetry frames.'
            )
            return OperationControl.CANCEL

        # Making a backend request to change the minimum/maximum time and update the table
        self.controller.set_start_time(start_time)
        self.controller.set_end_time(end_time)
        self.dashboard_current_frame_number = 0
        self.controller.change_index(0)
        self.controller.create(self.dm)
        self._change_frame_navigation_text()

        self._refresh_data_table()
        return OperationControl.CONTINUE

    def _first_frame(self) -> None:
        """
        Sets the current frame to the first available telemetry frame
        """
        if self.controller.get_num_frames() == 0:
            return
        self.dashboard_current_frame_number = 0
        self.controller.change_index(0)
        self.controller.create(self.dm)
        self._refresh_data_table()

    def _last_frame(self) -> None:
        """
        Sets the current frame to the last available telemetry frame
        """
        if self.controller.get_num_frames() == 0:
            return
        last = self.controller.get_num_frames() - 1
        self.dashboard_current_frame_number = last
        self.controller.change_index(last)
        self.controller.create(self.dm)
        self._refresh_data_table()

    def _decrement_frame(self) -> None:
        """
        Sets the current frame to the previous available telemetry frame, if any exist
        """
        # Case for no available frames
        if self.controller.get_num_frames() == 0:
            return

        # Ensures nothing occurs when on the first available frame
        if self.dashboard_current_frame_number > 0:
            self.dashboard_current_frame_number -= 1

        index = self.dashboard_current_frame_number
        self.controller.change_index(index)
        self.controller.create(self.dm)
        self._refresh_data_table()

    def _increment_frame(self) -> None:
        """
        Sets the current frame to the next available telemetry frame, if any exist
        """

        if self.controller.get_num_frames() == 0:
            return
        last = self.controller.get_num_frames() - 1

        # Ensures nothing occurs when on the last available frame
        if self.dashboard_current_frame_number < last:
            self.dashboard_current_frame_number += 1
        index = self.dashboard_current_frame_number
        self.controller.change_index(index)
        self.controller.create(self.dm)
        self._refresh_data_table()

    def _move_row_up(self, event: Event):
        """
        Moves the currently selected row up one row
        """
        focus_item = self.dashboard_table.focus()

        region = self.dashboard_table.identify('region', event.x, event.y)

        # Ensuring the current focus is a table row
        if focus_item and region != 'heading':
            focus_row = self.dashboard_table.selection()
            index = self.dashboard_table.index(focus_item)

            if len(focus_row) == 1 and index > 0:
                # If focusing the first available row, nothing happens
                self.dashboard_table.move(focus_row[0],
                                          self.dashboard_table.parent(focus_row[0]), index - 1)

                # Workaround for selection skipping where we previously were
                prev_row = self.dashboard_table.get_children()[index]
                self.dashboard_table.focus(prev_row)
                self.dashboard_table.selection_set(prev_row)

    def _move_row_down(self, event: Event) -> None:
        """
        Moves the currently selected row down one row
        """
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

    def _change_frame_navigation_text(self) -> None:
        """
        Changes the table header to account for changes in number of available frame
        or change in examined frame
        """
        curr = self.dashboard_current_frame_number + 1
        total = self.controller.get_num_frames()
        time = self.controller.get_time()
        self.navigation_text.set(
            f'Frame {curr}/{total} at {time}'
        )

    def dashboard_searcher_update(self) -> None:
        """
        Watcher function to be called once any update occurs in the search widget
        """
        # Convert to list to enforce ordering
        selected_tags = list(self.dashboard_searcher.selected_tags)

        # changing available tags
        self.controller.set_shown_tags(selected_tags)
        if self.controller.get_num_frames() > 0:

            self.controller.update()
            self._refresh_data_table()
