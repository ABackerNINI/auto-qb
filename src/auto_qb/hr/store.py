"""站点数据文件存储: 一个站点一个 JSON 文件 + 一把锁(计划 §5)。

为什么账号级状态不进 state_file: 多客户端 / 多实例是常态, 而 HR 索引 / 放行 / 已取记录 /
配额账本 / 熔断**全部是账号级**的 —— 它们必须由实例们共享。共享靠「站点分文件 + 每站点一把锁」:

    <shared_dir>/hr/<site>.json   站点数据(读-改-写全在锁内)
    <shared_dir>/hr/<site>.lock   站点锁(filelock; 句柄随进程退出自动释放, 不留死锁)

硬约束(安全的关键): 取数线程**在持锁期间完成「读 → 判有效期 → 必要时抓 → 写 → 释放」全程**,
连分钟级的抓取也在锁内。这样即使代码有 bug, 也不可能出现两个实例同时读/写/抓同一站点;
拿不到锁的实例**直接等下一轮**(不排队、不重试轰炸)。

锁粒度 = **站点**: 抓站点 A 不阻塞站点 B(数据更新延迟随站点切分下降), 同站点严格互斥;
跨站点因此天然无覆盖问题。共享目录必须支持文件锁且各实例看到同一份文件 ——
本机 / 同一台 NAS 的 SMB 预期可用; **云同步盘(OneDrive / 坚果云)不可用**(原子替换与锁都不可靠)。
"""
import json
import logging
import os
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple

from filelock import FileLock, Timeout

from ..infra.utils import atomic_write
from .model import SCHEMA_VERSION, HrSiteData

logger = logging.getLogger(__name__)

HR_SUBDIR = "hr"


class HrLockBusy(RuntimeError):
    """锁被别的实例持有 —— 本轮直接跳过该站点(不排队、不重试)"""


class HrStoreCorrupted(RuntimeError):
    """站点文件存在但无法解析(schema 不符 / JSON 坏) —— 不入库, 保守回落未核实"""


def instance_id() -> str:
    """本进程的实例标识(心跳自检用); 每次启动生成, 不落盘"""
    return uuid.uuid4().hex[:12]


def hr_dir(data_dir: str, shared_dir: str = "") -> str:
    """HR 文件所在目录: shared_dir 非空时用它(多实例共享), 否则落 <data_dir>/hr/"""
    base = str(shared_dir).strip() if str(shared_dir).strip() else str(data_dir).rstrip("/\\")
    return os.path.join(base.rstrip("/\\"), HR_SUBDIR)


class HrSiteStore:
    """单个站点的文件 + 锁。所有磁盘访问都经 `hold()`(锁内), 无锁路径不提供写。"""
    def __init__(self, site: str, directory: str, *, lock_timeout: float = 0.0, owner: str = "") -> None:
        self.site = site
        self.dir = Path(directory)
        self.path = self.dir / f"{site}.json"
        self.lock_path = self.dir / f"{site}.lock"
        self.owner = owner or instance_id()
        self._lock = FileLock(str(self.lock_path), timeout=lock_timeout)
        # 写者心跳自检基线(仅本进程内存): revision 回退 / 心跳被覆盖 => 锁在该共享目录上不生效
        self._last_write_rev = 0
        self._last_write_heartbeat = 0.0
        self._unsafe_warned = False

    # ---------- 锁 ----------

    @contextmanager
    def hold(self) -> Iterator["HrLockSession"]:
        """抢锁并给出一份已读的会话; 拿不到锁抛 HrLockBusy(调用方等下一轮)。

        锁超时取构造参数(配置项 lock_timeout, 默认 0 = 不等)。
        """
        self.dir.mkdir(parents=True, exist_ok=True)
        try:
            self._lock.acquire()
        except Timeout as e:
            raise HrLockBusy(f"站点 {self.site} 的锁被其它实例持有({self.lock_path})") from e
        try:
            yield HrLockSession(self)
        finally:
            try:
                self._lock.release()
            except Exception:  # pragma: no cover - filelock 释放失败不影响正确性
                logger.debug(f"释放站点锁失败: {self.lock_path}", exc_info=True)

    # ---------- 读 / 写(仅在 hold 内调用) ----------

    def read_unlocked(self) -> Tuple[HrSiteData, Optional[str]]:
        """无锁只读快照(供视图构建 / 报告展示)。

        写入是「同目录临时文件 + os.replace」原子替换, 故无锁读到的必然是**完整的一份**
        (要么旧内容、要么新内容), 不会读到半截 —— 这是把只读交给无锁路径的前提。
        """
        return self._read()

    def _read(self) -> Tuple[HrSiteData, Optional[str]]:
        """读站点文件; 返回 (数据, 错误原因)。文件缺失 = 全新站点(不是错误); 坏文件 = 错误。"""
        if not self.path.exists():
            return HrSiteData(), None
        try:
            raw: Dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            return HrSiteData(), f"站点文件读取/解析失败: {e}"
        if not isinstance(raw, dict):
            return HrSiteData(), "站点文件根节点不是字典"
        version = raw.get("schema_version")
        if version != SCHEMA_VERSION:
            return HrSiteData(), f"站点文件 schema_version={version} 与期望 {SCHEMA_VERSION} 不符"
        try:
            return HrSiteData.from_json(raw), None
        except (TypeError, ValueError, KeyError) as e:
            return HrSiteData(), f"站点文件字段解析失败: {e}"

    def _check_lock_effective(self, data: HrSiteData) -> bool:
        """写者心跳自检: revision 回退 / 自己的心跳被覆盖 ⇒ 锁在该共享目录上不生效。

        判定为不安全时**退化为单实例只读**(宁可保守, 不可双写), 并只告警一次。
        """
        if data.revision < self._last_write_rev:
            self._warn_unsafe(f"revision 回退({data.revision} < 本实例上次写入的 {self._last_write_rev})")
            return False
        if data.writer_instance == self.owner and 0 < data.writer_heartbeat < self._last_write_heartbeat:
            self._warn_unsafe("本实例的心跳被覆盖")
            return False
        return True

    def _warn_unsafe(self, why: str) -> None:
        if self._unsafe_warned:
            return
        self._unsafe_warned = True
        logger.warning(f"HR 站点 {self.site} | 文件锁疑似在该目录不生效({why}), 已退化为只读以免双写; "
                       f"共享目录需支持文件锁且各实例看到同一份文件(云同步盘不可用)")

    def _write(self, data: HrSiteData, now: float) -> None:
        """原子替换写入(含 revision 抬升与写者心跳)"""
        data.revision += 1
        data.schema_version = SCHEMA_VERSION
        data.writer_instance = self.owner
        data.writer_heartbeat = now
        payload = json.dumps(data.to_json(), ensure_ascii=False, sort_keys=True)
        atomic_write(str(self.path), lambda f: f.write(payload))
        self._last_write_rev = data.revision
        self._last_write_heartbeat = now


class HrLockSession:
    """持锁期间的读-改-写会话(由 HrSiteStore.hold() 产出)"""
    def __init__(self, store: HrSiteStore) -> None:
        self._store = store
        self.data, self.read_error = store._read()
        if self.read_error:
            logger.warning(f"HR 站点 {store.site} | {self.read_error}; 本轮按空数据处理(保守回落未核实)")
            self.data = HrSiteData()
        self.writable = store._check_lock_effective(self.data)

    @property
    def site(self) -> str:
        return self._store.site

    def commit(self, now: float) -> str:
        """写回(锁内); 返回 'written' / 'readonly'"""
        if not self.writable:
            return "readonly"
        self._store._write(self.data, now)
        return "written"


__all__ = [
    "HR_SUBDIR",
    "HrLockBusy",
    "HrLockSession",
    "HrSiteStore",
    "HrStoreCorrupted",
    "hr_dir",
    "instance_id",
]
