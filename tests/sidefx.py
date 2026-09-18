r"""测试期"真实系统副作用"**记账器与判定策略**(2026-09-18 普查后固化)。

**为什么要有它**: 2026-09-18 用户报"测试时会弹出系统通知框", 根因是测试真的走了系统通知通道;
修完通知后做了一次**全量副作用普查**, 又挖出一个"真写 HKCU 注册表且写完不清理"的 AUMID 键。
那次普查用的是临时探针(在 `%TEMP%` 里, 随会话消失)。本模块把它固化成**常驻守卫** ——
同类问题不再靠人肉发现。

**做什么**: 拦在五类"真实副作用入口"之前**记账**(只记录, 一律放行给真实实现), 再按
`is_violation()` 判定是否越界:

| 类别 | 记账入口 | 放行条件(不在放行条件内 = 越界) |
|---|---|---|
| `POPEN` | `subprocess.Popen.__init__` | 可执行名 ∈ `ALLOWED_EXECUTABLES` |
| `REG` | `winreg.CreateKeyEx` / `DeleteKey` | 键路径 ∈ `ALLOWED_REG_KEYS` |
| `REGVAL` | `winreg.SetValueEx` / `DeleteValue` | 值名 ∈ `ALLOWED_REG_VALUES` |
| `FSDEL` | `os.remove` / `unlink` / `rmdir` + `shutil.rmtree` | 路径落在临时目录 |
| `SYMLINK` | `os.symlink` | 路径落在临时目录 |
| `BIND` | `socket.socket.bind` | 地址为回环 |
| `CONNECT` | `socket.socket.connect` / `socket.create_connection` | 目标为回环(测试不得连外网) |
| `LAUNCH` | `os.startfile` / `os.system` / `webbrowser.open` | **无** —— 一律越界 |

`LAUNCH` 是单列的一类: 它们**不走 `subprocess`**(所以 `POPEN` 抓不到), 但同样会"弹个窗口"
(资源管理器 / 浏览器 / shell), 和用户最初报的"测试时弹出系统通知框"是同一族问题。
`open_path()` 在 Windows 上就走 `os.startfile`, `/api/open-path` 能触达它。
(`subprocess.call/check_output/run` 内部都会走到 `Popen`, 由 `POPEN` 覆盖, 不必单列。)

**不做什么**: ①**不阻断**任何操作(只记账, 语义不变); ②不记录只读操作
(`winreg.OpenKey`/`QueryValue`/`os.stat` 等无副作用); ③`SetValueEx` 只记值名不记键路径 ——
本仓两处调用都紧跟 `CreateKeyEx`, 键路径由 `REG` 那条记录覆盖(见 `is_violation` 注释)。

**已知坑(普查时踩过, 已固化在 `is_temp_path`)**: 用 `tempfile.gettempdir()` 直接做
`abspath` 前缀比对会被 Windows 扩展长度前缀 `\\?\` 绕过(`abspath` 不剥它) —— 那次把
157 条"临时目录内的 pytest 自检清理"全误判成"仓库外删除"。
"""
import os
import shutil
import socket
import subprocess
import tempfile
from typing import Any, List, Optional, Tuple

# ============================ 放行清单(与普查实测一一对应) ============================

# 测试期允许启动的外部进程: 目前只有前端静态守阵的 node 语法校验
ALLOWED_EXECUTABLES = frozenset({"node", "node.exe"})

# 允许写入的注册表键: autostart 的 HKCU Run 键(既有明文约定, 且用例在 finally 里自清理)。
# 注意 AUMID 键**不在**其中 —— 它由 conftest 的守卫拦成空操作, 真落盘就是越界。
ALLOWED_REG_KEYS = (r"Software\Microsoft\Windows\CurrentVersion\Run", )

# 允许读写的注册表值名: autostart 自己那个值(写 + 删都走它)
ALLOWED_REG_VALUES = ("auto-qb", )

# ============================ 判定工具 ============================


def _norm_path(path: Any) -> str:
    """规范化路径为可比较形式: 剥掉 Windows 扩展长度前缀 `\\\\?\\` 后转 normcase。

    `os.path.abspath()` **不会**剥掉 `\\\\?\\` 前缀, 直接拿它与 `tempfile.gettempdir()` 比前缀
    会把临时目录下的操作全判成"仓库外"(2026-09-18 普查的 157 条假阳性)。
    """
    s = str(path)
    if s.startswith("\\\\?\\"):
        rest = s[4:]
        s = "\\\\" + rest[4:] if rest.upper().startswith("UNC\\") else rest
    try:
        s = os.path.realpath(s)
    except OSError:  # 路径不存在/不可读时退回原样, 判定交给调用方
        pass
    return os.path.normcase(s)


def _temp_roots() -> List[str]:
    """临时目录根集合(取所有可能的来源, 避免不同机器上 gettempdir 不一致)"""
    candidates = [tempfile.gettempdir(), "/tmp", "/var/tmp"]
    for name in ("TMPDIR", "TEMP", "TMP"):
        value = os.environ.get(name)
        if value:
            candidates.append(value)
    roots = []
    for c in candidates:
        try:
            roots.append(_norm_path(c))
        except (OSError, ValueError):
            # 环境变量里的临时目录取值可能是畸形串(含空字节/超长等); 记账器绝不能因此拖垮整个测试会话
            continue
    return roots


TEMP_ROOTS = _temp_roots()


def is_temp_path(path: Any) -> bool:
    """路径是否落在临时目录下(经 realpath, 符号链接指向仓库外也会被识别)

    判定不了时返回 False(= 当作"不在临时目录" ⇒ 记越界) —— 守卫的取舍是**宁可误报也不能漏报**。
    """
    try:
        target = _norm_path(path)
    except (OSError, ValueError):  # 畸形路径(空字节/超长等): 记账器不得因此拖垮被记的那个调用
        return False
    for root in TEMP_ROOTS:
        if target == root or target.startswith(root.rstrip("\\/") + os.sep):
            return True
    return False


def is_loopback(addr: Any) -> bool:
    """socket 地址是否为回环(测试只允许监听本机)"""
    host = addr[0] if isinstance(addr, (list, tuple)) else addr
    host = str(host).lower()
    return host in ("localhost", "::1") or host.startswith("127.")


def _allowed_executable(args: Any) -> bool:
    if isinstance(args, (list, tuple)) and args:
        exe = os.path.basename(str(args[0])).lower()
        return exe in ALLOWED_EXECUTABLES
    return False


def is_violation(record: "Record") -> bool:
    """一条记录是否越界(不在放行清单里)"""
    kind, detail = record
    if kind == "POPEN":
        return not _allowed_executable(detail)
    if kind == "REG":
        return not str(detail).startswith(ALLOWED_REG_KEYS)
    if kind == "REGVAL":
        return str(detail) not in ALLOWED_REG_VALUES
    if kind == "FSDEL":
        return not is_temp_path(detail)
    if kind == "SYMLINK":
        return not is_temp_path(detail)
    if kind in ("BIND", "CONNECT"):
        return not is_loopback(detail)
    if kind == "LAUNCH":
        return True  # 弹窗口类副作用没有"测试期可以忍"的情形
    return True  # 未知类别一律当越界, 免得新类别悄悄漏过


# ============================ AUMID 空操作替身 ============================

# 记录项: (类别, 明细) —— 明细是可打印对象, 失败时便于定位
Record = Tuple[str, Any]


class StubRegKey:
    """`winreg.CreateKeyEx` 的替身: 支持 `with`, 不落盘。

    放在本模块(而不是 conftest)是为了让记账器能**识别**"被守卫拦下的调用" ——
    否则两个夹具谁先安装谁后安装会让 AUMID 键一会儿被记成越界、一会儿不被记。
    记账器见到本类型即知"这次调用没真的写注册表", 不记账、不判越界。
    """
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


# ============================ 记账器 ============================


class SideFxRecorder:
    """五类真实副作用的记账器: 安装后持续记账, 结束后按 `is_violation` 判定。"""
    def __init__(self) -> None:
        self.records: List[Record] = []
        self.installed = False
        self._saved: List[Tuple[Any, str, Any]] = []

    # ---------- 安装 / 卸载 ----------

    def install(self) -> None:
        """装上各入口的记账包装(幂等: 重复调用无副作用)"""
        if self.installed:
            return

        def patch(container, name, wrapper):
            self._saved.append((container, name, getattr(container, name)))
            setattr(container, name, wrapper)

        recorder = self

        # ① 外部进程
        orig_popen_init = subprocess.Popen.__init__

        def popen_init(self, args, *a, **kw):
            recorder.records.append(("POPEN", args))
            return orig_popen_init(self, args, *a, **kw)

        patch(subprocess.Popen, "__init__", popen_init)

        # ①b "启动"类: 不走 subprocess, 但同样会弹窗口(资源管理器 / 浏览器 / shell)
        for mod, name in ((os, "startfile"), (os, "system")):
            orig_launch = getattr(mod, name, None)
            if orig_launch is None:  # 非 Windows 上 os.startfile 不存在
                continue

            def make_launch(orig=orig_launch):
                def wrapper(target, *a, **kw):
                    recorder.records.append(("LAUNCH", target))
                    return orig(target, *a, **kw)

                return wrapper

            patch(mod, name, make_launch())

        import webbrowser

        orig_open_browser = webbrowser.open

        def open_browser(url, *a, **kw):
            recorder.records.append(("LAUNCH", url))
            return orig_open_browser(url, *a, **kw)

        patch(webbrowser, "open", open_browser)

        # ② 注册表(非 Windows 无 winreg, 跳过)
        try:
            import winreg
        except ImportError:
            winreg = None  # type: ignore
        if winreg is not None:
            orig_create = winreg.CreateKeyEx

            def create_key_ex(key, sub_key, *a, **kw):
                result = orig_create(key, sub_key, *a, **kw)
                if isinstance(result, StubRegKey):
                    return result  # 被 AUMID 守卫拦成空操作 —— 不是真实写入, 不记账
                recorder.records.append(("REG", sub_key))
                return result

            patch(winreg, "CreateKeyEx", create_key_ex)

            orig_delete_key = winreg.DeleteKey

            def delete_key(key, sub_key, *a, **kw):
                recorder.records.append(("REG", sub_key))
                return orig_delete_key(key, sub_key, *a, **kw)

            patch(winreg, "DeleteKey", delete_key)

            orig_set_value = winreg.SetValueEx

            def set_value_ex(key, name, *a, **kw):
                if not isinstance(key, StubRegKey):
                    recorder.records.append(("REGVAL", name))
                return orig_set_value(key, name, *a, **kw)

            patch(winreg, "SetValueEx", set_value_ex)

            orig_delete_value = winreg.DeleteValue

            def delete_value(key, name, *a, **kw):
                recorder.records.append(("REGVAL", name))
                return orig_delete_value(key, name, *a, **kw)

            patch(winreg, "DeleteValue", delete_value)

        # ③ 文件删除
        for name in ("remove", "unlink", "rmdir"):
            orig = getattr(os, name, None)
            if orig is None:
                continue

            def make_fs_del(orig=orig):
                def wrapper(path, *a, **kw):
                    recorder.records.append(("FSDEL", path))
                    return orig(path, *a, **kw)

                return wrapper

            patch(os, name, make_fs_del())

        orig_rmtree = shutil.rmtree

        def rmtree(path, *a, **kw):
            recorder.records.append(("FSDEL", path))
            return orig_rmtree(path, *a, **kw)

        patch(shutil, "rmtree", rmtree)

        # ④ 建符号链接(极老版本 Windows 上 os.symlink 不存在, 那就无从"真实建链", 跳过)
        orig_symlink = getattr(os, "symlink", None)
        if orig_symlink is not None:

            def symlink(src, dst, *a, **kw):
                recorder.records.append(("SYMLINK", dst))
                return orig_symlink(src, dst, *a, **kw)

            patch(os, "symlink", symlink)

        # ⑤ 网络监听
        orig_bind = socket.socket.bind

        def bind(self, addr, *a, **kw):
            recorder.records.append(("BIND", addr))
            return orig_bind(self, addr, *a, **kw)

        patch(socket.socket, "bind", bind)

        # ⑥ 出站连接: 测试不得连外网(本地假服务是回环, 放行)
        orig_connect = socket.socket.connect

        def connect(self, addr, *a, **kw):
            recorder.records.append(("CONNECT", addr))
            return orig_connect(self, addr, *a, **kw)

        patch(socket.socket, "connect", connect)

        orig_create_connection = socket.create_connection

        def create_connection(addr, *a, **kw):
            recorder.records.append(("CONNECT", addr))
            return orig_create_connection(addr, *a, **kw)

        patch(socket, "create_connection", create_connection)

        self.installed = True

    def uninstall(self) -> None:
        for container, name, original in reversed(self._saved):
            setattr(container, name, original)
        self._saved.clear()
        self.installed = False

    # ---------- 查询 ----------

    @property
    def violations(self) -> List[Record]:
        """越界记录(不在放行清单里的真实副作用)"""
        return [r for r in self.records if is_violation(r)]

    def report(self) -> str:
        """人类可读的台账摘要(与 2026-09-18 普查报告同形态)"""
        lines = [f"副作用台账: 共 {len(self.records)} 条, 越界 {len(self.violations)} 条"]
        for kind in ("POPEN", "LAUNCH", "REG", "REGVAL", "FSDEL", "SYMLINK", "BIND", "CONNECT"):
            total = sum(1 for k, _ in self.records if k == kind)
            if not total:
                continue
            bad = sum(1 for r in self.violations if r[0] == kind)
            lines.append(f"  {kind:<8} {total:>4} 条, 越界 {bad}")
        for kind, detail in self.violations[:20]:
            lines.append(f"  !! {kind}: {detail!r}")
        return "\n".join(lines)


# 会话级单例: 由 conftest 的 autouse 夹具安装, 测试可通过同名夹具取用
SESSION: Optional[SideFxRecorder] = None

# 收尾台账文本: 夹具在 finally 里写好, 由 conftest 的 pytest_terminal_summary 打印。
# 存在的理由: 没有越界时守卫**完全静默** —— 不打印就没人知道它在工作, 久了会被当死代码删掉。
LAST_REPORT: Optional[str] = None
