"""
This file contains helper functions that view.py may use
"""

from tkinter import Frame, Label


def draw_status(status_frame, descriptions):
    """
    Draws the status frame of the dashboard

    Args:
        status_frame: frame of the status
        descriptions: content to be displayed in the frame
    """

    # Wipe the frame first
    for widget in status_frame.winfo_children():
        widget.destroy()

    for i in range(len(descriptions)):
        frameview_block_frame = Frame(status_frame)
        frameview_block_frame.grid(sticky="W", row=i, column=0)
        for line in descriptions[i]:
            description_label = Label(frameview_block_frame, text=line)
            description_label.pack()


def draw_warnings(warnings_frame, descriptions):
    """
    Draws the warnings frame of the dashboard
    Assumes warnings are sorted by critical first

    Args:
        warnings_frame: frame for warnings
        descriptions: informations for what to go in the warnings
    """

    # Wipe the frame first
    for widget in warnings_frame.winfo_children():
        widget.destroy()

    for i in range(len(descriptions)):
        # Detect criticality, style the frame accordingly
        color = None
        if descriptions[i][0] == "Critical":
            color = "red"
        else:
            color = "yellow"

        # create subframe
        warning_block_frame = Frame(warnings_frame, bg=color)
        warning_block_frame.grid(sticky="W", row=i, column=0)

        for j in range(len(descriptions[i])):
            description_label = Label(warning_block_frame, text=descriptions[i][j], bg=color)
            description_label.grid(sticky="W", row=0, column=j)


def draw_frameview(frameview_frame, descriptions):
    """
    Fuctions related to rendering elements of the frameview
    Takes a tkinter Frame, and a 2d array of label strings
    Can be called whenever an update is required

    Args:
        frameview_frame (_type_): tkinter frame
        descriptions (_type_): list of lists to display
    """

    # Wipe the frame first
    for widget in frameview_frame.winfo_children():
        widget.destroy()

    for i in range(len(descriptions)):
        frameview_block_frame = Frame(frameview_frame)
        frameview_block_frame.grid(sticky="W", row=i, column=0)
        for line in descriptions[i]:
            description_label = Label(frameview_block_frame, text=line)
            description_label.pack()
