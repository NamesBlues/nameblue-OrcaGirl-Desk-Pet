"""把各个部件组装起来，并管理说话节奏、托盘状态、单实例。"""

from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from autostart import is_enabled, set_enabled
from bubble import BubbleWindow
from config import ASSETS_DIR, BUBBLES_DIR, PET_IMAGE, Config, bubble_files
from pet import PetWindow
from settings_dialog import SettingsDialog
from tray import PetTray

SERVER_NAME = "OrcaDesktopPet-single-instance"


def _acquire_single_instance() -> Optional[QLocalServer]:
    """返回 QLocalServer 表示本次是第一个实例；返回 None 表示已有实例在跑。"""
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(300):
        socket.write(b"show")
        socket.flush()
        socket.waitForBytesWritten(300)
        socket.disconnectFromServer()
        return None

    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    server.listen(SERVER_NAME)
    return server


class PetApp(QObject):
    def __init__(self, qapp: QApplication) -> None:
        super().__init__()
        self.qapp = qapp
        self.cfg = Config.load()
        self._settings_dialog: Optional[SettingsDialog] = None

        self.pet = PetWindow(self.cfg)
        self.bubble = BubbleWindow(self.cfg)
        self.tray = PetTray(
            visible=True,
            autostart=is_enabled(),
        )

        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._on_idle)

        self._wire()

        # 配置里的开机自启是「期望值」，注册表是「实际值」，不一致就以配置为准同步一次
        if bool(self.cfg["autostart"]) != is_enabled():
            self._apply_autostart(bool(self.cfg["autostart"]))
        self.tray.set_autostart_checked(is_enabled())

    def _wire(self) -> None:
        self.tray.visibility_toggled.connect(self.set_pet_visible)
        self.tray.speak_requested.connect(lambda: self.speak(force=True))
        self.tray.settings_requested.connect(self.open_settings)
        self.tray.autostart_toggled.connect(self._apply_autostart)
        self.tray.open_assets_requested.connect(self._open_assets)
        self.tray.quit_requested.connect(self.quit)
        self.pet.clicked.connect(self._on_pet_clicked)
        self.pet.moved.connect(self._on_pet_moved)

    # ---------- 启动 ----------

    def start(self) -> None:
        self.pet.restore_position()
        self.pet.show()
        self.pet.raise_()

        if self.cfg["startup_greeting"]:
            QTimer.singleShot(700, self._greet)
        self._schedule_next()

    def _greet(self) -> None:
        startup = BUBBLES_DIR / str(self.cfg["startup_bubble"])
        self.speak(path=startup if startup.exists() else None, force=True)

    # ---------- 说话 ----------

    def speak(self, path: Optional[Path] = None, force: bool = False) -> None:
        if not force and not self.pet.isVisible():
            return
        if path is None:
            pool = self._idle_pool()
            if not pool:
                return
            path = random.choice(pool)
        if not path.exists():
            return
        self.bubble.show_bubble(path, self.pet.frameGeometry())

    def _idle_pool(self):
        files = bubble_files()
        exclude = set(self.cfg.get("idle_exclude") or [])
        pool = [f for f in files if f.name not in exclude]
        return pool or files

    def _schedule_next(self) -> None:
        low = float(self.cfg["bubble_interval_min"])
        high = float(self.cfg["bubble_interval_max"])
        if high < low:
            low, high = high, low
        self._idle_timer.start(max(3000, int(random.uniform(low, high) * 1000)))

    def _on_idle(self) -> None:
        self.speak()
        self._schedule_next()

    def _on_pet_clicked(self) -> None:
        if self.cfg["click_to_speak"]:
            self.speak(force=True)

    # ---------- 窗口控制 ----------

    def set_pet_visible(self, visible: bool) -> None:
        self.tray.set_visible_checked(visible)
        if visible:
            self.pet.show()
            self.pet.raise_()
        else:
            self.bubble.hide_now()
            self.pet.hide()

    def show_from_other_instance(self) -> None:
        """第二个实例被启动时，把已经跑着的这个叫出来。"""
        self.set_pet_visible(True)

    def _on_pet_moved(self, position) -> None:
        self.cfg["pet_position"] = [position.x(), position.y()]
        self.cfg.save()

    # ---------- 设置 ----------

    def open_settings(self) -> None:
        if self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(self.cfg)
            self._settings_dialog.finished.connect(self._on_settings_closed)
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    def _on_settings_closed(self, result: int) -> None:
        dialog = self._settings_dialog
        self._settings_dialog = None
        if dialog is None:
            return
        dialog.deleteLater()
        if result != SettingsDialog.Accepted:
            return

        old_top = bool(self.cfg["always_on_top"])
        old_autostart = is_enabled()
        dialog.apply_to(self.cfg)

        if bool(self.cfg["always_on_top"]) != old_top:
            self.pet.apply_always_on_top()
        self.pet.reload()

        if bool(self.cfg["autostart"]) != old_autostart:
            self._apply_autostart(bool(self.cfg["autostart"]))

        self.cfg.save()
        self._schedule_next()

    def _apply_autostart(self, enabled: bool) -> None:
        ok = set_enabled(enabled)
        actual = is_enabled()
        self.cfg["autostart"] = actual
        self.tray.set_autostart_checked(actual)
        if enabled and not ok:
            self.tray.show_message("虎鲸桌宠", "开机自启设置失败，请检查系统权限。")

    def _open_assets(self) -> None:
        target = ASSETS_DIR if ASSETS_DIR.exists() else ASSETS_DIR.parent
        try:
            os.startfile(str(target))  # noqa: S606 - Windows 桌面程序
        except OSError as exc:
            self.tray.show_message("虎鲸桌宠", f"打不开素材文件夹：{exc}")

    # ---------- 退出 ----------

    def quit(self) -> None:
        self.cfg.save()
        self._idle_timer.stop()
        self.tray.hide()
        self.bubble.hide_now()
        self.pet.quit_cleanly()
        self.qapp.quit()


def _check_assets() -> Optional[str]:
    if not PET_IMAGE.exists():
        return (
            f"找不到桌宠素材：\n{PET_IMAGE}\n\n"
            "请先在项目目录执行：\n    python tools/prepare_assets.py"
        )
    if not bubble_files():
        return f"气泡素材是空的：\n{BUBBLES_DIR}\n\n请先执行 tools/prepare_assets.py"
    return None


def run() -> int:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("OrcaDesktopPet")
    app.setQuitOnLastWindowClosed(False)

    problem = _check_assets()
    if problem:
        QMessageBox.critical(None, "虎鲸桌宠", problem)
        return 1

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.warning(None, "虎鲸桌宠", "当前系统托盘不可用，可能无法正常操作桌宠。")

    server = _acquire_single_instance()
    if server is None:
        return 0

    pet_app = PetApp(app)
    if server is not None:
        server.newConnection.connect(pet_app.show_from_other_instance)

    pet_app.start()
    return app.exec()
