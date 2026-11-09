"""relocate_journal: 迁移收尾的两本账落盘(计划 26-10-18-1604 §3.5 起家, 26-11-05-0808 扩展)

两本账的分工:
- state.json → relocate.jobs.<job_id>: **权威**, 唯一写者 = auto-qb 主循环线程;
- <data_dir>/relocate/<job_id>.json: job journal(收尾账)。实际有**两个写者**: 回收
  daemon 写成员改写账(rewrites)与 rewritten 相位翻转, auto-qb 主循环写终态
  (done/cancelled/failed)与重建回滚(armed) —— 无跨进程锁, 整包 last-writer-wins, 靠
  write_journal 的「终态不得被非终态覆盖」前向合并保序(两个写者都走该函数)。

第三份文件 `<job_id>.spec.json` 是 auto-qb 写给 daemon 的**规格**: 路径可能含
非 ASCII, 一律不经命令行参数 —— 经文件传递。

journal 写入一律原子写(tmp + fsync + os.replace)。旧 guardian 的 per-job pid 锁与
心跳账已随 finalize_watch.py 整文件退役(D12: per-job pid 锁/per-job 心跳退役,
daemon 用实例级 daemon.json 心跳; 进程探测单点 _alive 由 daemon_stale 继续消费)。
"""
import json
import os
import re
from typing import Dict, List, Optional

from .clock import SYSTEM_CLOCK
from .utils import atomic_write

SUBDIR = "relocate"


def relocate_dir(data_dir: str) -> str:
    """<data_dir>/relocate(生产红线目录内只增; 与 state.json 同级派生)"""
    return os.path.join(str(data_dir or "auto-qb-data"), SUBDIR)


def journal_path(data_dir: str, job_id: str) -> str:
    return os.path.join(relocate_dir(data_dir), f"{job_id}.json")


def spec_path(data_dir: str, job_id: str) -> str:
    return os.path.join(relocate_dir(data_dir), f"{job_id}.spec.json")


def _write_json(path: str, payload: dict) -> None:
    def _fn(f):
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)

    atomic_write(path, _fn)


def _read_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


# ---------- journal(daemon 写改写账 / auto-qb 写终态与回滚) ----------

# journal 里出现这三个相位 = auto-qb 侧已收口(撤销/收尾完成/失败终态), daemon 必须退出/
# 放弃该 job —— 否则已终结 job 的改写账会被继续重放(D12: 取消/收口即时生效)。failed 是
# 主循环对账消费收尾校验失败证据时写下的终相位(与 done/cancelled 同为终态: 非终态写者
# 不得覆盖, 失败证据不被 daemon 重拉后的记账/翻相抹掉; 终态互覆仍 last-writer-wins)
STOP_PHASES = frozenset({"done", "cancelled", "failed"})


def write_journal(data_dir: str, job_id: str, payload: dict) -> bool:
    """写一条 journal(相位/改写账/证据); ts 缺省取当前墙钟; 返回是否落盘

    整包 last-writer-wins 且无跨进程锁, 唯一必须守住的序: **非终态相位不得覆盖终态**
    ——否则 daemon 的记账落进 auto-qb「写终态」之后的读-写间隙, 终态被回退成非终态,
    daemon 看不到退休指令(已收口 job 的改写账被继续重放)。写前读一次做前向合并:
    竞态窗口从「整个循环轮次」收窄到本函数内部读-写的微秒级。终态写终态(done/cancelled/failed
    互覆)仍 last-writer-wins。返回 False = 被拒写(对方已收口), 调用方(daemon)据此立即
    放弃该 job, 不再继续后续动作。
    """
    body = dict(payload or {})
    body.setdefault("ts", SYSTEM_CLOCK.now())  # journal 时间戳: 挂钟语义走取时单点(S2 时钟注入收编)
    current = _read_json(journal_path(data_dir, job_id))
    if current is not None and str(current.get("phase") or "") in STOP_PHASES \
            and str(body.get("phase") or "") not in STOP_PHASES:
        return False
    _write_json(journal_path(data_dir, job_id), body)
    return True


def read_journal(data_dir: str, job_id: str) -> Optional[dict]:
    return _read_json(journal_path(data_dir, job_id))


def clear_journal(data_dir: str, job_id: str) -> bool:
    """删除一份 job journal(主循环专属清理口; 返回是否真删除, 幂等)

    唯一合法用途: 对账确证 journal 是**上一生命周期**的陈旧残留(同 job_id 再迁移,
    ts 早于新生命周期锚点)时清除 —— failed 入 STOP_PHASES 后 daemon 对该 job_id 退休
    (scan 剔除 + record_rewrites 拒写), 残留账不清, 新生命周期的改写/重放被永久堵死。
    绕过 write_journal 前向合并是刻意的: 该账不属于任何在途生命周期, 「非终态不得覆盖
    终态」要保护的对象不存在; 删除与同目录 daemon.json 的按归属删除(release_daemon_state)
    同先例。证据处置: 调用方必须在调用本函数**之前**把 reason/ts 留一行日志(证据行
    存续先于删除 —— os.remove 成功与后续动作之间进程退出, 证据仍有痕; 结果行删后另记)
    —— state.json 旧条目随再发起登记被覆盖本就是既有语义(新世接管), 盘上证据的存续面
    即该行日志。
    """
    try:
        os.remove(journal_path(data_dir, job_id))
    except OSError:
        return False  # 已不在(FileNotFoundError)或盘/权限问题: 幂等不抛, 调用方下拍重试
    return True


# ---------- spec(auto-qb 写 / daemon 读) ----------


def write_spec(data_dir: str, job_id: str, spec: dict) -> None:
    _write_json(spec_path(data_dir, job_id), spec)


def read_spec(data_dir: str, job_id: str) -> Optional[dict]:
    return _read_json(spec_path(data_dir, job_id))


# ---------- 进程探测(实例级 daemon 存活判据的底层单点) ----------
# (S4 退役注记) 旧 guardian 的 per-job pid 锁(pid_path/acquire_pid/release_pid)已随
# finalize_watch.py 整文件退役(D12: per-job pid 锁/per-job 心跳退役) —— daemon 的
# 归属与心跳走实例级 daemon.json(下方 S3 扩展段); _alive 是进程探测单点, 由
# daemon_stale 继续消费。


def _alive(pid: int) -> bool:
    """进程是否存活

    !Windows **不能**用 os.kill(pid, 0): Windows 上 os.kill 对非 CTRL_* 信号一律走
    TerminateProcess —— 探测一次就把在跑的进程杀掉, 随后判「已在跑」让新实例退出,
    结果谁都没在跑; 巡检再重拉 -> 再杀 -> 自噬循环(P7 真机实测)。改走 OpenProcess
    (PROCESS_QUERY_LIMITED_INFORMATION)+GetExitCodeProcess(STILL_ACTIVE), 纯探测零副作用。
    """
    if os.name == "nt":
        import ctypes

        k32 = ctypes.windll.kernel32
        handle = k32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong(0)
            ok = k32.GetExitCodeProcess(handle, ctypes.byref(code))
            return bool(ok) and code.value == 259  # STILL_ACTIVE
        finally:
            k32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except (OSError, AttributeError):
        return False
    return True


# --------------------------------------------------------------------------
# S3 扩展(计划 26-11-05-0808): rewritten 相位 + 成员改写账 + daemon 心跳账
#
# 写方契约(D13): 回收 daemon(tools/recycle_daemon.py)是成员改写账与 rewritten 相位的
# **唯一写方**, 且只写 job journal、绝不碰 state.json;state.json 的 job 镜像由主循环
# 合并(主循环侧的事)。前向合并口径: 旧 reader 遇新字段(rewrites/daemon.* 文件)不炸
# —— journal 整包 last-writer-wins + write_journal 终态保护不变, 新字段只是 body 里的
# 普通键。
# --------------------------------------------------------------------------

# journal 相位补充: job 的全部 pending 成员收口后, daemon 把 journal 相位翻到 rewritten
# (计划 §2.4 新相位模型 {armed, rewritten}; 仍是**非终态** —— 终态(done/cancelled/failed)
# 只有主循环能写, 前向合并保护不变)
PHASE_REWRITTEN = "rewritten"

# 成员改写账(journal.rewrites.<member_key> 的 status)词表与「已收口」集合:
# - rewritten: 双键改写已落盘(retarget written)
# - already:   改写前已是目标值(retarget unchanged 且有键 already)—— 黄金法则 1: 幂等
#              重放必须收敛而非空转, 已在目标值 = 无事可做
# - unmatched: 全部路径键都不命中旧根(retarget unchanged 且纯 unmatched, 含 N10 相对
#              路径形态与 AutoTMM 之外的键缺席形态)—— 确定性无操作, 重放无意义; 真错向
#              由主循环重启后逐成员 save_path 核验兜住(S4), 账里保留逐键明细供诊断
# 三者视为已收口(pending 出账)。not_found / failed 不在集合: 留待窗口内重试与下一
# 窗口重放(D8), fails 计数进账(每失败一次 +1), 供对账「失败计数上限转人工告警」。
REWRITE_SETTLED = frozenset({"rewritten", "already", "unmatched"})

# 成员账记录里计数控的键名(单点: daemon 写 / 对账读)
REWRITE_FAILS_KEY = "fails"

# 重放入口(S4b, 计划 26-11-05-0808 §3.1「未通过 → journal 悬挂」支线的恢复面):
# 核验不过时主循环清 settled 记录使其重回 pending, daemon 在下一窗口重放改写。
# reset_rewrites 把 settled 记录的 status 置成 REWRITE_RESET_STATUS(pending_members 判
# 非 settled 即回账), 原状态保留在 prev_status 供诊断; 相位翻回 armed(pending 期)。
REWRITE_RESET_STATUS = "pending"
# journal 里的重放次数计数键(重放节奏闸: 重放一次后仍不过则维持悬挂+告警, 防无限
# 改写循环 —— 主循环写, daemon 的 record_rewrites 整包合并时原样保留)
VERIFY_REPLAYS_KEY = "verify_replays"


def instance_key(host: str, port: int) -> str:
    """qB 实例键: (host, port) 的文件名安全形制 —— daemon 心跳文件命名与对账分组的单点。

    Windows 文件名禁冒号 => ':' 与其它非 [A-Za-z0-9._-] 字符一律折叠为 '_'(IPv6 主机
    同样适用)。折叠不可逆: 实例身份判定一律以 (host, port) 原值字面相等为准(与
    bt_backup_path_of 同口径, 不做 localhost/127.0.0.1 智能匹配), 键只作文件名与分组。
    """
    raw = f"{str(host or '').strip()}_{int(port or 0)}"
    return re.sub(r"[^A-Za-z0-9._-]", "_", raw)


def daemon_state_path(data_dir: str, key: str) -> str:
    """daemon 心跳账路径: <data_dir>/relocate/daemon.<instance_key>.json(pid/ts 每 10s touch)"""
    return os.path.join(relocate_dir(data_dir), f"daemon.{key}.json")


def read_daemon_state(data_dir: str, key: str) -> Optional[dict]:
    return _read_json(daemon_state_path(data_dir, key))


def write_daemon_state(
    data_dir: str, key: str, pid: int, *, host: str = "", port: int = 0, ts: Optional[float] = None
) -> None:
    """落 daemon 心跳账(pid 抢占与其后的心跳 touch 共用此单点); host/port 仅作诊断字段"""
    body: Dict[str, object] = {"pid": int(pid), "ts": ts if ts is not None else SYSTEM_CLOCK.now()}
    if host:
        body["host"] = str(host)
    if port:
        body["port"] = int(port)
    _write_json(daemon_state_path(data_dir, key), body)


def touch_daemon_state(data_dir: str, key: str, pid: int, *, ts: Optional[float] = None) -> bool:
    """心跳 touch(读-验-写): 记录 pid 非我(已被退位)⇒ False 且**不落盘** —— 退位互斥的
    写侧闸门: 被退位者不得用心跳覆盖新主的 pid; 记录缺失(异常消失)⇒ 重新落盘认主。
    """
    cur = read_daemon_state(data_dir, key)
    if cur is not None and int(cur.get("pid") or 0) != int(pid):
        return False
    body: Dict[str, object] = {"pid": int(pid), "ts": ts if ts is not None else SYSTEM_CLOCK.now()}
    if cur:
        # 诊断字段随touch保留(claim 时写入的 host/port)
        body["host"] = str(cur.get("host") or "")
        body["port"] = int(cur.get("port") or 0)
    _write_json(daemon_state_path(data_dir, key), body)
    return True


def daemon_heartbeat_age(data_dir: str, key: str, now: Optional[float] = None) -> float:
    """daemon 心跳年龄(秒); 无记录/无 ts ⇒ 无穷大(对账据此判死)"""
    st = read_daemon_state(data_dir, key)
    ts = (st or {}).get("ts")
    if not ts:
        return float("inf")
    return max(0.0, (now if now is not None else SYSTEM_CLOCK.now()) - float(ts))


def daemon_stale(
    data_dir: str, key: str, *, max_age: float, now: Optional[float] = None, alive: Optional[bool] = None
) -> bool:
    """daemon 挂死/缺位判定(对账 ACT_ENSURE_DAEMON 重拉判据的协议单点; S3 提供本函数,
    接线在下一任务): 无记录 / 记录 pid 已死 / 心跳年龄 > max_age ⇒ True(可重拉);
    pid 仍活且心跳未过期 ⇒ False(健康 watcher 在位, 不得重复拉起)。
    alive 可注入 pid 存活替身(测试用); 缺省用进程探测单点 _alive。"""
    st = read_daemon_state(data_dir, key)
    if not st:
        return True
    pid = int(st.get("pid") or 0)
    if not pid:
        return True
    pid_ok = bool(alive) if alive is not None else _alive(pid)
    if not pid_ok:
        return True
    return daemon_heartbeat_age(data_dir, key, now=now) > max_age


def release_daemon_state(data_dir: str, key: str, pid: int) -> bool:
    """按归属释放 daemon 心跳账: 仅当记录 pid 是自己才删(被退位者不得删新主记录)。"""
    path = daemon_state_path(data_dir, key)
    cur = read_daemon_state(data_dir, key)
    if cur is None or int(cur.get("pid") or 0) != int(pid):
        return False
    try:
        os.remove(path)
    except OSError:
        return False
    return True


def record_rewrites(
    data_dir: str,
    job_id: str,
    records: Dict[str, dict],
    *,
    phase: Optional[str] = None,
    ts: Optional[float] = None,
    pid: Optional[int] = None
) -> bool:
    """daemon 专用记账口: 把成员改写账读-改-写并进 journal.rewrites(整包 last-writer-wins
    下的合并单点), 可选翻转相位(phase=rewritten)。落盘走 write_journal 复用其前向合并:
    对账已收口(journal 已终态 done/cancelled/failed)⇒ 拒写返回 False —— 取消/完成/失败对 daemon
    即时生效的协议级闸门(D12), 调用方据此立即放弃该 job。phase 参数只收非终态相位
    (终态是主循环的专属写权, fail-fast)。
    """
    if phase is not None and str(phase) in STOP_PHASES:
        raise ValueError(f"record_rewrites 不接受终态相位: {phase}(终态只有主循环能写)")
    cur = read_journal(data_dir, job_id) or {}
    if str(cur.get("phase") or "") in STOP_PHASES:
        return False
    body = dict(cur)
    body["phase"] = str(phase) if phase else str(cur.get("phase") or "armed")
    rewrites = dict(body.get("rewrites") or {})
    now = ts if ts is not None else SYSTEM_CLOCK.now()
    for k, v in dict(records or {}).items():
        rec = dict(v or {})
        rec.setdefault("ts", now)
        rewrites[str(k)] = rec
    body["rewrites"] = rewrites
    if pid:
        body["pid"] = int(pid)
    body["ts"] = now
    return write_journal(data_dir, job_id, body)


def read_rewrites(data_dir: str, job_id: str) -> Dict[str, dict]:
    """成员改写账(journal.rewrites); 无 journal/无账/形不符 ⇒ {}"""
    j = read_journal(data_dir, job_id)
    rewrites = (j or {}).get("rewrites")
    return dict(rewrites) if isinstance(rewrites, dict) else {}


def verify_replays_of(data_dir: str, job_id: str) -> int:
    """已重放次数(journal.verify_replays); 无 journal/无键/坏形 ⇒ 0(从未重放)"""
    j = read_journal(data_dir, job_id) or {}
    try:
        return max(0, int(j.get(VERIFY_REPLAYS_KEY) or 0))
    except (TypeError, ValueError):
        return 0


def reset_rewrites(data_dir: str, job_id: str, *, ts: Optional[float] = None) -> int:
    """清 settled 改写记录使其重回 pending(核验未过的重放入口; S3a 范围外发现第 3 条)

    rewritten 账已收口但重启后核验不过(save_path 未到目标)= 改写被错过/未生效 ——
    本接口把 settled 记录整体清回 pending(status -> REWRITE_RESET_STATUS, 原状态留
    prev_status 诊断), 相位翻回 armed(pending 期), 并累加 verify_replays 计数供调用方
    做「只重放一次」的节奏闸(重放一次后仍不过 = 维持悬挂+告警, 防无限改写循环)。

    返回重置条数; 0 = 无 settled 记录可重置(不动盘, 幂等); -1 = journal 已终态
    (拒写, 走 write_journal 的前向合并保护 —— 已收口/已取消/已判失败的 job 不再重放)。
    """
    cur = read_journal(data_dir, job_id) or {}
    if str(cur.get("phase") or "") in STOP_PHASES:
        return -1
    raw_rewrites = cur.get("rewrites")
    rewrites = raw_rewrites if isinstance(raw_rewrites, dict) else {}
    now = ts if ts is not None else SYSTEM_CLOCK.now()
    body = dict(cur)
    new_rewrites: Dict[str, dict] = {}
    n = 0
    for k, rec in rewrites.items():
        status = str(rec.get("status") or "") if isinstance(rec, dict) else ""
        if status in REWRITE_SETTLED:
            nr = dict(rec) if isinstance(rec, dict) else {}
            nr["prev_status"] = status
            nr["status"] = REWRITE_RESET_STATUS
            nr["ts"] = now
            new_rewrites[str(k)] = nr
            n += 1
        else:
            new_rewrites[str(k)] = rec
    if n:
        body["rewrites"] = new_rewrites
    else:
        return 0  # 无 settled 记录: 不写盘不翻相位(幂等, 重复调用无副作用)
    body["phase"] = "armed"  # 回到 pending 期, 等 daemon 在下一窗口重放
    body[VERIFY_REPLAYS_KEY] = verify_replays_of(data_dir, job_id) + 1
    body["ts"] = now
    return n if write_journal(data_dir, job_id, body) else -1


def list_spec_jobs(data_dir: str) -> List[str]:
    """现存 spec 的 job_id 清单(目录扫描; spec 文件命名协议的单点)"""
    try:
        names = os.listdir(relocate_dir(data_dir))
    except OSError:
        return []
    out = []
    for name in names:
        if name.endswith(".spec.json"):
            out.append(name[:-len(".spec.json")])
    return sorted(out)


# --------------------------------------------------------------------------
# S5 扩展(计划 26-11-05-0808 §3.4/D15/D19/D20): supersede 重定向的账面单点
#
# armed/rewritten 相位放行再迁移后, 前任 job 的改写账 {A→B} 必须改道 {A→C}(先搬后
# 重定向, 硬约束1): spec.dst 是 daemon 改写映射的唯一来源(_rewrite_member 读
# spec.src/spec.dst), 改道 = 覆写 spec.dst; journal 记一笔 retarget 供诊断与「旧条目
# 零残留」核验(N10)。两者都是主循环在线时点的写(qB 在线 ⇒ daemon 不在窗口, 无并发写;
# §07 串行化行), 读-改-写沿各自单点, 幂等可重放(D20 搬后重试至收敛)。
# --------------------------------------------------------------------------


def retarget_spec(data_dir: str, job_id: str, new_dst: str) -> bool:
    """spec.dst 重定向({A→B}→{A→C}; S5 supersede 的账面单点): 返回是否真落盘

    - spec 缺失/缺 src(旧链 job / bt_backup 未配置的降级账)⇒ False, 不猜不建
      (arm 侧责任, 与 daemon 的残缺 spec 跳过同口径);
    - dst 已是新值 ⇒ False(幂等, 黄金法则 1);
    - daemon 的改写映射 = spec.src→spec.dst 整对, files/members 不随重定向变化
      (相对路径与成员清单与目标无关)。
    """
    spec = read_spec(data_dir, job_id)
    if not isinstance(spec, dict) or not str(spec.get("src") or "").strip():
        return False
    cur, new = str(spec.get("dst") or ""), str(new_dst or "")
    if os.path.normcase(os.path.normpath(cur.replace("\\", "/"))) == \
            os.path.normcase(os.path.normpath(new.replace("\\", "/"))):
        return False
    spec["dst"] = new
    write_spec(data_dir, job_id, spec)
    return True


def mark_journal_retarget(
    data_dir: str, job_id: str, from_dst: str, to_dst: str, *, ts: Optional[float] = None
) -> bool:
    """journal 记一笔重定向(retarget 字段; 读-改-写保留 rewrites/verify_replays 等既有账)

    返回 False = 拒写(journal 已终态, write_journal 前向合并保护)或盘写失败 —— 记账
    是诊断面不是承重面, 调用方告警后继续, 不因它回滚重定向。
    """
    cur = read_journal(data_dir, job_id) or {}
    body = dict(cur)
    body["retarget"] = {"from": str(from_dst or ""), "to": str(to_dst or "")}
    return write_journal(data_dir, job_id, body)


def spec_members(spec: dict) -> List[dict]:
    """spec 的改写成员清单: members 字段优先(v2/hybrid 显式双 hash 形态, arm 时由主循环
    写入); 缺省从 hashes 派生(逐个视作 hash_v1 —— v1 种子的 fastresume 文件名即
    <infohash_v1>, N 系列实测; hybrid/v2 形态由 arm 侧显式给 members, 不猜命名)。"""
    members = spec.get("members")
    if isinstance(members, list):
        out = [m for m in members if isinstance(m, dict)]
        if out:
            return out
    return [{"hash_v1": str(h), "hash_v2": ""} for h in (spec.get("hashes") or [])]


def member_key(member: dict) -> str:
    """成员账键: hash_v1 优先, 退 hash_v2(spec_members 的产出必有其一非空)"""
    return str(member.get("hash_v1") or member.get("hash_v2") or "")


def pending_members(spec: dict, rewrites: Dict[str, dict]) -> List[dict]:
    """pending 口径单点(计划 §3.1「窗口开头现读 pending 集」): 已记账(spec 成员清单,
    arm 时落账)且未收口(journal.rewrites 无记录或 status 不在 REWRITE_SETTLED)的成员。
    纯函数: 不做 I/O, 不看相位 —— 终态剔除是调用方(scan)的职责。"""
    rewrites = rewrites or {}
    out = []
    for m in spec_members(spec):
        rec = rewrites.get(member_key(m)) or {}
        if str(rec.get("status") or "") not in REWRITE_SETTLED:
            out.append(m)
    return out


# --------------------------------------------------------------------------
# S6 扩展(计划 26-11-10-0318 §03.4): 实例级观测账(obs 文件)
#
# recycle daemon 的实例级证据链(观测面 O1/O2, 该计划 W1)自维护的持久化观测状态:
# owner 死证(LISTENING 归属 + 映像名交叉校验的 {pid, ct, ts})与新面孔 absorbed 清单。
# 与同目录 daemon.json 的分工: daemon.json 是 watcher 归属与心跳(谁在看), obs 是进程
# 观测结论(看到了什么)—— 语义不混(D13 账本契约不动, state.json 一概不碰)。写时机 =
# 状态变更即写(owner 换身/吸收/清出, 频率低); 读侧缺失/坏形一律按「无有效观测」退回
# 全机口径(保守退化, 黄金法则 2)。
# --------------------------------------------------------------------------

# obs 账 schema 版本(计划 §03.4 钉死: {schema_version, host, port, owner, absorbed, ts};
# ct = create_time epoch 秒, ts = 观测时刻)
OBS_SCHEMA_VERSION = 1


def obs_path(data_dir: str, key: str) -> str:
    """观测账路径: <data_dir>/relocate/obs-<instance_key>.json(与 spec/journal/daemon.json
    同目录同家族, 复用 SUBDIR/instance_key 家族)"""
    return os.path.join(relocate_dir(data_dir), f"obs-{key}.json")


def _obs_pos_num(v: object) -> bool:
    """正数值严格判型: int/float 且非 bool(bool 是 int 子类, True/False 不得冒充 1/0)
    且 >0; 混型(数值字符串等)一律不符 —— 观测账是证据面, 判型从宽等于放行半残记录"""
    return not isinstance(v, bool) and isinstance(v, (int, float)) and v > 0


def _obs_entry_ok(entry: object) -> bool:
    """obs 单条进程记录形校验(严格判型): {pid, ct, ts} 且 pid 为正 int、ct/ts 为正数值"""
    if not isinstance(entry, dict):
        return False
    pid = entry.get("pid")
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return False
    return _obs_pos_num(entry.get("ct")) and _obs_pos_num(entry.get("ts"))


def read_obs(data_dir: str, key: str) -> Optional[dict]:
    """读观测账; 缺文件/schema_version 不符/形不符 => None(保守: 无有效记录 = 调用方
    退回全机口径, 绝不把半残记录当证据用)

    形校验(计划 §03.4 schema, 全部严格判型): owner 为 None 或 {pid, ct, ts} 实记录;
    absorbed 为其清单(缺失也判废 —— 我们自己的写方恒带该键, 缺键即非本链产物); host 为
    非空 str、port 为正 int(与 absorbed 缺键同口径, 非 本链写方产物判废); schema_version
    为 int 且非 bool; 顶层 ts 为正数值; 未知新字段放行(前向兼容, 与 S3 写方契约同口径)。
    """
    st = _read_json(obs_path(data_dir, key))
    if st is None:
        return None
    sv = st.get("schema_version")
    if isinstance(sv, bool) or not isinstance(sv, int) or sv != OBS_SCHEMA_VERSION:
        return None
    host = st.get("host")
    if not isinstance(host, str) or not host.strip():
        return None
    port = st.get("port")
    if isinstance(port, bool) or not isinstance(port, int) or port <= 0:
        return None
    owner = st.get("owner")
    if owner is not None and not _obs_entry_ok(owner):
        return None
    absorbed = st.get("absorbed")
    if not isinstance(absorbed, list) or not all(_obs_entry_ok(e) for e in absorbed):
        return None
    if not _obs_pos_num(st.get("ts")):
        return None
    return st


def write_obs(data_dir: str, key: str, payload: dict) -> bool:
    """写观测账(原子写, 复用 _write_json 家族); 返回是否落盘(False = 盘故障, 调用方
    告警留痕后继续 —— 观测持久化是 best-effort, 缺失即退回全机口径, 不中断 daemon 节拍)

    **新写入即全量替换**: 不读旧账不合并 —— 已存记录的 host/port 与本次不一致时**同样
    直接覆盖**。理由: obs 账语义 =「实例 (host, port) 的当前观测」, 文件按实例键分家;
    键内 host/port 变化 = 调用方换了实例身份, owner/absorbed 都是按实例归属的, 旧观测
    整体作废, 继承才是错。schema_version 由本函数强制钉上(写侧不可能漏, 读侧不必猜);
    ts 缺省取当前挂钟(SYSTEM_CLOCK 单点), 调用方可显式传观测时刻。
    """
    body = dict(payload or {})
    body["schema_version"] = OBS_SCHEMA_VERSION
    body.setdefault("ts", SYSTEM_CLOCK.now())
    try:
        _write_json(obs_path(data_dir, key), body)
    except OSError:
        return False
    return True
