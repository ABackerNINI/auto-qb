"""relocate_journal: 收尾 guardian 的两本账落盘(计划 26-10-18-1604 §3.5, P6)

两本账的分工(§3.5「为什么需要两本账」):
- state.json → relocate.jobs.<job_id>: **权威**, 唯一写者 = auto-qb 主循环线程;
- <data_dir>/relocate/<job_id>.json: guardian 自述的 journal(相位/心跳/三证证据),
  唯一写者 = guardian 进程。两个进程永不写同一份文件 ⇒ 不需要跨进程锁。

第三份文件 `<job_id>.spec.json` 是 auto-qb 写给 guardian 的**规格**: 路径可能含
非 ASCII(§3.3 实测韩文名 + 括号), 一律不经命令行参数 —— 经文件传递。

journal 写入一律原子写(tmp + fsync + os.replace): 「删链接」是唯一「删完就观测不到」
的动作, 必须先落 removing 意图再删, 崩在哪一侧由「journal 相位 + 链接是否还在」
二者唯一确定(§3.5)。
"""
import json
import os
import time
from typing import Optional

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


def write_journal(data_dir: str, job_id: str, payload: dict) -> None:
    """写一条 journal(相位/心跳/证据); ts 缺省取当前墙钟"""
    body = dict(payload or {})
    body.setdefault("ts", time.time())
    _write_json(journal_path(data_dir, job_id), body)


def read_journal(data_dir: str, job_id: str) -> Optional[dict]:
    return _read_json(journal_path(data_dir, job_id))


def heartbeat_age(data_dir: str, job_id: str, now: Optional[float] = None) -> float:
    """心跳年龄(秒); 无 journal ⇒ 无穷大(对账表据此重拉 guardian)"""
    j = read_journal(data_dir, job_id)
    ts = (j or {}).get("ts")
    if not ts:
        return float("inf")
    return max(0.0, (now if now is not None else time.time()) - float(ts))


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
    _write_json(path, {"pid": os.getpid(), "ts": time.time()})
    return True


def _alive(pid: int) -> bool:
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
