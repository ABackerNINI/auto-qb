"""recycle_daemon: fastresume 收尾回收 daemon(计划 26-11-05-0808 §3.1 daemon 段/§3.2, D11-D13)

职权(D11 换位): 等 qB 下线窗口, 批量改写 pending 成员的 fastresume 双键, journal 落账。
**绝不**做: 删链(主循环在线做, D11)/碰 state.json(D13 账本契约, 与旧 guardian 同契约)/
taskkill(进程红线)/窗口外任何 fastresume 落盘(N1 铁律: qB 运行期秒级重写, 0.5s 实测覆盖)。

形制(D12 简化): 每 qB 实例至多一个 watcher;触发只有「qB 下线」一个事件 —— 无 TCP
nudge/无端口文件/无兜底扫;窗口开头现读 pending 集(supersede/取消即时生效, 窗口内逐拍
现读续保);进窗判据照搬 guardian 三证(进程不在 + 端口拒连 + 稳定 STABLE_WINDOW, 判据
函数原样复用 finalize_watch —— 其整文件退役后由本模块继承);退位 = pid 抢占 + 旧 daemon
自检自杀, 绝不 taskkill;心跳 = daemon.json(pid/ts)每 HEARTBEAT_INTERVAL touch。

账本(D13/D8): 只写 job journal(rewrites 成员账 + rewritten 相位), 绝不碰 state.json;
每个下线窗口限一轮会话, 窗口内失败重试至成功或 qB 回升, 失败计数(fails)进账;qB 抢先
回升 = 本轮放弃, 无害(N4 实证自愈: 成员经别名正常加载, journal 待重放, 下一窗口重放)。
半途崩溃/退位/回升都留下一致账态(逐成员即改即记账, 原子写), 下一窗口按账重放。

发现面: 扫 <data_dir>/relocate/*.spec.json 中属于本实例(host/port 字面相等, 与
bt_backup_path_of 同口径)且带 bt_backup 字段(**新链 opt-in 标记** —— 旧链 spec 无此
字段, 仍归旧链管辖, 本模块不碰)的 job;pending 口径单点在
relocate_journal.pending_members = 已记账(spec 成员清单)且 journal.rewrites 未收口
(REWRITE_SETTLED 之外)的成员。

与主循环的串行化(§07 并发写账行): daemon 只在 qB 离线时动 fastresume;主循环的
setLocation/取消/再迁移只在 qB 在线时可达;两侧写不同文件(job journal vs state.json)。

用法: `python -m auto_qb.tools.recycle_daemon --data-dir <dir> --host <host> --port <port>`
(独立 CLI 入口, 可手动运行做验证;规格/账本全经文件传递 —— 路径可能含非 ASCII, 不经
命令行;不 import 主循环 store/state/config)
"""
import argparse
import os
import sys
import time
from typing import Optional

from ..core import fastresume
from ..infra import relocate_journal as rj
from .finalize_watch import (  # 三证判据原样复用(finalize_watch 退役后由本模块继承)
    STABLE_WINDOW,
    _port_refused,
    _proc_absent,
    _qb_process_names,
)

HEARTBEAT_INTERVAL = 10.0  # daemon.json 心跳周期(D12: 每 10s touch)
HEARTBEAT_MAX_AGE = 60.0  # 心跳过期线(对账判挂死/重拉的口径, 与旧 guardian 判过期同量级)
POLL_INTERVAL = 5.0  # 主循环节拍(也是窗口内失败重试的节拍, D8)
GRACE_EXIT = 60.0  # pending 集空后的宽限退出时长(D12)


def _window_open(host: str, port: int) -> bool:
    """窗口开启判据的瞬时复验 = 证一+证二(进程不在 + 端口拒连; 证三「稳定 30s」只在
    进窗时要求一次, 见 run)。名册现读不用快照: qB 可能在任何毫秒起身 —— N1 铁律的
    守门粒度 = 每次落盘之前(与 guardian run 循环同款两证合取)。"""
    return _proc_absent(_qb_process_names(), host, port) and _port_refused(host, port)


class _Owner:
    """daemon.json(pid/ts)的归属与心跳编排(协议原语单点在 relocate_journal, 本类只做
    节流与判定; Windows 残留锁/进程探测的坑都在 _alive 单点里, 此处不重复)。"""
    def __init__(
        self, data_dir: str, key: str, pid: int, host: str = "", port: int = 0, heartbeat: float = HEARTBEAT_INTERVAL
    ):
        self.data_dir = data_dir
        self.key = key
        self.pid = int(pid)
        self.host = str(host or "")
        self.port = int(port or 0)
        self.heartbeat = float(heartbeat)
        self._last_touch: Optional[float] = None

    def claim(self, now: float, max_age: float) -> str:
        """pid 抢占: 现存记录是健康 watcher(心跳未过期且 pid 活, daemon_stale 判据单点)
        ⇒ already_running 让路(至多一个 watcher, D12);否则(无记录/记录 pid 已死/心跳
        过期)落自己的 pid 接管 —— 旧主(若还醒着)在下一次自检看见外来 pid 即退位自杀。
        """
        if not rj.daemon_stale(self.data_dir, self.key, max_age=max_age, now=now):
            return "already_running"
        rj.write_daemon_state(self.data_dir, self.key, self.pid, host=self.host, port=self.port, ts=now)
        self._last_touch = now
        return "claimed"

    def beat(self, now: float) -> bool:
        """每拍归属自检 + 节流心跳 touch; False = 已被退位(记录 pid 非我)⇒ 调用方自杀退出。
        记录缺失(异常消失)⇒ touch 重新落盘认主(daemon 不因账文件消失而白死)。"""
        cur = rj.read_daemon_state(self.data_dir, self.key)
        if cur is not None and int(cur.get("pid") or 0) != self.pid:
            return False
        if self._last_touch is None or now - self._last_touch >= self.heartbeat:
            if not rj.touch_daemon_state(self.data_dir, self.key, self.pid, ts=now):
                return False
            self._last_touch = now
        return True

    def release(self) -> bool:
        return rj.release_daemon_state(self.data_dir, self.key, self.pid)


def _scan_jobs(data_dir: str, host: str, port: int) -> list:
    """扫本实例的待收尾 job(「窗口开头现读 pending 集」与主循环节拍共用的入口)。

    口径: spec 属本实例(host/port 字面相等, 不做 localhost/127.0.0.1 智能匹配)且带
    bt_backup 字段(新链 opt-in; 旧链 spec 无此字段不归本模块); journal 已终态
    (done/cancelled)的 job 跳过 —— 取消/收口即时生效(D12)。src/dst 缺项的残缺 spec
    跳过(arm 侧责任, daemon 不猜)。
    返回 [{job_id, spec, pending, flip}]; flip = pending 空 + 改写账非空 + 相位未翻
    (窗口中崩溃错过翻相)⇒ 主循环补翻 rewritten。
    """
    out = []
    for job_id in rj.list_spec_jobs(data_dir):
        spec = rj.read_spec(data_dir, job_id)
        if not isinstance(spec, dict):
            continue
        if str(spec.get("host") or "") != str(host or ""):
            continue
        try:
            spec_port = int(spec.get("port") or 0)
        except (TypeError, ValueError):
            spec_port = 0
        if spec_port != int(port or 0):
            continue
        if not str(spec.get("bt_backup") or "").strip():
            continue
        if not str(spec.get("src") or "").strip() or not str(spec.get("dst") or "").strip():
            continue
        journal = rj.read_journal(data_dir, job_id) or {}
        if str(journal.get("phase") or "") in rj.STOP_PHASES:
            continue
        rewrites = journal.get("rewrites") if isinstance(journal.get("rewrites"), dict) else {}
        pending = rj.pending_members(spec, rewrites)
        out.append(
            {
                "job_id": job_id,
                "spec": spec,
                "pending": pending,
                "flip": not pending and bool(rewrites) and str(journal.get("phase") or "") != rj.PHASE_REWRITTEN,
            }
        )
    return out


def _rewrite_member(spec: dict, member: dict, prev: Optional[dict]) -> dict:
    """单成员改写 + 记账构造(纯构造不落账; 落账由调用方走 record_rewrites 单点)。

    记账取舍(already/unmatched 按语义入账, 见 REWRITE_SETTLED):
    - written -> rewritten(双键已落盘, 逐键明细随账)
    - unchanged 且有键 already -> already(已在目标值: 幂等重放证据 —— 出账, 否则重放
      永不收敛, 违反黄金法则 1)
    - unchanged 且纯 unmatched(含无任何路径键) -> unmatched(确定性无操作: 全部路径键
      都不命中旧根, 含 N10 相对路径形态 —— 重放无意义; 真错向由主循环重启后逐成员
      save_path 核验兜住(S4), 账留逐键明细供诊断) —— 出账
    - not_found / FastresumeError/ValueError/OSError -> not_found/failed: 不出账,
      fails 计数承前累计 +1(每失败一次进一账), 窗口内随拍重试(D8)、下一窗口重放
    """
    backup = str(spec.get("bt_backup") or "")
    old_root = str(spec.get("src") or "")
    new_root = str(spec.get("dst") or "")
    h1 = str(member.get("hash_v1") or "")
    h2 = str(member.get("hash_v2") or "")
    fails = int((prev or {}).get(rj.REWRITE_FAILS_KEY) or 0)
    try:
        report = fastresume.retarget(backup, h1, h2, old_root, new_root)
    except (fastresume.FastresumeError, ValueError, OSError) as e:
        return {"status": "failed", "error": str(e), rj.REWRITE_FAILS_KEY: fails + 1}
    if report.status == "written":
        return {
            "status": "rewritten",
            "path": report.path or "",
            "keys": list(report.rewritten),
            "already": list(report.already),
            "unmatched": list(report.unmatched),
            rj.REWRITE_FAILS_KEY: fails,
        }
    if report.status == "not_found":
        return {"status": "not_found", rj.REWRITE_FAILS_KEY: fails + 1}
    if report.already:
        return {
            "status": "already",
            "path": report.path or "",
            "keys": list(report.already),
            "unmatched": list(report.unmatched),
            rj.REWRITE_FAILS_KEY: fails,
        }
    return {
        "status": "unmatched",
        "path": report.path or "",
        "keys": [],
        "unmatched": list(report.unmatched),
        rj.REWRITE_FAILS_KEY: fails,
    }


def _process_window(
    data_dir: str,
    jobs: list,
    owner: _Owner,
    host: str,
    port: int,
    *,
    started: float,
    max_wait: float,
    poll: float,
    clock=time.time,
    sleep=time.sleep
) -> str:
    """一个下线窗口的改写会话(D8: 每窗口限一轮会话; 窗口内失败重试至成功或 qB 回升)。

    每拍/每次落盘前的闸门(顺序即成本序):
      1. 归属(beat): 被退位 ⇒ deposed(自杀, 未落盘的成员留给新主/下一窗口);
      2. pending 现读: journal 已终态的 job 剔除(取消/收口即时生效), 已收口成员出账;
      3. 全收口 ⇒ settled(相位翻正交给主循环拍间 scan 的 flip);
      4. 窗口仍开(瞬时两证: 进程不在 + 端口拒连)—— 任一证失守 = qB 有生命迹象 ⇒
         立即放弃本轮(qb_back; N4: 已写成员经别名正常加载, 未写成员 journal 待重放)。
    """
    while True:
        now = clock()
        if not owner.beat(now):
            return "deposed"
        if max_wait and now - started > max_wait:
            return "timeout"
        remaining = []
        for job in jobs:
            journal = rj.read_journal(data_dir, job["job_id"]) or {}
            if str(journal.get("phase") or "") in rj.STOP_PHASES:
                continue
            rewrites = journal.get("rewrites") if isinstance(journal.get("rewrites"), dict) else {}
            pend = rj.pending_members(job["spec"], rewrites)
            if pend:
                remaining.append((job, pend))
        if not remaining:
            return "settled"
        if not _window_open(host, port):
            return "qb_back"
        for job, pend in remaining:
            job_id = job["job_id"]
            for member in pend:
                now = clock()
                if not owner.beat(now):
                    return "deposed"
                if not _window_open(host, port):
                    return "qb_back"
                journal = rj.read_journal(data_dir, job_id) or {}
                if str(journal.get("phase") or "") in rj.STOP_PHASES:
                    break  # 本 job 已收口(取消): 剩余成员全跳
                prev = journal.get("rewrites") if isinstance(journal.get("rewrites"), dict) else {}
                mkey = rj.member_key(member)
                rec = _rewrite_member(job["spec"], member, prev.get(mkey))
                if not rj.record_rewrites(data_dir, job_id, {mkey: rec}, ts=now, pid=owner.pid):
                    break  # 拒写 = 对账刚收口: 放弃本 job(下拍 scan 剔除)
        sleep(poll)


def run(
    data_dir: str,
    host: str,
    port: int,
    *,
    stable: float = STABLE_WINDOW,
    poll: float = POLL_INTERVAL,
    grace: float = GRACE_EXIT,
    heartbeat: float = HEARTBEAT_INTERVAL,
    max_wait: float = 0.0,
    clock=time.time,
    sleep=time.sleep
) -> str:
    """daemon 主循环; 返回结论(供 CLI 与测试断言)。

    - already_running: 本实例已有健康 watcher(心跳未过期且 pid 活) —— 不重复拉起;
    - idle: pending 集空持续 grace 秒(无事可做/已全收口) ⇒ 宽限退出;
    - deposed: daemon.json 记录 pid 非我(被新主抢占) ⇒ 自检自杀, 绝不恋战;
    - timeout: max_wait 到点(0 = 不限, 窗口内同样生效) —— pending 原样保留, 对账续拉。
    收敛不变量: 窗口外零 fastresume 落盘(三证进窗 + 每次落盘前瞬时两证复验); journal
    是唯一账面, 任一退出路径都留一致账态, 下一窗口可重放(D8/N4)。
    """
    key = rj.instance_key(host, port)
    owner = _Owner(data_dir, key, os.getpid(), host, port, heartbeat=heartbeat)
    started = clock()
    if owner.claim(clock(), HEARTBEAT_MAX_AGE) == "already_running":
        return "already_running"
    down_since = 0.0
    grace_since = 0.0
    try:
        while True:
            now = clock()
            if not owner.beat(now):
                return "deposed"
            jobs = _scan_jobs(data_dir, host, port)
            pending_any = False
            for job in jobs:
                if job["pending"]:
                    pending_any = True
                elif job["flip"]:
                    # 全员已收口而相位未翻(窗口中崩溃/错过翻相)⇒ 补翻 rewritten; 拒写 =
                    # 对账已收口(终态), 下拍 scan 自然剔除 —— journal 写不限窗口(D13)
                    rj.record_rewrites(data_dir, job["job_id"], {}, phase=rj.PHASE_REWRITTEN, ts=now, pid=owner.pid)
            if not pending_any:
                if not grace_since:
                    grace_since = now
                elif now - grace_since >= grace:
                    return "idle"
            else:
                grace_since = 0.0
                names = _qb_process_names()
                down = _proc_absent(names, host, port) and _port_refused(host, port)
                if down:
                    if not down_since:
                        down_since = now
                    if now - down_since >= stable:
                        outcome = _process_window(
                            data_dir,
                            jobs,
                            owner,
                            host,
                            port,
                            started=started,
                            max_wait=max_wait,
                            poll=poll,
                            clock=clock,
                            sleep=sleep
                        )
                        down_since = 0.0
                        if outcome in ("deposed", "timeout"):
                            return outcome
                        continue  # settled/qb_back: 回主循环重扫(pending 决定续等或宽限退出)
                else:
                    down_since = 0.0
            if max_wait and now - started > max_wait:
                return "timeout"
            sleep(poll)
    finally:
        owner.release()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="fastresume 收尾回收 daemon(等 qB 下线窗口批量改写)")
    ap.add_argument("--data-dir", required=True, help="运行时数据目录(与 config.data_dir 同源)")
    ap.add_argument("--host", required=True, help="qB 实例 host(与 spec/journal 字面相等判定)")
    ap.add_argument("--port", type=int, required=True, help="qB 实例 port")
    ap.add_argument("--stable", type=float, default=STABLE_WINDOW)
    ap.add_argument("--poll", type=float, default=POLL_INTERVAL)
    ap.add_argument("--grace", type=float, default=GRACE_EXIT)
    ap.add_argument("--heartbeat", type=float, default=HEARTBEAT_INTERVAL)
    ap.add_argument("--max-wait", type=float, default=0.0, help="最长运行秒数(0 = 不限)")
    args = ap.parse_args(argv)
    result = run(
        args.data_dir,
        args.host,
        args.port,
        stable=args.stable,
        poll=args.poll,
        grace=args.grace,
        heartbeat=args.heartbeat,
        max_wait=args.max_wait,
    )
    key = rj.instance_key(args.host, args.port)
    print(
        f"recycle_daemon: instance {args.host}:{args.port} -> {result}"
        f"(daemon.json: {rj.daemon_state_path(args.data_dir, key)})"
    )
    return 0 if result in ("idle", "deposed", "already_running") else 1


if __name__ == "__main__":
    sys.exit(main())
