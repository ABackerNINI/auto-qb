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
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple

from filelock import FileLock, Timeout

from ..infra.utils import BACKUP_SUFFIX, atomic_write
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
        #: 读坏已告警过的文本: 坏文件是**持续状态**, 逐轮重报会变成通知轰炸
        self._read_error_warned = ""

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
        data, err, _recoverable = self._read_full()
        return data, err

    def _read_full(self) -> Tuple[HrSiteData, Optional[str], bool]:
        """读站点文件 → (数据, 错误原因, 是否属于「坏文件」)

        「坏文件」= 不可解析(空 / 非 JSON / 根节点与字段都不是预期形状)——它**可以从 `.bak` 兜底**;
        `schema_version` 不符**不算**: 那是版本迁移, 备份里也是同一个旧版本, 猜没有意义。
        """
        if not self.path.exists():
            return HrSiteData(), None, False
        try:
            text = self.path.read_text(encoding="utf-8")
        except OSError as e:
            return HrSiteData(), f"站点文件读取失败: {e}{self._file_hint()}", True
        return self._parse(text)

    def _parse(self, text: str) -> Tuple[HrSiteData, Optional[str], bool]:
        """解析站点文件文本 → (数据, 错误原因, 是否属于「坏文件」)"""
        try:
            raw: Dict[str, Any] = json.loads(text)
        except ValueError as e:
            return HrSiteData(), f"站点文件解析失败: {e}{self._file_hint(text)}", True
        if not isinstance(raw, dict):
            return HrSiteData(), f"站点文件根节点不是字典{self._file_hint(text)}", True
        version = raw.get("schema_version")
        if version != SCHEMA_VERSION:
            return HrSiteData(), f"站点文件 schema_version={version} 与期望 {SCHEMA_VERSION} 不符", False
        try:
            return HrSiteData.from_json(raw), None, False
        except (TypeError, ValueError, KeyError) as e:
            return HrSiteData(), f"站点文件字段解析失败: {e}{self._file_hint(text)}", True

    def _file_hint(self, text: str = "") -> str:
        """坏文件取证串: 大小 + 开头字节 —— 「空文件」与「被写坏的内容」一眼可分

        报错只说 `Expecting value: line 1 column 1 (char 0)` 时人看不出是**文件被清空了**还是
        内容坏了, 而这决定了下手方向(前者是外部工具/同步盘/写盘中断, 后者要看内容)。
        """
        try:
            size = self.path.stat().st_size
        except OSError:
            return ""
        if size == 0:
            return "(文件为空 0 字节: 可能被编辑器 / 同步盘清空, 或写盘被中断)"
        if not text:
            return f"(文件 {size} 字节)"
        return f"(文件 {size} 字节, 开头 {text[:40]!r})"

    def quarantine(self) -> str:
        """把坏文件挪到 `<site>.json.bad-<ts>`(**保留现场**, 而不是让它被下一次写盘覆盖掉)

        返回新路径; 挪不动(被其它程序占用等)返回空串 —— 那种情况下宁可继续跑, 但调用方须知悉,
        因为它决定后面写盘能不能安全地保留 `.bak`。
        """
        if not self.path.exists():
            return ""
        target = f"{self.path}.bad-{int(time.time())}"
        try:
            os.replace(str(self.path), target)
        except OSError as e:
            logger.debug(f"HR 站点 {self.site} | 坏文件挪走失败(继续运行): {e}")
            return ""
        return target

    def read_backup(self) -> Tuple[HrSiteData, Optional[str]]:
        """读 `<site>.json.bak`(每次写盘前的上一版) → (数据, 不可用原因); 不抛"""
        backup = Path(str(self.path) + BACKUP_SUFFIX)
        if not backup.exists():
            return HrSiteData(), "没有备份文件"
        try:
            text = backup.read_text(encoding="utf-8")
        except OSError as e:
            return HrSiteData(), f"备份读取失败: {e}"
        data, err, _recoverable = self._parse(text)
        return data, err

    def rebaseline_after_recovery(self, data: HrSiteData) -> None:
        """从备份恢复后重置写者心跳自检基线

        〘必需〙备份必然比本进程上次写的**旧**, 不重置的话下面「revision 回退」的锁自检会把这次
        恢复判成「共享目录上锁不生效」而退化为只读 —— 于是这个站点再也写不回去(自愈反而变砖)。
        只发生恢复时基线, 不取消自检本身: 没恢复过的路径照常拦 revision 回退。
        """
        self._last_write_rev = data.revision
        self._last_write_heartbeat = data.writer_heartbeat

    def _warn_read_error(self, detail: str) -> bool:
        """读坏只 WARNING 一次(同一文本), 返回是否真的报了 —— 坏文件是持续状态, 逐轮重报等于通知轰炸"""
        if self._read_error_warned == detail:
            logger.debug(f"HR 站点 {self.site} | {detail}(同一条已告警过, 不再重复)")
            return False
        self._read_error_warned = detail
        logger.warning(f"HR 站点 {self.site} | {detail}")
        return True

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

    def _write(self, data: HrSiteData, now: float, *, keep_backup: bool = True) -> None:
        """原子替换写入(含 revision 抬升与写者心跳); 默认把上一版留为 `.bak`

        `.bak` 是**读坏时的兜底**: 站点文件丢了索引 / 已取记录 / 放行记录, 等于要重新烧配额抓一遍
        (`hr_downloaded` 没了还会重下 .torrent), 所以默认保留。仅在「当前主文件本身是坏的」时
        才 `keep_backup=False` —— 否则会把唯一一份好备份盖成坏的(与 `state.json` 自愈同一个坑)。
        """
        data.revision += 1
        data.schema_version = SCHEMA_VERSION
        data.writer_instance = self.owner
        data.writer_heartbeat = now
        payload = json.dumps(data.to_json(), ensure_ascii=False, sort_keys=True)
        atomic_write(str(self.path), lambda f: f.write(payload), keep_backup=keep_backup)
        self._last_write_rev = data.revision
        self._last_write_heartbeat = now


class HrLockSession:
    """持锁期间的读-改-写会话(由 `HrSiteStore.hold()` 产出)

    站点文件读坏时**不直接把数据清空**: 先把坏文件挪到 `.bad-<ts>` 留证, 再试 `.bak` 兜底。
    顺序不能反 —— 若备份恰好也不可用, 下一步写盘会把坏文件覆盖掉, 现场就永远看不到了。
    """
    def __init__(self, store: HrSiteStore) -> None:
        self._store = store
        self.data, self.read_error, recoverable = store._read_full()
        #: 从 `.bak` 恢复过 ⇒ 本次写盘**不得**再复制 `.bak`(否则好备份被坏内容盖掉)
        self.recovered_from_backup = False
        #: 读坏是否由本会话报过 WARNING(供调用方决定还要不要另报一次)
        self.read_alerted = False
        if self.read_error:
            self.data = HrSiteData()
            if recoverable:
                self._recover(store)
            self.read_alerted = store._warn_read_error(self.read_error)
        self.writable = store._check_lock_effective(self.data)

    def _recover(self, store: HrSiteStore) -> None:
        """坏文件处置: 挪走留证 → 试备份 → 把结论写进 `read_error`(一条消息说清发生了什么)"""
        moved = store.quarantine()
        self.read_error += f"; 坏文件已挪走: {moved}" if moved else "; 坏文件未能挪走(它将被下次写盘覆盖)"
        data, backup_err = store.read_backup()
        if backup_err is None:
            self.data = data
            self.recovered_from_backup = True
            store.rebaseline_after_recovery(data)
            self.read_error += f"; 已从备份(.bak)恢复: 索引 {len(data.index)} 条 / 放行 {len(data.verified)} 条"
        else:
            self.read_error += f"; 备份不可用({backup_err}), 本轮按空数据处理(保守回落未核实)"

    @property
    def site(self) -> str:
        return self._store.site

    def commit(self, now: float) -> str:
        """写回(锁内); 返回 'written' / 'readonly'"""
        if not self.writable:
            return "readonly"
        self._store._write(self.data, now, keep_backup=not self.recovered_from_backup)
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
