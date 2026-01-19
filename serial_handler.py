import queue
import serial
import threading
from queue import Queue
from typing import Callable

class SerialHandler:
    def __init__(self):
        self.serial_port: serial.Serial | None = None
        self.w_queue: Queue[str] = Queue()
        self.running: bool = False

        # Callbacks
        self.on_data: Callable[[str], None] | None = None
        self.on_error: Callable[[Exception], None] | None = None
        self.on_connect: Callable[[], None] | None = None
        self.on_disconnect: Callable[[], None] | None = None

    @property
    def is_connected(self) -> bool:
        return self.serial_port is not None and self.serial_port.is_open

    def connect(self, port: str, baudrate: int = 115200):
        try:
            self.serial_port = serial.Serial(port, baudrate, timeout=0.5)
            self.running = True
            threading.Thread(target=self._read_thread, daemon=True).start()
            threading.Thread(target=self._write_thread, daemon=True).start()
            if self.on_connect:
                self.on_connect()
        except Exception as e:
            if self.on_error:
                self.on_error(e)

    def disconnect(self):
        self.running = False
        if self.serial_port:
            self.serial_port.close()
            self.serial_port = None
        if self.on_disconnect:
            self.on_disconnect()

    def send(self, data: str):
        if not self.is_connected:
            return
        self.w_queue.put(item=data, block=True, timeout=5)

    def _read_thread(self):
        while self.running and self.serial_port:
            try:
                data = self.serial_port.read_all()
                if data:
                    decoded = data.decode('utf-8', errors='ignore')
                    if self.on_data:
                        self.on_data(decoded)
            except Exception as e:
                if self.on_error:
                    self.on_error(e)

    def _write_thread(self):
        while self.running and self.serial_port:
            try:
                data = self.w_queue.get(timeout=0.1)
                _ = self.serial_port.write(data.encode())
            except queue.Empty:
                continue
            except Exception as e:
                if self.on_error:
                    self.on_error(e)

