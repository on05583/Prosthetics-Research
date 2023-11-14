import argparse
import asyncio
import queue
import sys
import threading
import time
from pprint import pprint

import aioconsole
import keyboard
import numpy as np
from brainflow.board_shim import (
    BoardIds,
    BoardShim,
    BrainFlowInputParams,
    BrainFlowPresets,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

from bleak import BleakClient, BleakScanner, BLEDevice

data_queue = queue.Queue()

class TimerThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.start_time = None
        self.elapsed_time = 0
        self.running = False

    def run(self):
        self.running = True
        self.start_time = time.time()
        while self.running:
            self.elapsed_time = time.time() - self.start_time
            time.sleep(0.01)  # small sleep to prevent high CPU usage

    def stop(self):
        self.running = False

    def get_elapsed_time(self):
        return self.elapsed_time

class IntegerHolder:
    def __init__(self, value=0):
        self._value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if isinstance(new_value, int):
            self._value = new_value
        else:
            raise ValueError("Value must be an integer")
        
class ApplicationWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()

        self.main_widget = QWidget(self)
        layout = QVBoxLayout(self.main_widget)
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        layout.addWidget(self.canvas)
        self.main_widget.setLayout(layout)

        self.setCentralWidget(self.main_widget)
        self.setWindowTitle("Real-Time Plot")

        self.timer = QTimer(self)
        self.timer.setInterval(5)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()

    def update_plot(self):
        for i in range(0, 10):
            if not data_queue.empty():
                data = data_queue.get()
                self.canvas.plot_data(data)


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=200):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        self.line, = self.axes.plot([], [], 'r-')
        super().__init__(self.fig)

        self.x_data, self.y_data = [], []
        self.window_size = 200

        self.axes.set_autoscale_on(False)
        self.axes.set_ylim(1000, -1000) 

    def plot_data(self, data):
        x, y = data

        self.x_data.append(x)
        self.y_data.append(y)

        if len(self.x_data) > self.window_size:
            self.x_data = self.x_data[-self.window_size:]
            self.y_data = self.y_data[-self.window_size:]

        self.line.set_data(self.x_data, self.y_data)
        self.axes.set_xlim(max(0, self.x_data[0]), self.x_data[-1] + 1)

        self.axes.relim()  # Recalculate limits
        # self.axes.autoscale_view(True, True, True)  # Autoscale

        self.draw_idle()  # Use draw_idle instead of draw for more efficient updates

def launch():
    app = QApplication(sys.argv)
    w = ApplicationWindow()
    w.show()
    sys.exit(app.exec_())


address = ""
read_uuid = "2d30c082-f39f-4ce6-923f-3484ea480596"
write_uuid = "2d30c083-f39f-4ce6-923f-3484ea480596"
SCALE = 0.001869917138805
count = IntegerHolder(0)
timer_thread = TimerThread()

async def callback(sender, data):

    if (len(data) == 20 and data[19] != 0):
        full_int = int.from_bytes(data, 'big')

        mask = (1 << 19) - 1  # 19 bits mask
        num_bits = len(data) * 8

        # TODO: fix noise filtering below

        extracted_bits = (full_int >> (num_bits - 27)) & mask
        extracted_bits *= SCALE
        if extracted_bits < 800 or extracted_bits > 1000:
            count.value += 1
            if count.value % 5 == 0:
                data_queue.put((timer_thread.get_elapsed_time(), extracted_bits))    
            

        extracted_bits = (full_int >> (num_bits - 103)) & mask # skip 84 + 19
        extracted_bits *= SCALE
        if extracted_bits < 800 or extracted_bits > 1000:
            count.value += 1
            if count.value % 5 == 0:
                data_queue.put((timer_thread.get_elapsed_time(), extracted_bits))

async def main(address):
    
    devices = await BleakScanner.discover()
    for d in devices:
        if d.name == "Ganglion-2b18" or d.name == "Simblee":
            address = d.address
            break

    if address == "":
        print("Ganglion not found.")
        return
    else:
        print("Ganglion connected.")
    
    async with BleakClient(address) as client:
        await client.start_notify(read_uuid, callback)
    
        print("Ganglion sending data...")

        await client.write_gatt_char(write_uuid,  bytes("b", "ascii")) 

        print("Data stream started.") 
        timer_thread.start()

        while True:
            input_str = await aioconsole.ainput("Press 'q' to quit: \n")
            if input_str == 'q':
                print("Data stream ending...")
                await client.write_gatt_char(write_uuid,  bytes("s", "ascii")) 
                await client.disconnect()
                timer_thread.stop()
                print("Client disconnected.")
                break


thread = threading.Thread(target=launch)
thread.daemon = True
thread.start()

loop = asyncio.get_event_loop()
loop.run_until_complete(main(address))