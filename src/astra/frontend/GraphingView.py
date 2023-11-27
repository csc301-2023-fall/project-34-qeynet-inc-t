from datetime import datetime
from tkinter import ttk, Frame, Label, StringVar, Button
from tkinter.ttk import Combobox

from astra.data.data_manager import DataManager
from astra.frontend.tag_searcher import GraphingTagSearcher
from astra.frontend.timerange_input import TimerangeInput, OperationControl
from astra.usecase.graphing_request_receiver import GraphingRequestReceiver


class GraphingView:
    def __init__(self, frame: ttk.Notebook, num_rows: int, dm: DataManager):
        self.overall_frame = Frame(frame)
        self.controller = GraphingRequestReceiver()

        for i in range(num_rows):
            self.overall_frame.grid_rowconfigure(i, weight=1)
        # Ratio determines weighting on tag searcher vs the rest of the tab
        self.overall_frame.grid_columnconfigure(0, weight=1)
        self.overall_frame.grid_columnconfigure(1, weight=10)

        self.searcher = GraphingTagSearcher(num_rows, self.overall_frame, dm, self.searcher_update)

        graphing_frame = Frame(self.overall_frame)
        graphing_frame.grid(sticky="news", row=0, column=1)

        graphing_time_option = Frame(graphing_frame)
        graphing_time_option.grid(sticky="news", row=0, column=0)

        TimerangeInput(
            graphing_time_option, 'Time range', self.times_update
        ).grid(row=0, column=0, padx=20, pady=20)

        graphing_region = Frame(graphing_frame)
        graphing_region.grid(sticky="news", row=1, column=0)

        y_axis_selection_region = Frame(graphing_frame)
        y_axis_selection_region.grid(sticky="news", row=2, column=0)

        y_axis_label = Label(y_axis_selection_region, text="y-axis labels:")
        y_axis_label.grid(row=0, column=0, padx=5, pady=20)

        self.y_axis_selection_text = StringVar()
        self.y_axis_selector = Combobox(y_axis_selection_region,
                                        textvariable=self.y_axis_selection_text)
        self.y_axis_selector.grid(row=0, column=1, padx=5, pady=20)

        button_selection_region = Frame(graphing_frame)
        button_selection_region.grid(sticky="nes", row=3, column=0, padx=20, pady=20)

        export_graph_button = Button(button_selection_region, text="Export Graph", command=self.export_graph)
        export_graph_button.grid(row=0, column=0)

        export_data_button = Button(button_selection_region, text="Export Data", command=self.export_data)
        export_data_button.grid(row=0, column=1, padx=20, pady=20)

        self.searcher.deselect_all_tags()

    def searcher_update(self):
        selected_tags = self.searcher.selected_tags
        detailed_tags = []
        for tag in selected_tags:
            detailed_tags.append(self.searcher.tag_description_lookup[tag])
        detailed_tags.sort()

        self.y_axis_selector['values'] = detailed_tags

        selected_value = self.y_axis_selection_text.get()
        if len(selected_value) > 0:
            # If there is a selected value, concatenate selected_value to just the tag
            tag_index = selected_value.index(':')
            selected_value = selected_value[:tag_index]

        if selected_value not in selected_tags and len(detailed_tags) == 0:
            # When there's no options left, reset the entry field
            self.y_axis_selection_text.set('')
        elif selected_value not in selected_tags and len(detailed_tags) > 0:
            # When there's available options and the previous selection was removed, force set
            # the first available option
            self.y_axis_selection_text.set(detailed_tags[0])

        self.controller.set_shown_tags(selected_tags)

    def times_update(self, start_time: datetime | None, end_time: datetime | None):
        self.controller.set_start_date(start_time)
        self.controller.set_end_date(end_time)
        return OperationControl.CONTINUE

    def export_graph(self):
        pass

    def export_data(self):
        pass