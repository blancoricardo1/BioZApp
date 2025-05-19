import sys
import time
import serial
import serial.tools.list_ports
import threading
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

class SerialPlotter(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Serial Plotter")

        # ====== Layouts ======
        main_layout = QtWidgets.QVBoxLayout(self)
        control_layout = QtWidgets.QHBoxLayout()
        graph_layout = QtWidgets.QVBoxLayout()
        slider_layout = QtWidgets.QHBoxLayout()

        # ====== COM Port Selector ======
        self.port_box = QtWidgets.QComboBox()
        self.refresh_ports()
        control_layout.addWidget(self.port_box)

        # ====== Connect / Disconnect Buttons ======
        self.connect_button = QtWidgets.QPushButton("Connect")
        self.disconnect_button = QtWidgets.QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)
        control_layout.addWidget(self.connect_button)
        control_layout.addWidget(self.disconnect_button)

        # ====== Start / Stop Buttons ======
        self.start_button = QtWidgets.QPushButton("Start")
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)

        # ====== Ohms Display ======
        self.ohm_label_layout = QtWidgets.QVBoxLayout()
        self.i_ohms_label = QtWidgets.QLabel("Q (Ohms): 0")
        self.q_ohms_label = QtWidgets.QLabel("I (Ohms): 0")
        self.ohm_label_layout.addWidget(self.i_ohms_label)
        self.ohm_label_layout.addWidget(self.q_ohms_label)
        control_layout.addLayout(self.ohm_label_layout)

        # Add control panel to main layout
        main_layout.addLayout(control_layout, stretch=0)

        # ====== Slider to control window size ======
        self.slider_label = QtWidgets.QLabel("Window Size: 500")
        self.window_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.window_slider.setMinimum(100)
        self.window_slider.setMaximum(2000)
        self.window_slider.setValue(500)
        self.window_slider.setTickInterval(100)
        self.window_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        slider_layout.addWidget(self.slider_label)
        slider_layout.addWidget(self.window_slider)
        main_layout.addLayout(slider_layout)

        # ====== Graphs ======
        self.graph1 = pg.PlotWidget(title="Q (Ohms) vs Time")
        self.graph2 = pg.PlotWidget(title="I (Ohms) vs Time")
        self.curve1 = self.graph1.plot(pen='y')  # Line graph for I
        self.scatter1 = pg.ScatterPlotItem(brush='y', size=5)  # Scatter plot for I
        self.graph1.addItem(self.scatter1)

        self.curve2 = self.graph2.plot(pen='c')  # Line graph for Q
        self.scatter2 = pg.ScatterPlotItem(brush='c', size=5)  # Scatter plot for Q
        self.graph2.addItem(self.scatter2)

        # Link the x-axis of graph1 to graph2
        self.graph1.setXLink(self.graph2)

        # Hide the x-axis of graph1
        self.graph1.getPlotItem().hideAxis('bottom')

        self.window_size = 500

        for graph in [self.graph1, self.graph2]:
            graph.setMouseEnabled(x=False, y=False)
            vb = graph.getViewBox()
            vb.setMouseMode(pg.ViewBox.PanMode)
            vb.setMenuEnabled(False)
            vb.enableAutoRange(y=True)
            vb.enableAutoRange(x=False)  # Disable x-axis auto-range to prevent flickering
            graph.getPlotItem().buttonsHidden = True
            graph.setMinimumHeight(300)

        graph_layout.addWidget(self.graph1)
        graph_layout.addWidget(self.graph2)
        main_layout.addLayout(graph_layout, stretch=1)

        # ====== Data Storage ======
        self.x_data = []
        self.y1_data = []
        self.y2_data = []

        # ====== Serial & Threading ======
        self.serial = None
        self.read_thread = None
        self.running = False

        # ====== Button Signals ======
        self.connect_button.clicked.connect(self.connect_serial)
        self.disconnect_button.clicked.connect(self.disconnect_serial)
        self.start_button.clicked.connect(self.send_start)
        self.stop_button.clicked.connect(self.send_stop)
        self.window_slider.valueChanged.connect(self.update_window_size)

    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        self.port_box.clear()
        self.port_box.addItems([port.device for port in ports])

    def connect_serial(self):
        port_name = self.port_box.currentText()
        try:
            self.serial = serial.Serial(port_name, 115200, timeout=1)
            time.sleep(0.5)
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            print("Connected to:", port_name)

            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.start_button.setEnabled(True)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to open port: {e}")

    def disconnect_serial(self):
        try:
            if self.running:
                self.running = False
                self.read_thread.join()
            if self.serial and self.serial.is_open:
                self.serial.close()
            print("Disconnected.")
        except Exception as e:
            print("Error disconnecting:", e)
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    def send_start(self):
        if self.serial and self.serial.is_open:
            self.serial.write(b'start\r\n')
            print("Sent: start")
            self.running = True
            self.read_thread = threading.Thread(target=self.read_serial)
            self.read_thread.start()
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)

    def send_stop(self):
        if self.serial and self.serial.is_open:
            self.serial.write(b'stop\r\n')
            print("Sent: stop")
            self.running = False
            self.read_thread.join()
            self.stop_button.setEnabled(False)
            self.start_button.setEnabled(True)

    def update_window_size(self, value):
        self.window_size = value
        self.slider_label.setText(f"Window Size: {value}")

    def read_serial(self):
        SCALE_K = 85.481  # Conversion factor for 256uA drive

        while self.running:
            try:
                line = self.serial.readline().decode('utf-8').strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) != 3:
                    continue
                x, y1, y2 = map(float, parts)

                # Convert y1 and y2 to ohms
                I_ohms = y1 / SCALE_K
                Q_ohms = y2 / SCALE_K

                self.x_data.append(x)
                self.y1_data.append(I_ohms)  # Store I in ohms
                self.y2_data.append(Q_ohms)  # Store Q in ohms

                if len(self.x_data) > self.window_size:
                    self.x_data = self.x_data[-self.window_size:]
                    self.y1_data = self.y1_data[-self.window_size:]
                    self.y2_data = self.y2_data[-self.window_size:]

                # Update line graphs
                self.curve1.setData(self.x_data, self.y1_data)
                self.curve2.setData(self.x_data, self.y2_data)

                # Update scatter plots
                self.scatter1.setData(self.x_data, self.y1_data)
                self.scatter2.setData(self.x_data, self.y2_data)

                self.i_ohms_label.setText(f"Q (Ohms): {I_ohms:.2f}")
                self.q_ohms_label.setText(f"I (Ohms): {Q_ohms:.2f}")

                # Update x-axis range only when there is sufficient data
                if len(self.x_data) >= 10:  # Wait until at least 10 data points are available
                    x_min = self.x_data[0]
                    x_max = self.x_data[-1]
                    self.graph1.setXRange(x_min, x_max, padding=0.01)
                    self.graph2.setXRange(x_min, x_max, padding=0.01)
            except Exception as e:
                print("Read error:", e)
                continue

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    plotter = SerialPlotter()
    plotter.resize(1000, 850)
    plotter.show()
    sys.exit(app.exec_())
