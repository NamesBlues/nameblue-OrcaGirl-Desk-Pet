"""系统托盘图标与右键菜单。"""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from config import TRAY_IMAGE


def _fallback_icon() -> QIcon:
    """素材缺失时画一个蓝色圆点，至少让托盘图标有东西可显示。"""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setBrush(QColor("#2f6fd0"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(4, 4, 56, 56)
    painter.end()
    return QIcon(pixmap)


class PetTray(QObject):
    visibility_toggled = Signal(bool)
    speak_requested = Signal()
    settings_requested = Signal()
    autostart_toggled = Signal(bool)
    open_assets_requested = Signal()
    quit_requested = Signal()

    def __init__(self, visible: bool = True, autostart: bool = False, parent=None) -> None:
        super().__init__(parent)

        icon = QIcon(str(TRAY_IMAGE)) if TRAY_IMAGE.exists() else QIcon()
        self._icon = QSystemTrayIcon(icon if not icon.isNull() else _fallback_icon())
        self._icon.setToolTip("虎鲸桌宠")

        menu = QMenu()

        self._show_action = QAction("显示桌宠", menu)
        self._show_action.setCheckable(True)
        self._show_action.setChecked(visible)
        self._show_action.toggled.connect(self.visibility_toggled.emit)
        menu.addAction(self._show_action)

        speak = QAction("说句话", menu)
        speak.triggered.connect(self.speak_requested.emit)
        menu.addAction(speak)

        menu.addSeparator()

        settings = QAction("设置…", menu)
        settings.triggered.connect(self.settings_requested.emit)
        menu.addAction(settings)

        self._autostart_action = QAction("开机自启", menu)
        self._autostart_action.setCheckable(True)
        self._autostart_action.setChecked(autostart)
        self._autostart_action.toggled.connect(self.autostart_toggled.emit)
        menu.addAction(self._autostart_action)

        assets = QAction("打开素材文件夹", menu)
        assets.triggered.connect(self.open_assets_requested.emit)
        menu.addAction(assets)

        menu.addSeparator()

        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self._menu = menu
        self._icon.setContextMenu(menu)
        self._icon.activated.connect(self._on_activated)
        self._icon.show()

    # ---------- 外部同步状态 ----------

    def set_visible_checked(self, visible: bool) -> None:
        self._show_action.blockSignals(True)
        self._show_action.setChecked(visible)
        self._show_action.blockSignals(False)

    def set_autostart_checked(self, enabled: bool) -> None:
        self._autostart_action.blockSignals(True)
        self._autostart_action.setChecked(enabled)
        self._autostart_action.blockSignals(False)

    def show_message(self, title: str, text: str) -> None:
        self._icon.showMessage(title, text, QSystemTrayIcon.Information, 3000)

    @staticmethod
    def is_available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def hide(self) -> None:
        self._icon.hide()

    # ---------- 内部 ----------

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_action.setChecked(not self._show_action.isChecked())
