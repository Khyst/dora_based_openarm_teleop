import sys
import os
import time
import threading
from collections import deque

from PyQt5 import QtWidgets, QtCore
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# =========================
# PATH
# =========================
sys.path.append(os.path.join(os.path.dirname(__file__), "../cpp"))
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

import scservo_py
from hamsa import hand

# =========================
# CONFIG
# =========================
MOTOR_IDS = list(range(1, 11))
MAX_POINTS = 100

motor_names = {
    1: "Pinky Wiggle", 2: "Pinky Curl",
    3: "Ring Wiggle", 4: "Ring Curl",
    5: "Middle Wiggle", 6: "Middle Curl",
    7: "Index Wiggle", 8: "Index Curl",
    9: "Thumb Wiggle", 10: "Thumb Curl",
}

# =========================
# THREAD SAFE STATE
# =========================
class SharedState:
    def __init__(self, motor_ids):
        self.lock = threading.Lock()
        self.load = {i: 0 for i in motor_ids}

    def update(self, motor_id, value):
        with self.lock:
            self.load[motor_id] = value

    def snapshot(self):
        with self.lock:
            return dict(self.load)

# =========================
# SENSOR READER THREAD
# =========================
class LoadReader(threading.Thread):
    def __init__(self, state, motor_ids):
        super().__init__(daemon=True)
        self.state = state
        self.motor_ids = motor_ids

    def run(self):
        while True:
            for i in self.motor_ids:
                val = scservo_py.read_load(i)

                if val < 0:
                    continue
                if val < 5:
                    val = 0

                self.state.update(i, val)

            time.sleep(0.05)

# =========================
# HAND CONTROLLER
# =========================
class HandController:
    def __init__(self, hand_api):
        self.hand = hand_api

    def run_parallel(self, funcs):
        threads = [threading.Thread(target=f) for f in funcs]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    # 기본 동작
    def normal(self):
        self.hand.wiggle_pinky(0.5, 1000)
        self.hand.wiggle_ring(0.5, 1000)
        self.hand.wiggle_middle(0.5, 1000)
        self.hand.wiggle_index(0.5, 1000)
        self.hand.wiggle_thumb(0.5, 1000)

    def close_palm(self):
        self.hand.wiggle_pinky(0, 1000)
        self.hand.wiggle_ring(0, 1000)
        self.hand.wiggle_middle(1, 1000)
        self.hand.wiggle_index(1, 500)
        self.hand.wiggle_thumb(1, 1000)

    def open_palm(self):
        self.hand.wiggle_pinky(1, 1000)
        self.hand.wiggle_ring(1, 1000)
        self.hand.wiggle_index(0, 500)
        self.hand.wiggle_thumb(0, 1000)

    def grip(self):
        self.run_parallel([
            lambda: self.hand.curl_pinky(0, 2000),
            lambda: self.hand.curl_ring(0, 2000),
            lambda: self.hand.curl_middle(0, 2000),
            lambda: self.hand.curl_index(0, 2000),
            lambda: self.hand.curl_thumb(0, 2000),
            lambda: self.hand.wiggle_thumb(0, 2000),
        ])

    def release(self):
        self.run_parallel([
            lambda: self.hand.curl_pinky(1, 2000),
            lambda: self.hand.curl_ring(1, 2000),
            lambda: self.hand.curl_middle(1, 2000),
            lambda: self.hand.curl_index(1, 2000),
            lambda: self.hand.curl_thumb(1, 1800),
        ])

    def scissor(self):
        self.hand.curl_pinky(0, 1000)
        self.hand.curl_ring(0, 1000)
        self.hand.curl_thumb(0, 1000)
        self.hand.curl_middle(1, 1000)
        self.hand.curl_index(1, 1000)

    def finger_grip(self):
        self.run_parallel([
            lambda: self.hand.curl_pinky(1, 2000),
            lambda: self.hand.curl_ring(1, 2000),
            lambda: self.hand.curl_middle(1, 2000),
            lambda: self.hand.curl_index(0, 2000),
            lambda: self.hand.curl_thumb(0, 2000),
            lambda: self.hand.wiggle_thumb(1, 2000),
        ])

# =========================
# MATPLOTLIB WIDGET
# =========================
class PlotWidget(FigureCanvas):
    def __init__(self, state, motor_ids):
        self.fig = Figure(figsize=(8, 6))
        self.axes = self.fig.subplots(5, 2).flatten()
        super().__init__(self.fig)

        self.state = state
        self.motor_ids = motor_ids

        self.data = {
            i: deque([0]*MAX_POINTS, maxlen=MAX_POINTS)
            for i in motor_ids
        }

        self.lines = {}

        self.fig.subplots_adjust(hspace=1.5, wspace=0.3)

        for i, ax in zip(motor_ids, self.axes):
            line, = ax.plot(self.data[i])
            ax.set_title(motor_names[i])
            ax.set_ylim(0, 1000)
            ax.axhline(y=250, color='red', linestyle='--', linewidth=1)
            self.lines[i] = line

    def update_plot(self):
        snapshot = self.state.snapshot()

        for i in self.motor_ids:
            self.data[i].append(snapshot[i])
            self.lines[i].set_ydata(self.data[i])

        self.draw_idle()

# =========================
# GUI
# =========================
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, controller, plot_widget):
        super().__init__()
        self.setWindowTitle("Robot Hand Monitor")

        self.controller = controller
        self.plot = plot_widget

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(self.plot)

        btn_layout = QtWidgets.QGridLayout()

        # 제어 버튼
        btn_layout.addWidget(self._btn("Normal", self.controller.normal), 0, 0)
        btn_layout.addWidget(self._btn("Close", self.controller.close_palm), 0, 1)
        btn_layout.addWidget(self._btn("Open", self.controller.open_palm), 0, 2)
        btn_layout.addWidget(self._btn("Grip", self.controller.grip), 0, 3)
        btn_layout.addWidget(self._btn("Release", self.controller.release), 0, 4)
        btn_layout.addWidget(self._btn("Finger Grip", self.controller.finger_grip), 1, 0)

        layout.addLayout(btn_layout)

        central.setLayout(layout)
        self.setCentralWidget(central)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.plot.update_plot)
        self.timer.start(50)

    def _btn(self, name, func):
        btn = QtWidgets.QPushButton(name)
        btn.clicked.connect(func)
        return btn

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    state = SharedState(MOTOR_IDS)

    reader = LoadReader(state, MOTOR_IDS)
    reader.start()

    controller = HandController(hand)

    app = QtWidgets.QApplication(sys.argv)

    plot = PlotWidget(state, MOTOR_IDS)
    window = MainWindow(controller, plot)

    window.show()
    sys.exit(app.exec_())