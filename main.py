import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable
import sv_ttk
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


class App:
    def __init__(self, root: tk.Tk):
        self.root: tk.Tk = root
        self.root.title("GDiags")

        self.serial: SerialHandler = SerialHandler()
        self.serial.on_data = self._on_serial_data
        self.serial.on_error = self._on_error

        axis_frame = ttk.Frame(root)
        axis_frame.pack(pady=10, padx=10)
        self.axis1: AxisControl = AxisControl(axis_frame, "Axis 1", self.serial.send, ["m", "a"])
        self.axis1.pack(side=tk.LEFT, padx=5)
        self.axis2: AxisControl = AxisControl(axis_frame, "Axis 2", self.serial.send, ["m", "b"])
        self.axis2.pack(side=tk.LEFT, padx=5)
        self.axis3: AxisControl = AxisControl(axis_frame, "Axis 3", self.serial.send, ["m", "c"])
        self.axis3.pack(side=tk.LEFT, padx=5)
        self.axis4: AxisControl = AxisControl(axis_frame, "Axis 4", self.serial.send, ["m", "d"])
        self.axis4.pack(side=tk.LEFT, padx=5)

        self.terminal: Terminal = Terminal(root, self.serial.send)
        self.terminal.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.serial.connect("/dev/pts/6")

    def _on_serial_data(self, data: str):
        _ = self.root.after(0, lambda: self.terminal.append(data))

    def _on_error(self, e: Exception):
        _ = self.root.after(0, lambda: self.terminal.append(f"Diags App Error: {e}\n"))

root = tk.Tk()
sv_ttk.set_theme("dark")
app = App(root)
root.mainloop()

