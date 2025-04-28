import serial
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
import numpy as np
import sys

# Serial port setup
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)

# Settings
window_size = 500
smoothing_window = 100
sample_interval = 0.02  # 20 ms = 50 Hz

# Data buffer
data = np.zeros((3, window_size))
valid_samples = 0
current_time = 0.0

# Create the app
app = QtWidgets.QApplication([])
main_layout = QtWidgets.QWidget()
layout = QtWidgets.QVBoxLayout()
main_layout.setLayout(layout)

# Graph widget
win = pg.GraphicsLayoutWidget(title="Real-Time Sensor Data")
win.resize(1000, 600)

plots = []
curves = []

for i in range(2):
    p = win.addPlot(row=i, col=0)
    p.showGrid(x=True, y=True)
    c = p.plot(pen=pg.intColor(i))
    plots.append(p)
    curves.append(c)

layout.addWidget(win)

# --- Buttons ---
button_layout = QtWidgets.QHBoxLayout()

start_button = QtWidgets.QPushButton("Start")
stop_button = QtWidgets.QPushButton("Stop")

button_layout.addWidget(start_button)
button_layout.addWidget(stop_button)
layout.addLayout(button_layout)

# Button handlers
def send_start():
    try:
        ser.write(b"start\r\n")
        ser.flush()
        print("Sent: start")
    except Exception as e:
        print(e)

def send_stop():
    try:
        ser.write(b"stop\n\r")
        ser.flush()
        print("Sent: stop")
    except Exception as e:
        print(e)

start_button.clicked.connect(send_start)
stop_button.clicked.connect(send_stop)

# --- Smoothing function ---
def smooth(data_array, window_size):
    if len(data_array) < window_size:
        return data_array
    return np.convolve(data_array, np.ones(window_size)/window_size, mode='valid')

# --- Timer update ---
def update():
    global data, current_time, valid_samples
    try:
        line = ser.readline().decode('utf-8').strip()
        tokens = line.split()
        if len(tokens) >= 3:
            values = np.array([float(x) for x in tokens[1:3]])

            data = np.roll(data, -1, axis=1)
            data[1:, -1] = values
            data[0, -1] = current_time

            current_time += sample_interval

            if valid_samples < window_size:
                valid_samples += 1
    except Exception as e:
        print(e)

    x = data[0, -valid_samples:]
    y1 = data[1, -valid_samples:]
    y2 = data[2, -valid_samples:]

    if len(x) >= smoothing_window:
        smoothed_y1 = smooth(y1, smoothing_window)
        smoothed_y2 = smooth(y2, smoothing_window)

        x_smoothed = np.linspace(x[0], x[-1], num=len(smoothed_y1))

        curves[0].setData(x_smoothed, smoothed_y1)
        curves[1].setData(x_smoothed, smoothed_y2)
    else:
        curves[0].setData(x, y1)
        curves[1].setData(x, y2)

# Setup timer
timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(int(sample_interval * 1000))  # 20 ms

# Start app
main_layout.show()
sys.exit(app.exec_())
