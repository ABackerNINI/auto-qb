"""产品进程起停 —— 真机片「进程边界」类用例的公共件(RM01 起, 后续片可复用)。

为什么不复用 runner.py: 那个管的是 **qB 实例**(36595/36596 的进程), 这里管的是**产品自身**
(`python -m auto_qb <config>`)。两者的生命周期、日志位置、退出语义完全不同, 混在一起会让
"停的是谁"变成每次都要想一遍的问题。

三条硬事实(2026-10-31 RM01 实测得出, 全部有现场证据, 别再踩):

1. **`--dry-run` 不启 WEB 服务** —— `webui/module.py:66` 是 `if dry_run or not web.enabled: return`。
   所以 WEB 相关用例(启动日志/端口/token)**必须不带 --dry-run**; 反过来, 只验进程边界的用例
   可以带, 少一堆副作用。
2. **Windows 上从外部发 SIGTERM 等于强杀** —— `Popen.send_signal(SIGTERM)` 走 TerminateProcess,
   退出码 1, `finally` 一行都不跑, 日志里没有收尾。真正的 SIGTERM handler(`cli._sigterm_to_keyboardinterrupt`)
   只能用**进程内** `signal.raise_signal(SIGTERM)` 触发(见 `graceful_after`), 或者在 Linux 上从外部发。
   Ctrl+C 那条路也不行: 子进程没有控制台, `CTRL_C_EVENT` 投递不到。
3. **配置必须写 `schema_version: 5`** —— 否则每次启动都走 v1→v5 迁移; 非 dry-run 时还会**改写**
   配置文件并留备份, 把临时目录搅浑。

安全口径: 生成的配置**只指向 36596**(空库副实例), 端口写死不走参数; 用例开头可 `assert_cfg_target()`
复核, 防止手滑把产品进程指到 36595 的真实种子上。
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                      # tests-real/lib -> 仓库根
PY = ROOT / ".venv" / "Scripts" / "python.exe"
WORK = HERE.parent / ".work" / "rm01"       # 与 seed.py 同族的 .work 落点

QB_PORT = 36596                             # 只碰空库副实例
WEB_PORT_LO, WEB_PORT_HI = 39000, 39999     # 与 36595/36596/生产 WEB 端口互不重叠
WEB_START_TIMEOUT = 30.0

CONFIG_TEMPLATE = """\
config:
    schema_version: 5
    qbittorrent:
        host: 127.0.0.1
        port: {qb_port}
        username: ""
        password: ""
    data_dir: "{data_dir}"
    main_tick: 1.5S
    interval: 60S
    log:
        level: INFO
    grouping:
        enabled: false
    web:
        enabled: {web_enabled}
        host: 127.0.0.1
        port: {web_port}
        skip_local_verify: true
    notify:
        enabled: false
"""


# ---------- 端口 ----------

def port_free(port: int) -> bool:
    """能否 bind 到 127.0.0.1:port(探空口径, 不占端口)

    **不要加 SO_REUSEADDR**: Windows 上它的语义是「允许抢占别人正在监听的端口」, 于是
    `bind` 成功并不代表端口空闲 —— 实测 2026-10-31 RM01-07 就因此谎报「已释放」, 紧接着
    重启撞 Errno 10048。裸 bind 才是可信探针。
    """
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


_USED_PORTS: set[int] = set()


def free_port(lo: int = WEB_PORT_LO, hi: int = WEB_PORT_HI) -> int:
    """取一个当前空闲、且**本会话没用过**的端口; 段内全被占则抛(不静默退到别的段)

    为什么记 `_USED_PORTS`: 上一条用例刚停掉的进程, 监听套接字在 Windows 上要过一小会儿
    才真正消失(实测 2026-10-31: 整片连跑时 RM01-07 抢到 RM01-05 刚释放的 39000, 立刻
    10048; 单跑则不复现)。端口段够大, 直接不复用比 sleep 等它更可靠 —— 也避免"多睡一会儿
    就好了"这种靠时间的假稳。
    """
    for port in range(lo, hi + 1):
        if port in _USED_PORTS:
            continue
        if port_free(port):
            _USED_PORTS.add(port)
            return port
    raise RuntimeError(f"{lo}-{hi} 段没有可用端口 —— 先查残留进程")


# ---------- 临时工作区 / 配置 ----------

def case_dir(name: str, fresh: bool = True) -> Path:
    """用例专属目录 <tests-real>/.work/rm01/<name>; fresh=True 时先清空"""
    d = WORK / name
    if fresh and d.exists():
        import shutil

        shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_config(
    case: Path,
    web_port: int | None = None,
    web_enabled: bool = True,
    qb_port: int = QB_PORT,
) -> Path:
    """生成临时配置; 返回配置路径。data_dir 落在 case 目录内(状态/锁/token/日志都在里面)"""
    data_dir = (case / "data").as_posix()
    cfg = case / "config.yml"
    cfg.write_text(
        CONFIG_TEMPLATE.format(
            qb_port=qb_port,
            data_dir=data_dir,
            web_enabled="true" if web_enabled else "false",
            web_port=web_port if web_port is not None else free_port(),
        ),
        encoding="utf-8",
    )
    return cfg


def assert_cfg_target(cfg: Path, qb_port: int = QB_PORT) -> None:
    """复核配置指向 36596 —— 防手滑把产品进程指到真实种子所在的 36595"""
    text = cfg.read_text(encoding="utf-8")
    if f"port: {qb_port}" not in text:
        raise AssertionError(f"配置未指向 {qb_port}, 拒跑: {cfg}")
    if "port: 36595" in text:
        raise AssertionError(f"配置指向了 36595(真实种子), 拒跑: {cfg}")


def log_path(case: Path) -> Path:
    """产品日志: <data_dir>/logs/auto-qb.log"""
    return case / "data" / "logs" / "auto-qb.log"


def read_log(case: Path) -> str:
    p = log_path(case)
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


# ---------- 进程 ----------

class AppProc:
    """一个产品进程。所有起法都经 `start()`; 收尾必须 `stop()/kill()` 之一。"""

    def __init__(self, popen: subprocess.Popen, case: Path, cfg: Path):
        self.popen = popen
        self.case = case
        self.cfg = cfg

    # 观测
    @property
    def pid(self) -> int:
        """**启动器**的 pid(Popen 拿到的那个)。

        ⚠️ 不等于跑代码那个进程的 pid: uv 在 Windows 上给 venv 的 `Scripts/python.exe` 是个
        47KB 启动器(基解释器 91KB), 它 CreateProcess 出真解释器再等着 —— 所以 `Popen.pid`
        与产品日志/锁 meta 里的 pid **不是同一个**。要真 pid 用 `real_pid()`。
        """
        return self.popen.pid

    def real_pid(self) -> int:
        """真正在跑产品代码的 pid: 优先取锁 meta(持锁者就是它), 拿不到退回启动器 pid"""
        meta = self.case / "data" / "state.lock.meta.json"
        try:
            import json

            return int(json.loads(meta.read_text(encoding="utf-8"))["pid"])
        except (OSError, ValueError, KeyError):
            return self.popen.pid

    def alive(self) -> bool:
        return self.popen.poll() is None

    def returncode(self) -> int | None:
        return self.popen.poll()

    def wait(self, timeout: float = 30.0) -> int:
        return self.popen.wait(timeout=timeout)

    def log(self) -> str:
        return read_log(self.case)

    def wait_log(self, pattern: str, timeout: float = WEB_START_TIMEOUT) -> bool:
        """等日志里出现 pattern; 超时返回 False(由用例决定怎么判, 这里不抛)"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if pattern in self.log():
                return True
            if not self.alive():
                return pattern in self.log()
            time.sleep(0.15)
        return False

    def wait_web(self, timeout: float = WEB_START_TIMEOUT) -> bool:
        return self.wait_log("WEB UI 已启动", timeout)

    # 收尾
    def stop(self, timeout: float = 15.0) -> int | None:
        """请求退出并等待: 先走优雅路径(见 graceful_after), 不行再强杀"""
        if not self.alive():
            return self.returncode()
        try:
            self.popen.terminate()
            return self.popen.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.kill()
            return self.returncode()

    def kill(self) -> None:
        """强杀整棵进程树(taskkill /F /T): 模拟崩溃/断电, 用于验「锁会不会被永久占住」

        **必须带 /T**: venv 的 `Scripts/python.exe` 是启动器, 真解释器是它的子进程 ——
        只杀启动器会留下孤儿进程继续持锁, 用例就会"测了个寂寞"(还以为在验崩溃恢复)。
        """
        if not self.alive():
            return
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(self.popen.pid)],
            capture_output=True,
            check=False,
        )
        try:
            self.popen.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stop()
        return False


def _graceful_runner(case: Path) -> Path:
    """生成"N 秒后给自己发 SIGTERM"的跑壳 —— Windows 上唯一能触发 handler 的办法(见模块 docstring 第 2 条)"""
    runner = case / "runner_graceful.py"
    runner.write_text(
        "import signal, sys, threading\n"
        "from auto_qb import cli\n"
        "# argv: <脚本> <配置> <延迟秒>; 延迟先 pop, 否则 argparse 报 unrecognized\n"
        "delay = float(sys.argv.pop(2))\n"
        "threading.Timer(delay, lambda: signal.raise_signal(signal.SIGTERM)).start()\n"
        "raise SystemExit(cli.main() or 0)\n",
        encoding="utf-8",
    )
    return runner


def start(
    cfg: Path,
    case: Path | None = None,
    *,
    dry_run: bool = False,
    graceful_after: float | None = None,
    extra_args: list[str] | None = None,
) -> AppProc:
    """起一个产品进程。

    dry_run:        传 --dry-run(注意: 同时**不会**启 WEB 服务)
    graceful_after: 不为 None 时走 `_graceful_runner`, N 秒后给自己发 SIGTERM ⇒ 走优雅退出
    """
    case = case or cfg.parent
    assert_cfg_target(cfg)
    if graceful_after is not None:
        cmd = [str(PY), str(_graceful_runner(case)), str(cfg), str(graceful_after)]
    else:
        cmd = [str(PY), "-m", "auto_qb", str(cfg)]
    if dry_run:
        cmd.append("--dry-run")
    if extra_args:
        cmd.extend(extra_args)
    popen = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    return AppProc(popen, case, cfg)


def run_cli(args: list[str], timeout: float = 60.0) -> subprocess.CompletedProcess:
    """跑一次产品 CLI 并收齐 stdout/stderr(用于"起不来"类断言: 退出码 + stderr 文案)"""
    return subprocess.run(
        [str(PY), "-m", "auto_qb", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


# ---------- 注册表(开机自启) ----------

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_KEY = "auto-qb"


def registry_backup() -> tuple[bool, str | None]:
    """备份 HKCU\\...\\Run\\auto-qb: (是否存在, 原值)。读不到按不存在处理(不抛)"""
    if sys.platform != "win32":
        return (False, None)
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, APP_KEY)
            return (True, str(value))
    except OSError:
        return (False, None)


def registry_restore(existed: bool, value: str | None) -> None:
    """按备份还原: 原本不存在就删掉(不留痕), 原本有值就写回。失败抛, 由用例记红"""
    if sys.platform != "win32":
        return
    import winreg

    if existed and value is not None:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_KEY, 0, winreg.REG_SZ, value)
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_KEY)
    except OSError:
        pass
