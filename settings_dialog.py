"""设置对话框。"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from config import CONFIG_PATH, DEFAULTS


class SettingsDialog(QDialog):
    """改完点保存才写回配置。"""

    def __init__(self, cfg, parent=None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("虎鲸桌宠 · 设置")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setMinimumWidth(380)

        root = QVBoxLayout(self)

        # ---- 外观 ----
        appearance = QGroupBox("外观")
        form = QFormLayout(appearance)

        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(40, 250)
        self.scale_slider.setValue(round(float(cfg["pet_scale"]) * 100))
        self.scale_label = QLabel()
        self._sync_scale_label(self.scale_slider.value())
        self.scale_slider.valueChanged.connect(self._sync_scale_label)
        scale_row = QHBoxLayout()
        scale_row.addWidget(self.scale_slider, 1)
        scale_row.addWidget(self.scale_label)
        form.addRow("桌宠大小", self._wrap(scale_row))

        self.bubble_scale = QDoubleSpinBox()
        self.bubble_scale.setRange(0.4, 2.0)
        self.bubble_scale.setSingleStep(0.05)
        self.bubble_scale.setValue(float(cfg["bubble_scale"]))
        self.bubble_scale.setMaximumWidth(90)
        form.addRow("气泡大小", self.bubble_scale)

        self.always_on_top = QCheckBox("始终显示在其他窗口上方")
        self.always_on_top.setChecked(bool(cfg["always_on_top"]))
        form.addRow("", self.always_on_top)

        self.pixel_hit = QCheckBox("只在角色本体上响应鼠标（透明处点击穿透）")
        self.pixel_hit.setChecked(bool(cfg["pixel_perfect_hit"]))
        form.addRow("", self.pixel_hit)

        root.addWidget(appearance)

        # ---- 说话 ----
        talking = QGroupBox("说话")
        form2 = QFormLayout(talking)

        self.greeting = QCheckBox("启动时打招呼")
        self.greeting.setChecked(bool(cfg["startup_greeting"]))
        form2.addRow("", self.greeting)

        self.click_speak = QCheckBox("点击桌宠时说一句")
        self.click_speak.setChecked(bool(cfg["click_to_speak"]))
        form2.addRow("", self.click_speak)

        self.duration = QDoubleSpinBox()
        self.duration.setRange(1.0, 30.0)
        self.duration.setSingleStep(0.5)
        self.duration.setSuffix(" 秒")
        self.duration.setValue(float(cfg["bubble_duration"]))
        self.duration.setMaximumWidth(110)
        form2.addRow("气泡停留", self.duration)

        self.interval_min = QSpinBox()
        self.interval_min.setRange(3, 3600)
        self.interval_min.setSuffix(" 秒")
        self.interval_min.setValue(round(float(cfg["bubble_interval_min"])))
        self.interval_min.setMaximumWidth(90)
        self.interval_max = QSpinBox()
        self.interval_max.setRange(3, 3600)
        self.interval_max.setSuffix(" 秒")
        self.interval_max.setValue(round(float(cfg["bubble_interval_max"])))
        self.interval_max.setMaximumWidth(90)
        interval_row = QHBoxLayout()
        interval_row.addWidget(self.interval_min)
        interval_row.addWidget(QLabel("～"))
        interval_row.addWidget(self.interval_max)
        interval_row.addStretch(1)
        form2.addRow("随机说话间隔", self._wrap(interval_row))

        root.addWidget(talking)

        # ---- 系统 ----
        system = QGroupBox("系统")
        form3 = QFormLayout(system)

        self.autostart = QCheckBox("开机自动启动")
        self.autostart.setChecked(bool(cfg["autostart"]))
        form3.addRow("", self.autostart)

        open_config = QPushButton("打开配置文件")
        open_config.clicked.connect(self._open_config)
        form3.addRow("", open_config)

        root.addWidget(system)

        # ---- 按钮 ----
        buttons = QDialogButtonBox()
        reset = buttons.addButton("恢复默认", QDialogButtonBox.ResetRole)
        cancel = buttons.addButton("取消", QDialogButtonBox.RejectRole)
        save = buttons.addButton("保存", QDialogButtonBox.AcceptRole)
        save.setDefault(True)
        reset.clicked.connect(self._reset)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        root.addWidget(buttons)

    # ---------- 内部 ----------

    @staticmethod
    def _wrap(layout) -> "QWidget":  # noqa: F821 - 仅作类型提示
        from PySide6.QtWidgets import QWidget

        holder = QWidget()
        holder.setLayout(layout)
        return holder

    def _sync_scale_label(self, value: int) -> None:
        self.scale_label.setText(f"{value}%")
        self.scale_label.setMinimumWidth(44)
        self.scale_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def _open_config(self) -> None:
        if not CONFIG_PATH.exists():
            self.cfg.save()
        os.startfile(str(CONFIG_PATH))  # noqa: S606 - Windows 桌面程序，直接用系统默认程序打开

    def _reset(self) -> None:
        self.scale_slider.setValue(round(float(DEFAULTS["pet_scale"]) * 100))
        self.bubble_scale.setValue(float(DEFAULTS["bubble_scale"]))
        self.always_on_top.setChecked(bool(DEFAULTS["always_on_top"]))
        self.pixel_hit.setChecked(bool(DEFAULTS["pixel_perfect_hit"]))
        self.greeting.setChecked(bool(DEFAULTS["startup_greeting"]))
        self.click_speak.setChecked(bool(DEFAULTS["click_to_speak"]))
        self.duration.setValue(float(DEFAULTS["bubble_duration"]))
        self.interval_min.setValue(round(float(DEFAULTS["bubble_interval_min"])))
        self.interval_max.setValue(round(float(DEFAULTS["bubble_interval_max"])))
        self.autostart.setChecked(bool(DEFAULTS["autostart"]))

    def apply_to(self, cfg) -> None:
        """把界面上的值写进配置对象（不落盘）。"""
        cfg["pet_scale"] = self.scale_slider.value() / 100.0
        cfg["bubble_scale"] = self.bubble_scale.value()
        cfg["always_on_top"] = self.always_on_top.isChecked()
        cfg["pixel_perfect_hit"] = self.pixel_hit.isChecked()
        cfg["startup_greeting"] = self.greeting.isChecked()
        cfg["click_to_speak"] = self.click_speak.isChecked()
        cfg["bubble_duration"] = self.duration.value()
        low = self.interval_min.value()
        high = self.interval_max.value()
        cfg["bubble_interval_min"] = float(min(low, high))
        cfg["bubble_interval_max"] = float(max(low, high))
        cfg["autostart"] = self.autostart.isChecked()
