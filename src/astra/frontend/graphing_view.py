from datetime import datetime
from tkinter import ttk, Frame, Label, StringVar, Button, CENTER
from tkinter.ttk import Combobox
import matplotlib as mpl
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from astra.data.data_manager import DataManager
from astra.frontend.tag_searcher import GraphingTagSearcher
from astra.frontend.timerange_input import TimerangeInput, OperationControl
from astra.usecase.graphing_request_receiver import GraphingRequestReceiver

mpl.use("TkAgg")


class GraphingView:
    """
    Defines the actual view and some minor logic for the graphing tab

    :param dm: Contains all data known to the program
    :param overall_frame: Contains all visual aspects of the view
    :param controller: Interface for backend requests
    :param searcher: The tag searcher used to select parameters to plot
    :param figure: The actual graphing data to be shown
    :param figure_canvas: A canvas to display <cls.figure> on
    :param y_axis_selection_text: Contains the most recently selected y-axis selection option
    :param y_axis_selector: Allows user to select a tag to use for y-axis values
    """

    def __init__(self, frame: ttk.Notebook, num_rows: int, dm: DataManager):
        """
        Initializes the view of the tab

        :param frame: The Notebook to insert this frame under
        :param num_rows: Used for resolution scaling
        :param dm: Contains all data known to the program
        """
        self.dm = dm
        self.overall_frame = Frame(frame)
        self.controller = GraphingRequestReceiver()

        # Ratio determines weighting on tag searcher vs the rest of the tab
        self.overall_frame.grid_columnconfigure(0, weight=1)
        self.overall_frame.grid_columnconfigure(1, weight=10)

        self.searcher = GraphingTagSearcher(num_rows, self.overall_frame, dm, self.searcher_update)

        # Creating the region for all UI options excluding tag searcher
        graphing_frame = Frame(self.overall_frame)
        graphing_frame.grid(sticky="news", row=0, column=1)

        # Creating time selection UI
        graphing_time_option = Frame(graphing_frame)
        graphing_time_option.grid(sticky="news", row=0, column=0)

        time_input = TimerangeInput(graphing_time_option, 'Time range', self.times_update)
        time_input.grid(row=0, column=0, padx=20, pady=20,)

        # Creating graphing region UI
        graphing_region = Frame(graphing_frame)
        graphing_region.grid(row=1, column=0)

        self.figure = Figure(figsize=(4, 4), dpi=100)
        self.figure_canvas = FigureCanvasTkAgg(self.figure, graphing_region)

        NavigationToolbar2Tk(self.figure_canvas)

        # Creating the combobox to select y-axis values
        y_axis_selection_region = Frame(graphing_frame)
        y_axis_selection_region.grid(row=2, column=0)

        y_axis_label = Label(y_axis_selection_region, text="y-axis labels:")
        y_axis_label.grid(row=0, column=0, padx=5, pady=20)

        self.y_axis_selection_text = StringVar()
        self.y_axis_selector = Combobox(y_axis_selection_region,
                                        textvariable=self.y_axis_selection_text)
        self.y_axis_selector.grid(row=0, column=1, padx=5, pady=20)

        # Creating region for export data button
        button_selection_region = Frame(graphing_frame)
        button_selection_region.grid(sticky="nes", row=3, column=0, padx=20, pady=20)

        export_data_button = Button(button_selection_region, text="Export Data",
                                    command=self.export_data)
        export_data_button.grid(row=0, column=1, padx=20, pady=20)

        self.searcher.deselect_all_tags()

    def searcher_update(self) -> None:
        """
        Once tag toggles have changed, reconstructs UI options surrounding graph
        """
        # Creating a list of values to show in the combobox
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
        self.create_graph()

    def times_update(self, start_time: datetime | None, end_time: datetime | None) -> (
            OperationControl):
        """
        Changes filtering for times once the user changes their input

        :param start_time: The minimum time to show in the graph
        :param end_time:  The maximum time to show in the graph
        :return: Whether to proceed with operations
        """
        self.controller.set_start_date(start_time)
        self.controller.set_end_date(end_time)
        self.create_graph()
        return OperationControl.CONTINUE

    def export_data(self) -> None:
        pass

    def create_graph(self) -> None:
        """
        Constructs the graph according to previous user inputs
        """
        self.figure.clear()
        graph_data = self.controller.create(self.dm)
        shown_tags = graph_data.shown_tags

        for tag in shown_tags:
            timestamp_info = graph_data.shown_tags[tag][0]
            param_info = graph_data.shown_tags[tag][1]

            new_plot = self.figure.add_subplot(111)
            new_plot.plot(timestamp_info, param_info)

        self.figure_canvas.draw()
        self.figure_canvas.get_tk_widget().pack()
