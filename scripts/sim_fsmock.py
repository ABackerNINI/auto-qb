"""进程内 FS mock —— 让 auto-qb 在**不物化任何文件**的前提下, 看到"真机录制下来的磁盘状态"。

语料计划 26-09-21-0024 §07 的定案: 磁盘事实来源默认走 mock(不是稀疏文件物化真树)。
auto-qb 碰磁盘的入口收敛在 4 个调用点, 全部经 `os.path.*` / `shutil.disk_usage`:

    mixins/grouping.py:239 · :244   缺文件扫描(头号, D4)      os.path.exists + os.path.getsize
    mixins/checking.py:26 · :29     跳检前完整性检查           os.path.exists + os.path.getsize
    rules/expr/env.py:228           表达式取值 exists(path)   os.path.exists
    rules/expr/env.py:219           表达式取值 disk_used(path) shutil.disk_usage

三条硬条件(不满足就会出错):
  ① **按路径前缀限定作用域** —— 默认放行, 只有命中语料树(<fs-root> 之下)才拦。否则会把
     auto-qb 自己的文件也 mock 掉: `config/writer.py`(config.yml, 红线) / `utils.py`(state 文件 / 原子写 /
     备份) / `notify.py` / `web.py`(WEB 密钥 / 静态目录) / `qbclient.py`(~/.netrc)。
  ② **大小写不敏感 + 剥 `\\\\?\\` 前缀** —— 传进来的路径是 `add_long_path_prefix_for_win(...)` 的产物
     (`\\\\?\\D:\\…` 形态), 而 NTFS 不区分大小写。若按原样精确匹配, 会把存在的文件报成缺失 ⇒ D4 判据全假。
  ③ **时间源归播放器** —— 磁盘状态随时间变(录制期的 fs_delta), 而 mock 在 auto-qb 进程里不知道回放游标
     走到哪。故 mock 向播放器查"当前磁盘状态"(`GET /_fsmock/state`, 按 t_seq 缓存约 1 次/秒),
     保持"播放器是唯一时间源"这条原则。

⚠ 白盒代价: 本模块依赖"auto-qb 内部用 os.path.exists"这个实现细节。哪天有人把它改成
  `pathlib.Path.exists()` 或 `os.stat`, mock 会**静默失效、判据变假绿** —— 最坏的一种失败。
  故必须配静态守阵 `CORPUS.fs_mock_coverage`(FS 调用点 ⊆ 本模块覆盖集)+ 红绿双验, 见 §09。

用法(必须在 `from auto_qb.cli import main` **之前**调用):
    from sim_fsmock import install
    install(root=args.fs_root, player_url=args.player_url)
    from auto_qb.cli import main
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
import urllib.request
from typing import Any, Callable, Optional

__all__ = ["FsMock", "install", "MockCoverage"]

# 本模块覆盖的 FS 调用点(静态守阵 CORPUS.fs_mock_coverage 的期望值)
MockCoverage = {
    "os.path.exists":
        "src/auto_qb/mixins/grouping.py:239, src/auto_qb/mixins/checking.py:26, src/auto_qb/rules/expr/env.py:228",
    "os.path.getsize":
        "src/auto_qb/mixins/grouping.py:244, src/auto_qb/mixins/checking.py:29",
    "shutil.disk_usage":
        "src/auto_qb/rules/expr/env.py:219",
}


def _key(p: str) -> str:
    """路径归一成查表用的 key: 剥 `\\\\?\\` 前缀 + 反斜杠转正斜杠 + normcase

    不做 realpath/abspath —— mock 表是按语料里的 save_path 拼出来的, 走 realpath 会因
    本机不存在该盘符而产出意外结果(而且这里要的正是"按字符串查表", 不是"问操作系统")。
    """
    if not p:
        return p
    s = str(p)
    if s.startswith("\\\\?\\"):
        s = s[4:]
    elif s.startswith("\\\\?\\UNC\\"):
        s = "\\\\" + s[8:]
    return os.path.normcase(s.replace("/", "\\"))


class FsMock:
    """磁盘状态表 + 三个被拦函数。表 = {normcase 全路径: {"exists": bool, "size": int|None}}。"""
    def __init__(self, root: str, table: dict[str, dict], free_space: int = 0, total_space: int = 0):
        self.root_key = _key(root).rstrip("\\") + "\\"
        self.table = {_key(k): v for k, v in table.items()}
        self.free_space = int(free_space or 0)
        self.total_space = int(total_space or 0)
        self.hits = {"exists": 0, "getsize": 0, "disk_usage": 0}
        self.misses = 0  # 命中语料树但表里没有 -> 记下来, 说明探测不完整
        self.delegated = 0  # 不命中语料树 -> 原样委托真函数
        self._lock = threading.Lock()

    # ---- 判定 ----
    def in_scope(self, path: str) -> bool:
        return _key(path).startswith(self.root_key)

    def lookup(self, path: str) -> Optional[dict]:
        return self.table.get(_key(path))

    # ---- 被拦的三个函数 ----
    def exists(self, path, _orig=None) -> bool:
        with self._lock:
            self.hits["exists"] += 1
        if not self.in_scope(path):
            self.delegated += 1
            return (_orig or _real_exists)(path)
        rec = self.lookup(path)
        if rec is None:
            self.misses += 1
            # 语料树内但表里没有: 按"不存在"回 —— 与真机"没探测到的文件就是不在"一致,
            # 但计数暴露出来, 免得把"探测不完整"伪装成"文件确实缺失"。
            return False
        return bool(rec.get("exists"))

    def getsize(self, path, _orig=None) -> int:
        with self._lock:
            self.hits["getsize"] += 1
        if not self.in_scope(path):
            self.delegated += 1
            return (_orig or _real_getsize)(path)
        rec = self.lookup(path)
        if rec is None or not rec.get("exists"):
            raise FileNotFoundError(2, "No such file or directory", str(path))
        size = rec.get("size")
        if size is None:
            raise OSError(22, "Invalid argument", str(path))
        return int(size)

    def disk_usage(self, path, _orig=None):
        with self._lock:
            self.hits["disk_usage"] += 1
        if not self.in_scope(path):
            self.delegated += 1
            return (_orig or _real_disk_usage)(path)
        total = self.total_space or max(self.free_space, 1)
        used = max(total - self.free_space, 0)
        return shutil._ntuple_diskusage(total, used, self.free_space)

    def stats(self) -> dict:
        return {
            "hits": dict(self.hits),
            "misses": self.misses,
            "delegated": self.delegated,
            "table_size": len(self.table),
            "root": self.root_key
        }


_real_exists = os.path.exists
_real_getsize = os.path.getsize
_real_disk_usage = shutil.disk_usage


# ==========================================================================================
# 播放器侧状态拉取(时间源归播放器)
# ==========================================================================================
class _PlayerPoller:
    """按 ~1 次/秒向播放器查"当前磁盘状态", 保持"播放器是唯一时间源"。

    静态回放时表不变, 拉到的与初值相同; 时间轴回放时按 t_seq 施加 fs_delta ⇒ 真机重演。
    拉取失败**不阻断**: 保留上一次成功的表(录制期磁盘状态变化是增量信息, 不是可用性前提)。
    """
    def __init__(self, mock: FsMock, url: str, interval: float = 1.0):
        self.mock = mock
        self.url = url
        self.interval = interval
        self._stop = threading.Event()
        self._errs = 0

    def start(self) -> None:
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                with urllib.request.urlopen(self.url, timeout=3) as r:
                    payload = json.loads(r.read().decode("utf-8"))
                table = payload.get("files") or {}
                with self.mock._lock:
                    self.mock.table = {_key(k): v for k, v in table.items()}
                    self.mock.free_space = int(payload.get("free_space", self.mock.free_space) or 0)
            except Exception:  # noqa: BLE001
                self._errs += 1
            self._stop.wait(self.interval)


# ==========================================================================================
# 安装
# ==========================================================================================
_INSTALLED: Optional[FsMock] = None


def install(
    root: str,
    table: Optional[dict] = None,
    state_file: str = "",
    player_url: str = "",
    free_space: int = 0,
    total_space: int = 0
) -> FsMock:
    """把 mock 装到 os.path.exists / os.path.getsize / shutil.disk_usage 上。

    必须在 `from auto_qb.cli import main` **之前**调用 —— auto-qb 内部是 `import os` 后按属性访问
    (`os.path.exists(...)`), 所以替换模块属性即可生效, **不需要改 src/ 一行**。

    root:       语料 FS 根(`<fs-root>`); 只有它之下的路径才拦
    table:      直接给的磁盘状态表(与 state_file 二选一)
    state_file: 从播放器导出的表(JSON)
    player_url: 可选; 给了就按秒拉取, 让磁盘状态随时间变
    """
    global _INSTALLED
    if table is None:
        table = {}
        if state_file and os.path.exists(state_file):
            with open(state_file, encoding="utf-8") as f:
                payload = json.load(f)
            table = payload.get("files") or {}
            free_space = free_space or int(payload.get("free_space") or 0)
            total_space = total_space or int(payload.get("total_space") or 0)

    mock = FsMock(root, table, free_space=free_space, total_space=total_space)
    if player_url:
        _PlayerPoller(mock, player_url).start()

    _orig_exists, _orig_getsize, _orig_du = os.path.exists, os.path.getsize, shutil.disk_usage
    os.path.exists = lambda p: mock.exists(p, _orig_exists)  # type: ignore[assignment]
    os.path.getsize = lambda p: mock.getsize(p, _orig_getsize)  # type: ignore[assignment]
    shutil.disk_usage = lambda p: mock.disk_usage(p, _orig_du)  # type: ignore[assignment]
    _INSTALLED = mock
    return mock


def current() -> Optional[FsMock]:
    return _INSTALLED
