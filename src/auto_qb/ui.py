"""托盘常驻 UI(--tray 模式): CustomTkinter 主窗口 + pystray 托盘 + 单实例唤起 IPC

线程模型("主循环所在线程是唯一修改者"约束不破):
- 主线程: CustomTkinter mainloop + 每 100ms after() 轮询事件队列/状态快照/日志增量
- pystray 线程: 托盘消息循环; 菜单回调只向事件队列投递, 不碰任何共享状态
- manager 线程: manager.run(dry_run, stop_event, pause_event) —— 主循环整体在后台线程,
  仍是任务队列/state_file 的唯一修改者
- 通知/IPC 线程: 现状不变
跨线程通道唯一: queue.Queue(UI 动作) + Event + 只读快照(status_snapshot/UiLogHandler);
UI 从不直接跨线程调用控件。

单实例唤起: 首实例 IPC server 端口写 <state_file 同目录>/ui.port; 第二实例(--tray)
获锁失败后读该文件发送 "show" 并静默退出, 首实例弹窗。残留文件由 connect 失败自然退化。
"""
import logging
import os
import queue
import sys
import threading
import time
import webbrowser
from collections import deque

import customtkinter as ctk
import pystray
import tkinter as tk
from PIL import Image
from tkinter import messagebox

from . import autostart, utils
from .errors import AutoQbError
from .notify import WINDOWS_TOAST_APPID, setup_notify
from .qbmanager import QbManager

logger = logging.getLogger(__name__)

ICON_PNG = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
ICON_ICO = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
UI_PORT_FILE_NAME = "ui.port"
POLL_MS = 100
LOG_VIEW_LINES = 200

COLOR_BG_CARD = ("gray86", "#1E355C")
COLOR_OK = "#34C759"
COLOR_WARN = "#E0A422"
COLOR_ERR = "#E05252"


class UiLogHandler(logging.Handler):
    """日志 -> UI 环形缓冲: emit 仅入队, UI 线程每轮 drain 增量(线程安全)"""
    def __init__(self):
        super().__init__()
        self._pending = deque()
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord):
        try:
            if record.levelno != logging.DEBUG:
                line = f"[{record.levelname}] {record.getMessage()}"
                with self._lock:
                    self._pending.append(line)
        except Exception:
            pass

    def drain(self) -> list:
        """取走全部未消费日志行"""
        with self._lock:
            items = list(self._pending)
            self._pending.clear()
        return items


class ShowIpcServer:
    """单实例唤起 IPC: 监听 localhost 随机端口, 收到 "show" 触发回调; 端口写入端口文件"""
    def __init__(self, port_file: str, on_show):
        self.port_file = port_file
        self.on_show = on_show
        self._sock = None

    def start(self):
        import socket

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(1)
        port = self._sock.getsockname()[1]
        with open(self.port_file, "w", encoding="ascii") as f:
            f.write(str(port))
        threading.Thread(target=self._serve, name="auto-qb-ipc", daemon=True).start()

    def _serve(self):
        while True:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return  # socket 已关闭(退出)
            with conn:
                try:
                    data = conn.recv(64)
                except OSError:
                    continue
                if data.startswith(b"show"):
                    try:
                        self.on_show()
                    except Exception:
                        logger.debug("IPC 唤起处理失败", exc_info=True)

    def stop(self):
        """关闭监听并删除端口文件(残留文件由第二实例 connect 失败自然退化, 此处尽力清理)"""
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        try:
            os.remove(self.port_file)
        except OSError:
            pass


def send_show(port_file: str, timeout: float = 2.0) -> bool:
    """向已运行实例发送唤起请求; 成功返回 True(第二实例随后静默退出)"""
    import socket

    try:
        with open(port_file, "r", encoding="ascii") as f:
            port = int(f.read().strip())
        with socket.create_connection(("127.0.0.1", port), timeout=timeout) as conn:
            conn.sendall(b"show\n")
        return True
    except (OSError, ValueError):
        return False


def _set_windows_appid() -> None:
    """设置进程显式 AppUserModelID(须在首个窗口创建前调用)

    Win10/11 任务栏按钮在有显式 AUMID 时才取窗口图标(与 iconbitmap 配合),
    否则恒显示 python.exe 默认图标。AUMID 与 toast 来源(notify.WINDOWS_TOAST_APPID,
    对应开始菜单 AutoQB.UI.lnk, 图标 = orbit)同一身份。
    """
    try:
        import ctypes

        set_aumid = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
        set_aumid.argtypes = [ctypes.c_wchar_p]
        set_aumid.restype = ctypes.c_long
        hr = set_aumid(WINDOWS_TOAST_APPID)
        if hr != 0:
            logger.warning("AppUserModelID 设置失败: HRESULT=%s", hr)
            return
        # 读回校验: 设置结果以系统实际持有的 AUMID 为准(explorer 任务栏图标按它解析)
        kernel32 = ctypes.windll.kernel32
        kernel32.GetApplicationUserModelId.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint),
            ctypes.c_wchar_p,
        ]
        length = ctypes.c_uint(0)
        current = ctypes.windll.kernel32.GetCurrentProcess()
        if kernel32.GetApplicationUserModelId(current, ctypes.byref(length), None) == 122:  # ERROR_INSUFFICIENT_BUFFER
            buf = ctypes.create_unicode_buffer(length.value)
            if kernel32.GetApplicationUserModelId(current, ctypes.byref(length), buf) == 0:
                if buf.value == WINDOWS_TOAST_APPID:
                    logger.debug("AppUserModelID 已生效: %s", buf.value)
                else:
                    logger.warning("AppUserModelID 读回不一致: %s", buf.value)
    except Exception:
        logger.debug("AppUserModelID 设置失败", exc_info=True)


class TrayUi:
    """托盘应用编排: 窗口/托盘/manager 线程/事件轮询"""
    def __init__(self, manager: QbManager, dry_run: bool = False):
        self.manager = manager
        self.dry_run = dry_run
        self.events: "queue.Queue" = queue.Queue()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.log_handler = UiLogHandler()
        logging.getLogger("auto_qb").addHandler(self.log_handler)
        self.port_file = os.path.join(os.path.dirname(manager.state_file) or ".", UI_PORT_FILE_NAME)
        self.ipc = ShowIpcServer(self.port_file, lambda: self.events.put(("show", None)))
        self._icon = None
        self._icon_title = ""
        self._paused = False  # 托盘勾选态缓存(权威来源为 pause_event, 轮询时同步)
        self._started = time.time()
        self._manager_thread = None
        self._build_window()
        self._build_tray()

    # ---------- 窗口 ----------

    def _build_window(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.root = ctk.CTk()
        self.root.title("auto-qb")
        self.root.geometry("780x560")
        self.root.minsize(700, 500)
        self._icon_tk = tk.PhotoImage(file=ICON_PNG)  # 引用须保留, 否则被 GC
        # Windows 走 CTk 的 iconbitmap(BMP 帧 .ico, 含 16~256 多尺寸)—— 诊断对照实测
        # CTk 窗口上此方式标题栏/任务栏/alt-tab 均正确; 其它平台 iconphoto(PhotoImage 不支持 ico)
        if sys.platform.startswith("win32"):
            # 仅 iconbitmap(BMP 帧 ico, 含 16~256 多尺寸): 与诊断对照 C 完全一致 ——
            # 实测 CTk 窗口上此方式标题栏/任务栏/alt-tab 均为 orbit; 此前叠加的
            # iconphoto/WM_SETICON(32px 单尺寸) 反而在高 DPI 下破坏任务栏图标(回退 python)
            self.root.iconbitmap(ICON_ICO)
            # 手动标记 CTk 自定义标志, 阻断其 200ms 默认图标覆盖; 晚于该点再重设一次 iconbitmap 兜底
            self.root._iconbitmap_method_called = True
            self.root.after(450, lambda: self.root.iconbitmap(ICON_ICO))
        else:
            self.root.iconphoto(False, self._icon_tk)
        self.root.protocol("WM_DELETE_WINDOW", self._hide_window)

        from . import __version__

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(3, weight=1)

        # 顶部: 名称 + 状态徽章
        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(header, text="auto-qb", font=ctk.CTkFont(size=22, weight="bold")).grid(row=0, column=0)
        self.badge = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_OK)
        self.badge.grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(header, text=f"v{__version__}", text_color="gray60").grid(row=0, column=2, padx=(12, 0))

        # 状态卡片: 受管种子 / 运行时长 / qB 连接
        cards = ctk.CTkFrame(self.root, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", padx=20, pady=4)
        for i in range(3):
            cards.grid_columnconfigure(i, weight=1)
        self.card_torrents = self._card(cards, 0, "受管种子")
        self.card_uptime = self._card(cards, 1, "运行时长")
        self.card_conn = self._card(cards, 2, "qB 连接")

        # 控制区: 暂停/恢复 + 通知开关 + 开机自启
        controls = ctk.CTkFrame(self.root, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", padx=20, pady=8)
        self.pause_btn = ctk.CTkButton(controls, text="暂停自动管理", width=160, command=self._toggle_pause)
        self.pause_btn.grid(row=0, column=0, padx=(0, 20))
        self.notify_switch = ctk.CTkSwitch(controls, text="通知", command=self._toggle_notify)
        self.notify_switch.grid(row=0, column=1, padx=(0, 20))
        if self._notify_on():
            self.notify_switch.select()
        self.autostart_switch = ctk.CTkSwitch(controls, text="开机自启", command=self._toggle_autostart)
        self.autostart_switch.grid(row=0, column=2)
        if autostart.is_enabled(self.manager.config_path):
            self.autostart_switch.select()

        # 日志区
        self.log_box = ctk.CTkTextbox(self.root, font=ctk.CTkFont(family="Consolas", size=11), wrap="none")
        self.log_box.grid(row=3, column=0, sticky="nsew", padx=20, pady=8)
        self.log_box.configure(state="disabled")

        # 底部: 常用链接
        footer = ctk.CTkFrame(self.root, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 14))
        ctk.CTkButton(
            footer,
            text="打开 qBittorrent WebUI",
            width=180,
            fg_color="transparent",
            border_width=1,
            command=lambda: webbrowser.open(self.manager.config.qbittorrent.base_url)
        ).pack(side="left")
        ctk.CTkButton(
            footer,
            text="打开日志目录",
            width=140,
            fg_color="transparent",
            border_width=1,
            command=self._open_logs,
        ).pack(side="left", padx=10)

    @staticmethod
    def _log_dir(manager) -> str:
        """日志目录绝对路径(打开前确保存在)

        logging.file 可能是相对路径(相对进程 cwd)或为空(仅控制台, 理论不出现)——
        空值兜底 state_file 目录(data_dir); 相对路径以当前 cwd 绝对化后确保目录存在,
        避免 os.startfile 对不存在目录抛 FileNotFoundError。
        """
        log_dir = os.path.dirname(os.path.abspath(manager.config.logging.file or manager.state_file))
        os.makedirs(log_dir, exist_ok=True)
        return log_dir

    def _open_logs(self):
        utils.open_path(self._log_dir(self.manager))

    @staticmethod
    def _card(parent, column: int, title: str):
        card = ctk.CTkFrame(parent, fg_color=COLOR_BG_CARD, corner_radius=10)
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0))
        ctk.CTkLabel(card, text=title, text_color="gray60",
                     font=ctk.CTkFont(size=12)).pack(anchor="w", padx=16, pady=(10, 0))
        value = ctk.CTkLabel(card, text="-", font=ctk.CTkFont(size=24, weight="bold"))
        value.pack(anchor="w", padx=16, pady=(0, 10))
        return value

    # ---------- 托盘 ----------

    def _build_tray(self):
        self._icon = pystray.Icon(
            "auto-qb",
            Image.open(ICON_PNG),
            "auto-qb",
            menu=pystray.Menu(
                pystray.MenuItem("显示 / 隐藏窗口", default=True, action=lambda: self.events.put(("toggle_window", None))),
                pystray.Menu.SEPARATOR,
                # pystray 的 checked 回调以菜单项为参数调用(lambda 须收 1 参, 否则托盘线程崩溃)
                pystray.MenuItem(
                    "暂停自动管理", checked=lambda item: self._paused, action=lambda: self.events.put(("toggle_pause", None))
                ),
                pystray.MenuItem(
                    "通知",
                    checked=lambda item: self._notify_on(),
                    action=lambda: self.events.put(("toggle_notify", None))
                ),
                pystray.MenuItem(
                    "开机自启",
                    checked=lambda item: autostart.is_enabled(self.manager.config_path),
                    action=lambda: self.events.put(("toggle_autostart", None))
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("打开 qBittorrent WebUI", action=lambda: self.events.put(("open_webui", None))),
                pystray.MenuItem("打开日志目录", action=lambda: self.events.put(("open_logs", None))),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", action=lambda: self.events.put(("quit", None))),
            ),
        )
        self._icon.run_detached()

    # ---------- 事件处理(全部在主线程执行) ----------

    def _poll(self):
        try:
            while True:
                kind, _ = self.events.get_nowait()
                if kind == "quit":
                    self.root.quit()
                    return
                handler = {
                    "toggle_window": self._toggle_window,
                    "show": self._show_window,
                    "toggle_pause": self._toggle_pause,
                    "toggle_notify": self._toggle_notify,
                    "toggle_autostart": self._toggle_autostart,
                    "open_webui": lambda: webbrowser.open(self.manager.config.qbittorrent.base_url),
                    "open_logs": self._open_logs,
                }.get(kind)
                if handler is not None:
                    try:
                        handler()
                    except Exception:
                        # 单个事件失败不杀死 after 轮询链(否则 UI 从此停止刷新)
                        logger.exception("托盘事件处理失败: %s", kind)
        except queue.Empty:
            pass
        self._drain_logs()
        self._refresh_status()
        self.root.after(POLL_MS, self._poll)

    def _drain_logs(self):
        lines = self.log_handler.drain()
        if not lines:
            return
        self.log_box.configure(state="normal")
        for line in lines:
            self.log_box.insert("end", line + "\n")
        excess = int(self.log_box.index("end-1c").split(".")[0]) - LOG_VIEW_LINES
        if excess > 0:
            self.log_box.delete("1.0", f"{excess}.0")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _refresh_status(self):
        snap = self.manager.status_snapshot()
        self._paused = snap["paused"]  # 同步托盘勾选态缓存(权威来源为 pause_event)
        self.card_torrents.configure(text=str(snap["torrents"]))
        self.card_uptime.configure(text=self._format_uptime(time.time() - self._started))
        conn_text = {None: "连接中…", True: "已连接", False: "已断开"}[snap["connected"]]
        self.card_conn.configure(text=conn_text)
        if snap["paused"]:
            badge, color = "已暂停", COLOR_WARN
        elif snap["connected"] is False:
            badge, color = "qB 断开", COLOR_ERR
        else:
            badge, color = "运行中", COLOR_OK
        self.badge.configure(text=badge, text_color=color)
        self.pause_btn.configure(text="恢复自动管理" if snap["paused"] else "暂停自动管理")
        # 通知开关同步: handler 由 manager 线程的 run() 挂载, 晚于窗口构建(配置已启用时
        # Switch 初始为未选中, 此处按 handler 实际状态补正; 用户切换时两边即时一致)
        handler = self.manager._notify_handler
        if handler is not None and bool(self.notify_switch.get()) != handler.enabled:
            if handler.enabled:
                self.notify_switch.select()
            else:
                self.notify_switch.deselect()
        title = f"auto-qb ({badge})"
        if self._icon is not None and title != self._icon_title:
            self._icon.title = title  # 托盘悬浮提示跟随状态
            self._icon_title = title

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        seconds = int(seconds)
        if seconds < 3600:
            return f"{seconds // 60}分{seconds % 60:02d}秒"
        if seconds < 86400:
            return f"{seconds // 3600}时{(seconds % 3600) // 60:02d}分"
        return f"{seconds // 86400}天{(seconds % 86400) // 3600:02d}时"

    def _notify_on(self) -> bool:
        handler = self.manager._notify_handler
        return handler is not None and handler.enabled

    # ---------- 动作 ----------

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(200, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()

    def _toggle_window(self):
        if self.root.state() == "withdrawn":
            self._show_window()
        else:
            self._hide_window()

    def _hide_window(self):
        self.root.withdraw()  # 关闭按钮 = 隐藏到托盘(标准托盘应用行为)

    def _toggle_pause(self):
        paused = not self.pause_event.is_set()
        if paused:
            self.pause_event.set()
        else:
            self.pause_event.clear()
        logger.info("已暂停自动管理" if paused else "已恢复自动管理")

    def _toggle_notify(self):
        handler = self.manager._notify_handler
        if handler is None:
            # 配置未启用通知: 会话内动态挂载(重启后回到配置状态); 平台不支持则弹窗提示, 开关由勾选态回弹
            try:
                self.manager._notify_handler = setup_notify(self.manager.config.notify, force=True)
            except AutoQbError as e:
                messagebox.showwarning("auto-qb", str(e), parent=self.root)
                return
            self.notify_switch.select()
            logger.info("主动通知已开启(会话级, 重启后回到配置状态)")
            return
        handler.enabled = not handler.enabled
        if handler.enabled:
            self.notify_switch.select()
        else:
            self.notify_switch.deselect()
        logger.info("主动通知已%s", "开启" if handler.enabled else "关闭")

    def _toggle_autostart(self):
        try:
            if autostart.is_enabled(self.manager.config_path):
                autostart.disable()
                logger.info("开机自启已关闭")
            else:
                autostart.enable(self.manager.config_path)
                logger.info("开机自启已开启")
        except AutoQbError as e:
            messagebox.showwarning("auto-qb", str(e), parent=self.root)

    # ---------- 编排 ----------

    def run(self) -> int:
        """阻塞运行直至用户退出; 返回进程退出码"""
        self.ipc.start()
        self._manager_thread = threading.Thread(
            target=self.manager.run,
            args=(self.dry_run, self.stop_event, self.pause_event),
            name="auto-qb-mainloop",
            daemon=True,
        )
        self._manager_thread.start()
        self.root.after(POLL_MS, self._poll)
        self.root.mainloop()
        # mainloop 结束(托盘"退出"/root.quit): 依序停托盘 -> 停主循环(落盘) -> 清理 IPC
        self.stop_event.set()
        if self._icon is not None:
            self._icon.stop()
        if self._manager_thread is not None:
            self._manager_thread.join(timeout=5)
        self.ipc.stop()
        logging.getLogger("auto_qb").removeHandler(self.log_handler)
        return 0


def run_tray(manager: "QbManager", dry_run: bool = False) -> int:
    """托盘模式入口; 无桌面环境(SSH/服务会话)下抛 AutoQbError 干净退出"""
    try:
        ui = TrayUi(manager, dry_run)
    except Exception as e:
        if isinstance(e, (AutoQbError, )):
            raise
        raise AutoQbError(f"托盘 UI 初始化失败(无桌面环境?): {e}") from e
    return ui.run()
