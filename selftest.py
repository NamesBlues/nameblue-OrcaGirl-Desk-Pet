"""快速自检：把所有窗口建出来、量一遍关键数值、模拟一次拖拽，然后立刻退出。

改完代码后跑一下，能在几秒内发现导入错误、素材缺失、尺寸异常、点击区域失效等问题：

    .venv\\Scripts\\python.exe tools\\selftest.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from bubble import BubbleWindow  # noqa: E402
from config import BASE_PET_HEIGHT, Config, bubble_files  # noqa: E402
from pet import PetWindow  # noqa: E402
from settings_dialog import SettingsDialog  # noqa: E402
from tray import PetTray  # noqa: E402


def mouse_event(kind, local: QPoint, global_pos: QPoint, held: bool) -> QMouseEvent:
    buttons = Qt.LeftButton if held else Qt.NoButton
    return QMouseEvent(
        kind,
        QPointF(local),
        QPointF(global_pos),
        Qt.LeftButton,
        buttons,
        Qt.NoModifier,
    )


def simulate_drag(widget, start: QPoint, delta: QPoint) -> QPoint:
    """模拟一次真实的按下 → 移动 → 松开，返回最终位置。"""
    widget.move(start)
    QApplication.sendEvent(widget, mouse_event(QEvent.MouseButtonPress, QPoint(8, 8), start + QPoint(8, 8), True))
    QApplication.sendEvent(
        widget,
        mouse_event(QEvent.MouseMove, QPoint(8, 8), start + QPoint(8, 8) + delta, True),
    )
    QApplication.sendEvent(
        widget,
        mouse_event(QEvent.MouseButtonRelease, QPoint(8, 8), start + QPoint(8, 8) + delta, False),
    )
    return widget.pos()


def main() -> int:
    app = QApplication([])
    cfg = Config.load()
    problems: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            problems.append(message)

    files = bubble_files()
    print(f"[素材] 气泡 {len(files)} 张：{', '.join(f.name for f in files) or '（空）'}")
    check(bool(files), "assets/bubbles 里没有气泡图")

    started = time.perf_counter()
    pet = PetWindow(cfg)
    cost_ms = (time.perf_counter() - started) * 1000
    region = pet.mask()
    rects = region.rectCount() if hasattr(region, "rectCount") else -1
    expected_h = round(BASE_PET_HEIGHT * float(cfg["pet_scale"]))
    print(f"[桌宠] 尺寸 {pet.width()}x{pet.height()}，构建 {cost_ms:.0f} ms，点击区域 {rects} 个矩形")
    check(pet.width() > 0 and pet.height() > 0, "桌宠窗口尺寸异常")
    check(abs(pet.height() - expected_h) <= 2, f"桌宠高度 {pet.height()} 与预期 {expected_h} 不符")
    check(not cfg["pixel_perfect_hit"] or rects > 0, "点击区域是空的（mask 生成失败）")
    check(cost_ms < 3000, f"窗口构建耗时过长（{cost_ms:.0f} ms）")

    pet.restore_position()
    screen = QApplication.primaryScreen().availableGeometry()
    check(screen.contains(pet.geometry().center()), f"初始位置 {pet.pos()} 跑到屏幕外了")
    print(f"[桌宠] 初始位置 {pet.pos()}（屏幕可用区 {screen.width()}x{screen.height()}）")

    # --- 拖拽 ---
    clicks: list[int] = []
    drags: list[int] = []
    pet.clicked.connect(lambda: clicks.append(1))
    pet.moved.connect(lambda _: drags.append(1))

    before = QPoint(300, 300)
    after = simulate_drag(pet, before, QPoint(90, 60))
    print(f"[拖拽] {before} + (90,60) -> {after}")
    check(after == before + QPoint(90, 60), "拖拽位移不正确")
    check(len(drags) == 1, "拖拽结束没有发出 moved 信号")

    # --- 点击（只按下松开，不移动）---
    simulate_drag(pet, QPoint(320, 320), QPoint(0, 0))
    print(f"[点击] clicked 信号触发 {len(clicks)} 次")
    check(len(clicks) == 1, "单击没有触发 clicked 信号")
    check(len(drags) == 1, "原地点击被误判成了拖拽")

    # --- 气泡 ---
    bubble = BubbleWindow(cfg)
    for path in files:
        bubble.show_bubble(path, pet.frameGeometry())
        app.processEvents()
        print(f"[气泡] {path.name} -> {bubble.width()}x{bubble.height()} @ {bubble.pos()}")
        check(bubble.width() > 0 and bubble.height() > 0, f"{path.name} 气泡尺寸异常")
    bubble.hide_now()

    # --- 设置界面 ---
    dialog = SettingsDialog(cfg)
    dialog.show()
    app.processEvents()
    print(f"[设置] 对话框 {dialog.width()}x{dialog.height()}")
    check(dialog.width() > 200 and dialog.height() > 200, "设置对话框尺寸异常")
    dialog.close()

    # --- 托盘 ---
    tray = PetTray()
    print(f"[托盘] 系统托盘可用：{tray.is_available()}")
    check(tray.is_available(), "系统托盘不可用")

    assert pet and tray and bubble  # 防止被 gc
    print()
    if problems:
        print("发现问题：")
        for item in problems:
            print(f"  - {item}")
        return 1
    print("全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
