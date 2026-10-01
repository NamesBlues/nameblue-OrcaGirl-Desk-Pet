"""桌宠主窗口：无边框、背景全透明、可拖拽、可点击。"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QPixmap, QRegion
from PySide6.QtWidgets import QWidget

from config import BASE_PET_HEIGHT, PET_IMAGE

# 超过这个像素距离才算「拖拽」，否则算「点击」
DRAG_THRESHOLD = 4


class PetWindow(QWidget):
    clicked = Signal()
    moved = Signal(QPoint)

    def __init__(self, cfg) -> None:
        super().__init__(None)
        self.cfg = cfg
        self._press_global: Optional[QPoint] = None
        self._press_window: Optional[QPoint] = None
        self._dragging = False
        self._allow_close = False
        self._source = QPixmap()
        self._pixmap = QPixmap()

        self.setWindowTitle("虎鲸桌宠")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setCursor(Qt.OpenHandCursor)
        self._apply_flags()
        self.reload()

    # ---------- 窗口属性 ----------

    def _apply_flags(self) -> None:
        flags = Qt.FramelessWindowHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus
        if self.cfg["always_on_top"]:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def apply_always_on_top(self) -> None:
        """改了「始终置顶」之后需要重建窗口标志并重新显示。"""
        was_visible = self.isVisible()
        position = self.pos()
        self._apply_flags()
        if was_visible:
            self.show()
            self.move(position)

    # ---------- 绘制 ----------

    def reload(self) -> None:
        """按当前缩放重新载入并绘制素材。"""
        self._source = QPixmap(str(PET_IMAGE))

        scale = float(self.cfg["pet_scale"])
        if self._source.isNull():
            logical_w, logical_h = round(180 * scale), round(BASE_PET_HEIGHT * scale)
        else:
            # 以 BASE_PET_HEIGHT 为基准算高度，宽度按素材宽高比推出来，
            # 这样换任何比例的立绘都不会突然变得巨大或压扁。
            logical_h = max(32, round(BASE_PET_HEIGHT * scale))
            logical_w = max(
                24, round(logical_h * self._source.width() / self._source.height())
            )

        dpr = self._device_pixel_ratio()
        if not self._source.isNull():
            pixmap = self._source.scaled(
                max(1, round(logical_w * dpr)),
                max(1, round(logical_h * dpr)),
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation,
            )
            pixmap.setDevicePixelRatio(dpr)
            self._pixmap = pixmap

        self.setFixedSize(logical_w, logical_h)
        self._apply_click_mask(logical_w, logical_h)
        self.update()

    def _device_pixel_ratio(self) -> float:
        screen = self.screen() or QGuiApplication.primaryScreen()
        return float(screen.devicePixelRatio()) if screen else 1.0

    def _apply_click_mask(self, width: int, height: int) -> None:
        """只让角色本体接收鼠标，全透明的地方点击可以穿透到桌面。

        mask 由 alpha > 0 的像素构成，也就是所有会被画出来的像素都保留在区域内，
        所以渲染结果完全不变，纯粹是影响鼠标命中判定。
        """
        if not self.cfg["pixel_perfect_hit"] or self._source.isNull():
            self.clearMask()
            return
        image = (
            self._source.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            .toImage()
            .convertToFormat(QImage.Format_ARGB32)
        )
        self.setMask(self._alpha_region(image))

    @staticmethod
    def _alpha_region(image: QImage) -> QRegion:
        """把 alpha > 0 的像素按行合并成横向矩形，拼成点击区域。"""
        region = QRegion()
        width, height = image.width(), image.height()
        for y in range(height):
            x = 0
            while x < width:
                if (image.pixel(x, y) >> 24) & 0xFF:
                    start = x
                    while x < width and (image.pixel(x, y) >> 24) & 0xFF:
                        x += 1
                    region = region.united(QRegion(start, y, x - start, 1))
                else:
                    x += 1
        return region

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt 命名
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawPixmap(0, 0, self._pixmap)

    # ---------- 位置 ----------

    def restore_position(self) -> None:
        saved = self.cfg.get("pet_position")
        if (
            isinstance(saved, (list, tuple))
            and len(saved) == 2
            and all(isinstance(v, (int, float)) for v in saved)
        ):
            self.move(self._clamp_to_screen(QPoint(int(saved[0]), int(saved[1]))))
        else:
            self.move_to_default_corner()

    def move_to_default_corner(self) -> None:
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        margin = 40
        target = QPoint(
            geo.right() - self.width() - margin,
            geo.bottom() - self.height() - margin,
        )
        self.move(self._clamp_to_screen(target))

    def _clamp_to_screen(self, position: QPoint) -> QPoint:
        """保证窗口中心始终落在某个屏幕内，拖不出视野。"""
        center = position + QPoint(self.width() // 2, self.height() // 2)
        screen = (
            QGuiApplication.screenAt(center)
            or self.screen()
            or QGuiApplication.primaryScreen()
        )
        if screen is None:
            return position
        geo = screen.availableGeometry()
        x = min(max(center.x(), geo.left()), geo.right())
        y = min(max(center.y(), geo.top()), geo.bottom())
        return QPoint(x - self.width() // 2, y - self.height() // 2)

    # ---------- 鼠标交互 ----------

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.LeftButton:
            return
        self._press_global = event.globalPosition().toPoint()
        self._press_window = self.pos()
        self._dragging = False
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._press_global is None or not (event.buttons() & Qt.LeftButton):
            return
        delta = event.globalPosition().toPoint() - self._press_global
        if not self._dragging and delta.manhattanLength() > DRAG_THRESHOLD:
            self._dragging = True
            self.setCursor(Qt.ClosedHandCursor)
        if self._dragging:
            self.move(self._clamp_to_screen(self._press_window + delta))
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.LeftButton:
            return
        was_dragging = self._dragging
        self._press_global = None
        self._press_window = None
        self._dragging = False
        self.setCursor(Qt.OpenHandCursor)
        if was_dragging:
            self.moved.emit(self.pos())
        else:
            self.clicked.emit()
        event.accept()

    # ---------- 生命周期 ----------

    def closeEvent(self, event) -> None:  # noqa: N802
        """点 X 或者 Alt+F4 只隐藏，真正退出走托盘菜单。"""
        if self._allow_close:
            event.accept()
        else:
            event.ignore()
            self.hide()

    def quit_cleanly(self) -> None:
        self._allow_close = True
        self.close()
