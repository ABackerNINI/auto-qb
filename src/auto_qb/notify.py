"""主动通知: 程序 ERROR/WARNING 日志经平台原生通知推送(零第三方依赖)

设计:
- 接入: NotifyHandler 挂在 "auto_qb" logger 上, 复用全项目统一日志规范(ai/06 日志骨架)——
  现有与未来的 logger.warning/error 调用自动成为通知源, 新增告警点无需逐处接入;
- 防打扰双层: ①平台原生 toast 受 OS 专注助手/勿扰管理(Windows 全屏时横幅自动静默转入通知中心);
  ②程序级 quiet_hours 免打扰时段兜底(时段内跳过发送, 与 date_time 条件共用 utils.time_in_range);
- 线程模型: 日志调用线程仅在 handler 内做非阻塞 enqueue, subprocess 派发在 daemon 线程完成——
  不碰任务队列/state_file/store, 不违反"主循环单写线程"约束; 通知失败只 DEBUG, 绝不外抛;
- 防自环: handler 忽略来自本模块 logger 的记录, 杜绝"通知触发通知";
- 渠道: v1 仅平台原生单渠道(platform), Windows = PowerShell 调 WinRT ToastNotificationManager
  (winotify 同款零依赖路径), Linux = notify-send, macOS = osascript; 文本全部经 base64/转义
  传递, 无注入风险。
"""
import base64
import logging
import os
import queue
import subprocess
import sys
import threading
import time
import xml.sax.saxutils
from datetime import datetime
from typing import Callable, List, Optional

from . import utils
from .config import NotifyConfig

logger = logging.getLogger(__name__)

# 防自环: 本模块(含子 logger)产生的日志不再进入通知
NOTIFY_LOGGER_PREFIX = "auto_qb.notify"
# Windows toast 来源应用标识(AUMID): 开始菜单 Programs 目录下同名 .lnk 快捷方式会获得
# 与文件名(去扩展名)相同的隐式 AppUserModelID, 注册后 toast 来源显示为 "AutoQB"
WINDOWS_TOAST_APPID = "AutoQB"
# AUMID 注册失败的回退来源(PowerShell 自带标识, 无需注册即可用, 显示为 "Windows PowerShell")
WINDOWS_TOAST_APPID_FALLBACK = "Microsoft.Windows.PowerShell"
# toast 正文字符上限(WinRT toast 单文本节点约 250 字符可见, 截断防溢出)
MAX_BODY_LEN = 280


class NotifyThrottle:
    """滑动窗口节流: 每小时上限 + 同键去重窗口

    内存态(非正确性语义, 重启重置可接受, 不进 state_file); 线程安全经外部锁或单线程约定。
    """
    def __init__(self, max_per_hour: int, dedup_window: float, now: Callable[[], float] = time.monotonic):
        self.max_per_hour = max_per_hour
        self.dedup_window = dedup_window
        self._now = now
        self._sent_at: List[float] = []  # 最近一小时内已放行的时间戳
        self._dedup_at: dict = {}  # 去重键 -> 上次放行时间戳

    def allow(self, key: str) -> bool:
        """是否放行该通知: 超每小时上限或处于同键去重窗口内则丢弃"""
        now = self._now()
        self._sent_at = [t for t in self._sent_at if now - t < 3600.0]
        if len(self._sent_at) >= self.max_per_hour:
            return False
        if self.dedup_window > 0:
            last = self._dedup_at.get(key)
            if last is not None and now - last < self.dedup_window:
                return False
        self._sent_at.append(now)
        self._dedup_at[key] = now
        return True


class PlatformChannel:
    """平台原生通知渠道: 按运行平台构造系统通知命令并执行(无第三方依赖)

    send 失败(命令缺失/超时/非零退出)仅返回 False, 由调用方 DEBUG 记录——通知链路
    的任何异常都不允许影响主程序。
    """

    TIMEOUT_S = 10.0

    def __init__(self, platform: str = None, launch_arguments: str = ""):
        # platform 运行时求值(默认参数在导入时绑定 sys.platform, 会固化到模块导入场景)
        self.platform = platform if platform is not None else sys.platform
        # toast 点击激活命令的参数(Windows: 写入 AUMID 快捷方式 Arguments, 点击通知即以此重启应用)
        self._launch_arguments = launch_arguments
        if self.platform.startswith("win32"):
            self._appid = self._ensure_windows_appid()
            self._build = self._build_windows
        elif self.platform.startswith("linux"):
            self._build = self._build_linux
        elif self.platform.startswith("darwin"):
            self._build = self._build_darwin
        else:
            raise ValueError(f"不支持的平台原生通知: {self.platform}")

    # ---------- Windows AUMID 注册(toast 来源显示名) ----------

    @staticmethod
    def _windows_shortcut_path() -> str:
        """当前用户的 AUMID 快捷方式路径(%APPDATA% 开始菜单 Programs 目录); 无 APPDATA 返回空串"""
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            return ""
        return os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", f"{WINDOWS_TOAST_APPID}.lnk")

    def _ensure_windows_appid(self) -> str:
        """注册 AUMID 快捷方式并返回来源应用标识

        每次启动幂等重写快捷方式(CreateShortcut 覆盖写): Arguments 需与当前配置路径保持一致,
        否则 toast 点击会以过期参数启动。注册失败回退 PowerShell AUMID 并 DEBUG 记录 ——
        来源名/点击激活退化, 通知功能本身不受影响。构造期同步执行(每进程一次, 数百毫秒)。
        """
        shortcut = self._windows_shortcut_path()
        if not shortcut:
            return WINDOWS_TOAST_APPID_FALLBACK  # 无 APPDATA(异常环境): 直接回退
        try:
            self._register_windows_appid(shortcut)
            return WINDOWS_TOAST_APPID
        except (OSError, subprocess.SubprocessError) as e:
            logger.debug("通知 AUMID 注册失败, 回退 PowerShell 来源: %s", e)
            return WINDOWS_TOAST_APPID_FALLBACK

    def _register_windows_appid(self, shortcut: str) -> None:
        """经 PowerShell(WScript.Shell COM)创建 AUMID 快捷方式: 指向当前解释器,
        Arguments = launch_arguments(toast 点击激活即以该参数重启应用, 经单实例锁唤起已有窗口)"""
        def ps_quote(s: str) -> str:
            return s.replace("'", "''")  # PowerShell 单引号字面量转义

        script = (
            "$ws = New-Object -ComObject WScript.Shell; "
            f"$lnk = $ws.CreateShortcut('{ps_quote(shortcut)}'); "
            f"$lnk.TargetPath = '{ps_quote(sys.executable)}'; "
            f"$lnk.Arguments = '{ps_quote(self._launch_arguments)}'; "
            f"$lnk.IconLocation = '{ps_quote(sys.executable)},0'; "
            "$lnk.Save()"
        )
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            capture_output=True,
            timeout=self.TIMEOUT_S,
        )
        if result.returncode != 0:
            raise OSError(f"快捷方式创建失败: {result.stderr.decode('utf-8', 'ignore')[:200]}")
        if not os.path.exists(shortcut):
            raise OSError("快捷方式未生成")

    def send(self, title: str, body: str, urgent: bool = False) -> bool:
        """发送一条通知; 返回是否成功"""
        try:
            cmd = self._build(title, body, urgent)
            result = subprocess.run(cmd, capture_output=True, timeout=self.TIMEOUT_S)
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError) as e:
            logger.debug("通知发送失败: %s", e)
            return False

    def _build_windows(self, title: str, body: str, urgent: bool) -> List[str]:
        """WinRT toast(Windows 10/11 原生通知): PowerShell 脚本经 -EncodedCommand 传递,
        规避引号/中文编码问题; toast XML 内容二次 base64, 文本零注入;
        来源 AUMID 为已注册的快捷方式标识(未注册成功时回退 PowerShell)"""
        esc = xml.sax.saxutils.escape
        toast_xml = (
            '<toast><visual><binding template="ToastText02">'
            f'<text id="1">{esc(title)}</text>'
            f'<text id="2">{esc(body[:MAX_BODY_LEN])}</text>'
            '</binding></visual></toast>'
        )
        xml_b64 = base64.b64encode(toast_xml.encode("utf-8")).decode("ascii")
        script = (
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
            "ContentType = WindowsRuntime] | Out-Null; "
            "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, "
            "ContentType = WindowsRuntime] | Out-Null; "
            "$Xml = New-Object Windows.Data.Xml.Dom.XmlDocument; "
            f"$Xml.LoadXml([System.Text.Encoding]::UTF8.GetString("
            f"[System.Convert]::FromBase64String('{xml_b64}'))); "
            "$Toast = New-Object Windows.UI.Notifications.ToastNotification $Xml; "
            f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
            f"'{self._appid}').Show($Toast)"
        )
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        return ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded]

    @staticmethod
    def _build_linux(title: str, body: str, urgent: bool) -> List[str]:
        return [
            "notify-send",
            "-a",
            "auto-qb",
            "-u",
            "critical" if urgent else "normal",
            title,
            body[:MAX_BODY_LEN],
        ]

    @staticmethod
    def _build_darwin(title: str, body: str, urgent: bool) -> List[str]:
        def esc_applescript(text: str) -> str:
            return text.replace("\\", "\\\\").replace('"', '\\"')

        script = (
            f'display notification "{esc_applescript(body[:MAX_BODY_LEN])}" '
            f'with title "{esc_applescript(title)}"'
        )
        return ["osascript", "-e", script]


class NotifyHandler(logging.Handler):
    """日志 -> 通知桥: 按 min_level 过滤日志记录, 经时段/节流过滤后交后台线程派发

    - emit 任意异常不外抛(logging.handleError 兜底), 通知链路故障不影响主程序;
    - 防自环: 忽略 NOTIFY_LOGGER_PREFIX 来源;
    - quiet_hours: 时段内跳过发送(DEBUG 记录), 与 date_time 条件共用 utils.time_in_range。
    """

    DEDUP_PREFIX_LEN = 80

    def __init__(self, config: NotifyConfig, channel: PlatformChannel, now: Callable[[], datetime] = None):
        super().__init__(level=getattr(logging, config.min_level, logging.WARNING))
        self.channel = channel
        self.enabled = True  # 运行时热开关(UI Switch/托盘勾选共用; bool 赋值原子, 无需锁)
        self.throttle = NotifyThrottle(config.max_per_hour, config.dedup_window)
        self.quiet_hours = (config.quiet_hours or "").strip() or None
        self._now = now if now is not None else datetime.now
        self._queue: "queue.Queue" = queue.Queue()
        self._lock = threading.Lock()  # allow+标记的原子性(日志可能来自任意线程)
        self._worker = threading.Thread(target=self._drain, name="auto-qb-notify", daemon=True)
        self._worker.start()

    def emit(self, record: logging.LogRecord):
        try:
            if not self.enabled:
                return
            if record.name and record.name.startswith(NOTIFY_LOGGER_PREFIX):
                return  # 防自环
            message = record.getMessage()
            key = f"{record.name}:{record.levelname}:{message[:self.DEDUP_PREFIX_LEN]}"
            with self._lock:
                allowed = self.throttle.allow(key)
            if not allowed:
                return  # 节流丢弃(防风暴, 不再打日志避免自身刷屏)
            if self.quiet_hours and utils.time_in_range(self._now().time(), self.quiet_hours):
                logger.debug("免打扰时段(%s), 跳过通知: %s", self.quiet_hours, message[:80])
                return
            self._queue.put_nowait((f"auto-qb {record.levelname}", message, record.levelno >= logging.ERROR))
        except Exception:
            self.handleError(record)

    def _drain(self):
        """后台派发线程: 逐条发送; daemon 线程随进程退出, 积压通知允许丢弃"""
        while True:
            item = self._queue.get()
            if item is None:
                return
            title, body, urgent = item
            if not self.channel.send(title, body, urgent):
                logger.debug("通知发送失败: %s", body[:80])

    def close(self):
        """logging.shutdown 钩子: 唤醒派发线程优雅退出(队列积压不保证送达)"""
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass
        super().close()


def setup_notify(config: Optional[NotifyConfig],
                 force: bool = False,
                 launch_arguments: str = "") -> Optional[NotifyHandler]:
    """按配置构造并挂载通知 handler 到 "auto_qb" logger; 未启用且未强挂返回 None

    force=True: 配置未启用时也会挂载(UI 通知开关热开启, 会话级, 重启后回到配置状态)。
    launch_arguments: Windows toast 点击激活的启动参数(经 AUMID 快捷方式 Arguments)。
    平台不支持时抛 AutoQbError(启动期 fail-fast, CLI 干净退出 / UI 弹窗提示);
    dry-run 下不调用本函数(调用点判定, 与全项目 dry_run 约定一致)。
    """
    if not config or (not config.enabled and not force):
        return None
    try:
        channel = PlatformChannel(launch_arguments=launch_arguments)
    except ValueError as e:
        from .errors import AutoQbError
        raise AutoQbError(f"主动通知启用失败: {e}") from e
    handler = NotifyHandler(config, channel)
    pkg_logger = logging.getLogger("auto_qb")
    pkg_logger.addHandler(handler)
    logger.info(
        "主动通知已启用: 最低级别 %s, 免打扰时段 %s, 每小时上限 %d",
        config.min_level,
        config.quiet_hours or "无",
        config.max_per_hour,
    )
    return handler


def notify_fatal(message: str, config: Optional[NotifyConfig] = None) -> None:
    """进程退出前的致命错误通知(best-effort: 同步发送, 短超时, 任何异常静默)

    仅在"程序运行中致命退出"(如 QbCompatError)且通知已启用时由 CLI 调用;
    配置错误/锁竞争等启动失败场景 manager 未构造(无配置可读), 不发。
    """
    if not config or not config.enabled:
        return
    try:
        PlatformChannel().send("auto-qb 已停止", message, urgent=True)
    except Exception:
        logger.debug("致命错误通知发送失败", exc_info=True)
