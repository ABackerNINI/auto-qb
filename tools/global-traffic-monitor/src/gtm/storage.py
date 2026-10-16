"""落盘: TM 兼容 history_traffic.dat + state.json 原子写 + 单实例锁 (S2 实现).

单写线程 (与采样同一线程, 黄金法则 5) 内写 TM 兼容文件: 首行总行数 N, 每行
"YYYY/MM/DD 上传KB/下载KB" (整数 KB, 与 auto-qb curves.py 解析一致; 行格式单点为
sampler.DAT_ROW_RE, 读写两侧共用防漂移)。写 = 临时文件 -> fsync -> os.replace
原子替换, 任意时刻读者 (任意数量进程) 见到完整一致的文件 —— 通知推送与落盘解耦,
推送失败不影响落盘, 订阅者丢失通知可靠慢轮询兜底。

落盘节流: 日累计变化 >= 1 MiB 或距上次落盘 >= 30s (对齐 TM 落盘节拍), 内存活尾
随时可服务 (render 当前值)。state.json (上次快照/当日累计; S3/S4 将扩展事件号/
租约表, 顶层键向后兼容) **每次采样必写** (原子写), 保证 kill -9 后丢失窗口
<= 采样间隔; dat 可按节流懒写, 恢复时 state 权威、dat 仅兜底。

filelock 保证工具单实例, 二次启动 fail-fast 报错 (含持有者信息)。

模块边界: 唯一运行时 import 为 sampler 的 dat 行格式单点 DAT_ROW_RE (读侧
restore_from_dat 与本模块写侧共用防漂移; 依赖方向 storage -> sampler, 不反向)。
recover(duck-typed sampler) 驱动 sampler.restore/restore_from_dat 完成崩溃恢复。
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import time
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Mapping, Optional

from filelock import FileLock, Timeout

from gtm.sampler import DAT_ROW_RE

if TYPE_CHECKING:
    from gtm.sampler import SampleResult, Sampler

logger = logging.getLogger("gtm.storage")

# dat 数值单位: KB, 按 1024 字节换算 (与 curves.py 的 KB 常量同值; 写入向下取整,
# 宁可少报不可虚增, 读侧 curves.py 按 KB*1024 还原, 误差 <= 1KB/行)
KB = 1024
MIB = 1024 * 1024

# 落盘节流默认 (计划 §05): 日累计变化 >= 1MiB 或距上次落盘 >= 30s
DEFAULT_FLUSH_DELTA_BYTES = 1 * MIB
DEFAULT_FLUSH_INTERVAL_S = 30.0

# dat 首行 (TM 兼容): lines: "N" —— N 为数据行数 (curves.py 忽略该行仅作提示)
DAT_HEADER = 'lines: "{n}"'


def default_data_dir() -> str:
    """工具数据目录默认值 (dat/state/lock/config 落点): 环境变量 GTM_DATA_DIR 优先,
    否则按平台惯例 —— Windows %LOCALAPPDATA%/gtm, macOS ~/Library/Application
    Support/gtm, Linux ~/.local/share/gtm (XDG_DATA_HOME 优先)。"""
    env = os.environ.get("GTM_DATA_DIR")
    if env:
        return env
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "gtm")
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "gtm")
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "gtm")


# Windows os.replace 遇读者持句柄 (WinError 5) 的退避重试参数: 读者开-读-关只
# 持句柄微秒~毫秒级, 5 次 x 50ms 覆盖常见读窗口; 耗尽后抛错由调用方容错
_REPLACE_RETRY_ATTEMPTS = 5
_REPLACE_RETRY_DELAY_S = 0.05


def _replace_retry(tmp_path: str, path: str) -> None:
    """os.replace 的退避重试单点 (仅 PermissionError; 其它 OSError 原样抛出)."""
    last: Optional[OSError] = None
    for attempt in range(_REPLACE_RETRY_ATTEMPTS):
        try:
            os.replace(tmp_path, path)
            return
        except PermissionError as e:
            last = e
            if attempt < _REPLACE_RETRY_ATTEMPTS - 1:
                time.sleep(_REPLACE_RETRY_DELAY_S)
    assert last is not None
    raise last


def atomic_write_text(path: str, text: str) -> None:
    """原子写盘: 同目录临时文件 -> flush -> fsync -> os.replace (失败退避重试).

    与 auto-qb infra/utils.atomic_write 同纪律 (工具独立, 不 import auto-qb,
    本函数为工具内原子写单点): 目标路径要么完全是旧内容, 要么完全是新内容 ——
    直接 open(path, "w") 会先 truncate 旧文件, 写盘途中被杀/磁盘满/序列化抛异常
    都会留下半截文件, 而读者 (auto-qb 多实例/curves.py) 任何时刻打开都必须见到
    完整文件。临时文件与失败清理由本函数负责; os.replace 成功时临时文件已不存在,
    不再删除。

    ⚠ Windows 附加竞态 (坑档 platform-fs): os.replace 的目标文件若被读者持句柄
    (Python open() 不含 FILE_SHARE_DELETE), MoveFileEx 抛 PermissionError
    (WinError 5) —— 读者只短暂持句柄 (开-读-关), 退避重试即可; 持久冲突
    (读家长持/磁盘满) 重试耗尽后抛错, 由调用方容错 (下一节流轮重试)。POSIX 上
    replace 不受读者影响, 不会触发重试。

    空路径直接报错 (不静默兜底): abspath("") 是 CWD, 会把临时文件丢到别处。
    """
    if not path:
        raise ValueError("atomic_write_text: path 不能为空")
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=os.path.basename(path) + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        _replace_retry(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):  # os.replace 已成功时临时文件不存在, 不该再删
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise


class DatStore:
    """history_traffic.dat 的内存镜像 + 原子落盘 (单写线程内使用; 读者只见磁盘文件).

    TM 兼容格式: 首行 lines: "N", 其后每行 "YYYY/MM/DD 上传KB/下载KB", 新日在
    前 (TM 倒序口径; curves.py 与 sampler.restore_from_dat 均行序不敏感)。加载
    时坏行跳过并告警 (与 curves.py 容错口径一致: 坏行不影响其它日)。
    """
    def __init__(self, path: str) -> None:
        self.path = path
        self._rows: dict[date, tuple[int, int]] = {}
        self._loaded = False

    @property
    def loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        """读现有 dat 进内存镜像 (文件缺失/为空 -> 空镜像; 幂等, 重复调用重读)."""
        self._rows = {}
        try:
            text = Path(self.path).read_text(encoding="utf-8")
        except FileNotFoundError:
            self._loaded = True
            return
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.lower().startswith("lines:"):
                continue
            m = DAT_ROW_RE.match(line)
            if not m:
                logger.warning("dat 坏行跳过: %r", line)
                continue
            y, mo, d, up_kb, down_kb = m.groups()
            try:
                day = date(int(y), int(mo), int(d))
            except ValueError:
                logger.warning("dat 非法日期行跳过: %r", line)
                continue
            self._rows[day] = (int(up_kb) * KB, int(down_kb) * KB)
        self._loaded = True

    def upsert(self, day: date, up_bytes: int, down_bytes: int) -> None:
        """当日行原地更新 (当日累计随流量增长覆盖写; 其它日不动)."""
        self._rows[day] = (up_bytes, down_bytes)

    def render(self) -> str:
        """序列化当前镜像 -> TM 兼容文本 (新日在前; 内存活尾随时可服务)."""
        lines = [DAT_HEADER.format(n=len(self._rows))]
        for day in sorted(self._rows, reverse=True):
            up, down = self._rows[day]
            lines.append(f"{day:%Y/%m/%d} {up // KB}/{down // KB}")
        return "\n".join(lines) + "\n"

    def flush(self) -> None:
        """原子落盘当前镜像 (调用方保证已 load)."""
        atomic_write_text(self.path, self.render())


class StateStore:
    """state.json: 采样快照载荷的原子读写 (S3/S4 将扩展事件号/租约表, 顶层键向后兼容).

    read() 仅在文件缺失/JSON 解析失败/顶层非对象时返回 None (由调用方走降级恢复);
    字段级校验归 sampler.restore (版本不符/字段非法 -> 告警降级)。
    """
    def __init__(self, path: str) -> None:
        self.path = path

    def read(self) -> Optional[dict]:
        try:
            text = Path(self.path).read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("state.json 损坏: JSON 解析失败, 走降级恢复")
            return None
        if not isinstance(payload, dict):
            logger.warning("state.json 损坏: 顶层不是对象 (type=%s), 走降级恢复", type(payload).__name__)
            return None
        return payload

    def write(self, payload: Mapping[str, object]) -> None:
        """原子写快照载荷 (每次采样调用, 丢失窗口 <= 采样间隔)."""
        atomic_write_text(self.path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


class FlushPolicy:
    """dat 落盘节流 (计划 §05): 日累计变化 >= delta_bytes 或距上次落盘 >= interval_s.

    首帧必落盘 (last_at=None -> due): 把恢复值/初始值立即持久化, 之后才有节拍。
    clock 为单调时钟 (默认 time.monotonic; 测试注入替身)。
    """
    def __init__(
        self,
        *,
        delta_bytes: int = DEFAULT_FLUSH_DELTA_BYTES,
        interval_s: float = DEFAULT_FLUSH_INTERVAL_S,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self.delta_bytes = delta_bytes
        self.interval_s = interval_s
        self._clock = clock or time.monotonic
        self._last_total: Optional[int] = None
        self._last_at: Optional[float] = None

    def due(self, day_total: int, now: Optional[float] = None) -> bool:
        now = self._clock() if now is None else now
        if self._last_at is None:
            return True  # 首帧: 立即落盘 (恢复值/初始值即时持久化)
        if day_total - (self._last_total or 0) >= self.delta_bytes:
            return True
        return now - self._last_at >= self.interval_s

    def mark_flushed(self, day_total: int, now: Optional[float] = None) -> None:
        now = self._clock() if now is None else now
        self._last_total = day_total
        self._last_at = now

    def reset(self, day_total: int, now: Optional[float] = None) -> None:
        """跨天: 新日节流基线重置 (旧日已封存落盘, 不再参与新日阈值累计)."""
        now = self._clock() if now is None else now
        self._last_total = day_total
        self._last_at = now


class SingleInstanceLockError(RuntimeError):
    """工具单实例锁竞争 (fail-fast; 二次启动即报错, 不静默排队)."""


class SingleInstanceLock:
    """filelock 单实例锁 + 伴生 meta (持有者 PID/启动时间, 报错时告知).

    与 auto-qb infra/locking.SingleInstanceLock 同族同纪律 (工具独立, 此处为工具内
    单点): 非阻塞获取 (timeout=0), 失败抛 SingleInstanceLockError; release 幂等;
    锁文件残留按平台 (Windows 删/POSIX flock 残留, 平台语义非 bug), 伴生 meta
    无条件删除。
    """
    def __init__(self, lock_path: str) -> None:
        self.lock_path = lock_path
        self.meta_path = lock_path + ".meta.json"
        self._lock = FileLock(str(lock_path), timeout=0.0)
        self._held = False

    def acquire(self) -> None:
        holder = self._read_meta()
        try:
            self._lock.acquire()
        except Timeout as e:
            detail = f" (PID {holder.get('pid')}, 启动于 {holder.get('started_at')})" if holder else ""
            raise SingleInstanceLockError(f"另一 gtm 实例已持有锁 {self.lock_path}{detail}; 工具仅允许单实例") from e
        self._held = True
        self._write_meta()

    def release(self) -> None:
        if self._held:
            self._lock.release()
            self._held = False
        try:
            os.remove(self.meta_path)
        except FileNotFoundError:
            pass
        except OSError:
            pass

    def __enter__(self) -> "SingleInstanceLock":
        self.acquire()
        return self

    def __exit__(self, *args: object) -> None:
        self.release()

    def _write_meta(self) -> None:
        meta = {"pid": os.getpid(), "started_at": datetime.now().astimezone().isoformat(timespec="seconds")}
        try:
            atomic_write_text(self.meta_path, json.dumps(meta, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.debug("锁伴生 meta 写入失败 (锁是主防线, meta 仅辅助报错): %s", e)

    def _read_meta(self) -> dict:
        try:
            with open(self.meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}


class Storage:
    """落盘编排 (单写线程内使用, 非线程安全 —— 并发读者只见磁盘文件):

    - acquire_lock/release_lock: 单实例 (fail-fast), data_dir 自动创建
    - load/recover: 启动恢复 —— state.json 权威 (sampler.restore), 缺失/损坏
     降级时当日累计从 dat 末行兜底 (sampler.restore_from_dat, 计数器基线取当前值)
    - record(result, snapshot): 单次采样后落盘编排 —— 跨天封存旧日最终值 ->
      upsert 当日 -> dat 按节流 -> state 每次必写
    - flush/close: 强制落盘 dat (优雅退出最终落盘)
    """
    def __init__(
        self,
        data_dir: str,
        *,
        dat_name: str = "history_traffic.dat",
        state_name: str = "state.json",
        lock_name: str = "gtm.lock",
        flush_delta_bytes: int = DEFAULT_FLUSH_DELTA_BYTES,
        flush_interval_s: float = DEFAULT_FLUSH_INTERVAL_S,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self.data_dir = data_dir
        self.dat_path = os.path.join(data_dir, dat_name)
        self.state_path = os.path.join(data_dir, state_name)
        self.lock_path = os.path.join(data_dir, lock_name)
        self._dat = DatStore(self.dat_path)
        self._state = StateStore(self.state_path)
        self._lock = SingleInstanceLock(self.lock_path)
        self._policy = FlushPolicy(delta_bytes=flush_delta_bytes, interval_s=flush_interval_s, clock=clock)
        self._current_total = 0

    # ---- 单实例锁 ----

    def acquire_lock(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        self._lock.acquire()

    def release_lock(self) -> None:
        self._lock.release()

    def __enter__(self) -> "Storage":
        self.acquire_lock()
        return self

    def __exit__(self, *args: object) -> None:
        self.release_lock()

    # ---- 启动恢复 ----

    def _ensure_loaded(self) -> None:
        if not self._dat.loaded:
            self._dat.load()

    def load(self) -> None:
        """显式加载现有 dat (acquire 后、recover/record 前; 重复调用安全)."""
        self._dat.load()

    def recover(self, sampler: "Sampler") -> tuple[str, ...]:
        """崩溃恢复: state.json -> sampler.restore; 缺失/损坏/降级 -> dat 兜底.

        返回恢复告警 (调用方负责日志可见; sampler.restore 的语义见 S1)。
        有效载荷 (今天接续/昨天清零基线续) 不触发兜底 —— state 权威, dat 仅兜底。
        """
        self._ensure_loaded()
        state = self._state.read()
        warnings = list(sampler.restore(state))
        if state is None or not sampler.has_baseline:
            # 降级路径 (计划 S1 口径: state 缺失/损坏 -> 当日累计从 dat 末行恢复,
            # 计数器基线仍取当前值, 停机窗口丢流量)
            sampler.restore_from_dat(self._dat.render())
        return tuple(warnings)

    # ---- 采样后落盘编排 ----

    def record(self, result: "SampleResult", snapshot: Mapping[str, object]) -> None:
        """单次采样后落盘编排 (单写线程):
        跨天封存旧日最终值 -> upsert 当日 -> dat 按节流 -> state 每次必写。
        """
        self._ensure_loaded()
        if result.day_rolled:
            # 旧日最终值先封存 (dat 中旧日行 = 上次 upsert 的值; 新日从 0 起不覆盖旧行)
            self.flush()
            self._policy.reset(result.day_total_bytes)
        self._dat.upsert(result.day, result.day_up_bytes, result.day_down_bytes)
        self._current_total = result.day_total_bytes
        if self._policy.due(result.day_total_bytes):
            self.flush()
        # state 每次采样必写: kill -9 后丢失窗口 <= 采样间隔 (黄金法则 3)
        self._state.write(snapshot)

    def flush(self) -> None:
        """强制落盘 dat 当前镜像并标记节流基线."""
        self._ensure_loaded()
        self._dat.flush()
        self._policy.mark_flushed(self._current_total)

    def dat_text(self) -> str:
        """当前 dat 镜像文本 (内存活尾随时可服务; 磁盘文件可能尚未落盘)."""
        self._ensure_loaded()
        return self._dat.render()

    def close(self) -> None:
        """优雅退出: 最终落盘 (dat 封口; state 已随每次采样落盘)."""
        self.flush()
