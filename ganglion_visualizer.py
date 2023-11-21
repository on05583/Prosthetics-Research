import argparse
import asyncio
import queue
import sys
import threading
import time
from pprint import pprint

import aioconsole
import brainflow as brainflow
import keyboard
import numpy as np
from brainflow.board_shim import (
    BoardIds,
    BoardShim,
    BrainFlowInputParams,
    BrainFlowPresets,
)
from brainflow.data_filter import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from nptyping import NDArray
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

from bleak import BleakClient, BleakScanner, BLEDevice

data_queue = queue.Queue()
freq_queue = queue.Queue()
nd_array_points = np.array([0.0])
nd_array_times = np.array([0.0])
filter = DataFilter()


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
        self.canvas1 = MplCanvas(self, width=5, height=4, dpi=100, plot_type="line")
        layout.addWidget(self.canvas1)

        self.canvas2 = MplCanvas(self, width=5, height=4, dpi=100, plot_type="point")
        layout.addWidget(self.canvas2)
        self.canvas2.axes.set_ylim(-10000, 10000)
        self.canvas2.axes.set_xlim(0, 100)

        self.main_widget.setLayout(layout)
        self.setCentralWidget(self.main_widget)
        self.setWindowTitle("Real-Time Plots")

        self.timer = QTimer(self)
        self.timer.setInterval(5)
        self.timer.timeout.connect(self.update_plots)
        self.timer.start()

    def update_plots(self):
        for i in range(0, 20):
            if not data_queue.empty():
                data = data_queue.get()
                self.canvas1.plot_data(data)
        if not freq_queue.empty():
            self.canvas2.plot_data_freq(freq_queue.get())


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=200, plot_type="line"):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        (self.line,) = self.axes.plot([], [], "r-")
        super().__init__(self.fig)

        self.plot_type = plot_type

        if self.plot_type == "line":
            (self.line,) = self.axes.plot([], [], "r-")
        else:
            (self.scatter,) = self.axes.plot([], [], "ro")  # 'ro' for red circles
            (self.line,) = self.axes.plot([], [], "r-")  # 'r-' for a red line

        self.x_data, self.y_data = [], []
        self.window_size = 200

        self.axes.set_autoscale_on(False)
        self.axes.set_ylim(-1000, 1000)

    def plot_data(self, data):
        x, y = data

        self.x_data.append(x)
        self.y_data.append(y)

        if len(self.x_data) > self.window_size:
            self.x_data = self.x_data[-self.window_size :]
            self.y_data = self.y_data[-self.window_size :]

        if self.plot_type == "line":
            self.line.set_data(self.x_data, self.y_data)
            self.axes.set_xlim(max(0, self.x_data[0]), self.x_data[-1] + 1)

        self.axes.relim()
        self.draw_idle()

    def plot_data_freq(self, data):
        frequencies, magnitudes = data

        if self.plot_type == "point":
            self.scatter.set_data(frequencies, magnitudes)
            self.line.set_data(frequencies, magnitudes)

        self.draw_idle()
        frequencies, magnitudes = data

        """
        self.x_data = []
        self.y_data = []

        # self.scatter.set_offsets(np.column_stack((frequencies, magnitudes)))

        self.axes.set_ylim(min(magnitudes), max(magnitudes))
        self.scatter.set_data(frequencies, magnitudes)
        self.line.set_data(frequencies, magnitudes)

        self.axes.relim()
        self.draw_idle()
        """


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
refresh_rate = 20


async def callback(sender, data):
    global nd_array_points
    global nd_array_times
    if len(data) == 20 and data[19] != 0:
        full_int = int.from_bytes(data, "big")

        mask = (1 << 19) - 1  # 19 bits mask
        num_bits = len(data) * 8

        extracted_bits = (full_int >> (num_bits - 27)) & mask
        extracted_bits *= SCALE

        if extracted_bits < 900 or extracted_bits > 1000:
            if count.value % 5 == 0:
                nd_array_points = np.insert(
                    nd_array_points, nd_array_points.size - 1, [extracted_bits]
                )
                nd_array_times = np.insert(
                    nd_array_times,
                    nd_array_times.size - 1,
                    [timer_thread.get_elapsed_time()],
                )
                if nd_array_points.size > refresh_rate:
                    """
                    filter.perform_lowpass(
                        nd_array_points,  # data
                        200,  # sampling rate
                        150,  # cutoff frequency
                        1,  # filter order
                        FilterTypes.CHEBYSHEV_TYPE_1,  # filter type
                        0,  # Chebyshev filter ripple value
                    )
                    """
                    fft_result = np.fft.fft(nd_array_points)
                    frequencies = np.fft.fftfreq(len(nd_array_points), 1 / 200)
                    magnitudes = np.abs(fft_result)

                    fft_result = np.fft.fft(nd_array_points)

                    half_index = len(frequencies) // 2
                    positive_frequencies = frequencies[:half_index]
                    positive_magnitudes = magnitudes[:half_index]
                    sorted_indices = np.argsort(positive_frequencies)
                    sorted_frequencies = positive_frequencies[sorted_indices]
                    sorted_magnitudes = positive_magnitudes[sorted_indices]

                    # Now put the sorted data into the queue
                    freq_queue.put((sorted_frequencies, sorted_magnitudes))

                    for i in range(0, refresh_rate):
                        data_queue.put((nd_array_times[i], nd_array_points[i]))

                    nd_array_points = np.array([0.0])
                    nd_array_times = np.array([0.0])
            count.value += 1
        # if count.value % 5 == 0:
        # data_queue.put((timer_thread.get_elapsed_time(), extracted_bits))

        extracted_bits = (full_int >> (num_bits - 103)) & mask  # skip 84 + 19
        extracted_bits *= SCALE
        if extracted_bits < 900 or extracted_bits > 1000:
            if count.value % 5 == 0:
                nd_array_points = np.insert(
                    nd_array_points, nd_array_points.size - 1, [extracted_bits]
                )
                nd_array_times = np.insert(
                    nd_array_times,
                    nd_array_times.size - 1,
                    [timer_thread.get_elapsed_time()],
                )
                if nd_array_points.size > refresh_rate:
                    """
                    filter.perform_lowpass(
                        nd_array_points,  # data
                        200,  # sampling rate
                        150,  # cutoff frequency
                        1,  # filter order
                        FilterTypes.CHEBYSHEV_TYPE_1,  # filter type
                        0,  # Chebyshev filter ripple value
                    )"""
                    fft_result = np.fft.fft(nd_array_points)
                    frequencies = np.fft.fftfreq(len(nd_array_points), 1 / 200)
                    magnitudes = np.abs(fft_result)

                    fft_result = np.fft.fft(nd_array_points)

                    half_index = len(frequencies) // 2
                    positive_frequencies = frequencies[:half_index]
                    positive_magnitudes = magnitudes[:half_index]
                    sorted_indices = np.argsort(positive_frequencies)
                    sorted_frequencies = positive_frequencies[sorted_indices]
                    sorted_magnitudes = positive_magnitudes[sorted_indices]

                    # Now put the sorted data into the queue
                    freq_queue.put((sorted_frequencies, sorted_magnitudes))

                    for i in range(0, refresh_rate):
                        data_queue.put((nd_array_times[i], nd_array_points[i]))

                    nd_array_points = np.array([0.0])
                    nd_array_times = np.array([0.0])
            count.value += 1
        # if count.value % 5 == 0:
        # data_queue.put((timer_thread.get_elapsed_time(), extracted_bits))


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

        await client.write_gatt_char(write_uuid, bytes("b", "ascii"))

        print("Data stream started.")
        timer_thread.start()

        while True:
            input_str = await aioconsole.ainput("Press 'q' to quit: \n")
            if input_str == "q":
                print("Data stream ending...")
                await client.write_gatt_char(write_uuid, bytes("s", "ascii"))
                await client.disconnect()
                timer_thread.stop()
                print("Client disconnected.")
                return


thread = threading.Thread(target=launch)
thread.daemon = True
thread.start()

loop = asyncio.get_event_loop()
loop.run_until_complete(main(address))
