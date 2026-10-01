"""虎鲸桌宠 —— 程序入口。

直接运行：
    pythonw main.py
或者双击 run.bat。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from app import run  # noqa: E402  - 必须先插好 sys.path


if __name__ == "__main__":
    sys.exit(run())
