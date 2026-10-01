"""开机自启：读写 HKCU\\...\\CurrentVersion\\Run 注册表项。"""

from __future__ import annotations

import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
ENTRY_NAME = "OrcaDesktopPet"
ROOT = Path(__file__).resolve().parent.parent


def _interpreter() -> Path:
    """优先用 pythonw.exe，这样开机启动时不会闪出一个黑色控制台窗口。"""
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    return pythonw if pythonw.exists() else exe


def command() -> str:
    return f'"{_interpreter()}" "{ROOT / "main.py"}"'


def is_enabled() -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, ENTRY_NAME)
            return bool(value)
    except (ImportError, FileNotFoundError, OSError):
        return False


def set_enabled(enabled: bool) -> bool:
    """返回操作是否成功。"""
    try:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            if enabled:
                winreg.SetValueEx(key, ENTRY_NAME, 0, winreg.REG_SZ, command())
            else:
                try:
                    winreg.DeleteValue(key, ENTRY_NAME)
                except FileNotFoundError:
                    pass
        return True
    except (ImportError, OSError):
        return False
