from tkinter import StringVar, Frame, Label, Entry, Button, ttk, NO, END
from typing import Callable

from astra.data.data_manager import DataManager
from astra.data.parameters import Tag
from astra.usecase.dashboard_request_receiver import DashboardRequestReceiver


class TagSearcher:
    """
    Defines a widget that can be used to search through a series of tags and allows the user to
    make selections on those tags for a number of purposes

    :param: search_bar: Contains the text held in the search bar
    :param: search_controller: Defines the controller used to make search requests
    :param: dm: Stores all data known to the program
    :param: shown_tags: An ordered list of tags and their descriptions to show in the search results
    :param: selected_tags: The set of tags selected by the user
    :param: watcher: A arbitrary function with no inputs to call any time a search toggle
    occurs
    :param: tag_table: Represents the area of the screen holding all tags matching search query
    """

    def __init__(self, num_rows: int, frame: Frame, dm: DataManager, watcher: Callable):
        """
        Sets up all visual elements of the searcher

        :param num_rows: Used for resolution scaling
        :param frame: The frame to insert this widget into
        :param dm: Contains all data known to the program
        :param watcher: The watcher function to call on toggle
        """

        # elements of dashboard_frame
        self.search_bar = StringVar()
        self.search_controller = DashboardRequestReceiver()
        self.dm = dm

        self.shown_tags = self.search_controller.search_tags("", self.dm)
        self.selected_tags = set(self.dm.tags)

        self.watcher = watcher

        filter_tags = Frame(frame)
        filter_tags.config(background='#fff')
        filter_tags.grid_columnconfigure(0, weight=1)
        filter_tags.grid_columnconfigure(1, weight=1)

        for i in range(num_rows):
            filter_tags.grid_rowconfigure(i, weight=1)

        filter_tags.grid(sticky='NSEW', row=0, column=0, rowspan=num_rows - 1, padx=(0, 3))
        Label(filter_tags, text=self.get_label_text(), background='#fff').grid(
            sticky='NSEW', row=0, column=0, columnspan=2)
        tag_search_area = Frame(filter_tags)
        tag_search_area.config(background='#fff')
        tag_search_area.grid_columnconfigure(0, weight=1)
        tag_search_area.grid_columnconfigure(1, weight=3)
        tag_search_area.grid(sticky='NSEW', row=1, column=0, columnspan=2)

        Label(tag_search_area, text="Search", background='#fff').grid(sticky='NSEW', row=0,
                                                                      column=0)
        Entry(tag_search_area, textvariable=self.search_bar).grid(sticky='NSEW', row=0, column=1)
        self.search_bar.trace_add("write", self.search_bar_change)

        (Button(filter_tags, text="Check all search results",
                wraplength=80, command=self.select_all_tags).grid(row=2, column=0, rowspan=2))
        (Button(filter_tags, text="Uncheck all search results",
                wraplength=80, command=self.deselect_all_tags).grid(row=2, column=1, rowspan=2))

        tag_table = ttk.Treeview(filter_tags, show='tree')
        tag_table_scroll = ttk.Scrollbar(filter_tags, orient="vertical", command=tag_table.yview)
        tag_table.configure(yscrollcommand=tag_table_scroll.set)
        tag_table_scroll.grid(sticky='NS', row=4, column=2, rowspan=num_rows - 4)
        self.tag_table = tag_table
        tag_table['columns'] = ("tag",)
        tag_table.column("#0", width=0, stretch=NO)
        tag_table.column("tag")
        tag_table.grid(sticky='NEWS', row=4, column=0, columnspan=2, rowspan=num_rows - 4)
        tag_table.bind('<ButtonRelease-1>', self.toggle_tag_table_row)

    def get_label_text(self) -> str:
        """Returns an appropriate descriptor for this search widget"""
        return "Parameters to display"

    def search_bar_change(self, *args) -> None:
        """
        Updates available tag results upon any keystroke to the search bar

        :param args: required by trace update, not used in the function
        """
        del args
        self.shown_tags = self.search_controller.search_tags(self.search_bar.get(), self.dm)
        self.update_searched_tags()

    def update_searched_tags(self) -> None:
        """
        Updates the actual view of tag results
        """
        # Refreshing the table
        for tag in self.tag_table.get_children():
            self.tag_table.delete(tag)
        # Inserting rows based on what tags match search query and if they were toggled or not
        for tag in self.shown_tags:
            check = " "
            tag_index = tag.index(':')
            if tag[:tag_index] in self.selected_tags:
                check = "x"
            self.tag_table.insert("", END, values=(f"[{check}] {tag}",))

    def toggle_tag_table_row(self, event) -> None:
        """
        Toggles the selected tag as being either on/off

        :param event: Used by the Treeview callee, not used by function
        """
        del event
        cur_item = self.tag_table.focus()

        # Getting the actual string representation of the table entry
        try:
            tag_str = self.tag_table.item(cur_item)['values'][0][4:]
        except IndexError:
            # Do nothing
            return

        # Getting the actual tag name from the row string
        tag_info = Tag(tag_str)
        tag_index = tag_info.index(':')
        tag = tag_info[:tag_index]

        # Indicating tag is not selected
        if tag in self.selected_tags:
            self.selected_tags.remove(Tag(tag))
        else:
            # Indicating tag is now selected
            self.selected_tags.add(Tag(tag))
        self.update_searched_tags()
        self.watcher()

    def select_all_tags(self) -> None:
        """
        Force selects every single tag, not just shown ones
        """

        # Iterate through all shown tags and force choose them
        for tag_info in self.shown_tags:
            tag_index = tag_info.index(':')
            self.selected_tags.add(Tag(tag_info[:tag_index]))
        self.update_searched_tags()
        self.watcher()

    def deselect_all_tags(self) -> None:
        """
        Force de-selects all tags, not just shown ones
        """
        # Clone the toggled tags, as it will mutate
        for tag_info in self.shown_tags:
            tag_index = tag_info.index(':')
            if tag_info[:tag_index] in self.selected_tags:
                self.selected_tags.remove(Tag(tag_info[:tag_index]))
        self.update_searched_tags()
        self.watcher()


class AlarmTagSearcher(TagSearcher):
    """
    A child class of TagSearcher helping distinguish certain shown text
    """

    def __init__(self, num_rows: int, frame: Frame, dm: DataManager, watcher: Callable):
        super().__init__(num_rows, frame, dm, watcher)

    def get_label_text(self) -> str:
        return "Filter Parameters"


class GraphingTagSearcher(TagSearcher):
    """
    A child class of TagSearcher helping distinguish certain shown text
    """

    def __init__(self, num_rows: int, frame: Frame, dm: DataManager, watcher: Callable):
        super().__init__(num_rows, frame, dm, watcher)
        self.tag_description_lookup = dict()

        for tag in self.shown_tags:
            tag_index = tag.index(':')
            self.tag_description_lookup[tag[:tag_index]] = tag

    def get_label_text(self) -> str:
        return "Select Parameters to Graph"
