"""自启: 三平台幂等注册/卸载 (S5 实现).

  Windows  HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run 写一个值 (当前用户, 零提权)
  Linux    ~/.config/systemd/user/global-traffic-monitor.service + systemctl --user enable --now
  macOS    ~/Library/LaunchAgents/<label>.plist + launchctl bootstrap

Windows 为什么不用计划任务 (2026-10-17 改道, 见 memory-bank/issues/26-10-17-1455):
`schtasks /SC ONLOGON` 是「任何用户登录」级系统触发器, 普通权限进程创建会被 Task
Scheduler 拒 (rc=1 拒绝访问), 只有提权才能注册; 而本工具由 auto-qb 以普通权限拉起,
无人值守路径上没人点 UAC。HKCU Run 是「当前用户登录」级、零提权、stdlib 可读写,
语义比 ONLOGON 更贴本工具 (单用户后台服务)。

由 auto-qb WebUI 设置页开关调用 (S6 经控制面 `POST /autostart` 在工具进程内跑 installer),
也可命令行直接跑 (`global-traffic-monitor install-autostart` / `uninstall-autostart`)。

设计要点
--------
* **注册什么**: 一条 `python -m gtm run --data-dir <DIR>` 的守护命令 (包名 gtm 不变, D16),
  解释器取**调用本命令的那个 python** (`sys.executable`) —— 它按定义就是装了本工具的
  venv, 不猜路径、不依赖 PATH。data_dir 解析成绝对路径后**写死进注册项**: 自启拉起时是
  登录会话, 环境变量 (GLOBAL_TRAFFIC_MONITOR_DATA_DIR) 不可控。
* **幂等**: 重复注册 / 重复卸载都是成功 no-op。判据是**期望态是否已达成** ——
  Windows: Run 值内容与当前参数一致; Linux/macOS: 单元/plist 文件内容一致 **且**
  已启用/已加载。未达成则收敛到期望态 (Windows 覆盖写, Linux/macOS 重写文件 + 重新
  启用, 服务被停就重新启用)。计划原文的「存在则跳过」是本判据的常态分支; 只查「文件
  存在」会把「文件在但服务被 disable」误判成已注册, 让设置页开关谎报成功。
* **不解析平台命令的输出**: systemctl / launchctl 的 stdout/stderr 随系统语言本地化
  (中文 Windows 的表头与错误文案是中文), 按英文字面解析会静默得零值
  (坑档 pitfalls/ops/console-encoding.md)。本模块**只信退出码**; 输出仅作失败时给人
  看的附注, 解码走兜底链 (UTF-8 -> 本地码页 -> replace)。Windows 侧已无平台命令,
  注册表值按原样读回比对 (不经本地化文本)。
* **零第三方依赖**: 平台命令走 subprocess, 注册表走 stdlib winreg, plist 用 stdlib plistlib。
* **单写者**: 注册项由本模块独占生成; 单元/plist 文件是**生成物**, 手改会在下次注册
  时被覆盖 (文件头注释已注明)。
"""

from __future__ import annotations

import locale
import os
import plistlib
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

# ---- 注册项名称 (单点; 改名会留下孤儿注册项, 需先 uninstall 再 install) ----

DEFAULT_WINDOWS_VALUE = "global-traffic-monitor"
DEFAULT_SYSTEMD_UNIT = "global-traffic-monitor.service"
DEFAULT_LAUNCHD_LABEL = "com.global-traffic-monitor.autostart"

# ---- Windows 注册表口径 (Run 键 = 当前用户登录时起, 零提权) ----

WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
# Run 值长度上限 (MAX_PATH 口径): 超了会被截断成一条跑不起来的命令, 注册前必须拦住
WINDOWS_COMMAND_MAX = 260

# ---- 平台口径 (内部名; 与 sys.platform 的映射见 platform_from_sys) ----

PLATFORM_WINDOWS = "windows"
PLATFORM_LINUX = "linux"
PLATFORM_MACOS = "macos"

# ---- 动作口径 (结果对象的 action 字段; 供 CLI 与 S6 设置页消费) ----

ACTION_REGISTERED = "registered"  # 本次注册成功 (期望态原未达成)
ACTION_SKIPPED = "skipped"  # 期望态已达成, 未做任何改动
ACTION_UNREGISTERED = "unregistered"  # 本次卸载成功
ACTION_ABSENT = "absent"  # 本来就没注册, 无需卸载


class AutostartError(RuntimeError):
    """自启注册/卸载失败 (平台命令非 0 退出 / 前置条件缺失 / 平台不支持)."""


class UnsupportedPlatformError(AutostartError):
    """当前平台没有自启后端 (非 Windows / Linux / macOS)."""


# ---- 平台命令层 (可注入; 单测全部走替身, 不碰真机) ----


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


Runner = Callable[[Sequence[str]], CommandResult]


def _decode(raw: bytes) -> str:
    """外部命令输出解码兜底链 (UTF-8 -> 本地码页 -> replace).

    绝不依赖 locale 直接解: 中文 Windows 下原生命令按 OEM/本地码页输出, 按 UTF-8
    硬解会抛 UnicodeDecodeError 或静默 mojibake (坑档 pitfalls/ops/console-encoding.md)。
    结果**只用于失败时给人看**, 不参与任何语义判断 (语义只认退出码)。
    """
    for enc in ("utf-8", locale.getpreferredencoding(False) or "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def default_runner(argv: Sequence[str]) -> CommandResult:
    """生产 runner: 收字节不收文本 (解码走 _decode 兜底链), 不经 shell (免引号二次解析)."""
    proc = subprocess.run(list(argv), capture_output=True)
    return CommandResult(
        returncode=proc.returncode,
        stdout=_decode(proc.stdout or b""),
        stderr=_decode(proc.stderr or b""),
    )


# ---- 注册目标与结果 ----


@dataclass(frozen=True)
class AutostartPlan:
    """要注册的自启目标: 用什么解释器、跑什么命令、落在哪个数据目录."""

    python_exe: str
    data_dir: str

    def daemon_argv(self) -> list[str]:
        """守护命令 argv (launchd ProgramArguments / systemd ExecStart 共用)."""
        return [self.python_exe, "-m", "gtm", "run", "--data-dir", self.data_dir]

    def windows_command(self) -> str:
        """Run 值 / 登录命令行: 单个字符串 (两段路径各自带引号, 空格安全)."""
        return f'"{self.python_exe}" -m gtm run --data-dir "{self.data_dir}"'


@dataclass(frozen=True)
class AutostartResult:
    """注册/卸载结果: action 见 ACTION_* 常量, message 是一行人读结论."""

    action: str
    message: str

    @property
    def changed(self) -> bool:
        """本次是否真的改动了系统状态 (skipped / absent 都是 no-op)."""
        return self.action in (ACTION_REGISTERED, ACTION_UNREGISTERED)


# ---- 后端基类 ----


class AutostartBackend:
    """平台后端公共面: is_registered / register / unregister / target."""

    platform: str = ""

    def __init__(self, plan: AutostartPlan, runner: Runner) -> None:
        self._plan = plan
        self._runner = runner

    # -- 供子类与测试使用 --

    @property
    def plan(self) -> AutostartPlan:
        return self._plan

    @property
    def target(self) -> str:
        """注册项的人读标识 (任务名 / 单元路径 / plist 路径)."""
        raise NotImplementedError

    def _run(self, argv: Sequence[str]) -> CommandResult:
        """跑一条平台命令; 命令本身缺失/不可执行 -> AutostartError (fail-fast)."""
        try:
            return self._runner(list(argv))
        except FileNotFoundError as e:
            raise AutostartError(f"找不到命令 {argv[0]!r} (本机没有该自启机制?): {e}") from e
        except OSError as e:
            raise AutostartError(f"执行 {argv[0]!r} 失败: {e}") from e

    def _run_checked(self, argv: Sequence[str], what: str) -> None:
        """跑一条命令并要求退出码 0; 失败 -> AutostartError (带输出附注)."""
        r = self._run(argv)
        if r.returncode != 0:
            detail = (r.stderr or r.stdout).strip().replace("\n", " | ")
            raise AutostartError(f"{what} 失败 (rc={r.returncode}): {detail or '无输出'}")

    # -- 子类实现 --

    def is_registered(self) -> bool:
        raise NotImplementedError

    def register(self) -> AutostartResult:
        raise NotImplementedError

    def unregister(self) -> AutostartResult:
        raise NotImplementedError


# ---- 生成物读写 (单元文件 / plist 是生成物, 一律 UTF-8 + LF) ----


def _read_text_lf(path: str) -> Optional[str]:
    """读生成物原文 (newline='' 不做行尾翻译, 供逐字节比对判漂移)."""
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            return f.read()
    except FileNotFoundError:
        return None


def _write_text_lf(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# ---- Windows: 当前用户 Run 键 (登录时触发, 零提权) ----


class WindowsRunKeyBackend(AutostartBackend):
    """Windows 后端: HKCU Run 写一个值, 当前用户登录时起, 零提权.

    「已注册」判据只有一条: **值存在**。不比对命令内容 —— 设置页开关的语义是「有没有
    自启项」, 解释器/数据目录变了不该让开关跳到「未注册」(用户什么都没做错)。内容漂移
    由 register() 无条件覆盖写收敛: auto-qb 每次拉起 launch.cmd 都带 --autostart, 值会
    被刷成当前参数。

    注册表访问走注入的 `registry` (缺省惰性 `import winreg`, 只有 Windows 有); 单测
    全程走替身, 不碰真注册表。替身只需覆盖 OpenKey / CreateKeyEx / QueryValueEx /
    SetValueEx / DeleteValue 与常量 HKEY_CURRENT_USER / KEY_READ / KEY_SET_VALUE / REG_SZ。
    """

    platform = PLATFORM_WINDOWS

    def __init__(
        self,
        plan: AutostartPlan,
        runner: Runner,
        *,
        value_name: str = DEFAULT_WINDOWS_VALUE,
        registry: object | None = None,
    ) -> None:
        super().__init__(plan, runner)
        self._value_name = value_name
        self._registry = registry

    @property
    def target(self) -> str:
        """人读标识: 注册表值的完整位置."""
        return f"HKCU\\{WINDOWS_RUN_KEY}\\{self._value_name}"

    def _reg(self):
        """注册表模块 (惰性 import: 非 Windows 上 import winreg 会 ImportError)."""
        if self._registry is None:
            import winreg  # noqa: PLC0415 - 平台专属模块, 只在 Windows 后端里用

            return winreg
        return self._registry

    def _read_value(self) -> Optional[str]:
        """读 Run 值; 值或键不存在 -> None (其余 OSError -> AutostartError)."""
        reg = self._reg()
        try:
            with reg.OpenKey(reg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY) as key:
                value, _kind = reg.QueryValueEx(key, self._value_name)
                return str(value)
        except FileNotFoundError:
            return None
        except OSError as e:
            raise AutostartError(f"读注册表 HKCU\\{WINDOWS_RUN_KEY} 失败: {e}") from e

    def is_registered(self) -> bool:
        return self._read_value() is not None

    def register(self) -> AutostartResult:
        command = self._plan.windows_command()
        # 超限必须拦在写入前: 截断后的值会变成一条跑不起来的命令, 且用户无从判断
        if len(command) > WINDOWS_COMMAND_MAX:
            raise AutostartError(
                f"自启命令长 {len(command)} 字符, 超过注册表 Run 值上限 {WINDOWS_COMMAND_MAX}: "
                f"请把工具目录或数据目录挪短后重试 (命令: {command})"
            )
        existing = self._read_value()
        if existing == command:
            return AutostartResult(
                ACTION_SKIPPED,
                f"自启已注册, 跳过: {self.target} (命令与当前参数一致)",
            )
        reg = self._reg()
        try:
            with reg.CreateKeyEx(reg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY, 0, reg.KEY_SET_VALUE) as key:
                reg.SetValueEx(key, self._value_name, 0, reg.REG_SZ, command)
        except OSError as e:
            raise AutostartError(f"写注册表 HKCU\\{WINDOWS_RUN_KEY} 失败: {e} "
                                 f"(该键属当前用户, 正常无需提权; 被安全软件拦截时请放行本工具)") from e
        refreshed = "已刷新" if existing is not None else "已注册"
        return AutostartResult(
            ACTION_REGISTERED,
            f"{refreshed}开机自启: {self.target} (登录时触发) -> {command}",
        )

    def unregister(self) -> AutostartResult:
        if not self.is_registered():
            return AutostartResult(
                ACTION_ABSENT,
                f"自启未注册, 无需卸载: {self.target} 不存在",
            )
        reg = self._reg()
        try:
            with reg.OpenKey(reg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY, 0, reg.KEY_SET_VALUE) as key:
                reg.DeleteValue(key, self._value_name)
        except FileNotFoundError:
            # 竞态: 判存在与删之间被别人删了 -> 已是期望态
            return AutostartResult(ACTION_ABSENT, f"自启未注册, 无需卸载: {self.target} 已不存在")
        except OSError as e:
            raise AutostartError(f"删注册表值 {self.target} 失败: {e}") from e
        return AutostartResult(ACTION_UNREGISTERED, f"已卸载开机自启: {self.target} 已删除")


# ---- Linux: systemd --user ----


class SystemdUserBackend(AutostartBackend):
    """Linux 后端: ~/.config/systemd/user/<unit> + systemctl --user enable --now.

    已注册判据 = 单元文件内容一致 **且** `systemctl --user is-enabled` 退出码 0。
    只查文件存在会漏掉「文件在但服务被 disable」(重复注册会谎报成功却拉不起来)。
    前置条件: systemd --user 需登录会话 (SSH 裸连需 loginctl enable-linger)。
    """

    platform = PLATFORM_LINUX

    def __init__(
        self,
        plan: AutostartPlan,
        runner: Runner,
        *,
        home: str,
        unit_name: str = DEFAULT_SYSTEMD_UNIT,
    ) -> None:
        super().__init__(plan, runner)
        self._unit_name = unit_name
        self._path = os.path.join(home, ".config", "systemd", "user", unit_name)

    @property
    def target(self) -> str:
        return self._path

    def render_unit(self) -> str:
        """单元文件内容 (纯函数, 逐字节可比对 -> 漂移可判)."""
        argv = self._plan.daemon_argv()
        exec_start = " ".join(f'"{a}"' if " " in a else a for a in argv)
        return (
            "# Generated by global-traffic-monitor install-autostart (S5).\n"
            "# Manual edits are overwritten on the next register.\n"
            "[Unit]\n"
            "Description=global-traffic-monitor - machine-wide traffic history (TrafficMonitor replacement)\n"
            "Wants=network-online.target\n"
            "After=network-online.target\n"
            "\n"
            "[Service]\n"
            "Type=simple\n"
            f"ExecStart={exec_start}\n"
            "Restart=on-failure\n"
            "RestartSec=5\n"
            "\n"
            "[Install]\n"
            "WantedBy=default.target\n"
        )

    def is_registered(self) -> bool:
        return os.path.isfile(self._path)

    def _is_enabled(self) -> bool:
        """只认退出码 (is-enabled 的文案随语言变; 0 = 已启用/静态)."""
        return self._run(["systemctl", "--user", "is-enabled", self._unit_name]).returncode == 0

    def register(self) -> AutostartResult:
        desired = self.render_unit()
        current = _read_text_lf(self._path)
        same = current == desired
        if same and self._is_enabled():
            return AutostartResult(
                ACTION_SKIPPED,
                f"自启已注册, 跳过: {self._path} (单元内容一致且已启用)",
            )
        if not same:
            _write_text_lf(self._path, desired)
        self._run_checked(["systemctl", "--user", "daemon-reload"], "systemctl --user daemon-reload")
        self._run_checked(
            ["systemctl", "--user", "enable", "--now", self._unit_name],
            "systemctl --user enable --now",
        )
        refreshed = "已重写单元内容" if not same else "单元内容未变, 仅重新启用"
        return AutostartResult(
            ACTION_REGISTERED,
            f"已注册开机自启: {self._path} ({refreshed}; systemctl --user enable --now {self._unit_name})",
        )

    def unregister(self) -> AutostartResult:
        if not self.is_registered():
            return AutostartResult(ACTION_ABSENT, f"自启未注册, 无需卸载: {self._path} 不存在")
        # disable 失败不阻断: 卸载目标是「下次登录不再自起」, 删掉单元文件 + reload 即达成;
        # 失败原因 (如单元未加载) 记进结论, 不静默吞掉
        warn = ""
        r = self._run(["systemctl", "--user", "disable", "--now", self._unit_name])
        if r.returncode != 0:
            warn = f" [WARN: systemctl disable --now 非 0 (rc={r.returncode}), 单元文件仍已删除]"
        os.remove(self._path)
        self._run_checked(["systemctl", "--user", "daemon-reload"], "systemctl --user daemon-reload")
        return AutostartResult(
            ACTION_UNREGISTERED,
            f"已卸载开机自启: 已删除 {self._path} 并 daemon-reload{warn}",
        )


# ---- macOS: launchd LaunchAgent ----


class LaunchdBackend(AutostartBackend):
    """macOS 后端: ~/Library/LaunchAgents/<label>.plist + launchctl bootstrap.

    已注册判据 = plist 内容一致 **且** `launchctl print gui/<uid>/<label>` 退出码 0。
    RunAtLoad + KeepAlive 与 systemd 侧 Restart=on-failure 对齐 (崩溃自恢复)。
    """

    platform = PLATFORM_MACOS

    def __init__(
        self,
        plan: AutostartPlan,
        runner: Runner,
        *,
        home: str,
        uid: int,
        label: str = DEFAULT_LAUNCHD_LABEL,
    ) -> None:
        super().__init__(plan, runner)
        self._label = label
        self._uid = uid
        self._path = os.path.join(home, "Library", "LaunchAgents", f"{label}.plist")

    @property
    def target(self) -> str:
        return self._path

    @property
    def service_target(self) -> str:
        return f"gui/{self._uid}/{self._label}"

    def render_plist(self) -> bytes:
        """plist 内容 (纯函数; plistlib 对 dict 键排序 -> 输出确定可比对)."""
        return plistlib.dumps(
            {
                "Label": self._label,
                "ProgramArguments": self._plan.daemon_argv(),
                "RunAtLoad": True,
                "KeepAlive": True,
            },
            fmt=plistlib.FMT_XML,
            sort_keys=True,
        )

    def is_registered(self) -> bool:
        return os.path.isfile(self._path)

    def _is_loaded(self) -> bool:
        return self._run(["launchctl", "print", self.service_target]).returncode == 0

    def _read_plist(self) -> Optional[bytes]:
        try:
            with open(self._path, "rb") as f:
                return f.read()
        except FileNotFoundError:
            return None

    def register(self) -> AutostartResult:
        desired = self.render_plist()
        loaded = self._is_loaded()
        if self._read_plist() == desired and loaded:
            return AutostartResult(
                ACTION_SKIPPED,
                f"自启已注册, 跳过: {self._path} (plist 一致且已加载)",
            )
        if loaded:
            # 已加载但内容要变: 先 bootout 再 bootstrap, 免得 launchd 拒绝重复加载
            self._run_checked(["launchctl", "bootout", self.service_target], "launchctl bootout")
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "wb") as f:
            f.write(desired)
        self._run_checked(
            ["launchctl", "bootstrap", f"gui/{self._uid}", self._path],
            "launchctl bootstrap",
        )
        return AutostartResult(
            ACTION_REGISTERED,
            f"已注册开机自启: {self._path} (launchctl bootstrap gui/{self._uid})",
        )

    def unregister(self) -> AutostartResult:
        if not self.is_registered():
            return AutostartResult(ACTION_ABSENT, f"自启未注册, 无需卸载: {self._path} 不存在")
        warn = ""
        r = self._run(["launchctl", "bootout", self.service_target])
        if r.returncode != 0:
            warn = f" [WARN: launchctl bootout 非 0 (rc={r.returncode}), plist 仍已删除]"
        os.remove(self._path)
        return AutostartResult(
            ACTION_UNREGISTERED,
            f"已卸载开机自启: 已删除 {self._path}{warn}",
        )


# ---- 平台探测与装配 ----


def platform_from_sys(sys_platform: str) -> str:
    """sys.platform 值 -> 内部平台名; 无后端 -> UnsupportedPlatformError (明确提示)."""
    if sys_platform.startswith("win"):
        return PLATFORM_WINDOWS
    if sys_platform == "linux":
        return PLATFORM_LINUX
    if sys_platform == "darwin":
        return PLATFORM_MACOS
    raise UnsupportedPlatformError(
        f"当前平台不支持自启注册: {sys_platform!r} (仅支持 Windows / Linux / macOS); "
        "请自行把 `global-traffic-monitor run` 加进本机自启机制"
    )


def detect_platform() -> str:
    """探测本机平台 (CLI 生产路径; 测试走 build_installer 的 platform 注入)."""
    return platform_from_sys(sys.platform)


def build_installer(
    data_dir: str,
    *,
    platform: Optional[str] = None,
    python_exe: Optional[str] = None,
    home: Optional[str] = None,
    uid: Optional[int] = None,
    runner: Optional[Runner] = None,
    registry: object | None = None,
) -> AutostartBackend:
    """按平台装配自启后端.

    默认值全部取自真实环境 (平台 = sys.platform, 解释器 = sys.executable, home = ~,
    uid = os.getuid, runner = subprocess, registry = winreg); 显式传入只用于测试注入
    平台命令层 / 文件系统根 / 注册表模块 —— 生产路径同样经过本函数, 没有「只为测试
    存在」的分支。
    """
    plat = platform or detect_platform()
    exe = python_exe if python_exe is not None else sys.executable
    if not exe:
        raise AutostartError("无法确定解释器路径 (sys.executable 为空); 请用装了 global-traffic-monitor 的 python 运行本命令")
    if not os.path.isfile(exe):
        raise AutostartError(f"解释器不存在: {exe!r} (自启项会指向一个跑不起来的命令, 已拒绝注册)")
    plan = AutostartPlan(
        python_exe=exe,
        data_dir=os.path.abspath(os.path.expanduser(data_dir)),
    )
    run = runner or default_runner
    if plat == PLATFORM_WINDOWS:
        return WindowsRunKeyBackend(plan, run, registry=registry)
    if plat == PLATFORM_LINUX:
        return SystemdUserBackend(plan, run, home=home or os.path.expanduser("~"))
    if plat == PLATFORM_MACOS:
        if uid is None:
            uid = os.getuid()
        return LaunchdBackend(plan, run, home=home or os.path.expanduser("~"), uid=uid)
    raise UnsupportedPlatformError(
        f"当前平台不支持自启注册: {plat!r} (仅支持 Windows / Linux / macOS); "
        "请自行把 `global-traffic-monitor run` 加进本机自启机制"
    )
