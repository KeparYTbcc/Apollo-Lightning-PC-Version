#!/usr/bin/env python3
"""
LED Controller - Graphical Interface (PyQt5)

Modern Android-inspired PyQt5 GUI with minimalist design, icon buttons,
compact device scanning, and an integrated color wheel for intuitive color selection.

Run with: `python gui.py` (requires PyQt5 installed in your environment)
"""

import asyncio
import json
import math
import threading
from pathlib import Path
from typing import Any

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QIcon, QPixmap

from ble_led_controller import BLELedController, DeviceScanner, LEDMode


CONFIG_FILE = Path(__file__).parent / ".led_controller_config.json"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(cfg: dict) -> bool:
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
        return True
    except Exception:
        return False


def load_default_mac() -> str | None:
    return load_config().get("default_mac")


def set_default_mac_in_config(mac: str) -> bool:
    cfg = load_config()
    cfg["default_mac"] = mac
    return save_config(cfg)


def remove_default_mac_from_config() -> bool:
    cfg = load_config()
    if "default_mac" in cfg:
        del cfg["default_mac"]
        return save_config(cfg)
    return True


def load_presets() -> dict:
    return load_config().get("presets", {})


def save_preset_in_config(name: str, r: int, g: int, b: int, brightness: int = 100) -> bool:
    cfg = load_config()
    presets = cfg.get("presets", {})
    presets[name] = {"r": r, "g": g, "b": b, "brightness": brightness}
    cfg["presets"] = presets
    return save_config(cfg)


def remove_preset_from_config(name: str) -> bool:
    cfg = load_config()
    presets = cfg.get("presets", {})
    if name in presets:
        del presets[name]
        cfg["presets"] = presets
        return save_config(cfg)
    return True


def get_preset_from_config(name: str) -> dict | None:
    return load_presets().get(name)


class AsyncWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(str)

    def run_coro(self, coro: Any):
        def target():
            try:
                res = asyncio.run(coro)
                self.finished.emit(res)
            except Exception as e:
                self.error.emit(str(e))

        threading.Thread(target=target, daemon=True).start()


class ColorWheelWidget(QtWidgets.QWidget):
    """Smooth, image-based HSV color wheel.

    - Hue is chosen by angle around the wheel.
    - Saturation is chosen by radius from center (0..1).
    - Value is kept separate (via sliders) and not baked into the wheel image.
    Emits `color_changed(r,g,b)` with 0-255 RGB values.
    """
    color_changed = QtCore.pyqtSignal(int, int, int)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(260, 260)
        self._wheel_image = None
        self.h = 0.0
        self.s = 1.0
        self.v = 1.0
        self._last_size = None

    def _make_wheel(self, size):
        img = QtGui.QImage(size, size, QtGui.QImage.Format_RGBA8888)
        img.fill(Qt.transparent)
        cx = cy = size // 2
        radius = size // 2 - 2
        for y in range(size):
            for x in range(size):
                dx = x - cx
                dy = y - cy
                dist = math.hypot(dx, dy)
                if dist <= radius:
                    # saturation based on distance
                    sat = dist / radius
                    hue = (math.degrees(math.atan2(dy, dx)) + 360) % 360
                    r, g, b = self._hsv_to_rgb(hue, sat * 100.0, 100.0)
                    img.setPixelColor(x, y, QColor(r, g, b, 255))
                else:
                    img.setPixelColor(x, y, QColor(0, 0, 0, 0))
        return img

    def _ensure_wheel(self):
        size = min(self.width(), self.height())
        if self._wheel_image is None or self._last_size != size:
            if size <= 8:
                return
            self._wheel_image = self._make_wheel(size)
            self._last_size = size

    def _hsv_to_rgb(self, h, s, v):
        # h: 0..360, s/v: 0..100
        s, v = s / 100.0, v / 100.0
        c = v * s
        x = c * (1 - abs(((h / 60) % 2) - 1))
        m = v - c
        if h < 60:
            r, g, b = c, x, 0
        elif h < 120:
            r, g, b = x, c, 0
        elif h < 180:
            r, g, b = 0, c, x
        elif h < 240:
            r, g, b = 0, x, c
        elif h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        return int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)

    def paintEvent(self, event):
        self._ensure_wheel()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self._wheel_image:
            # center the image
            img = self._wheel_image
            x = (self.width() - img.width()) // 2
            y = (self.height() - img.height()) // 2
            painter.drawImage(x, y, img)

        # draw selector indicator
        size = min(self.width(), self.height())
        cx = self.width() // 2
        cy = self.height() // 2
        radius = size // 2 - 2
        angle = math.radians(self.h)
        sel_x = cx + self.s * radius * math.cos(angle)
        sel_y = cy + self.s * radius * math.sin(angle)
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        painter.setBrush(QBrush(Qt.transparent))
        painter.drawEllipse(QtCore.QPointF(sel_x, sel_y), 8, 8)

    def _pos_to_hs(self, pos):
        cx = self.width() // 2
        cy = self.height() // 2
        dx = pos.x() - cx
        dy = pos.y() - cy
        dist = math.hypot(dx, dy)
        radius = min(self.width(), self.height()) // 2 - 2
        if dist <= 0:
            return 0.0, 0.0
        s = min(1.0, dist / radius)
        h = (math.degrees(math.atan2(dy, dx)) + 360) % 360
        return h, s

    def mousePressEvent(self, event):
        h, s = self._pos_to_hs(event.pos())
        self.h, self.s = h, s
        r, g, b = self._hsv_to_rgb(self.h, self.s * 100.0, self.v * 100.0)
        self.color_changed.emit(r, g, b)
        self.update()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            h, s = self._pos_to_hs(event.pos())
            self.h, self.s = h, s
            r, g, b = self._hsv_to_rgb(self.h, self.s * 100.0, self.v * 100.0)
            self.color_changed.emit(r, g, b)
            self.update()

    def setSaturation(self, s_val):
        self.s = max(0.0, min(1.0, s_val / 100.0))
        r, g, b = self._hsv_to_rgb(self.h, self.s * 100.0, self.v * 100.0)
        self.color_changed.emit(r, g, b)
        self.update()

    def setValue(self, v_val):
        self.v = max(0.0, min(1.0, v_val / 100.0))
        r, g, b = self._hsv_to_rgb(self.h, self.s * 100.0, self.v * 100.0)
        self.color_changed.emit(r, g, b)
        self.update()

    def setRGB(self, r, g, b):
        # convert rgb to hsv and set internal state
        rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
        mx = max(rf, gf, bf)
        mn = min(rf, gf, bf)
        delta = mx - mn
        if delta == 0:
            h = 0.0
        elif mx == rf:
            h = (60 * (((gf - bf) / delta) % 6)) % 360
        elif mx == gf:
            h = (60 * (((bf - rf) / delta) + 2)) % 360
        else:
            h = (60 * (((rf - gf) / delta) + 4)) % 360
        s = 0.0 if mx == 0 else (delta / mx)
        v = mx
        self.h = h
        self.s = s
        self.v = v
        self.update()


class ColorPreview(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self._color = QColor(255, 255, 255)
        self.setMinimumSize(80, 80)

    def set_color(self, r: int, g: int, b: int):
        self._color = QColor(r, g, b)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -8)
        painter.setBrush(QBrush(self._color))
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawEllipse(rect)


STYLE = """
QWidget { background: #121212; color: #ffffff; font-family: 'Segoe UI', Roboto, Arial; }
QGroupBox { border: none; margin: 0; padding: 0; }
QGroupBox::title { subcontrol-origin: content; position: relative; left: 0; margin: 0; }
QPushButton { 
  background: #1f1f1f; 
  color: #ffffff; 
  border: none; 
  border-radius: 12px; 
  padding: 8px 12px; 
  font-weight: bold;
  font-size: 12px;
}
QPushButton:hover { background: #2a2a2a; }
QPushButton:pressed { background: #0d7377; }
QPushButton:disabled { background: rgba(100,100,100,0.2); color: rgba(255,255,255,0.4); }
QSlider::groove:horizontal { height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; }
QSlider::handle:horizontal { background: #0d7377; width: 18px; margin-top:-6px; margin-bottom:-6px; border-radius: 9px; }
QLineEdit, QComboBox { background: #1f1f1f; border: 1px solid rgba(255,255,255,0.1); padding: 6px; border-radius: 6px; }
QLabel { color: #ffffff; }
QTextEdit { background: #1a1a1a; color: #ffffff; border: 1px solid rgba(255,255,255,0.08); }
QTableWidget { background: #1a1a1a; color: #ffffff; border: none; gridline-color: rgba(255,255,255,0.06); }
QTableWidget::item { padding: 4px; }
QListWidget { background: #1f1f1f; color: #ffffff; border: 1px solid rgba(255,255,255,0.1); }
QHeaderView::section { background: #1f1f1f; color: #ffffff; padding: 4px; border: none; border-right: 1px solid rgba(255,255,255,0.08); }
"""


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LED Controller")
        self.setMinimumSize(360, 900)
        self.setMaximumWidth(500)
        self.worker = AsyncWorker()

        self.controller: BLELedController | None = None
        self.connected_address: str | None = None

        self._build_ui()
        self.setStyleSheet(STYLE)

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # === HEADER: Status ===
        header = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel("● Disconnected")
        self.status_label.setStyleSheet("color: #666; font-weight: bold; font-size: 14px;")
        header.addWidget(self.status_label)
        header.addStretch()
        layout.addLayout(header)

        # === SECTION 1: Compact Device Selector ===
        device_section = QtWidgets.QVBoxLayout()
        device_header = QtWidgets.QHBoxLayout()
        device_header.addWidget(QtWidgets.QLabel("Devices"))
        device_header.addStretch()
        device_section.addLayout(device_header)

        # Devices dropdown/list (compact)
        device_row = QtWidgets.QHBoxLayout()
        self.device_combo = QtWidgets.QComboBox()
        self.device_combo.setMinimumHeight(36)
        device_row.addWidget(self.device_combo, 1)
        
        # Icon-style buttons (small, round-ish, compact)
        scan_btn = QtWidgets.QPushButton("🔍")
        scan_btn.setMaximumWidth(40)
        scan_btn.setMaximumHeight(36)
        scan_btn.clicked.connect(self.scan_devices)
        scan_btn.setToolTip("Scan")
        device_row.addWidget(scan_btn)

        conn_btn = QtWidgets.QPushButton("✓")
        conn_btn.setMaximumWidth(40)
        conn_btn.setMaximumHeight(36)
        conn_btn.clicked.connect(self.connect_selected)
        conn_btn.setToolTip("Connect")
        self.conn_btn = conn_btn
        device_row.addWidget(conn_btn)

        disc_btn = QtWidgets.QPushButton("✕")
        disc_btn.setMaximumWidth(40)
        disc_btn.setMaximumHeight(36)
        disc_btn.clicked.connect(self.disconnect)
        disc_btn.setToolTip("Disconnect")
        device_row.addWidget(disc_btn)

        device_section.addLayout(device_row)
        layout.addLayout(device_section)

        # === SECTION 2: Power Controls ===
        power_row = QtWidgets.QHBoxLayout()
        on_btn = QtWidgets.QPushButton("◉ ON")
        on_btn.setMinimumHeight(44)
        on_btn.setStyleSheet("""
            QPushButton {
                background: #0d7377;
                color: #ffffff;
                font-weight: bold;
                border: none;
                border-radius: 12px;
                font-size: 14px;
            }
            QPushButton:hover { background: #14919b; }
            QPushButton:pressed { background: #0a5660; }
        """)
        on_btn.clicked.connect(self.turn_on)
        power_row.addWidget(on_btn)

        off_btn = QtWidgets.QPushButton("◯ OFF")
        off_btn.setMinimumHeight(44)
        off_btn.setStyleSheet("""
            QPushButton {
                background: #540d0d;
                color: #ffffff;
                font-weight: bold;
                border: none;
                border-radius: 12px;
                font-size: 14px;
            }
            QPushButton:hover { background: #7a1414; }
            QPushButton:pressed { background: #400a0a; }
        """)
        off_btn.clicked.connect(self.turn_off)
        power_row.addWidget(off_btn)
        layout.addLayout(power_row)

        # === SECTION 3: Color Wheel ===
        color_section = QtWidgets.QVBoxLayout()
        color_section.addWidget(QtWidgets.QLabel("Color"))

        wheel_container = QtWidgets.QWidget()
        wheel_layout = QtWidgets.QHBoxLayout(wheel_container)
        wheel_layout.setContentsMargins(0, 0, 0, 0)
        wheel_layout.setSpacing(12)
        self.color_wheel = ColorWheelWidget()
        self.color_wheel.color_changed.connect(self.on_wheel_color_changed)

        # Preview column to the right of the wheel
        preview_col = QtWidgets.QVBoxLayout()
        preview_col.setAlignment(Qt.AlignTop)
        self.preview = ColorPreview()
        preview_col.addWidget(self.preview, alignment=Qt.AlignCenter)

        self.preview_hex = QtWidgets.QLabel("#FFFFFF")
        self.preview_hex.setAlignment(Qt.AlignCenter)
        preview_col.addWidget(self.preview_hex)

        self.preview_rgb = QtWidgets.QLabel("RGB(255,255,255)")
        self.preview_rgb.setAlignment(Qt.AlignCenter)
        preview_col.addWidget(self.preview_rgb)

        # Quick apply small button
        quick_apply = QtWidgets.QPushButton("Apply")
        quick_apply.setMaximumWidth(100)
        quick_apply.clicked.connect(self.apply_color)
        preview_col.addWidget(quick_apply, alignment=Qt.AlignCenter)

        wheel_layout.addStretch()
        wheel_layout.addWidget(self.color_wheel)
        wheel_layout.addLayout(preview_col)
        wheel_layout.addStretch()
        color_section.addWidget(wheel_container)

        # Saturation & Value sliders (minimal, below wheel)
        sat_row = QtWidgets.QHBoxLayout()
        sat_row.addWidget(QtWidgets.QLabel("Sat"))
        self.sat_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.sat_slider.setRange(0, 100)
        self.sat_slider.setValue(100)
        self.sat_slider.sliderMoved.connect(lambda v: self.color_wheel.setSaturation(v))
        sat_row.addWidget(self.sat_slider)
        color_section.addLayout(sat_row)

        val_row = QtWidgets.QHBoxLayout()
        val_row.addWidget(QtWidgets.QLabel("Val"))
        self.val_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.val_slider.setRange(0, 100)
        self.val_slider.setValue(100)
        self.val_slider.sliderMoved.connect(lambda v: self.color_wheel.setValue(v))
        val_row.addWidget(self.val_slider)
        color_section.addLayout(val_row)

        layout.addLayout(color_section)

        # === SECTION 4: Brightness ===
        bright_row = QtWidgets.QHBoxLayout()
        bright_row.addWidget(QtWidgets.QLabel("Brightness"))
        self.brightness_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(100)
        self.brightness_label = QtWidgets.QLabel("100%")
        self.brightness_slider.valueChanged.connect(lambda v: self.brightness_label.setText(f"{v}%"))
        bright_row.addWidget(self.brightness_slider)
        bright_row.addWidget(self.brightness_label, 0)
        layout.addLayout(bright_row)

        # Apply color button
        apply_btn = QtWidgets.QPushButton("Apply Color")
        apply_btn.setMinimumHeight(40)
        apply_btn.clicked.connect(self.apply_color)
        layout.addWidget(apply_btn)

        # === SECTION 5: Presets & Modes (Tabs) ===
        tabs = QtWidgets.QTabWidget()
        tabs.setStyleSheet("""
            QTabBar::tab { padding: 8px 12px; }
        """)

        # Presets tab
        presets_widget = QtWidgets.QWidget()
        presets_layout = QtWidgets.QVBoxLayout(presets_widget)
        self.presets_list = QtWidgets.QListWidget()
        presets_layout.addWidget(self.presets_list)
        preset_btn_row = QtWidgets.QHBoxLayout()
        PresetApplyBtn = QtWidgets.QPushButton("Apply")
        PresetApplyBtn.clicked.connect(self.apply_selected_preset)
        preset_btn_row.addWidget(PresetApplyBtn)
        SavePresetBtn = QtWidgets.QPushButton("Save")
        SavePresetBtn.clicked.connect(self.save_preset_dialog)
        preset_btn_row.addWidget(SavePresetBtn)
        DelPresetBtn = QtWidgets.QPushButton("Remove")
        DelPresetBtn.clicked.connect(self.remove_selected_preset)
        preset_btn_row.addWidget(DelPresetBtn)
        presets_layout.addLayout(preset_btn_row)
        tabs.addTab(presets_widget, "Presets")

        # Modes tab
        modes_widget = QtWidgets.QWidget()
        modes_layout = QtWidgets.QVBoxLayout(modes_widget)
        self.mode_input = QtWidgets.QLineEdit()
        self.mode_input.setPlaceholderText("MODE_1 or 0x25")
        modes_layout.addWidget(self.mode_input)
        modes_layout.addWidget(QtWidgets.QLabel("Speed"))
        self.speed_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.speed_slider.setRange(0, 255)
        self.speed_slider.setValue(50)
        modes_layout.addWidget(self.speed_slider)
        mode_btn_row = QtWidgets.QHBoxLayout()
        ListModesBtn = QtWidgets.QPushButton("List")
        ListModesBtn.clicked.connect(self.show_modes)
        mode_btn_row.addWidget(ListModesBtn)
        SetModeBtn = QtWidgets.QPushButton("Set")
        SetModeBtn.clicked.connect(self.set_mode)
        mode_btn_row.addWidget(SetModeBtn)
        modes_layout.addLayout(mode_btn_row)
        tabs.addTab(modes_widget, "Modes")

        layout.addWidget(tabs)

        # === SECTION 6: Default MAC ===
        default_row = QtWidgets.QHBoxLayout()
        self.default_mac_edit = QtWidgets.QLineEdit()
        self.default_mac_edit.setText(load_default_mac() or "")
        self.default_mac_edit.setPlaceholderText("Default MAC...")
        self.default_mac_edit.setMaximumHeight(32)
        default_row.addWidget(self.default_mac_edit)
        set_def_btn = QtWidgets.QPushButton("✓")
        set_def_btn.setMaximumWidth(40)
        set_def_btn.setMaximumHeight(32)
        set_def_btn.clicked.connect(self.set_default_mac)
        set_def_btn.setToolTip("Set default")
        default_row.addWidget(set_def_btn)
        rm_def_btn = QtWidgets.QPushButton("✕")
        rm_def_btn.setMaximumWidth(40)
        rm_def_btn.setMaximumHeight(32)
        rm_def_btn.clicked.connect(self.remove_default_mac)
        rm_def_btn.setToolTip("Clear default")
        default_row.addWidget(rm_def_btn)
        layout.addLayout(default_row)

        # === SECTION 7: Log ===
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        layout.addStretch()
        self.refresh_presets()

    def _update_device_combo(self, devices):
        """Update device combo with scan results."""
        self.device_combo.clear()
        for d in devices:
            name = d.name or "Unknown"
            self.device_combo.addItem(f"{name} ({d.address})", d.address)

    # Helpers
    def log(self, *parts: object):
        self.log_text.append(" ".join(map(str, parts)))

    def run_async(self, coro, on_done=None, on_error=None):
        local_worker = AsyncWorker()
        if on_done:
            local_worker.finished.connect(on_done)
        if on_error:
            local_worker.error.connect(on_error)
        local_worker.run_coro(coro)

    # Device functions
    def scan_devices(self):
        self.status_label.setText("● Scanning...")
        self.log("Scanning for devices...")

        async def do_scan():
            scanner = DeviceScanner()
            devices = await scanner.scan(duration=5, led_only=True)
            return devices

        def done(devices):
            self.status_label.setText("● Scan complete")
            self._update_device_combo(devices or [])
            self.log(f"Found {len(devices) if devices else 0} device(s)")

        def err(e):
            self.status_label.setText("● Scan failed")
            self.log(f"Scan error: {e}")

        self.run_async(do_scan(), on_done=done, on_error=err)

    def connect_selected(self):
        addr = self.device_combo.currentData()
        if not addr:
            QtWidgets.QMessageBox.information(self, "Select", "Please scan and select a device, or enter default MAC")
            return
        self.connect(addr)

    def connect(self, address: str):
        self.status_label.setText(f"● Connecting...")
        self.log(f"Connecting to {address}...")

        async def do_connect():
            controller = BLELedController(address)
            await controller.connect(timeout=10)
            return controller

        def done(controller):
            self.controller = controller
            self.connected_address = address
            self.status_label.setText(f"● Connected")
            self.log(f"Connected!")

        def err(e):
            self.status_label.setText("● Connect failed")
            self.log(f"Error: {e}")

        self.run_async(do_connect(), on_done=done, on_error=err)

    def disconnect(self):
        if not self.controller:
            return

        async def do_disconnect():
            await self.controller.disconnect()

        def done(_):
            self.log("Disconnected")
            self.controller = None
            self.connected_address = None
            self.status_label.setText("● Disconnected")

        self.run_async(do_disconnect(), on_done=done, on_error=lambda e: self.log(e))

    # Color wheel integration
    def on_wheel_color_changed(self, r, g, b):
        """Update preview and store current color for apply/save."""
        self.current_rgb = (r, g, b)
        hexv = f"#{r:02X}{g:02X}{b:02X}"
        self.preview.set_color(r, g, b)
        self.preview_hex.setText(hexv)
        self.preview_rgb.setText(f"RGB({r},{g},{b})")

    # Power / Color
    def turn_on(self):
        if not self.controller:
            QtWidgets.QMessageBox.information(self, "Not connected", "Please connect to a device first")
            return
        self.run_async(self.controller.turn_on(), on_done=lambda _: self.log("Turned on"), on_error=lambda e: self.log(e))

    def turn_off(self):
        if not self.controller:
            QtWidgets.QMessageBox.information(self, "Not connected", "Please connect to a device first")
            return
        self.run_async(self.controller.turn_off(), on_done=lambda _: self.log("Turned off"), on_error=lambda e: self.log(e))

    def apply_color(self):
        if not self.controller:
            QtWidgets.QMessageBox.information(self, "Not connected", "Please connect to a device first")
            return
        if hasattr(self, 'current_rgb') and self.current_rgb is not None:
            r, g, b = self.current_rgb
        else:
            # fallback: compute from wheel internals
            r, g, b = self.color_wheel._hsv_to_rgb(self.color_wheel.h, self.color_wheel.s * 100.0, self.color_wheel.v * 100.0)
        br = self.brightness_slider.value()
        self.run_async(self.controller.set_rgb(r, g, b, br), on_done=lambda _: self.log(f"Color applied: RGB({r},{g},{b}) @ {br}%"), on_error=lambda e: self.log(e))

    def save_preset_dialog(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "Preset name", "Enter preset name:")
        if not ok or not name:
            return
        r, g, b = self.color_wheel.hsvToRgb(int(self.color_wheel.h), int(self.color_wheel.s), int(self.color_wheel.v))
        br = self.brightness_slider.value()
        if save_preset_in_config(name, r, g, b, br):
            self.log(f"Preset saved: {name}")
            self.refresh_presets()
        else:
            QtWidgets.QMessageBox.critical(self, "Error", "Could not save preset")

    def refresh_presets(self):
        self.presets_list.clear()
        presets = load_presets()
        for name, v in presets.items():
            self.presets_list.addItem(f"{name}: RGB({v['r']},{v['g']},{v['b']})")

    def apply_selected_preset(self):
        sel = self.presets_list.currentItem()
        if not sel:
            return
        name = sel.text().split(":", 1)[0]
        p = get_preset_from_config(name)
        if not p:
            return
        self.color_wheel.setRGB(p["r"], p["g"], p["b"])
        self.brightness_slider.setValue(p.get("brightness", 100))
        if self.controller:
            self.apply_color()

    def remove_selected_preset(self):
        sel = self.presets_list.currentItem()
        if not sel:
            return
        name = sel.text().split(":", 1)[0]
        if QtWidgets.QMessageBox.question(self, "Remove", f"Remove preset '{name}'?") != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        if remove_preset_from_config(name):
            self.log(f"Removed preset: {name}")
            self.refresh_presets()

    # Modes
    def show_modes(self):
        try:
            from ble_led_controller.constants import list_all_modes
            modes = list_all_modes()
            txt = "\n".join([f"0x{m['id']:02X} - {m['name']}" for m in modes])
        except Exception:
            txt = "Mode list unavailable"
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Modes")
        layout = QtWidgets.QVBoxLayout(dlg)
        t = QtWidgets.QTextEdit()
        t.setReadOnly(True)
        t.setText(txt)
        layout.addWidget(t)
        dlg.exec()

    def set_mode(self):
        if not self.controller:
            QtWidgets.QMessageBox.information(self, "Not connected", "Please connect to a device first")
            return
        mode_text = self.mode_input.text().strip()
        if not mode_text:
            QtWidgets.QMessageBox.information(self, "Mode", "Provide mode name or hex (e.g., MODE_1 or 0x25)")
            return
        speed = self.speed_slider.value()
        try:
            if mode_text.lower().startswith("0x"):
                mode_id = int(mode_text, 16)
                mode = LEDMode.from_id(mode_id)
            else:
                mode = LEDMode[mode_text.upper()]
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Invalid mode", str(e))
            return
        self.run_async(self.controller.set_mode(mode, speed), on_done=lambda _: self.log(f"Mode: {mode.name} speed={speed}"), on_error=lambda e: self.log(e))

    # Default MAC
    def set_default_mac(self):
        mac = self.default_mac_edit.text().strip()
        if not mac:
            QtWidgets.QMessageBox.information(self, "Default MAC", "Enter a MAC address")
            return
        if set_default_mac_in_config(mac):
            self.log(f"Default MAC set")
        else:
            QtWidgets.QMessageBox.critical(self, "Error", "Could not save default MAC")

    def remove_default_mac(self):
        if remove_default_mac_from_config():
            self.default_mac_edit.setText("")
            self.log("Default MAC removed")


def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
