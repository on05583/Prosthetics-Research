import argparse
import time
import sys
from pprint import pprint
import keyboard
import numpy as np
import threading
import queue
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import QTimer

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds, BrainFlowPresets

data_queue = queue.Queue()

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

        # Thread for data retrieval
        thread = threading.Thread(target=self.data_retrieval)
        thread.daemon = True
        thread.start()

    def update_plot(self):
        for i in range (0, 20):
            if not data_queue.empty():
                data = data_queue.get()
                self.canvas.plot_data(data)
            else:
                break

            
    def data_retrieval(self):
        board_id = 1
        serial_port = "COM5"

        BoardShim.enable_dev_board_logger()

        parser = argparse.ArgumentParser()
        # use docs to check which parameters are required for specific board, e.g. for Cyton - set serial port
        parser.add_argument('--timeout', type=int, help='timeout for device discovery or connection', required=False,
                            default=0)
        parser.add_argument('--ip-port', type=int, help='ip port', required=False, default=0)
        parser.add_argument('--ip-protocol', type=int, help='ip protocol, check IpProtocolType enum', required=False,
                            default=0)
        parser.add_argument('--ip-address', type=str, help='ip address', required=False, default='')
        parser.add_argument('--serial-port', type=str, help='serial port', required=False, default='')
        parser.add_argument('--mac-address', type=str, help='mac address', required=False, default='')
        parser.add_argument('--other-info', type=str, help='other info', required=False, default='')
        parser.add_argument('--serial-number', type=str, help='serial number', required=False, default='')
        parser.add_argument('--board-id', type=int, help='board id, check docs to get a list of supported boards',
                            required=False)
        parser.add_argument('--file', type=str, help='file', required=False, default='')
        parser.add_argument('--master-board', type=int, help='master board id for streaming and playback boards',
                            required=False, default=BoardIds.NO_BOARD)
        args = parser.parse_args()

        args.board_id = 1
        args.serial_port = "COM5"
        params = BrainFlowInputParams()
        params.ip_port = 0
        params.serial_port = args.serial_port
        params.mac_address = ''
        params.other_info = ''
        params.serial_number = ''
        params.ip_address = ''
        params.ip_protocol = 0
        params.timeout = 0
        params.file = ''
        params.master_board = BoardIds.NO_BOARD
        
        sample_num = 0

        board = BoardShim(args.board_id, params)
        board.prepare_session()
        board.start_stream ()
        time.sleep(1)

        # TODO: Set up plot for frequency

        while True:
            data = board.get_board_data()  # get all data and remove it from internal buffer
            if data.any(): 
                for y in data[1]:
                    sample_num += 1
                    x_val, y_val = sample_num / 200, y
                    if sample_num % 2 == 0:
                        data_queue.put((x_val, y_val))
            if keyboard.is_pressed('q'):
                board.stop_stream()
                board.release_session()
                return

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=200):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        self.line, = self.axes.plot([], [], 'r-')
        super().__init__(self.fig)

        self.x_data, self.y_data = [], []
        self.window_size = 200

        self.axes.set_autoscale_on(False)
        self.axes.set_ylim(10000, -10000) 

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

    # pprint(BoardShim.get_board_descr(board_id))
    # data = board.get_current_board_data (256) 
    # get latest 256 packages or less, doesnt remove them from internal buffer
    # data = board.get_board_data()  # get all data and remove it from internal buffer

    
    # board.stop_stream()
    # board.release_session()

    # print(data)
app = QApplication(sys.argv)
w = ApplicationWindow()
w.show()
sys.exit(app.exec_())