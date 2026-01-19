import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable
import sv_ttk
import serial.tools.list_ports
from serial_handler import SerialHandler

class AxisControl(ttk.LabelFrame):
    def __init__(self, parent: ttk.Widget | ttk.Frame, label: str, on_send: Callable[[str], None], menu_access: list[str]):
        super().__init__(parent, text=label, padding=10)

        self.on_send: Callable[[str], None] = on_send
        self.menu_access: list[str] = menu_access

        radio_frame = ttk.Frame(self)
        radio_frame.pack(pady=(0, 5))

        self.pid_var: tk.StringVar = tk.StringVar(value="P")
        for option in ["P", "I", "D"]:
            ttk.Radiobutton(radio_frame, text=option, value=option, variable=self.pid_var).pack(side=tk.LEFT, padx=3)

        input_frame = ttk.Frame(self)
        input_frame.pack()

        self.input: ttk.Entry = ttk.Entry(input_frame, width=20)
        self.input.pack(side=tk.LEFT, padx=(0, 5))
        _ = self.input.bind("<Return>", lambda e: self._send())

        self.send_btn: ttk.Button = ttk.Button(input_frame, text="Send", command=self._send)
        self.send_btn.pack(side=tk.LEFT)

    def _send(self):
        value = self.input.get()
        if not value:
            return

        try:
            _ = int(value)
        except ValueError:
            _ = messagebox.showerror("Invalid Input", "Only integer values accepted")
            return

        for menu_cmd in self.menu_access:
            self.on_send(menu_cmd)
        self.on_send(f"{self.pid_var.get()}{value}")
        self.input.delete(0, tk.END)


class Terminal(ttk.Frame):
    def __init__(self, parent: tk.Tk | tk.Widget, on_send: Callable[[str], None], height: int = 20, width: int = 80, max_lines: int = 1000):
        super().__init__(parent)

        self.on_send: Callable[[str], None] = on_send
        self.max_lines: int = max_lines

        self.text: tk.Text = tk.Text(self, height=height, width=width)
        self.text.pack(fill=tk.BOTH, expand=True)
        _ = self.text.bind("<Key>", self._on_keypress)

    def _on_keypress(self, event: tk.Event) -> str:
        if event.char and event.char != "\x08":
            self.on_send(event.char)
        elif event.keysym == "Return":
            self.on_send("\r")
        return "break"

    def append(self, data: str):
        data = data.replace("\r\n", "\n").replace("\r", "\n")
        self.text.insert(tk.END, data)

        line_count = int(self.text.index("end-1c").split(".")[0])
        if line_count > self.max_lines:
            self.text.delete("1.0", f"{line_count - self.max_lines}.0")

        self.text.see(tk.END)


class ConnectionManager(ttk.Frame):
    def __init__(self, parent: tk.Widget, serial_handler: SerialHandler):
        super().__init__(parent, padding=10)

        self.serial: SerialHandler = serial_handler
        self.serial.on_connect = self._on_connect
        self.serial.on_disconnect = self._on_disconnect

        port_frame = ttk.Frame(self)
        port_frame.pack(fill=tk.X, pady=5)

        ttk.Label(port_frame, text="Port:").pack(side=tk.LEFT, padx=(0, 5))
        self.port_var: tk.StringVar = tk.StringVar()
        self.port_combo: ttk.Combobox = ttk.Combobox(port_frame, textvariable=self.port_var, width=20)
        self.port_combo.pack(side=tk.LEFT, padx=(0, 5))

        self.refresh_btn: ttk.Button = ttk.Button(port_frame, text="Refresh", command=self._refresh_ports)
        self.refresh_btn.pack(side=tk.LEFT)

        baud_frame = ttk.Frame(self)
        baud_frame.pack(fill=tk.X, pady=5)

        ttk.Label(baud_frame, text="Baud:").pack(side=tk.LEFT, padx=(0, 5))
        self.baud_var: tk.StringVar = tk.StringVar(value="115200")
        self.baud_entry: ttk.Entry = ttk.Entry(baud_frame, textvariable=self.baud_var, width=10)
        self.baud_entry.pack(side=tk.LEFT)

        self.connect_btn: ttk.Button = ttk.Button(self, text="Connect", command=self._toggle_connection)
        self.connect_btn.pack(pady=10)

        self._refresh_ports()

    def _refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo["values"] = ports
        if ports and not self.port_var.get():
            self.port_var.set(ports[0])

    def _toggle_connection(self):
        if self.serial.is_connected:
            self.serial.disconnect()
        else:
            port = self.port_var.get()
            try:
                baud = int(self.baud_var.get())
            except ValueError:
                _ = messagebox.showerror("Invalid Baud Rate", "Only integer values accepted")
                return
            if port:
                self.serial.connect(port, baud)

    def _on_connect(self):
        _ = self.connect_btn.config(text="Disconnect")
        _ = self.port_combo.config(state="disabled")
        _ = self.baud_entry.config(state="disabled")
        _ = self.refresh_btn.config(state="disabled")

    def _on_disconnect(self):
        _ = self.connect_btn.config(text="Connect")
        _ = self.port_combo.config(state="normal")
        _ = self.baud_entry.config(state="normal")
        _ = self.refresh_btn.config(state="normal")


class App:
    def __init__(self, root: tk.Tk):
        self.root: tk.Tk = root
        self.root.title("GDiags")

        self.serial: SerialHandler = SerialHandler()
        self.serial.on_data = self._on_serial_data
        self.serial.on_error = self._on_error

        tabs = ttk.Notebook(root)
        tabs.pack(pady=10, padx=10, fill=tk.X)

        connection_tab = ttk.Frame(tabs)
        tabs.add(connection_tab, text="Connection")

        self.connection: ConnectionManager = ConnectionManager(connection_tab, self.serial)
        self.connection.pack(pady=10, padx=10)

        axes_tab = ttk.Frame(tabs)
        tabs.add(axes_tab, text="Axes")
        axis_frame = ttk.Frame(axes_tab)
        axis_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.axis1: AxisControl = AxisControl(axis_frame, "Axis 1", self.serial.send, ["m", "a"])
        self.axis1.pack(side=tk.LEFT, padx=5)
        self.axis2: AxisControl = AxisControl(axis_frame, "Axis 2", self.serial.send, ["m", "b"])
        self.axis2.pack(side=tk.LEFT, padx=5)
        self.axis3: AxisControl = AxisControl(axis_frame, "Axis 3", self.serial.send, ["m", "c"])
        self.axis3.pack(side=tk.LEFT, padx=5)
        self.axis4: AxisControl = AxisControl(axis_frame, "Axis 4", self.serial.send, ["m", "d"])
        self.axis4.pack(side=tk.LEFT, padx=5)

        utils_tab = ttk.Frame(tabs)
        tabs.add(utils_tab, text="Utils")

        placeholder = ttk.LabelFrame(utils_tab, text="Utils", padding=10)
        placeholder.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.terminal: Terminal = Terminal(root, self.serial.send)
        self.terminal.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    def _on_serial_data(self, data: str):
        _ = self.root.after(0, lambda: self.terminal.append(data))

    def _on_error(self, e: Exception):
        _ = self.root.after(0, lambda: self.terminal.append(f"Diags App Error: {e}\n"))

root = tk.Tk()
sv_ttk.set_theme("dark")
app = App(root)
root.mainloop()

