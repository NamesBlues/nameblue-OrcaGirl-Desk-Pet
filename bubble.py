"""气泡窗口：独立的小透明窗口，浮在桌宠头顶，永不接收鼠标事件。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, QTimer, Qt
from PySide6.QtGui import QGuiApplication, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from config import BASE_BUBBLE_WIDTH

FADE_MS = 160
# 兜底：万一系统的窗口透明度动画没生效，600ms 后强制显示出来
SAFETY_MS = 600


class BubbleWindow(QWidget):
    def __init__(self, cfg) -> None:
        super().__init__(None)
        self.cfg = cfg
        self._pixmap = QPixmap()

        self.setWindowTitle("虎鲸桌宠气泡")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput
            | Qt.WindowDoesNotAcceptFocus
        )

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.fade_out)

        self._safety_timer = QTimer(self)
        self._safety_timer.setSingleShot(True)
        self._safety_timer.timeout.connect(self._ensure_visible)

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(FADE_MS)
        self._fade.setEasingCurve(QEasingCurve.InOutQuad)
        self._fade.finished.connect(self._on_fade_finished)

    # ---------- 对外接口 ----------

    def show_bubble(self, image_path: Path, anchor: QRect) -> None:
        """在 anchor（桌宠的全局矩形）上方显示一张气泡图。"""
        source = QPixmap(str(image_path))
        if source.isNull():
            return

        scale = float(self.cfg["bubble_scale"])
        # 同样以基准宽度换算，素材分辨率再高也不会让气泡糊满屏幕
        logical_w = max(60, round(BASE_BUBBLE_WIDTH * scale))
        logical_h = max(40, round(logical_w * source.height() / source.width()))

        screen = QGuiApplication.screenAt(anchor.center()) or QGuiApplication.primaryScreen()
        dpr = float(screen.devicePixelRatio()) if screen else 1.0

        pixmap = source.scaled(
            max(1, round(logical_w * dpr)),
            max(1, round(logical_h * dpr)),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
        pixmap.setDevicePixelRatio(dpr)
        self._pixmap = pixmap

        self.setFixedSize(logical_w, logical_h)
        self.move(self._bubble_position(anchor, logical_w, logical_h))
        self.update()

        self._hide_timer.stop()
        self._safety_timer.stop()
        self._fade.stop()
        self.setWindowOpacity(0.0)
        self.show()

        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()
        self._safety_timer.start(SAFETY_MS)
        self._hide_timer.start(max(500, int(float(self.cfg["bubble_duration"]) * 1000)))

    def fade_out(self) -> None:
        self._fade.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def hide_now(self) -> None:
        self._hide_timer.stop()
        self._safety_timer.stop()
        self._fade.stop()
        self.hide()

    # ---------- 内部 ----------

    def _bubble_position(self, anchor: QRect, width: int, height: int) -> QPoint:
        """气泡放在桌宠头顶，尾巴稍微压住脑袋；上方放不下就改到下方。"""
        overlap = int(anchor.height() * float(self.cfg["bubble_gap"]))
        x = anchor.center().x() - width // 2
        y = anchor.top() - height + overlap

        screen = QGuiApplication.screenAt(anchor.center()) or QGuiApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            x = min(max(x, geo.left() + 4), max(geo.left() + 4, geo.right() - width - 4))
            if y < geo.top() + 4:
                y = min(anchor.bottom() - overlap, geo.bottom() - height - 4)
        return QPoint(x, y)

    def _ensure_visible(self) -> None:
        if self.isVisible() and self.windowOpacity() < 0.5:
            self.setWindowOpacity(1.0)

    def _on_fade_finished(self) -> None:
        if self.windowOpacity() < 0.02:
            self.hide()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt 命名
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawPixmap(0, 0, self._pixmap)
