import sys
import math
import requests
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QRadialGradient, QFont, QPainterPath
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QGridLayout, QStackedWidget, QMessageBox, QSizePolicy
)

class AnalogMeterWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 72)
        self.setMaximumHeight(82)
        self.frequency = 0

    def set_frequency(self, freq):
        self.frequency = freq
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        painter.fillRect(0, 0, w, h, QColor("#1c1f21"))

        # Cornice rettangolare arrotondata
        path = QPainterPath()
        path.addRoundedRect(QRectF(3, 3, w - 6, h - 6), 3, 3)
        
        painter.save()
        painter.setClipPath(path)

        # Colori originali del dial
        dial_grad = QLinearGradient(0, 0, 0, h)
        dial_grad.setColorAt(0, QColor("#ffcc70"))
        dial_grad.setColorAt(0.5, QColor("#e09835"))
        dial_grad.setColorAt(1, QColor("#8c5317"))
        painter.fillRect(0, 0, w, h, dial_grad)

        # Scala lineare orizzontale con numeri e tacche ingrandite
        painter.save()
        scale_y = h * 0.58
        painter.setPen(QPen(QColor("#000000"), 1.8))
        painter.drawLine(12, int(scale_y), w - 12, int(scale_y))
        
        step_minor = 200    
        step_major = 1000   
        scale_factor = 0.12 
        
        start_freq = int(self.frequency - (w / 2) / scale_factor)
        end_freq = int(self.frequency + (w / 2) / scale_factor)
        start_freq = (start_freq // step_minor) * step_minor
        
        painter.setFont(QFont("Consolas", 10, QFont.Bold))
        
        f = start_freq
        while f <= end_freq:
            x = (w / 2) + (f - self.frequency) * scale_factor
            if 12 <= x <= w - 12:
                is_major = (f % step_major == 0)
                tick_len = 10 if is_major else 5
                painter.setPen(QPen(QColor("#000000"), 1.8 if is_major else 1.0))
                painter.drawLine(int(x), int(scale_y), int(x), int(scale_y - tick_len))
                
                if is_major:
                    painter.setPen(QPen(QColor("#000000"), 1.2))
                    painter.drawText(QRectF(x - 40, scale_y - 26, 80, 18), Qt.AlignCenter, str(f))
            f += step_minor

        painter.restore()

        # Indice centrale rosso fisso
        painter.setPen(QPen(QColor("#b22222"), 2.2))
        painter.drawLine(w // 2, 4, w // 2, h - 4)

        # Effetto vetro superiore
        glass_grad = QLinearGradient(0, 0, 0, h / 2)
        glass_grad.setColorAt(0, QColor(255, 255, 255, 90))
        glass_grad.setColorAt(1, QColor(255, 255, 255, 0))
        painter.fillRect(0, 0, int(w), int(h / 2), glass_grad)
        painter.restore()

        # Bordo esterno e viti
        painter.setPen(QPen(QColor("#3c3f41"), 2))
        painter.drawPath(path)

        self.draw_screw(painter, 6, 6)
        self.draw_screw(painter, w - 6, 6)
        self.draw_screw(painter, 6, h - 6)
        self.draw_screw(painter, w - 6, h - 6)

    def draw_screw(self, painter, x, y):
        painter.setPen(QPen(QColor("#555"), 0.8))
        painter.setBrush(QBrush(QColor("#111")))
        painter.drawEllipse(QPointF(x, y), 2.0, 2.0)
        painter.setPen(QPen(QColor("#777"), 0.5))
        painter.drawLine(int(x - 1.2), int(y - 1.2), int(x + 1.2), int(y + 1.2))


class RotaryDialWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(140, 140)
        self.setMaximumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.dial_angle = 0.0
        self.is_dragging = False
        self.last_mouse_angle = 0.0
        self.on_rotate_callback = None

    def get_mouse_angle(self, event):
        center = QPointF(self.width() / 2, self.height() / 2)
        pos = event.pos()
        return math.degrees(math.atan2(pos.y() - center.y(), pos.x() - center.x()))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.last_mouse_angle = self.get_mouse_angle(event)

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            current_angle = self.get_mouse_angle(event)
            delta = current_angle - self.last_mouse_angle
            if delta > 180: delta -= 360
            if delta < -180: delta += 360
            self.last_mouse_angle = current_angle
            self.dial_angle = (self.dial_angle + delta) % 360
            if self.on_rotate_callback:
                self.on_rotate_callback(delta)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False

    def wheelEvent(self, event):
        delta = 10 if event.angleDelta().y() > 0 else -10
        self.dial_angle = (self.dial_angle + delta) % 360
        if self.on_rotate_callback:
            self.on_rotate_callback(10 if event.angleDelta().y() > 0 else -10)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        
        outer_radius = min(cx, cy) - 6

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.dial_angle)

        skirt_grad = QRadialGradient(-10, -10, outer_radius)
        skirt_grad.setColorAt(0, QColor("#d4af37"))
        skirt_grad.setColorAt(0.6, QColor("#b8860b"))
        skirt_grad.setColorAt(1, QColor("#5c4010"))
        painter.setBrush(QBrush(skirt_grad))
        painter.setPen(QPen(QColor("#222"), 1.5))
        painter.drawEllipse(QPointF(0, 0), outer_radius, outer_radius)

        for i in range(40):
            deg = i * 9
            rad = math.radians(deg)
            is_major = (i % 5 == 0)
            tick_len = max(4, int(outer_radius * 0.12)) if is_major else max(2, int(outer_radius * 0.06))
            painter.setPen(QPen(QColor("#111"), 1.2 if is_major else 0.7))
            painter.drawLine(QPointF((outer_radius - 3) * math.cos(rad), (outer_radius - 3) * math.sin(rad)),
                             QPointF((outer_radius - 3 - tick_len) * math.cos(rad), (outer_radius - 3 - tick_len) * math.sin(rad)))

        painter.restore()
        
        knob_r = outer_radius - max(12, int(outer_radius * 0.28))
        knob_grad = QRadialGradient(cx - 4, cy - 4, knob_r)
        knob_grad.setColorAt(0, QColor("#484a4b"))
        knob_grad.setColorAt(1, QColor("#1c1e1f"))
        painter.setBrush(QBrush(knob_grad))
        painter.setPen(QPen(QColor("#111"), 1.5))
        painter.drawEllipse(QPointF(cx, cy), knob_r, knob_r)

        painter.setPen(QPen(QColor("#ffb000"), 2.5, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(int(cx), int(cy - outer_radius - 3), int(cx), int(cy - outer_radius + 5))


class SDRangelVFOApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_offset = 0
        self.current_step = 100
        self.input_buffer = ""
        self.input_negative = False
        self.is_pinned = True
        self.is_updating_from_remote = False

        self.init_ui()
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(1000)
        self.poll_timer.timeout.connect(self.poll_sdrangel_status)
        self.poll_timer.start()

    def init_ui(self):
        self.setWindowTitle("SDRangel - VFO Faceplate")
        self.resize(340, 590)
        self.setMinimumSize(290, 480)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        self.setStyleSheet("""
            QMainWindow { background-color: #151515; }
            QWidget { color: #a9b7c6; font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 11px; }
            QPushButton { background-color: #3c3f41; border: 1px solid #555; border-radius: 3px; padding: 5px; color: #a9b7c6; }
            QPushButton:hover { background-color: #505355; color: #fff; border-color: #8c5317; }
            QPushButton:checked { background-color: #3c3f41; border: 1px solid #ffb000; color: #ffb000; font-weight: bold; }
            QLineEdit { background-color: #1e1e1e; border: 1px solid #3c3f41; color: #ffb000; font-family: 'Consolas'; padding: 4px; border-radius: 3px; }
        """)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)

        self.pin_btn = QPushButton("📌")
        self.pin_btn.setFixedSize(26, 22)
        self.pin_btn.clicked.connect(self.toggle_pin)
        header_layout.addWidget(self.pin_btn)

        self.tab_main_btn = QPushButton("Main")
        self.tab_main_btn.setCheckable(True)
        self.tab_main_btn.setChecked(True)
        self.tab_main_btn.clicked.connect(lambda: self.switch_tab(0))
        header_layout.addWidget(self.tab_main_btn)

        self.tab_setup_btn = QPushButton("Setup")
        self.tab_setup_btn.setCheckable(True)
        self.tab_setup_btn.clicked.connect(lambda: self.switch_tab(1))
        header_layout.addWidget(self.tab_setup_btn)

        header_layout.addStretch()

        self.status_label = QLabel("Init")
        self.status_label.setStyleSheet("color: #cc6666; font-size: 9px;")
        header_layout.addWidget(self.status_label)

        main_layout.addLayout(header_layout)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # --- MAIN VIEW ---
        main_view = QWidget()
        main_vbox = QVBoxLayout(main_view)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(6)

        self.analog_meter = AnalogMeterWidget()
        main_vbox.addWidget(self.analog_meter)

        self.rotary_dial = RotaryDialWidget()
        self.rotary_dial.on_rotate_callback = self.handle_dial_rotation
        dial_container = QHBoxLayout()
        dial_container.addStretch()
        dial_container.addWidget(self.rotary_dial)
        dial_container.addStretch()
        main_vbox.addLayout(dial_container)

        # Tasti di step (da 1 Hz a 10 kHz)
        step_layout = QHBoxLayout()
        step_layout.setSpacing(3)
        self.step_buttons = {}
        for s_val, s_text in [(1, "1 Hz"), (10, "10 Hz"), (100, "100 Hz"), (1000, "1 kHz"), (5000, "5 kHz"), (10000, "10 kHz")]:
            btn = QPushButton(s_text)
            btn.setCheckable(True)
            if s_val == 100: btn.setChecked(True)
            btn.clicked.connect(lambda checked, val=s_val: self.set_step(val))
            step_layout.addWidget(btn)
            self.step_buttons[s_val] = btn
        main_vbox.addLayout(step_layout)

        self.freq_display = QLabel("Dev Freq: 0 Hz")
        self.freq_display.setAlignment(Qt.AlignCenter)
        self.freq_display.setStyleSheet("""
            font-size: 14px; font-family: 'Consolas'; font-weight: bold;
            background-color: #1e1e1e; border: 1px inset #3c3f41;
            color: #ffb000; padding: 6px; border-radius: 3px;
        """)
        main_vbox.addWidget(self.freq_display)

        keypad_layout = QGridLayout()
        keypad_layout.setSpacing(3)
        keys = [
            ('1', 0, 0), ('2', 0, 1), ('3', 0, 2), ('C', 0, 3),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2), ('⌫', 1, 3),
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2), ('.', 2, 3),
            ('±', 3, 0), ('0', 3, 1)
        ]
        for key_text, r, c in keys:
            btn = QPushButton(key_text)
            btn.setFont(QFont("Consolas", 10, QFont.Bold))
            if key_text in ['C', '⌫', '.', '±']:
                btn.setStyleSheet("background-color: #2d3133; color: #ffb000;")
            btn.clicked.connect(lambda checked, t=key_text: self.press_key(t))
            keypad_layout.addWidget(btn, r, c)

        set_btn = QPushButton("SET DEV")
        set_btn.setStyleSheet("background-color: #8c5317; color: #fff; font-weight: bold; font-family: 'Consolas';")
        set_btn.clicked.connect(lambda: self.press_key('SET'))
        keypad_layout.addWidget(set_btn, 3, 2, 1, 2)

        main_vbox.addLayout(keypad_layout)
        self.stack.addWidget(main_view)

        # --- SETUP VIEW ---
        setup_view = QWidget()
        setup_vbox = QVBoxLayout(setup_view)
        setup_vbox.setSpacing(8)

        setup_vbox.addWidget(QLabel("SDRangel Host & Port:"))
        self.host_input = QLineEdit("http://127.0.0.1:8091")
        setup_vbox.addWidget(self.host_input)

        setup_vbox.addWidget(QLabel("Device Set ID:"))
        self.devset_input = QLineEdit("1")
        setup_vbox.addWidget(self.devset_input)

        setup_vbox.addWidget(QLabel("Channel Index:"))
        self.chan_input = QLineEdit("0")
        setup_vbox.addWidget(self.chan_input)

        setup_vbox.addWidget(QLabel("Detected Channel Type:"))
        self.type_input = QLineEdit("AMDemod")
        setup_vbox.addWidget(self.type_input)

        auto_btn = QPushButton("🔍 Auto-Rileva Canale")
        auto_btn.setStyleSheet("background-color: #8c5317; color: white; font-weight: bold; padding: 6px;")
        auto_btn.clicked.connect(self.auto_detect_channel)
        setup_vbox.addWidget(auto_btn)

        setup_vbox.addStretch()
        self.stack.addWidget(setup_view)

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        if self.is_pinned:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.pin_btn.setText("📌")
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.pin_btn.setText("📍")
        self.show()

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        self.tab_main_btn.setChecked(index == 0)
        self.tab_setup_btn.setChecked(index == 1)

    def set_step(self, step_val):
        self.current_step = step_val
        for s, btn in self.step_buttons.items():
            btn.setChecked(s == step_val)

    def handle_dial_rotation(self, delta):
        self.current_offset += int(delta * (self.current_step * 0.2))
        self.update_display()
        self.send_patch_request()

    def update_display(self):
        sign = "+" if self.current_offset > 0 else ""
        self.freq_display.setText(f"Dev Freq: {sign}{round(self.current_offset):,}".replace(",", ".") + " Hz")
        self.analog_meter.set_frequency(self.current_offset)

    def update_display_buffer(self):
        if not self.input_buffer:
            self.update_display()
        else:
            sign = "-" if self.input_negative else ""
            self.freq_display.setText(f"Dev Freq: {sign}{self.input_buffer} Hz")

    def press_key(self, val):
        if val == 'C':
            self.input_buffer = ""
            self.input_negative = False
            self.update_display()
            return
        if val == '⌫':
            if self.input_buffer:
                self.input_buffer = self.input_buffer[:-1]
            if not self.input_buffer:
                self.input_negative = False
            self.update_display_buffer()
            return
        if val == '±':
            self.input_negative = not self.input_negative
            self.update_display_buffer()
            return
        if val == 'SET':
            if self.input_buffer:
                try:
                    parsed = float(self.input_buffer.replace('.', '').replace(',', ''))
                    self.current_offset = int(parsed) * (-1 if self.input_negative else 1)
                    self.send_patch_request()
                except ValueError:
                    pass
                self.input_buffer = ""
                self.input_negative = False
            self.update_display()
            return

        self.input_buffer += val
        self.update_display_buffer()

    def auto_detect_channel(self):
        host = self.host_input.text()
        dev_set = self.devset_input.text()
        url = f"{host}/sdrangel/deviceset/{dev_set}"
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                if "channels" in data and len(data["channels"]) > 0:
                    chan = data["channels"][0]
                    chan_type = chan.get("channelType", "AMDemod")
                    self.type_input.setText(chan_type)
                    self.chan_input.setText("0")
                    self.status_label.setText("Auto OK")
                    self.status_label.setStyleSheet("color: #6a8759; font-size: 9px;")
                else:
                    QMessageBox.warning(self, "Attenzione", "Nessun canale attivo trovato.")
            else:
                raise Exception()
        except Exception:
            self.status_label.setText("Error")
            self.status_label.setStyleSheet("color: #cc6666; font-size: 9px;")
            QMessageBox.critical(self, "Errore", "Impossibile connettersi a SDRangel.")

    def poll_sdrangel_status(self):
        if self.is_updating_from_remote:
            return

        host = self.host_input.text()
        dev_set = self.devset_input.text()
        chan_idx = self.chan_input.text()
        chan_url = f"{host}/sdrangel/deviceset/{dev_set}/channel/{chan_idx}/settings"

        try:
            chan_resp = requests.get(chan_url, timeout=0.8)
            if chan_resp.status_code == 200:
                chan_data = chan_resp.json()
                offset = 0
                detected_type = self.type_input.text()

                for key, val in chan_data.items():
                    if key.endswith("Settings") and isinstance(val, dict):
                        detected_type = key.replace("Settings", "")
                        if "inputFrequencyOffset" in val:
                            offset = int(val["inputFrequencyOffset"])
                            break

                if detected_type and detected_type != self.type_input.text():
                    self.type_input.setText(detected_type)

                if offset != int(self.current_offset):
                    self.current_offset = offset
                    self.is_updating_from_remote = True
                    self.update_display()
                    self.is_updating_from_remote = False

                self.status_label.setText("Live")
                self.status_label.setStyleSheet("color: #6a8759; font-size: 9px;")
            else:
                self.status_label.setText("Offline")
                self.status_label.setStyleSheet("color: #cc6666; font-size: 9px;")
        except Exception:
            self.status_label.setText("No Conn")
            self.status_label.setStyleSheet("color: #cc6666; font-size: 9px;")

    def send_patch_request(self):
        if self.is_updating_from_remote:
            return

        host = self.host_input.text()
        dev_set = self.devset_input.text()
        chan_idx = self.chan_input.text()
        chan_type = self.type_input.text()

        url = f"{host}/sdrangel/deviceset/{dev_set}/channel/{chan_idx}/settings"
        payload = {
            "channelType": chan_type,
            "direction": 0,
            f"{chan_type}Settings": {
                "inputFrequencyOffset": int(round(self.current_offset))
            }
        }
        try:
            requests.patch(url, json=payload, timeout=1)
        except Exception:
            pass


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SDRangelVFOApp()
    window.show()
    sys.exit(app.exec_())