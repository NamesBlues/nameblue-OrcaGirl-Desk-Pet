"""配置读写与路径常量。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
ASSETS_DIR = ROOT / "assets"
BUBBLES_DIR = ASSETS_DIR / "bubbles"
PET_IMAGE = ASSETS_DIR / "orca_girl.png"
TRAY_IMAGE = ASSETS_DIR / "orca.png"

# 缩放基准：pet_scale = 1.0 时桌宠在屏幕上有多高（像素）。
# 素材本身是 1024px 级别的高清图，直接按原始分辨率显示会有半个屏幕那么大，
# 所以统一以这个尺寸为基准按比例换算，素材再大也不会影响默认观感。
BASE_PET_HEIGHT = 260
BASE_BUBBLE_WIDTH = 220

DEFAULTS: Dict[str, Any] = {
    # 桌宠
    "pet_scale": 1.0,
    "pet_position": None,          # [x, y]，None 表示默认右下角
    "always_on_top": True,
    "pixel_perfect_hit": True,     # 全透明处鼠标穿透，只点得中角色
    # 气泡
    "bubble_scale": 1.0,
    "bubble_gap": 0.10,            # 气泡尾巴压住头顶的比例
    "bubble_duration": 4.0,        # 单条气泡显示秒数
    "bubble_interval_min": 20.0,   # 随机说话间隔（秒）
    "bubble_interval_max": 45.0,
    "startup_greeting": True,      # 启动时打招呼
    "startup_bubble": "bubble_1.png",
    "idle_exclude": ["bubble_1.png"],  # 随机说话时排除的气泡
    "click_to_speak": True,        # 点击桌宠说话
    # 系统
    "autostart": False,
}


class Config:
    def __init__(self, data: Optional[Dict[str, Any]] = None) -> None:
        self.data: Dict[str, Any] = dict(DEFAULTS)
        if data:
            self.data.update(data)

    @classmethod
    def load(cls) -> "Config":
        if not CONFIG_PATH.exists():
            return cls()
        try:
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"[配置] 读取失败，改用默认值：{exc}")
            return cls()
        if not isinstance(raw, dict):
            print("[配置] 内容不是对象，改用默认值")
            return cls()
        return cls(raw)

    def save(self) -> None:
        try:
            CONFIG_PATH.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"[配置] 保存失败：{exc}")

    def reset(self) -> None:
        self.data = dict(DEFAULTS)

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


def bubble_files() -> List[Path]:
    """assets/bubbles 下所有气泡图。往这个文件夹里丢新 PNG 就会自动加入轮播。"""
    if not BUBBLES_DIR.is_dir():
        return []
    return sorted(BUBBLES_DIR.glob("*.png"))
