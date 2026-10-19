"""finalize_watch: 整组迁移收尾 guardian(独立进程, 计划 26-10-18-1604 §3.5/P6)

为什么是独立进程: 收尾窗口在 **qB 退出之后** —— auto-qb 自己可能已经不在了(关机/被关),
而删别名又必须发生在 qB 确实没在跑的时候(§3.5 不变量 2: qB 持有打开句柄时删链接, 它会
按旧句柄继续报做种 = 假种)。故 guardian 随迁移武装时拉起、分离运行、写完 journal 即退。

它做的全部事情:
  1. 抢占本 job 的 pid 锁(一个 job 只允许一个 guardian);
  2. 每 10s 写一次心跳 journal(phase=armed), 供 auto-qb 对账判「guardian 还活着」;
  3. 三证判 qB 已退出 —— 进程不存在 + 端口连不上 + 该状态稳定 30s;
  4. 校验目标侧数据完整(文件数/大小对齐);
  5. 先落 journal(phase=removing)再逐条删链接(非递归), 删完落 removed。

**绝不**做: 搬任何数据(D2)、自行 setLocation(那是 auto-qb 在 qB 回来后做的事)、
递归删除、修改 state.json(那是主循环线程的唯一写权)。

用法: `python -m auto_qb.tools.finalize_watch --data-dir <dir> --job <job_id>`
(规格经 `<data_dir>/relocate/<job_id>.spec.json` 传递: 路径可能含非 ASCII, 不经命令行)
"""
import argparse
import os
import socket
import subprocess
import sys
import time

from ..infra import alias_fs
from ..infra.relocate_journal import (
    acquire_pid,
    journal_path,
    read_journal,
    read_spec,
    release_pid,
    write_journal,
)

HEARTBEAT_INTERVAL = 10.0  # 心跳周期(§3.5; auto-qb 侧判过期 = >60s)
STABLE_WINDOW = 30.0  # 三证稳定窗口: 连续判定「qB 不在」这么久才动手
POLL_INTERVAL = 5.0  # 主循环节拍(心跳按 HEARTBEAT_INTERVAL 节流写)


def _port_refused(host: str, port: int, timeout: float = 1.0) -> bool:
    """证二: 端口连不上 ⇒ 拒连(超时同按连不上处理: 我们要的是「qB 不在」, 不是诊断网络)"""
    if not port:
        return True  # 无端口可判 ⇒ 视为连不上(配合进程证一起才算三证)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return False
    except OSError:
        return True


def _names_from_tasklist() -> tuple:
    """Windows: tasklist CSV 首列(引号内的映像名)"""
    out = subprocess.run(
        ["tasklist", "/NH", "/FO", "CSV"],
        capture_output=True,
        text=True,
        timeout=10,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    names = []
    for line in (out.stdout or "").splitlines():
        if line.startswith('"'):
            names.append(line.split('"')[1].lower())
    return tuple(names)


def _names_from_proc() -> tuple:
    """Linux: /proc/<pid>/comm(容器里普遍可用, 零子进程)"""
    names = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/comm", "r", encoding="utf-8") as f:
                names.append(f.read().strip().lower())
        except OSError:
            continue
    return tuple(names)


def _names_from_ps() -> tuple:
    """其它 POSIX: ps -eo comm="""
    out = subprocess.run(["ps", "-eo", "comm="], capture_output=True, text=True, timeout=10)
    return tuple(n.strip().lower() for n in (out.stdout or "").splitlines())


def _qb_process_names() -> tuple:
    """进程名清单(跨平台尽力而为: 判不出返回空, 调用方按「未能证明进程不存在」处理)"""
    try:
        if os.name == "nt":
            return _names_from_tasklist()
        if os.path.isdir("/proc"):
            return _names_from_proc()
        return _names_from_ps()
    except Exception:  # noqa: BLE001 - 判不出进程表: 保守(不算「已退出」)
        return ()


def _proc_absent(names: tuple) -> bool:
    """证一: qB 进程不存在; 进程表读不到 ⇒ False(未证明)"""
    if not names:
        return False
    return not any("qbittorrent" in n for n in names)


def _verify_dst(spec: dict) -> bool:
    """目标侧数据完整性(文件数 + 大小对齐): 不齐就不删链接(删了就真缺文件了)"""
    files = spec.get("files") or []
    if not files:
        return False
    dst = str(spec.get("dst") or "")
    for rel, size in files:
        p = os.path.join(dst, *[x for x in str(rel).replace("\\", "/").split("/") if x])
        try:
            if not os.path.isfile(p) or os.path.getsize(p) != int(size):
                return False
        except OSError:
            return False
    return True


def _delete_links(spec: dict) -> int:
    """逐条删链接(非递归, 幂等); 返回删除条数"""
    n = 0
    for p in spec.get("alias_paths") or []:
        if not p:
            continue
        try:
            if alias_fs.alias_kind_of(p) is not None:
                alias_fs.remove_alias(p)
                n += 1
        except Exception:  # noqa: BLE001 - 单条失败继续: 幂等重删交给 auto-qb 侧对账
            continue
    return n


def run(
    data_dir: str,
    job_id: str,
    *,
    heartbeat: float = HEARTBEAT_INTERVAL,
    stable: float = STABLE_WINDOW,
    poll: float = POLL_INTERVAL,
    max_wait: float = 0.0,
    clock=time.time,
    sleep=time.sleep
) -> str:
    """guardian 主循环; 返回收尾结论(供 CLI 与测试断言)

    max_wait > 0 时超过该时长仍未等到 qB 退出 ⇒ 退出并保留 armed(不等无限久; auto-qb
    侧 finalize_timeout 才是最终兜底)。
    """
    spec = read_spec(data_dir, job_id)
    if spec is None:
        return "no_spec"
    if not acquire_pid(data_dir, job_id):
        return "already_running"
    started = clock()
    down_since = 0.0
    last_hb = 0.0
    try:
        while True:
            now = clock()
            # auto-qb 侧已收口(撤销/收尾完成) ⇒ 退出, 不等 qB 退出也不碰链接
            current = read_journal(data_dir, job_id) or {}
            if str(current.get("phase") or "") in STOP_PHASES:
                return "stopped"
            if now - last_hb >= heartbeat:
                write_journal(data_dir, job_id, {"phase": "armed", "pid": os.getpid(), "job_id": job_id})
                last_hb = now
            names = _qb_process_names()
            down = _proc_absent(names
                               ) and _port_refused(str(spec.get("host") or "127.0.0.1"), int(spec.get("port") or 0))
            if down:
                if not down_since:
                    down_since = now
                if now - down_since >= stable:
                    if not _verify_dst(spec):
                        write_journal(
                            data_dir, job_id, {
                                "phase": "failed",
                                "reason": "verify_mismatch",
                                "pid": os.getpid(),
                            }
                        )
                        return "verify_mismatch"
                    write_journal(
                        data_dir,
                        job_id,
                        {
                            "phase": "removing",
                            "pid": os.getpid(),
                            "qb_down_evidence":
                                {
                                    "proc_absent": True,
                                    "port_refused": True,
                                    "stable_secs": round(now - down_since, 1),
                                },
                        },
                    )
                    n = _delete_links(spec)
                    write_journal(
                        data_dir,
                        job_id,
                        {
                            "phase": "removed",
                            "pid": os.getpid(),
                            "checks": {
                                "file_count": len(spec.get("files") or []),
                                "links_removed": n,
                            },
                        },
                    )
                    return "removed"
            else:
                down_since = 0.0
            if max_wait and now - started > max_wait:
                return "timeout"
            sleep(poll)
    finally:
        release_pid(data_dir, job_id)


# journal 里出现这两个相位 = auto-qb 侧已收口(撤销/收尾完成), guardian 必须退出 ——
# 否则一个已终结 job 的守护进程会永远每 10s 写心跳(armed 态本来就要等 qB 退出, 可能等几个月)
STOP_PHASES = frozenset({"done", "cancelled"})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="整组迁移收尾 guardian(等 qB 退出后删别名)")
    ap.add_argument("--data-dir", required=True, help="运行时数据目录(与 config.data_dir 同源)")
    ap.add_argument("--job", required=True, help="job_id")
    ap.add_argument("--heartbeat", type=float, default=HEARTBEAT_INTERVAL)
    ap.add_argument("--stable", type=float, default=STABLE_WINDOW)
    ap.add_argument("--poll", type=float, default=POLL_INTERVAL)
    ap.add_argument("--max-wait", type=float, default=0.0, help="最长等待秒数(0 = 不限)")
    args = ap.parse_args(argv)
    result = run(
        args.data_dir,
        args.job,
        heartbeat=args.heartbeat,
        stable=args.stable,
        poll=args.poll,
        max_wait=args.max_wait,
    )
    print(f"finalize_watch: job {args.job} -> {result}(journal: {journal_path(args.data_dir, args.job)})")
    return 0 if result in ("removed", "already_running", "stopped") else 1


if __name__ == "__main__":
    sys.exit(main())
