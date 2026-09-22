"""托盘常驻 UI（--tray 模式）表现层包

由根模块 ui.py 归拢而来（plan 26-09-22-2112 · 方案 C · W2）: app.py 承载 TrayUi
（CustomTkinter 深色窗口）/ pystray 托盘 / UiLogHandler / 单实例唤起 IPC（ShowIpcServer）。
图标 assets/ 留在包根（tray 与 autostart 共用）。

线程模型不变：主循环整体在 manager 线程（任务队列/state_file 唯一修改者），
UI 主线程 100ms 轮询事件队列 + 只读快照；pystray 菜单回调只投递事件。
GUI 栈仅托盘分支加载（cli.py 延迟导入，无显示环境不影响其它模式）。
"""
from .app import (
    UI_PORT_FILE_NAME,
    ShowIpcServer,
    TrayUi,
    UiLogHandler,
    run_tray,
    send_show,
)

__all__ = [
    "UI_PORT_FILE_NAME",
    "ShowIpcServer",
    "TrayUi",
    "UiLogHandler",
    "run_tray",
    "send_show",
]
