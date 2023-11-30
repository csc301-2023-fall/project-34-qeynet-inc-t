"""
This file holds the view that is used for the alarms tab
"""

from datetime import datetime
from tkinter import Button, Frame, Toplevel, Event
from tkinter import CENTER, BOTTOM, NO, END, BOTH
from tkinter import messagebox, ttk, Label

from astra.data.data_manager import DataManager
from astra.frontend.timerange_input import OperationControl, TimerangeInput
from .tag_searcher import AlarmTagSearcher
from .view_model import AlarmsViewModel
from ..data.alarms import Alarm


class AlarmView:

    def __init__(self, frame: ttk.Notebook, num_rows: int, dm: DataManager, watchers: list):
        self.dm = dm
        self.overall_frame = Frame(frame)
        self.alarms_view_model = AlarmsViewModel(self.dm, watchers)

        for i in range(num_rows):
            self.overall_frame.grid_rowconfigure(i, weight=1)

        self.overall_frame.grid_columnconfigure(0, weight=0)
        self.overall_frame.grid_columnconfigure(1, weight=1)

        self.alarms_searcher = AlarmTagSearcher(num_rows, self.overall_frame, self.dm,
                                                self.alarms_searcher_update)

        # alarms filters (for the table)
        alarms_tag_table = Frame(self.overall_frame)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview.Heading', background='#ddd', font=('TkDefaultFont', 10, 'bold'))
        alarms_tag_table.grid(sticky='NSEW', row=1, column=1)
        self.dangers = ['WARNING', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        self.types = ['RATE_OF_CHANGE', 'STATIC', 'THRESHOLD', 'SETPOINT', 'SOE', 'L_AND', 'L_OR']

        button = Button(alarms_tag_table, text='Show new alarms only', relief='raised',
                        command=lambda: self.flick_new())
        button.grid(sticky='w', row=0, columnspan=8)
        self.alarms_button_new = button

        self.alarms_buttons_priority = []
        label = Label(alarms_tag_table, text='Filter priority:')
        label.grid(sticky='news', row=1, column=0)

        for i in range(len(self.dangers)):
            button = Button(alarms_tag_table, text=self.dangers[i], relief='sunken',
                            command=lambda x=i: self.flick_priority(x))
            button.grid(sticky='news', row=1, column=i + 1)
            self.alarms_buttons_priority.append(button)

        label = Label(alarms_tag_table, text='Filter criticality:')
        label.grid(sticky='news', row=2, column=0)
        self.alarms_buttons_criticality = []

        for i in range(len(self.dangers)):
            button = Button(alarms_tag_table, text=self.dangers[i], relief='sunken',
                            command=lambda x=i: self.flick_criticality(x))
            button.grid(sticky='news', row=2, column=i + 1)
            self.alarms_buttons_criticality.append(button)

        TimerangeInput(
            alarms_tag_table, 'Registered', self.update_alarm_registered_times
        ).grid(sticky='W', row=3, columnspan=8)

        TimerangeInput(
            alarms_tag_table, 'Confirmed', self.update_alarm_confirmed_times
        ).grid(sticky='W', row=4, columnspan=8)

        label = Label(alarms_tag_table, text='Filter type:')
        label.grid(sticky='news', row=5, column=0)
        self.alarms_buttons_type = []

        for i in range(len(self.types)):
            button = Button(alarms_tag_table, text=self.types[i], relief='sunken',
                            command=lambda x=i: self.flick_type(x))
            button.grid(sticky='news', row=5, column=i + 1)
            self.alarms_buttons_type.append(button)

        # alarms table
        alarms_table_frame = Frame(self.overall_frame)
        alarms_table_frame.grid(sticky='NSEW', row=2, column=1, rowspan=num_rows - 3)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview.Heading', background='#ddd', font=('TkDefaultFont', 10, 'bold'))
        alarms_table = ttk.Treeview(alarms_table_frame, padding=3)
        alarms_table_scroll = ttk.Scrollbar(alarms_table_frame, orient='vertical',
                                            command=alarms_table.yview)
        alarms_table.configure(yscrollcommand=alarms_table_scroll.set)
        alarms_table_scroll.pack(side='right', fill='y')
        self.alarms_table = alarms_table
        alarms_table.pack(fill='both', expand=True, side='left')
        alarms_table['columns'] = (
            'ID', 'Priority', 'Criticality', 'Registered', 'Confirmed', 'Type', 'Parameter(s)',
            'Description')
        alarms_table.column('#0', width=0, stretch=NO)
        alarms_table.column('ID', anchor=CENTER, width=80)
        alarms_table.column('Priority', anchor=CENTER, width=80)
        alarms_table.column('Criticality', anchor=CENTER, width=80)
        alarms_table.column('Registered', anchor=CENTER, width=120)
        alarms_table.column('Confirmed', anchor=CENTER, width=120)
        alarms_table.column('Type', anchor=CENTER, width=80)
        alarms_table.column('Parameter(s)', anchor=CENTER, width=100)
        alarms_table.column('Description', anchor=CENTER, width=200)

        alarms_table.heading('ID', text='ID ▲', anchor=CENTER,
                             command=lambda: self.sort_alarms('ID'))
        alarms_table.heading('Priority', text='Priority ●', anchor=CENTER,
                             command=lambda: self.sort_alarms('PRIORITY'))
        alarms_table.heading('Criticality', text='Criticality ●', anchor=CENTER,
                             command=lambda: self.sort_alarms('CRITICALITY'))
        alarms_table.heading('Registered', text='Registered ●', anchor=CENTER,
                             command=lambda: self.sort_alarms('REGISTERED'))
        alarms_table.heading('Confirmed', text='Confirmed ●', anchor=CENTER,
                             command=lambda: self.sort_alarms('CONFIRMED'))
        alarms_table.heading('Type', text='Type ●', anchor=CENTER,
                             command=lambda: self.sort_alarms('TYPE'))
        alarms_table.heading('Parameter(s)', text='Parameter(s)', anchor=CENTER)
        alarms_table.heading('Description', text='Description', anchor=CENTER)
        alarms_table.bind('<Double-1>', self.double_click_alarms_table_row)

        if self.dm.get_telemetry_data(None, None, {}).num_telemetry_frames > 0:
            self.refresh_alarms_table()

            self.alarms_searcher.update_searched_tags()
            self.alarms_searcher.select_all_tags()

    def sort_alarms(self, tag: str):
        headers = ['ID', 'Priority', 'Criticality', 'Registered', 'Confirmed', 'Type']
        ascending = self.alarms_view_model.toggle_sort(heading=tag)

        if tag != 'ID':
            header_name = tag[0] + tag[1:].lower()
        else:
            header_name = tag

        if header_name in headers:
            if ascending:
                self.alarms_table.heading(header_name, text=header_name + ' ▲')
            else:
                self.alarms_table.heading(header_name, text=header_name + ' ▼')

            for header in headers:
                if header != header_name:
                    self.alarms_table.heading(header, text=header + ' ●')

        self.refresh_alarms_table()

    def flick_new(self):
        if self.alarms_view_model.get_new():
            self.alarms_button_new.config(relief='raised')
        else:
            self.alarms_button_new.config(relief='sunken')
        self.alarms_view_model.toggle_new()
        self.refresh_alarms_table()

    def flick_priority(self, index: int):
        tag = self.dangers[index]
        if tag in self.alarms_view_model.get_priorities():
            self.alarms_buttons_priority[index].config(relief='raised')
        else:
            self.alarms_buttons_priority[index].config(relief='sunken')
        self.alarms_view_model.toggle_priority(tag)
        self.refresh_alarms_table()

    def flick_criticality(self, index: int):
        tag = self.dangers[index]
        if tag in self.alarms_view_model.get_criticalities():
            self.alarms_buttons_criticality[index].config(relief='raised')
        else:
            self.alarms_buttons_criticality[index].config(relief='sunken')
        self.alarms_view_model.toggle_criticality(tag)
        self.refresh_alarms_table()

    def update_alarm_registered_times(
            self, start_time: datetime | None, end_time: datetime | None
    ) -> OperationControl:
        self.alarms_view_model.toggle_registered_start_time(start_time)
        self.alarms_view_model.toggle_registered_end_time(end_time)
        self.alarms_view_model.model.receive_updates()
        self.alarms_view_model.update_table_entries()
        self.refresh_alarms_table()
        return OperationControl.CONTINUE

    def update_alarm_confirmed_times(
            self, start_time: datetime | None, end_time: datetime | None
    ) -> OperationControl:
        self.alarms_view_model.toggle_confirmed_start_time(start_time)
        self.alarms_view_model.toggle_confirmed_end_time(end_time)
        self.alarms_view_model.model.receive_updates()
        self.alarms_view_model.update_table_entries()
        self.refresh_alarms_table()
        return OperationControl.CONTINUE

    def flick_type(self, index: int):
        tag = self.types[index]
        if tag in self.alarms_view_model.get_types():
            self.alarms_buttons_type[index].config(relief='raised')
        else:
            self.alarms_buttons_type[index].config(relief='sunken')
        self.alarms_view_model.toggle_type(tag)
        self.refresh_alarms_table()

    def double_click_alarms_table_row(self, event) -> None:
        """
        This method specifies what happens if a double click were to happen
        in the alarms table
        """
        cur_item = self.alarms_table.focus()

        region = self.alarms_table.identify('region', event.x, event.y)
        if cur_item and region != 'heading':
            index = self.alarms_table.index(cur_item)
            alarm = self.alarms_view_model.get_table_entries()[index][-1]
            self.open_alarm_popup(alarm)

    def construct_alarms_table(self, event: Event = None):
        self.alarms_view_model.model.receive_new_data(self.dm)
        self.alarms_view_model.toggle_all()
        self.refresh_alarms_table()

    def refresh_alarms_table(self) -> None:
        """
        This method wipes the data from the dashboard table and re-inserts
        the new values
        """
        for item in self.alarms_table.get_children():
            self.alarms_table.delete(item)
        for item in self.alarms_view_model.get_table_entries():
            self.alarms_table.insert('', END, values=tuple(item))

    def open_alarm_popup(self, alarm: Alarm) -> None:
        """
        This method opens a popup displaying details and options for an alarm

        Args:
            alarm (Alarm): the alarm the popup pertains to
        """
        new_window = Toplevel(self.overall_frame)
        new_window.grab_set()
        event = alarm.event
        new_window.title(f'{'[NEW] ' if not alarm.acknowledged else ''}Alarm #{event.id}')
        new_window.geometry('300x300')
        Label(new_window, text=f'Priority: {alarm.priority.value}', anchor='w').pack(fill=BOTH)
        Label(
            new_window, text=f'Criticality: {alarm.criticality.value}', anchor='w'
        ).pack(fill=BOTH)
        Label(new_window, text=f'Registered: {event.register_time.strftime('%Y-%m-%d %H:%M:%S')}',
              anchor='w').pack(fill=BOTH)
        Label(new_window, text=f'Confirmed: {event.confirm_time.strftime('%Y-%m-%d %H:%M:%S')}',
              anchor='w').pack(fill=BOTH)
        Label(new_window, text=f'Type: {event.type}', anchor='w').pack(fill=BOTH)
        Label(new_window).pack()
        Label(new_window, text='Parameters:', anchor='w').pack(fill=BOTH)
        for tag in event.base.tags:
            Label(
                new_window, text=f'- {tag}: {self.dm.parameters[tag].description}', anchor='w'
            ).pack(fill=BOTH)
        Label(new_window).pack()
        Label(new_window, text=f'Description: {event.description}', anchor='w').pack(fill=BOTH)
        buttons = Frame(new_window)
        if not alarm.acknowledged:
            Button(
                buttons, text='Acknowledge', width=12,
                command=lambda: self.acknowledge_alarm(alarm, new_window)
            ).grid(row=0, column=0, padx=10, pady=10)
        Button(
            buttons, text='Remove', width=12, command=lambda: self.remove_alarm(alarm, new_window)
        ).grid(row=0, column=1, padx=10, pady=10)
        buttons.pack(side=BOTTOM)

    def acknowledge_alarm(self, alarm: Alarm, popup: Toplevel) -> None:
        """
        This method handles acknowledging an alarm.

        Args:
            alarm (Alarm): the alarm to acknowledge
            popup (Toplevel): the popup that the alarm acknowledgement happens from,
                closed upon alarm acknowledgement
        """
        self.alarms_view_model.model.request_receiver.acknowledge_alarm(alarm, self.dm)
        popup.destroy()

    def remove_alarm(self, alarm: Alarm, popup: Toplevel) -> None:
        """
        This method handles removing an alarm.

        Args:
            alarm (Alarm): the alarm to remove
            popup (Toplevel): the popup that the alarm removal happens from,
                closed upon alarm removal
        """
        if messagebox.askokcancel(title='Remove alarm', message=f'Remove alarm #{alarm.event.id}?'):
            self.alarms_view_model.model.request_receiver.remove_alarm(alarm, self.dm)
            popup.destroy()

    def alarms_searcher_update(self):
        # Convert to list to enforce ordering
        selected_tags = list(self.alarms_searcher.selected_tags)
        self.alarms_view_model.model.request_receiver.set_shown_tags(selected_tags)
        self.alarms_view_model.model.receive_updates()
        self.alarms_view_model.update_table_entries()
        self.refresh_alarms_table()
