"""路径链逐跳探测(计划 26-11-04-1042 P2-1/P2-2): A -> B -> C 的事实链

只回答「这一跳是什么、指向哪里、探测到哪一步」, 不做迁移决策:
- 起点由服务端从种子记录派生(root_path / content_path 优先, 回退 save_path),
  客户端只传 hash, 不传路径;
- 允许根沿 fs.py 的白名单口径(全部种子 save_path), 范围外只展示不展开;
- 环检测 + 8 跳上限; 权限不足 / 不存在 / 类型未知各自可表达, 判不了返回 unknown。

**缓存**: 结果短缓存(~20s), 只由浮窗打开或显式 refresh 触发; 列表渲染期不调用本模块
(§P2-5 的「渲染期零探测」由调用方保证, 本模块本身不挂任何渲染钩子)。
"""
import copy
import os
import threading
from collections import OrderedDict
from typing import Mapping, Optional, Sequence, Tuple

from ..infra import alias_fs
from ..infra.clock import SYSTEM_CLOCK, Clock
from ..infra.utils_paths import path_normalize

#: 单条链最多跟随的链接跳数(超过即「链路过长」, 不再展开)
MAX_HOPS = 8

#: 结果 TTL(秒); 显式 refresh=1 绕过
CHAIN_CACHE_TTL = 20.0

#: 缓存容量(条目数; 超出按最久未用淘汰)
CHAIN_CACHE_CAPACITY = 128

#: 探测环境: 本地可逐跳探测; 另外两种只返回「未确认」
ENV_LOCAL = "local"
ENV_MAPPED = "mapped"
ENV_REMOTE = "remote"


def _compare_key(path: str) -> str:
    """归一成比较键: 剥设备前缀 + normpath + Windows 大小写折叠"""
    bare = alias_fs.strip_device_prefix(path or "")
    return os.path.normcase(os.path.normpath(bare)) if bare else ""


def path_within_roots(path: str, roots: Sequence[str]) -> bool:
    """逻辑路径是否落在任一允许根内(词法比较, 不解析链接本身)

    这里刻意不用 `file_access.realpath_lexical`: 它会把**当前这一跳**的链接解析到目标,
    导致「根内的链接 -> 根外目标」连链接节点本身都被判范围外。词法 normpath 已能消掉
    `..`, 足以拦住目标穿越; 目标是否在根内由调用方在跟随前判断。
    """
    key = _compare_key(path)
    if not key:
        return False
    for root in roots or ():
        root_key = _compare_key(root)
        if not root_key:
            continue
        prefix = root_key if root_key.endswith(os.sep) else root_key + os.sep
        if key == root_key or key.startswith(prefix):
            return True
    return False


def build_alias_index(snapshot: Optional[Mapping], torrent_hash: str) -> dict:
    """该 hash 的 job alias_paths -> job 索引(同路径多 job 时优先活跃 job)

    只用快照(零 syscall、零主循环访问); alias_paths 是建链接时登记的原值,
    与探测出的路径做同一套词法归一后精确比对。
    """
    if snapshot is None:
        return {}
    jobs = tuple(getattr(snapshot, "jobs", ()) or ())
    candidates = [job for job in jobs if torrent_hash in (job.get("hashes") or ()) and job.get("alias_paths")]
    if not candidates:
        return {}
    from ..core.modules.relocate_units import job_rank  # 局部导入: 只此一处消费选取序

    candidates.sort(key=job_rank, reverse=True)
    index = {}
    for job in candidates:
        for alias in job.get("alias_paths") or ():
            key = _compare_key(alias)
            if key and key not in index:
                index[key] = job
    return index


def pick_job_for(snapshot: Optional[Mapping], torrent_hash: str) -> Optional[Mapping]:
    """该 hash 的**当前** job 视图(收尾反馈面/按钮判据的取数单点)

    与 build_alias_index 同一套选取序(job_rank: 非终态优先, 再 updated_at 新→旧),
    但不限别名命中 —— 收尾窗口相位(armed/rewritten)下别名状态各异,
    job 登记仍在, 反馈面照常要能取到。无快照/无命中 ⇒ None。
    """
    if snapshot is None:
        return None
    jobs = [j for j in (getattr(snapshot, "jobs", ()) or ()) if torrent_hash in (j.get("hashes") or ())]
    if not jobs:
        return None
    from ..core.modules.relocate_units import TERMINAL_PHASES, job_rank  # 局部导入: 选取序单点

    jobs.sort(key=job_rank, reverse=True)
    for job in jobs:
        if str(job.get("phase") or "") not in TERMINAL_PHASES:
            return job
    return jobs[0]


def finalize_face(job: Mapping, data_dir: str, host: str, port: int, *, now: Optional[float] = None) -> dict:
    """收尾反馈面全量口径(计划 26-11-05-0808 §3.2「失败反馈面」行 / S4b 扩面)+ D14 按钮判据

    输入 job = pick_job_for 的快照视图; 字段:
    - window: 相位在 FINALIZE_WINDOW_PHASES(「立即收尾」按钮可见判据单点 —— S4 相位
      模型重定义后为 {armed, rewritten}, 随该单点自动跟随);
    - pending: journal 待改写成员数(rj.pending_members 现读 spec+journal.rewrites);
    - daemon_stale: 回收 daemon 死/心跳过期(rj.daemon_stale 判据单点);
    - verify_failed / chain_deps / note(S4b 全量口径): job 账上 reason 码分流 ——
      核验未过(verify_failed)/删链门依赖未清(chain_deps)时 note 带解法文案,
      前端照显不重判。三者只在 window 内有意义(前段相位零悬挂)。
    只对新链 spec(spec 带 bt_backup 字段)取证: 无 bt_backup 的 job 不走 fastresume 改写
    (S1 五闸应已拦下), pending 恒 0 防误导。journal 已终态 ⇒ pending 恒 0
    (已收口/已取消, 反馈面不再悬)。本函数只读 spec/journal 文件(原子写读侧安全),
    零主循环访问、零 state.json 触碰(D13 账本契约的读侧对称)。
    """
    from ..core.modules import relocate_units as ru  # 局部导入(与 build_alias_index 同款)
    from ..infra import relocate_journal as rj

    phase = str(job.get("phase") or "")
    job_id = str(job.get("job_id") or "")
    reason = str(job.get("reason") or "")
    face = {
        "job_id": job_id,
        "phase": phase,
        "window": phase in ru.FINALIZE_WINDOW_PHASES,
        "pending": 0,
        "daemon_stale": False,
        "verify_failed": reason == ru.REASON_VERIFY_FAILED,
        "chain_deps": reason == ru.REASON_CHAIN_DEPS,
        "note": str(job.get("last_error") or "") if reason in (ru.REASON_VERIFY_FAILED, ru.REASON_CHAIN_DEPS) else "",
    }
    spec = rj.read_spec(data_dir, job_id) if job_id else None
    if not isinstance(spec, dict) or not str(spec.get("bt_backup") or "").strip():
        return face
    journal = rj.read_journal(data_dir, job_id) or {}
    if str(journal.get("phase") or "") in rj.STOP_PHASES:
        return face
    rewrites = journal.get("rewrites") if isinstance(journal.get("rewrites"), dict) else {}
    face["pending"] = len(rj.pending_members(spec, rewrites))
    key = rj.instance_key(host, port)
    face["daemon_stale"] = rj.daemon_stale(data_dir, key, max_age=ru.DAEMON_HEARTBEAT_MAX_AGE, now=now)
    return face


def _attribution(job: Optional[Mapping], node_status: str, torrent_hash: str) -> dict:
    """一跳的归属章: 命中 job 登记 -> auto-qb 设置(带来源/相位/收尾信息); 否则非 auto-qb 设置"""
    if not job:
        return {"auto": False}
    return {
        "auto": True,
        "job_id": str(job.get("job_id") or ""),
        "origin": str(job.get("origin") or ""),
        "phase": str(job.get("phase") or ""),
        "alias_kind": str(job.get("alias_kind") or ""),
        "armed_at": float(job.get("armed_at") or 0.0),
        "updated_at": float(job.get("updated_at") or 0.0),
        "attempts": int(job.get("attempts") or 0),
        "last_error": str(job.get("last_error") or ""),
        "is_mover": bool(torrent_hash == str(job.get("mover") or "")),
        # 登记还在但文件已消失: 记录陈旧, 不当作「auto-qb 设置仍生效」
        "stale_record": node_status == "missing",
    }


def _node(
    path: str, info: Optional[alias_fs.PathInspection], status: str, reason: str, alias_index: Mapping[str, Mapping],
    torrent_hash: str
) -> dict:
    kind = info.kind if info and info.status == "ok" else "unknown"
    return {
        "path": path_normalize(path),
        "type": kind or "unknown",
        "status": status,
        "reason": reason,
        "target": "",
        "nlink": info.nlink if info else 0,
        "attribution": _attribution(alias_index.get(_compare_key(path)), status, torrent_hash),
    }


def probe_chain(
    start: str,
    allowed_roots: Sequence[str],
    alias_index: Mapping[str, Mapping],
    torrent_hash: str,
    *,
    env: str = ENV_LOCAL
) -> dict:
    """从服务端派生的起点开始逐跳探测, 返回可直接序列化的链结果

    env != local(容器映射/远程)时不做任何 syscall, 只返回一个 unknown 节点并给出原因。
    """
    start_norm = path_normalize(alias_fs.strip_device_prefix(start or ""))
    nodes = []
    if env == ENV_MAPPED:
        node = _node(start_norm, None, "unknown", "容器映射环境无法逐跳探测", alias_index, torrent_hash)
        nodes.append(node)
        return _result(start_norm, nodes, env)
    if env == ENV_REMOTE:
        node = _node(start_norm, None, "unknown", "远程路径需在 qB 主机查看", alias_index, torrent_hash)
        nodes.append(node)
        return _result(start_norm, nodes, env)
    if not start_norm:
        nodes.append(_node("", None, "unknown", "种子记录没有可用路径", alias_index, torrent_hash))
        return _result(start_norm, nodes, env)
    if not path_within_roots(start_norm, allowed_roots):
        nodes.append(_node(start_norm, None, "outside_scope", "起点在允许根之外, 未探测", alias_index, torrent_hash))
        return _result(start_norm, nodes, env)

    seen = set()
    current = start_norm
    links_followed = 0
    while True:
        key = _compare_key(current)
        if key and key in seen:
            nodes.append(_node(current, None, "cycle", "检测到环: 该路径已出现过", alias_index, torrent_hash))
            break
        if key:
            seen.add(key)

        info = alias_fs.inspect_path(current)
        if info.status != "ok":
            nodes.append(_node(current, info, info.status, info.error, alias_index, torrent_hash))
            break
        nodes.append(_node(current, info, "ok", "", alias_index, torrent_hash))
        if info.kind not in (alias_fs.KIND_JUNCTION, alias_fs.KIND_SYMLINK):
            break  # 普通目录/文件/硬链接/挂载点: 链到此为止

        target = alias_fs.resolve_link_target(info.target, current)
        if not target:
            nodes[-1]["status"] = "unknown"
            nodes[-1]["reason"] = "链接目标无法映射到逻辑路径(可能是卷设备路径)"
            break
        target = path_normalize(target)
        nodes[-1]["target"] = target
        links_followed += 1
        if links_followed > MAX_HOPS:
            nodes.append(_node(target, None, "limit", f"超过 {MAX_HOPS} 跳上限, 未继续展开", alias_index, torrent_hash))
            break
        if not path_within_roots(target, allowed_roots):
            nodes.append(_node(target, None, "outside_scope", "目标在允许根之外, 未展开", alias_index, torrent_hash))
            break
        current = target
    return _result(start_norm, nodes, env)


def _result(start: str, nodes: list, env: str) -> dict:
    # probed_at 叶子取时走单点(挂钟语义: 与展示/落盘时间戳同侧, S2 时钟注入收编)
    return {
        "start": start,
        "env": env,
        "max_hops": MAX_HOPS,
        "probed_at": SYSTEM_CLOCK.now(),
        "nodes": nodes,
    }


class ChainCache:
    """路径链结果的短缓存(线程安全; TTL + LRU 上限)

    key 由调用方拼好(hash + 起点 + 快照代次), 任何一代快照变化都会自然换键。
    """
    def __init__(
        self,
        ttl: float = CHAIN_CACHE_TTL,
        capacity: int = CHAIN_CACHE_CAPACITY,
        clock: Optional[Clock] = None
    ) -> None:
        self.ttl = float(ttl)
        self.capacity = int(capacity)
        # 取时注入(D8): TTL 判定与入缓存戳用挂钟; 缺省单点经模块属性现取(测试可换假钟)
        self._clock = SYSTEM_CLOCK if clock is None else clock
        self._lock = threading.Lock()
        self._data: "OrderedDict[str, Tuple[float, dict]]" = OrderedDict()

    def get(self, key: str, loader, refresh: bool = False) -> Tuple[dict, bool]:
        """返回 (结果, 是否命中缓存); refresh=True 强制重探

        miss 路径入缓存的是 loader 结果的深拷贝(issue 26-11-07-0536): 返回值保持 loader
        原件交给调用方自由追加装饰键(路由的 "cached" / "finalize"), 缓存内对象从此没有
        任何外部引用 —— 否则并发同 key 请求在锁内 deepcopy 缓存对象时, 恰逢持有原引用的
        一方在锁外追加键, deepcopy 迭代中 dict 变长会抛 RuntimeError -> 500。深拷贝在取锁
        之前完成, 不拉长锁持有时间。
        """
        now = self._clock.now()
        with self._lock:
            hit = self._data.get(key)
            if not refresh and hit is not None and now - hit[0] < self.ttl:
                self._data.move_to_end(key)
                return copy.deepcopy(hit[1]), True
        value = loader()
        stored = copy.deepcopy(value)
        with self._lock:
            self._data[key] = (self._clock.now(), stored)
            self._data.move_to_end(key)
            while len(self._data) > self.capacity:
                self._data.popitem(last=False)
        return value, False


def make_cache() -> ChainCache:
    """每个 app 一份缓存(测试可独立替换, 避免跨用例串 TTL)"""
    return ChainCache()
