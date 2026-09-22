"""开机自启(跨平台, 零第三方依赖): 注册当前用户的开机启动项

- Windows: 注册表 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run, 值名 "auto-qb"
- Linux:   XDG autostart(~/.config/autostart/auto-qb.desktop)
- macOS:   LaunchAgents(~/Library/LaunchAgents/com.autoqb.app.plist)

注册的启动命令 = 当前解释器(打包后为可执行文件自身) + 配置绝对路径 + --tray。
开关状态由 UI(窗口 Switch / 托盘勾选)读写; 不支持的平台 enable/disable 抛 AutoQbError。
"""
import os
import plistlib
import sys
from pathlib import Path

from .errors import AutoQbError

APP_KEY = "auto-qb"
RUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
LINUX_DESKTOP = Path.home() / ".config" / "autostart" / f"{APP_KEY}.desktop"
MACOS_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.autoqb.app.plist"

_DESKTOP_TEMPLATE = (
    "[Desktop Entry]\n"
    "Type=Application\n"
    "Name=auto-qb\n"
    "Comment=PT seed manager for qBittorrent\n"
    "Exec={command}\n"
    "Terminal=false\n"
    "X-GNOME-Autostart-enabled=true\n"
)


def autostart_command(config_path: str) -> str:
    """启动命令: 当前解释器(打包后为可执行文件自身) + 配置绝对路径 + --tray"""
    return f'"{sys.executable}" "{os.path.abspath(config_path)}" --tray'


def is_enabled(config_path: str) -> bool:
    """当前是否已注册开机自启(存在即视为启用, 不比对命令内容)"""
    if sys.platform.startswith("win32"):
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY) as key:
                winreg.QueryValueEx(key, APP_KEY)
                return True
        except OSError:
            return False
    if sys.platform.startswith("darwin"):
        return MACOS_PLIST.exists()
    return LINUX_DESKTOP.exists()


def enable(config_path: str) -> None:
    """注册开机自启; 失败抛 AutoQbError(UI 提示, 不中断程序)"""
    command = autostart_command(config_path)
    try:
        if sys.platform.startswith("win32"):
            import winreg

            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, APP_KEY, 0, winreg.REG_SZ, command)
        elif sys.platform.startswith("darwin"):
            MACOS_PLIST.parent.mkdir(parents=True, exist_ok=True)
            with open(MACOS_PLIST, "wb") as f:
                plistlib.dump(
                    {
                        "Label": "com.autoqb.app",
                        "ProgramArguments": [sys.executable, os.path.abspath(config_path), "--tray"],
                        "RunAtLoad": True
                    },
                    f,
                )
        else:
            LINUX_DESKTOP.parent.mkdir(parents=True, exist_ok=True)
            LINUX_DESKTOP.write_text(_DESKTOP_TEMPLATE.format(command=command), encoding="utf-8")
    except OSError as e:
        raise AutoQbError(f"开机自启注册失败: {e}") from e


def disable() -> None:
    """注销开机自启; 未注册时为幂等 no-op"""
    try:
        if sys.platform.startswith("win32"):
            import winreg

            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, APP_KEY)
            except OSError:
                return  # 未注册: 幂等
        elif sys.platform.startswith("darwin"):
            MACOS_PLIST.unlink(missing_ok=True)
        else:
            LINUX_DESKTOP.unlink(missing_ok=True)
    except OSError as e:
        raise AutoQbError(f"开机自启注销失败: {e}") from e
