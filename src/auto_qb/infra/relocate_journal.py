"""relocate_journal: 收尾 guardian 的两本账落盘(计划 26-10-18-1604 §3.5, P6)

两本账的分工(§3.5「为什么需要两本账」):
- state.json → relocate.jobs.<job_id>: **权威**, 唯一写者 = auto-qb 主循环线程;
- <data_dir>/relocate/<job_id>.json: guardian 自述的 journal(相位/心跳/三证证据)。
  实际有**两个写者**: guardian 写心跳/收尾意图(armed/removing/removed/failed),
  auto-qb 主循环写终态(done/cancelled)与意图回滚(armed) —— 无跨进程锁, 整包
  last-writer-wins, 靠 write_journal 的「终态不得被非终态覆盖」前向合并保序
  (两个写者都走该函数, 见其 docstring)。

第三份文件 `<job_id>.spec.json` 是 auto-qb 写给 guardian 的**规格**: 路径可能含
非 ASCII(§3.3 实测韩文名 + 括号), 一律不经命令行参数 —— 经文件传递。

journal 写入一律原子写(tmp + fsync + os.replace): 「删链接」是唯一「删完就观测不到」
的动作, 必须先落 removing 意图再删, 崩在哪一侧由「journal 相位 + 链接是否还在」
二者唯一确定(§3.5)。
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


def pid_path(data_dir: str, job_id: str) -> str:
    return os.path.join(relocate_dir(data_dir), f"{job_id}.pid")


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


# ---------- journal(guardian 写 / auto-qb 读) ----------

# journal 里出现这两个相位 = auto-qb 侧已收口(撤销/收尾完成), guardian 必须退出 ——
# 否则一个已终结 job 的守护进程会永远每 10s 写心跳(armed 态本来就要等 qB 退出, 可能等几个月)
STOP_PHASES = frozenset({"done", "cancelled"})


def write_journal(data_dir: str, job_id: str, payload: dict) -> bool:
    """写一条 journal(相位/心跳/证据); ts 缺省取当前墙钟; 返回是否落盘

    整包 last-writer-wins 且无跨进程锁, 唯一必须守住的序: **非终态相位不得覆盖终态**
    ——否则 guardian 的 armed 心跳落进 auto-qb「写终态」之后的读-写间隙, 终态被回退成
    armed, guardian 看不到退休指令(僵尸进程 + 对账面相位失真)。写前读一次做前向合并:
    竞态窗口从「整个循环轮次(毫秒级, 心跳 10s 一次)」收窄到本函数内部读-写的微秒级。
    终态写终态(done/cancelled 互覆)仍 last-writer-wins。返回 False = 被拒写(对方已收口),
    调用方(guardian)据此立即退休, 不再继续后续动作(尤其不得再删链接)。
    """
    body = dict(payload or {})
    body.setdefault("ts", SYSTEM_CLOCK.now())  # journal 心跳戳: 挂钟语义走取时单点(S2 时钟注入收编)
    current = _read_json(journal_path(data_dir, job_id))
    if current is not None and str(current.get("phase") or "") in STOP_PHASES \
            and str(body.get("phase") or "") not in STOP_PHASES:
        return False
    _write_json(journal_path(data_dir, job_id), body)
    return True


def read_journal(data_dir: str, job_id: str) -> Optional[dict]:
    return _read_json(journal_path(data_dir, job_id))


def heartbeat_age(data_dir: str, job_id: str, now: Optional[float] = None) -> float:
    """心跳年龄(秒); 无 journal ⇒ 无穷大(对账表据此重拉 guardian)"""
    j = read_journal(data_dir, job_id)
    ts = (j or {}).get("ts")
    if not ts:
        return float("inf")
    # 与落盘 ts 同侧相减: 挂钟语义走取时单点(now 参数照旧可注入, 缺省才取单点)
    return max(0.0, (now if now is not None else SYSTEM_CLOCK.now()) - float(ts))


# ---------- spec(auto-qb 写 / guardian 读) ----------


def write_spec(data_dir: str, job_id: str, spec: dict) -> None:
    _write_json(spec_path(data_dir, job_id), spec)


def read_spec(data_dir: str, job_id: str) -> Optional[dict]:
    return _read_json(spec_path(data_dir, job_id))


# ---------- pid 锁(本 job 只允许一个 guardian) ----------


def acquire_pid(data_dir: str, job_id: str) -> bool:
    """抢占 pid 锁: 成功写自己的 pid; 已存在且进程仍活 ⇒ False(不重复拉起)

    进程判定用 os.kill(pid, 0)(POSIX); Windows 无信号 0, 退化为「文件存在即认为在跑」——
    残留锁文件最多让本轮收尾推迟到下次巡检重拉(guardian 不工作是安全的: 别名态本身稳定)。
    """
    path = pid_path(data_dir, job_id)
    old = _read_json(path)
    if old:
        pid = int(old.get("pid") or 0)
        if pid and _alive(pid):
            return False
    _write_json(path, {"pid": os.getpid(), "ts": SYSTEM_CLOCK.now()})  # 锁文件落盘戳: 挂钟语义走单点
    return True


def _alive(pid: int) -> bool:
    """进程是否存活

    !Windows **不能**用 os.kill(pid, 0): Windows 上 os.kill 对非 CTRL_* 信号一律走
    TerminateProcess —— 探测一次就把在跑的 guardian 杀掉, 随后 acquire_pid 判「已在跑」
    让新实例退出, 结果谁都没在跑; 巡检再重拉 -> 再杀 -> 自噬循环(P7 真机实测: 日志每
    1.5s 一条「guardian 心跳过期/重拉」, journal 永远停在 armed)。改走 OpenProcess
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


def release_pid(data_dir: str, job_id: str) -> None:
    try:
        os.remove(pid_path(data_dir, job_id))
    except OSError:
        return


# --------------------------------------------------------------------------
# S3 扩展(计划 26-11-05-0808): rewritten 相位 + 成员改写账 + daemon 心跳账
#
# 写方契约(D13): 回收 daemon(tools/recycle_daemon.py)是成员改写账与 rewritten 相位的
# **唯一写方**, 且只写 job journal、绝不碰 state.json(与旧 guardian 同契约);
# state.json 的 job 镜像由主循环合并(主循环侧的事)。前向合并口径: 旧 reader 遇新字段
# (rewrites/daemon.* 文件)不炸 —— journal 整包 last-writer-wins + write_journal 终态
# 保护不变, 新字段只是 body 里的普通键。
# --------------------------------------------------------------------------

# journal 相位补充: job 的全部 pending 成员收口后, daemon 把 journal 相位翻到 rewritten
# (计划 §2.4 新相位模型 {armed, rewritten}; 仍是**非终态** —— 终态(done/cancelled)
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
    body = {"pid": int(pid), "ts": ts if ts is not None else SYSTEM_CLOCK.now()}
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
    body = {"pid": int(pid), "ts": ts if ts is not None else SYSTEM_CLOCK.now()}
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
    对账已收口(journal 已终态 done/cancelled)⇒ 拒写返回 False —— 取消/完成对 daemon
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
