"""测试临时目录自举 + 写重型测试互斥锁(计划 26-11-02-0657)。

进程启动极早期由 tests/conftest.py 模块级调用一次(`bootstrap()`)。职责:

1. 探测实例唯一临时根: 候选顺序 R: → H: → 系统 temp(单一配置点 TMP_ROOT_CANDIDATES,
   唯一一份, 引用者 import 不得复制字面量 —— 散落守卫见 tests/test_tmp_bootstrap.py);
2. 外部 TMPDIR 一律拒收(rc=4): 值不含 BOOTSTRAP_MARK 即视为外部注入, 响亮退出, 不兜底
   (旧 config 写死 R:/ 自 2026-09-23 引入起在本机静默回落从未生效 —— 教训就是不许静默);
3. 幂等: 已自举(值含标记, 如 xdist worker / 嵌套 pytest 继承 env)则复用, 不重探测;
4. 残留清扫: mtime 超 CLEAN_AGE_HOURS 且内嵌 pid 已死, 双条件缺一不可, 只删实例根;
5. 互斥锁(写重型): <系统temp>/auto-qb-locks/<仓库hash> mkdir 原子抢占, 失败 rc=3,
   僵尸(pid 死 / CreateTime 不符)自愈, sessionfinish + atexit 双释放;
6. coverage 落实例根, 不再脏仓库根: COVERAGE_FILE env(对 xdist worker/子进程有效)
   + conftest 的 pytest_configure 调 retarget_cov_data_file()(修主进程 pytest-cov
   早于 conftest 的 .coverage 绑定 —— env 对它无效, 实测见该函数 docstring)。
"""
from __future__ import annotations

import atexit
import hashlib
import os
import random
import re
import shutil
import string
import sys
import tempfile
import time
from pathlib import Path

# ===== 单一配置点: 候选根(全局唯一, 引用者 import 不得复制字面量) =====
# (盘符根, 子路径); 系统 temp 用 None 表示 —— 探测时取 tempfile 默认(tempfile.tempdir
# 已清缓存重算前不可信, 故这里直接读环境变量, 与 gettempdir 同序但只取 TEMP/TMP/默认)。
TMP_ROOT_CANDIDATES = (
    ("R:\\", "Temp"),
    ("H:\\", "Temp"),
    (None, ""),  # 系统 temp 回落
)

BOOTSTRAP_MARK = "auto-qb-tests"  # 自举值可识别标记(路径段)
CLEAN_AGE_HOURS = 12.0  # 残留清理阈值(暂定, 可调; 拍板 2026-11-02)
LOCK_MARK = "auto-qb-locks"
RC_EXTERNAL_TMPDIR = 4  # 外部 TMPDIR 拒收
RC_TEST_LOCKED = 3  # 写重型锁被占

_LOCK_HELD: Path | None = None
_INSTANCE_ROOT: Path | None = None


def _norm(p: str | os.PathLike) -> str:
    """路径归一化(大小写/8.3 短名/\\?\\ 前缀), 与 sidefx._norm_path 同思路。"""
    s = os.path.realpath(os.path.abspath(str(p)))
    if s.startswith("\\\\?\\"):
        s = s[4:]
    return os.path.normcase(s)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _repo_hash() -> str:
    return hashlib.sha1(_norm(_repo_root()).encode()).hexdigest()[:8]


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        h = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            if kernel32.GetExitCodeProcess(h, ctypes.byref(code)):
                return code.value == 259  # STILL_ACTIVE
            return False
        finally:
            kernel32.CloseHandle(h)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _proc_create_time(pid: int) -> float | None:
    """进程创建时间(epoch 秒); 取不到返回 None(僵尸判定降级由调用方处理)。"""
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        h = kernel32.OpenProcess(0x1000, False, pid)
        if not h:
            return None
        try:
            ct, et, kt, ut = (ctypes.c_ulonglong() for _ in range(4))
            if not kernel32.GetProcessTimes(h, ctypes.byref(ct), ctypes.byref(et), ctypes.byref(kt), ctypes.byref(ut)):
                return None
            return (ct.value / 10_000_000) - 11644473600  # FILETIME → epoch
        finally:
            kernel32.CloseHandle(h)
    try:
        return os.stat(f"/proc/{pid}").st_ctime
    except OSError:
        return None


def _system_temp() -> str:
    """系统 temp 根(不依赖 tempfile.tempdir 缓存): TMP/TEMP/USERPROFILE 同序回落。"""
    for var in ("TMP", "TEMP"):
        v = os.environ.get(var)
        if v and not _is_bootstrap_path(v):
            return v
    return tempfile.gettempdir()  # 最终兜底(此刻缓存尚未被本模块改写即系统值)


def _is_bootstrap_path(value: str) -> bool:
    return BOOTSTRAP_MARK in _norm(value).replace("\\", "/")


def _writable(root: Path) -> bool:
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / f".probe-{os.getpid()}"
        probe.write_text("x", encoding="ascii")
        probe.unlink()
        return True
    except OSError:
        return False


def _pick_root() -> Path:
    """按 TMP_ROOT_CANDIDATES 顺序探测, 首个可写者胜; 系统 temp 保底必可达。"""
    errors: list[str] = []
    for drive, sub in TMP_ROOT_CANDIDATES:
        if drive is None:
            base = Path(_system_temp()) / BOOTSTRAP_MARK
        else:
            base = Path(drive) / sub / BOOTSTRAP_MARK
        if drive is not None and not Path(drive).exists():
            continue  # 正常分支: 盘不存在走下一级(非失败)
        if _writable(base):
            return base
        errors.append(f"{base} 不可写")
    raise SystemExit(
        f"[FATAL] 临时根探测失败: 所有候选不可写 ({'; '.join(errors)})\n"
        f"候选顺序见 tests/_tmp_bootstrap.py::TMP_ROOT_CANDIDATES(R→H→系统temp, 单一配置点)。"
    )


def _rand6() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=6))


def _clean_stale(base: Path) -> list[str]:
    """双条件清扫: mtime 超 CLEAN_AGE_HOURS AND 内嵌 pid 已死; 只删实例根不钻子树。"""
    removed: list[str] = []
    now = time.time()
    pat = re.compile(r"^[0-9a-f]{8}-(\d+)-[a-z0-9]{6}$")
    try:
        entries = list(base.iterdir())
    except OSError:
        return removed
    for d in entries:
        m = pat.match(d.name)
        if not m or not d.is_dir():
            continue
        age_h = (now - d.stat().st_mtime) / 3600
        pid = int(m.group(1))
        if age_h >= CLEAN_AGE_HOURS and not _pid_alive(pid):
            shutil.rmtree(d, ignore_errors=True)
            removed.append(d.name)
    return removed


def _acquire_instance_root() -> Path:
    global _INSTANCE_ROOT
    if _INSTANCE_ROOT is not None:
        return _INSTANCE_ROOT
    env = os.environ.get("TMPDIR")
    if env:
        if _is_bootstrap_path(env):
            _INSTANCE_ROOT = Path(env)  # 幂等口: 继承自举值(xdist worker / 嵌套 pytest)
            return _INSTANCE_ROOT
        print(
            f"[FATAL] 外部 TMPDIR 拒收: {env!r}(进程 {os.getpid()})。\n"
            f"测试 TMPDIR 由 tests/_tmp_bootstrap.py 自举探测(R→H→%TEMP%), 不接受外部设置。\n"
            f"正确做法: 清掉环境变量后重跑(set TMPDIR= 或新 shell); "
            f"要换根, 改 tests/_tmp_bootstrap.py::TMP_ROOT_CANDIDATES 单一配置点。",
            file=sys.stderr,
        )
        raise SystemExit(RC_EXTERNAL_TMPDIR) from None
    base = _pick_root()
    _clean_stale(base)
    for _ in range(8):  # mkdir 原子抢占, 撞名重摇
        root = base / f"{_repo_hash()}-{os.getpid()}-{_rand6()}"
        try:
            root.mkdir()
            break
        except FileExistsError:
            continue
    else:
        raise SystemExit(f"[FATAL] 实例根创建连续撞名 8 次: {base}")
    os.environ["TMPDIR"] = str(root)
    tempfile.tempdir = None  # 清 gettempdir 缓存, 强制按新 TMPDIR 重算
    _INSTANCE_ROOT = root
    # 响亮断言: 禁止静默降级(旧 R:/ 配置失效 40 天无人察觉的根因)
    actual = _norm(tempfile.gettempdir())
    expect = _norm(root)
    if actual != expect:
        raise SystemExit(
            f"[FATAL] TMPDIR 自举后 gettempdir()={actual} 未落在实例根 {expect} 下 —— "
            f"有插件先于本模块固化了 tempfile 缓存, 拒绝带病继续。"
        )
    os.environ.setdefault("COVERAGE_FILE", str(root / "cov"))
    return root


# ===================== 写重型互斥锁 =====================


def _lock_dir() -> Path:
    return Path(_system_temp()) / LOCK_MARK / _repo_hash()


def _is_write_heavy(argv: list[str]) -> bool:
    """宁重勿轻: 收集根含 tests 目录且无 -k 过滤 → 写重型取锁; 显式参数优先。

    AQ_TEST_LOCK=off|force 逃生口; 误判只许偏重(多等一次锁)不许偏轻(放回并发)。
    """
    mode = os.environ.get("AQ_TEST_LOCK", "").lower()
    if mode == "off":
        return False
    if mode == "force":
        return True
    args = " ".join(argv)
    has_tests_root = any(
        a in ("tests", "tests/", ".commands",
              ".agents/skills/commands") or a.startswith("tests\\") or a.startswith("tests/")
        for a in argv if not a.startswith("-")
    )
    has_filter = "-k" in args or re.search(r"tests[\\/]\S+\.py", args)
    return has_tests_root and not has_filter


def _read_lock(d: Path) -> dict:
    try:
        parts = (d / "owner").read_text(encoding="utf-8").splitlines()
        return dict(kv.split("=", 1) for kv in parts if "=" in kv)
    except OSError:
        return {}


def _lock_zombie(d: Path, info: dict) -> bool:
    try:
        pid = int(info.get("pid", "-1"))
    except ValueError:
        return True
    if not _pid_alive(pid):
        return True
    ctime = _proc_create_time(pid)
    if ctime is None:  # CreateTime 取不到 → 降级: 锁龄 > 6h 判僵尸
        try:
            return (time.time() - d.stat().st_mtime) > 6 * 3600
        except OSError:
            return True
    expect = float(info.get("create_time", "0") or 0)
    return abs(ctime - expect) > 1.0  # PID 复用: 同人不同皮


def acquire_test_lock(argv: list[str]) -> None:
    """写重型: 抢占失败 rc=3 打印持锁者; 排查型放行。僵尸锁自愈回收。"""
    global _LOCK_HELD
    if not _is_write_heavy(argv):
        return
    d = _lock_dir()
    d.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(3):
        try:
            d.mkdir()
            break
        except FileExistsError:
            info = _read_lock(d)
            if not _lock_zombie(d, info):
                who = (f"pid={info.get('pid', '?')} 启动={info.get('started', '?')} "
                       f"repo={info.get('repo', '?')}")
                print(
                    f"[FATAL] 写重型测试锁被占: {d}\n持锁者 {who}\n"
                    f"等其结束或排查后手动删锁目录(若确认持锁者已死)。",
                    file=sys.stderr,
                )
                raise SystemExit(RC_TEST_LOCKED) from None
            shutil.rmtree(d, ignore_errors=True)  # 僵尸自愈
    else:
        raise SystemExit(f"[FATAL] 锁目录反复抢占失败: {d}")
    ctime = _proc_create_time(os.getpid()) or time.time()
    (d / "owner").write_text(
        f"pid={os.getpid()}\ncreate_time={ctime}\nrepo={_norm(_repo_root())}\n"
        f"started={time.strftime('%Y-%m-%d %H:%M:%S')}\n",
        encoding="utf-8",
    )
    _LOCK_HELD = d
    atexit.register(_release_test_lock)


def _release_test_lock() -> None:
    global _LOCK_HELD
    if _LOCK_HELD is None:
        return
    d, _LOCK_HELD = _LOCK_HELD, None
    shutil.rmtree(d, ignore_errors=True)


def pytest_session_finish_hook() -> None:
    """conftest 的 pytest_sessionfinish 转调这里(与 atexit 双挂)。"""
    _release_test_lock()


def retarget_cov_data_file(config) -> None:
    """把 coverage 数据文件重定向到实例根(计划 26-11-02-0657 「coverage 落实例根」)。

    为什么不只靠 COVERAGE_FILE env(2026-11-02 实测): pytest-cov 在
    pytest_load_initial_conftests(tryfirst=True) 里就构造并 start() 了 Coverage ——
    早于任何 conftest 导入, 此刻 env 尚未由 bootstrap 设置, data_file 绑死为
    CWD 的 .coverage(=仓库根); 且 start() 后 CoverageData 已把含后缀的完整文件名
    缓存进 _filename, 事后改 config.data_file / _basename 均无效(实测 A/B/C/D 探针)。
    唯一有效面是改写主 cov 的 _data._filename(保留原后缀); combining_cov 到 finish
    才懒绑定, 改它的 config.data_file 有效。xdist worker 的 cov 在 sessionstart 才
    start(), 晚于 worker 自己的 conftest 导入 —— env 对 worker 天然有效, 无需修。
    依赖 pytest-cov==7.1.0 + coverage 7.x 私有面(uv.lock 钉版; 升级时随回归用例暴露)。
    """
    if _INSTANCE_ROOT is None:
        return
    plugin = config.pluginmanager.get_plugin("_cov")
    ctl = getattr(plugin, "cov_controller", None)
    cov = getattr(ctl, "cov", None)
    if cov is None:
        return
    target = str(_INSTANCE_ROOT / "cov")
    data = getattr(cov, "_data", None)
    filename = getattr(data, "_filename", None)
    if filename:
        base = getattr(data, "_basename", "") or ""
        suffix = filename[len(base):] if base and filename.startswith(base) else ""
        data._filename = target + suffix
    else:
        cov.config.data_file = target
    combining = getattr(ctl, "combining_cov", None)
    if combining is not None:
        combining.config.data_file = target


def bootstrap(argv: list[str] | None = None) -> Path:
    """入口: conftest 模块级调用。返回实例根。"""
    root = _acquire_instance_root()
    acquire_test_lock(list(sys.argv[1:] if argv is None else argv))
    return root
