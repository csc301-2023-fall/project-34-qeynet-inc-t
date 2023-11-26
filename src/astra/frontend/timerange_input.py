"""This module provides a "widget" for selecting datetime ranges."""

import string
import tkinter
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from tkinter import Button, Entry, Frame, Label
from tkinter import StringVar, messagebox
from tkinter import LEFT


def _format_time(time: datetime | None) -> str:
    # Format time, either as YYYY-MM-DD hh:mm:ss or as '---' for None.
    return time.strftime('%Y-%m-%d %H:%M:%S') if time is not None else '---'


def _is_short_digit_string(s: str, max_length: int) -> bool:
    # Return whether s consists of at most max_length digits.
    return len(s) <= max_length and all(c in string.digits for c in s)


class OperationControl(Enum):
    """A value representing whether to proceed with an operation."""
    CONTINUE = True
    CANCEL = False


type ChangeCallback = Callable[[datetime | None, datetime | None], OperationControl]


class TimerangeInput(Frame):
    """A frame displaying a timerange, with a button for changing the timerange."""
    caption: str
    start_time: datetime | None
    end_time: datetime | None
    onchange: ChangeCallback

    def __init__(self, parent: tkinter.Misc, caption: str, onchange: ChangeCallback):
        """
        Construct a new TimerangeInput.

        :param parent:
            The container for this TimerangeInput.
        :param caption:
            A label to explain what the timerange pertains to.
            Will be incorporated as:
                {caption}: from {start time} to {end time} [change timerange button]
        :param onchange:
            A function to call upon setting a valid timerange.
            Should take (start time, end time) and return an OperationControl
            indicating whether to actually set the timerange --
            there may be additional reasons to reject an otherwise valid timerange.
        """
        super().__init__(parent)
        self.caption = caption
        self.onchange = onchange
        self.timerange_label = Label(self)
        self.update_timerange(None, None)
        self.timerange_label.pack(side=LEFT)
        Button(self, text='Change...', command=self.open_set_timerange_popup).pack(side=LEFT)

    def update_timerange(self, start_time: datetime | None, end_time: datetime | None) -> None:
        """
        Set the timerange for this TimerangeInput and update the timerange label accordingly.

        :param start_time:
            Start time to set. When None, the timerange includes arbitrarily early times.
        :param end_time:
            End time to set. When None, the timerange includes arbitrarily late times.
        """
        self.start_time = start_time
        self.end_time = end_time
        self.timerange_label['text'] = (
            f'{self.caption}: from {_format_time(start_time)} to {_format_time(end_time)} '
        )

    def open_set_timerange_popup(self) -> None:
        """Open a SetTimerangePopup for this TimerangeInput."""
        SetTimerangePopup(self).grab_set()


class SetTimerangePopup(tkinter.Toplevel):
    """A popup window to facilitate setting the timerange for a TimerangeInput."""
    timerange_input: TimerangeInput
    start_time_vars: list[StringVar]
    end_time_vars: list[StringVar]

    def __init__(self, timerange_input: TimerangeInput):
        """
        Construct a new popup.

        :param timerange_input:
            The TimerangeInput that this popup pertains to.
        """
        super().__init__()
        self.timerange_input = timerange_input
        self.start_time_vars = []
        self.end_time_vars = []
        Label(self, text='From: ').grid(row=0, column=0, sticky='W')
        Label(self, text='To: ').grid(row=1, column=0, sticky='W')
        for row, time_vars in enumerate([self.start_time_vars, self.end_time_vars]):
            time_display_frame = Frame(self)
            for element in [4, '-', 2, '-', 2, ' ', 2, ':', 2, ':', 2, ' ']:
                if isinstance(element, int):
                    time_var = StringVar()
                    time_vars.append(time_var)
                    time_entry = Entry(time_display_frame, textvariable=time_var, width=element)
                    time_entry.configure(validate='key', validatecommand=(time_entry.register(
                        lambda s, max_length=element: _is_short_digit_string(s, max_length)
                    ), '%P'))
                    time_entry.pack(side=LEFT)
                else:
                    Label(time_display_frame, text=element).pack(side=LEFT)
            time_display_frame.grid(row=row, column=1)
        self.set_time(self.timerange_input.start_time, self.start_time_vars)
        self.set_time(self.timerange_input.end_time, self.end_time_vars)
        Button(
            self, text='Clear', command=lambda: self.set_time(None, self.start_time_vars)
        ).grid(row=0, column=2)
        Button(
            self, text='Clear', command=lambda: self.set_time(None, self.end_time_vars)
        ).grid(row=1, column=2)
        set_timerange_button = Button(self, text='Set time range', command=self.set_timerange)
        set_timerange_button.grid(row=2, columnspan=3)

    @staticmethod
    def set_time(time: datetime | None, time_vars: list[StringVar]) -> None:
        """
        Set the text fields for a time input according to the given time.

        :param time:
            The time that the text fields should be set to.
        :param time_vars:
            A list of time StringVars for the corresponding set of text fields.
        """
        values = ([format(value, '04' if i == 0 else '02') for i, value in enumerate([
            time.year, time.month, time.day, time.hour, time.minute, time.second
        ])] if time is not None else [''] * 6)
        for value, time_var in zip(values, time_vars):
            time_var.set(value)

    def set_timerange(self) -> None:
        """Actually perform the action of setting a timerange."""
        times = [None, None]
        for i, (time_vars, time_type_capitalized, time_type_lowercase) in enumerate([
            (self.start_time_vars, 'Start', 'start'), (self.end_time_vars, 'End', 'end')
        ]):
            if all(not time_var.get() for time_var in time_vars):
                times[i] = None
            elif any(not time_var.get() for time_var in time_vars):
                messagebox.showwarning(title=f'Incomplete {time_type_lowercase} time', message=(
                    f'{time_type_capitalized} time must either be '
                    'completely filled or completely empty.'
                ))
                return
            else:
                year, month, day, hour, minute, second = [
                    int(time_var.get()) for time_var in time_vars
                ]
                try:
                    times[i] = datetime(year, month, day, hour, minute, second)
                except ValueError:
                    messagebox.showwarning(title=f'Invalid {time_type_lowercase} time', message=(
                        f'{year:04}-{month:02}-{day:02} {hour:02}:{minute:02}:{second:02}'
                        ' is not a valid time.'
                    ))
                    return
        start_time, end_time = times
        if self.timerange_input.onchange(start_time, end_time) is OperationControl.CONTINUE:
            self.destroy()
            self.timerange_input.update_timerange(start_time, end_time)
