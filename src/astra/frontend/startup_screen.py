"""This module provides the GUI for Astra's startup screen."""

from tkinter import Button, Frame, Label, Tk, Toplevel
from tkinter import filedialog, font, messagebox, simpledialog, ttk, Event
from tkinter import BOTTOM, LEFT, X, Y

from astra.data.data_manager import DataManager
from astra.frontend.view import View


class StartupScreen(Tk):
    """The window for the startup screen."""

    def __init__(self):
        """Initialize the screen, adding all the UI elements."""
        super().__init__()
        self.title('Astra')
        self.state('zoomed')

        large_font = font.nametofont('TkDefaultFont').copy()
        large_font.configure(size=large_font['size'] * 3)
        Label(self, text='Astra', font=large_font).pack()
        header_frame = Frame(self)
        Label(header_frame, text='Devices ').pack(side=LEFT)
        Button(header_frame, text='Add device...', command=self.add_device).pack(side=LEFT)
        header_frame.pack(fill=X)
        device_table_frame = Frame(self)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview.Heading', background='#ddd', font=('TkDefaultFont', 10, 'bold'))
        self.device_table = ttk.Treeview(
            device_table_frame, columns=['name', 'description'], show='headings'
        )
        self.device_table.column('description', width=1000)
        self.device_table.heading('name', text='Name')
        self.device_table.heading('description', text='Description')
        device_table_scrollbar = ttk.Scrollbar(
            device_table_frame, orient='vertical', command=self.device_table.yview
        )
        self.device_table.configure(yscrollcommand=device_table_scrollbar.set)
        self.device_table.bind('<Double-1>', self.double_click_device_table_row)
        for device in DataManager.get_devices().values():
            self.device_table.insert('', 'end', values=[device.name, device.description])
        self.device_table.pack(side=LEFT, fill=X, expand=True)
        device_table_scrollbar.pack(side=LEFT, fill=Y)
        device_table_frame.pack(fill=X)

    def add_device(self) -> None:
        """Let the user add a device, and update the table of devices accordingly."""
        config_path = filedialog.askopenfilename(title='Select new device config file')
        if not config_path:
            return
        devices_before = set(DataManager.get_devices().values())
        try:
            DataManager.add_device(config_path)
        except Exception as e:
            messagebox.showerror(title='Cannot read config', message=f'{type(e).__name__}: {e}')
            return
        devices_after = set(DataManager.get_devices().values())
        if devices_before == devices_after:  # Guard against adding an already-added device
            return
        [new_device] = devices_after - devices_before
        self.device_table.insert('', 'end', values=[new_device.name, new_device.description])
        messagebox.showinfo(
            title='Device added', message=f'Successfully added device {repr(new_device.name)}.'
        )

    def double_click_device_table_row(self, event: Event) -> None:
        """
        Handle a double click on the table of devices.

        :param event:
            The event associated with the double click action.
        """
        cur_item = self.device_table.focus()

        region = self.device_table.identify('region', event.x, event.y)
        if cur_item and region != 'heading':
            self.open_device_popup(cur_item)

    def open_device_popup(self, item: str) -> None:
        """
        Open a popup for a user-selected device.

        :param item:
            The item double-clicked by the user.
        """
        name, description = self.device_table.item(item)['values']
        popup = Toplevel()
        popup.grab_set()
        popup.geometry('500x200')
        Label(popup, text=f'Device: {name}').pack(anchor='w')
        Label(popup, text=f'Description: {description}').pack(anchor='w')
        Button(popup, text='Monitor', width=15, height=3, command=lambda: self.monitor(name)).pack(
            expand=True
        )
        Button(popup, text='Remove', command=lambda: self.remove_device(name, item)).pack(
            side=BOTTOM
        )

    def monitor(self, device_name: str) -> None:
        """
        Launch the application proper, monitoring the given device.

        :param device_name:
            The name of the selected device.
        """
        self.destroy()
        View(device_name).mainloop()

    def remove_device(self, device_name: str, item: str) -> None:
        """
        Let the user remove a device, and update the table of devices accordingly.

        :param device_name:
            The name of the device to remove.
        :param item:
            The corresponding item to remove from the table of devices.
        """
        if messagebox.askokcancel(
            title='Remove device?',
            message=(
                f'Delete device {repr(device_name)} and all of its data? '
                'This action cannot be undone.'
            ),
        ):
            entered_device_name = simpledialog.askstring(
                title=f'Confirm deletion of device {repr(device_name)}',
                prompt='To confirm deletion, please enter the name of the device.',
            )
            if entered_device_name == device_name:
                DataManager.remove_device(device_name)
                self.device_table.delete(item)
                messagebox.showinfo(
                    title='Device removed',
                    message=f'Successfully removed device {repr(device_name)}.',
                )
            elif entered_device_name is not None:
                messagebox.showinfo(
                    title='Incorrect device name',
                    message='Entered name does not match device name. Deletion canceled.',
                )
            else:
                messagebox.showinfo(title='Deletion canceled', message='Deletion canceled.')
