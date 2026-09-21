"""仿真测试驱动器: 起仿真客户端 + 拉起真实 auto-qb 子进程 + 出两层日志

一次运行 = 一个场景。产出:
  <root>/runs/<时间戳-场景>/
      summary.json / summary.txt   统计层: verdict + checks(每项自带阈值与结论)
      trace.jsonl / writes.jsonl / sim-events.jsonl / fs-before.txt / fs-after.txt
      autoqb.log                   完整层(auto-qb 子进程输出全文)

用法:
    python scripts/sim_run.py --scenario P3 --n 5000 --duration 60
    python scripts/sim_run.py --scenario S1 --n 500 --duration 20 --dry-run
    python scripts/sim_run.py --scenario D4 --n 500 --duration 40 --delete-files 5:0

统计层设计要点(见计划第 07 节): 每项 check 自带 `值 + op + 阈值 + result`;
阈值未固化时记 BASELINE 而非 FAIL(否则首次跑满屏红, 反而掩盖真问题);
BASELINE 不计入 verdict。
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import sim_qb
from sim_qb import SimQb, SimServer, make_run_dir, emit_config

# 未固化阈值 -> BASELINE(不算 FAIL)
BASELINE = "BASELINE"

# W4 固化后的阈值表: sim_baseline.py 生成, 键 = check id。文件不存在则全记 BASELINE。
BASELINE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "plans",
    "26-09-19-1433-sim-client-5000.baseline.json"
)

# 由 main() 在启动时填充(读 baseline.json); 未固化时为空 -> 相关项记 BASELINE
THRESH: dict = {}


def load_thresholds(path: str | None = None) -> dict:
    """读固化阈值; 缺文件或 --no-baseline 时返回空表(所有未显式给阈值的项记 BASELINE)"""
    if path is None:
        path = BASELINE_PATH
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        th = d.get("thresholds")
        return th if isinstance(th, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    i = min(len(s) - 1, int(round((len(s) - 1) * q)))
    return s[i]


def collect_sync_metrics(run_dir: str, boundaries: tuple[float, ...] = (), tick: float = 2.0) -> dict:
    """从 trace.jsonl 还原 sync 轮次时间线: 间隔 / 漂移 / 载荷

    boundaries: 相位切换时刻(两相运行时新进程重启)。跨边界的那个间隔是**进程重启**造成的,
    不是稳态抖动, 必须剔除 —— 否则 drift_max 直接飙到 1.8s 假红。
    """
    ts, sizes, changed = [], [], []
    tp = os.path.join(run_dir, "trace.jsonl")
    if not os.path.exists(tp):  # auto-qb 启动即失败(如配置校验不过)时没有 trace
        return {
            "rounds": 0,
            "first_round_s": 0.0,
            "avg_interval_s": 0.0,
            "p95_interval_s": 0.0,
            "drift_max_s": 0.0,
            "avg_bytes": 0,
            "max_bytes": 0,
            "changed_per_round": 0,
            "last_ts": None
        }
    for line in open(tp, encoding="utf-8"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("e") == "sync/maindata":
            ts.append(r["ts"])
            sizes.append(r.get("b", 0))
    gaps = [b - a for a, b in zip(ts, ts[1:]) if not any(a < m < b for m in boundaries)]
    # ❗首轮(第 1 个间隔)必须单列: 灌入 N 个种子时它包含 files 拉取 + maintenance 立即执行,
    # 实测 5000 种子约 17 s。混进稳态漂移会让每次跑都假红, 反而掩盖真正的稳态问题。
    first = round(gaps[0], 3) if gaps else 0.0
    steady = gaps[1:] if len(gaps) > 1 else []
    return {
        "rounds": len(ts),
        "first_round_s": first,
        "avg_interval_s": round(sum(steady) / len(steady), 3) if steady else 0.0,
        "p95_interval_s": round(_pct(steady, 0.95), 3),
        # ❗基准是**本次的 main_tick**, 不是写死的 2.0: --tick 1.5 时会把 0.5 s 的正常间隔算成漂移
        "drift_max_s": round(max([abs(g - tick) for g in steady], default=0.0), 3),
        "avg_bytes": int(sum(sizes) / len(sizes)) if sizes else 0,
        "max_bytes": max(sizes, default=0),
        "changed_per_round": 0,
        "last_ts": ts[-1] if ts else None,
    }


def collect_writes(run_dir: str) -> list[dict]:
    p = os.path.join(run_dir, "writes.jsonl")
    if not os.path.exists(p):
        return []
    out = []
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def stopped_hashes(writes: list[dict]) -> set[str]:
    """写台账里被 stop/pause 过的 hash 集合(D4 判据用)"""
    out = set()
    for w in writes:
        if w["endpoint"] in ("torrents/stop", "torrents/pause"):
            raw = str(w.get("params", {}).get("hashes") or "")
            out.update(x for x in raw.replace(",", "|").split("|") if x)
    return out


def hashes_of(w: dict) -> set[str]:
    """一条写台账涉及的 hash 集合"""
    raw = str(w.get("params", {}).get("hashes") or "")
    return {x for x in raw.replace(",", "|").split("|") if x}


def scan_log(path: str) -> dict:
    """完整层日志的快速体检: 只数异常信号, 不替代人工回溯

    traceback / CRITICAL 是硬信号(进程出错); ERROR 只计数(未配置站点等会正常报),
    阈值未固化前记 BASELINE。
    """
    out = {"tracebacks": 0, "critical": 0, "error": 0, "lines": 0}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            out["lines"] += 1
            if "Traceback (most recent call last)" in line:
                out["tracebacks"] += 1
            elif " CRITICAL " in line or "CRITICAL:" in line:
                out["critical"] += 1
            elif " ERROR " in line or "ERROR:" in line:
                out["error"] += 1
    return out


def graceful_stop(proc: subprocess.Popen, grace: float = 12) -> int:
    """优雅停 auto-qb: 让它走 KeyboardInterrupt -> finally -> save_state()

    ❗直接 terminate()/kill() 在 Windows 上是 TerminateProcess —— 进程没有机会跑 finally,
    state.json 永远不落盘, D5「状态持久化」判据就成了空转(实测: 目录里只有 state.lock)。
    CTRL_BREAK_EVENT 会触发 Python 的 KeyboardInterrupt, 才会走到 save_state()。
    """
    sig = getattr(signal, "CTRL_BREAK_EVENT", None)
    if sig is not None:
        try:
            proc.send_signal(sig)
            proc.wait(timeout=grace)
            return proc.returncode
        except (subprocess.TimeoutExpired, OSError, ValueError):
            pass
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    return -1


# auto-qb 允许在 data_dir 里写的东西: 状态(含原子写的备份) / 日志 / WEB 密钥 / 单实例锁
DATA_ALLOWLIST = frozenset(
    {
        "state.json",
        "state.json.bak",
        "autoqb.log",
        "web.token",
        "state.lock",
        "state.lock.meta.json",
        "state.lock.meta.json.bak",
    }
)


def data_dir_files(run_dir: str) -> set[str]:
    d = os.path.join(run_dir, "data")
    if not os.path.isdir(d):
        return set()
    return {f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))}


def poll_web(
    web_port: int,
    samples: list[dict],
    stop_ev: threading.Event,
    interval: float = 0.5,
    quiesce: threading.Event | None = None
):
    """S7: 并发轮询 WEB UI, 只做只读请求 —— 记状态码与耗时, Web 线程不得产生写台账"""
    while not stop_ev.is_set():
        if quiesce is not None and quiesce.is_set():
            stop_ev.wait(interval)
            continue
        for path in ("/api/status", "/api/state?rid=-1"):
            t0 = time.time()
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{web_port}{path}", timeout=3) as r:
                    code = r.status
                    r.read()
            except urllib.error.HTTPError as e:
                code = e.code
            except Exception:
                code = 0  # 连不上/未就绪, 与真实 HTTP 错误区分
            samples.append({"ts": time.time(), "path": path, "code": code, "ms": round((time.time() - t0) * 1000, 1)})
        stop_ev.wait(interval)


def exec_history_size(run_dir: str) -> int:
    """state.json 里 exec_history 的条目数(D5 跨进程幂等的判据载体)

    execute_once=once 的规则每命中一个种子留一条 `rule:hash`; 第二相若 state 真生效,
    一个都不该新增。读不到(文件不存在/损坏)返回 -1。
    """
    p = os.path.join(run_dir, "data", "state.json")
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        return -1
    h = d.get("exec_history")
    return len(h) if isinstance(h, dict) else 0


def wait_web_ready(web_port: int, timeout: float = 40) -> dict | None:
    """等 auto-qb 自带 WEB UI 就绪(loopback 免密钥)"""
    url = f"http://127.0.0.1:{web_port}/api/status"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(0.4)
    return None


def observe_web(
    web_port: int,
    series: list[dict],
    stop_ev: threading.Event,
    interval: float = 1.0,
    quiesce: threading.Event | None = None
):
    """轮询 /api/status 拿 auto-qb 快照规模

    ❗这是 D1/D2/D5 唯一**非空**的观测通道: 仅看写台账会测假 —— 打标签是一次性的
    (state_file 记过就不再写), 种子被删后 auto-qb 若留幽灵, 写台账上根本看不出来。
    """
    while not stop_ev.is_set():
        # 停机前先静默: 否则请求会被掐在半路, uvicorn 回 400 时连接已关 -> h11 异常栈
        if quiesce is not None and quiesce.is_set():
            stop_ev.wait(interval)
            continue
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{web_port}/api/status", timeout=2) as r:
                d = json.loads(r.read())
                series.append({"ts": time.time(), "torrents": d.get("torrents"), "groups": d.get("groups")})
        except Exception:
            pass
        stop_ev.wait(interval)


def post_web_cmd(web_port: int, path: str, body: dict) -> dict:
    """向 auto-qb WEB UI 投递命令(loopback + skip_local_verify 免鉴权)"""
    req = urllib.request.Request(
        f"http://127.0.0.1:{web_port}{path}",
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def build_checks(
    sim: SimQb, args, writes: list[dict], sync: dict, stopped: set[str], logscan: dict, web_results: list[dict],
    snaps: list[dict], rc: int, hist_sizes: list[int], polls: list[dict], data_after: set[str]
) -> list[dict]:
    c: list[dict] = []

    def add(cid, value, op, threshold, note=""):
        if threshold is None:
            threshold = THRESH.get(cid)  # 未显式给 -> 查 W4 固化表; 仍无 -> BASELINE
        if value is None or threshold is None:
            result = BASELINE  # 未观测到 / 阈值未固化 -> 都不算失败
        elif op == "==":
            result = "PASS" if value == threshold else "FAIL"
        elif op == "<=":
            result = "PASS" if value <= threshold else "FAIL"
        elif op == ">=":
            result = "PASS" if value >= threshold else "FAIL"
        else:
            result = BASELINE
        c.append({"id": cid, "value": value, "op": op, "threshold": threshold, "result": result, "note": note})

    n_writes = len(writes)
    # S1 dry-run 零写(硬判据)
    if args.dry_run:
        add("S1.dryrun_writes", n_writes, "==", 0, "--dry-run 下写端点必须 0 命中")
    else:
        add("S1.dryrun_writes", n_writes, "==", None, "非 dry-run: 仅记录, 无阈值")

    # S2 高风险端点; D3 会**有意**触发 torrents/delete, 那部分单独豁免(其余仍须 0)
    risky = {e: sim.stats["endpoint_hits"].get(e, 0) for e in sorted(sim_qb.RISK_ENDPOINTS)}
    intentional = {"torrents/delete"} if web_results else set()
    add(
        "S2.risky_endpoints", sum(v for e, v in risky.items() if e not in intentional), "==", 0,
        "除有意触发外, delete/setLocation/reannounce/recheck/add 必须 0 命中"
    )

    # S3 写速率(阈值待固化 -> BASELINE)
    mins = max(args.duration, 1) / 60
    add("S3.write_rate_per_min", round(n_writes / mins, 1), "<=", None, "稳态写速率, 待 W4 固化基线")

    # rid 语义: 全量轮次应 <= 进程数(更多说明 rid 失效退化成每轮全量)
    add(
        "SYNC.full_rounds", sim.stats["sync_full_rounds"], "<=", max(1, len(hist_sizes)),
        "首轮之外再出现全量 = rid 语义失效(每轮多 200ms+)"
    )

    # 首轮一次性成本(灌入 N 个种子: files 拉取 + maintenance 立即执行)
    add("P1.first_round_s", sync["first_round_s"], "<=", None, "首轮一次性成本, 待固化基线; 稳态不受影响")

    # tick 跟随(稳态)
    add("SYNC.avg_interval_s", sync["avg_interval_s"], "<=", None, "稳态 main_tick 跟随, 待固化基线")
    # P2(--ramp 渐进灌入) / --stress(人为打满)下"掉拍"是**要观测的现象**而非失败:
    # 换 id 记 BASELINE, 免得用稳态阈值把它判红, 反而把"跟不上"这个结论埋掉。
    # 只有"纯主循环"(无灌入 / 无 WEB 并发轮询 / 非压力档)才拿稳态漂移当硬判据;
    # 带 WEB 负载时漂移本来就该变差, 那是**观测对象**, 混进阈值反而放走真正的回归。
    if args.ramp or args.stress or args.web_poll:
        add("P2.drift_max_s", sync["drift_max_s"], "<=", None, "灌入期 / 带 WEB 轮询的漂移(观测项, 与纯主循环基线对比用)")
    else:
        add("SYNC.drift_max_s", sync["drift_max_s"], "<=", THRESH.get("SYNC.drift_max_s", 1.0), "纯主循环稳态单轮漂移上限(已排除首轮)")

    # 优雅停机: rc=0 说明走完 finally(save_state 已落盘); 非 0 多为被硬杀
    add("RUN.graceful_exit", rc, "==", 0, "auto-qb 必须优雅退出, 否则 state_file 不落盘")

    # 完整层日志体检(硬信号)
    add("LOG.tracebacks", logscan["tracebacks"], "==", 0, "auto-qb 子进程日志中的异常栈")
    add("LOG.critical", logscan["critical"], "==", 0, "CRITICAL 级日志")

    # B4 文件核账
    fs = sim.reconcile()
    add("B4.fs_unexpected_removals", len(fs["unexpected_removals"]), "==", 0, "文件树只允许出现预期删除")

    # ---------------- D1: 快照一致性(auto-qb 自己的种子数 == 仿真端剩余) ----------------
    # ❗唯一非空判据: 写台账看不出幽灵(打标签一次性), 必须直接问 auto-qb 快照里还有几个
    if snaps:
        final = snaps[-1]["torrents"]
        peak = max((x["torrents"] for x in snaps if x["torrents"] is not None), default=None)
        add(
            "D1.snapshot_final_match", final == len(sim.torrents), "==", True,
            f"auto-qb 快照 {final} 个 vs 仿真端剩余 {len(sim.torrents)} 个; 不等 = 幽灵种子"
        )
        if peak is not None:
            add(
                "D1.snapshot_drop", peak - final, "==", len(sim.removed_all),
                f"峰值 {peak} -> 终值 {final}; 应恰好等于删除总数 {len(sim.removed_all)}"
            )
    else:
        add("D1.snapshot_final_match", None, "==", None, "未开 WEB UI(--web-port): 无观测通道, 该项空转")

    # ---------------- D1/D2: 外部删除种子(带/不带文件) ----------------
    if sim.removed_all:
        grace = max(3 * args.tick, 5.0)  # auto-qb 要到下一轮 sync 才知道种子没了
        ev_ts = None
        for r in sim.events:
            if r.get("kind") == "delete_torrents":
                ev_ts = r["ts"]
                break
        if ev_ts:
            ghosts = [w for w in writes if w["ts"] > ev_ts + grace and (hashes_of(w) & sim.removed_all)]
            add("D1.writes_to_removed", len(ghosts), "==", 0, f"宽限 {grace:.0f}s 后仍对已删种子发写请求 = 快照残留幽灵")
        # 文件侧: 只有 with-files 才允许少文件(外部注入 + WEB 命令删除都算)
        with_files = (
            any(spec[2] for spec in (args.delete_torrents or [])) or any(r.get("delete_files") for r in web_results)
        )
        dropped = fs["files_before"] - fs["files_after"]
        if with_files:
            add("D2.files_dropped", dropped, ">=", 1, "删种子带文件: 文件必须真的少")
        else:
            add("D2.files_dropped", dropped, "==", 0, "删种子不带文件: 一个文件都不能少")

    # ---------------- D3: auto-qb 主动删除(WEB 命令路径) ----------------
    if web_results:
        ok = sum(1 for r in web_results if r.get("queued"))
        add("D3.cmd_queued", ok, "==", len(web_results), "WEB 删除命令必须全部投递成功")
        # sim 侧收到的 torrents/delete 必须: 恰好目标 hash / deleteFiles 与命令一致
        dels = [w for w in writes if w["endpoint"] == "torrents/delete"]
        want = {r["hash"]: r["delete_files"] for r in web_results}
        got: dict[str, bool] = {}
        for w in dels:
            for h in hashes_of(w):
                got[h] = str(w.get("params", {}).get("deleteFiles", "false")).lower() in ("true", "1", "yes")
        add("D3.delete_hashes_exact", sorted(got) == sorted(want), "==", True, "只允许删命令指定的 hash(多删/少删都是安全问题)")
        add("D3.delete_files_flag_match", got == want, "==", True, "deleteFiles 参数必须与 WEB 命令逐 hash 一致")
        add("D3.delete_count", len(dels), "==", len(want), f"删除请求数({len(dels)}) == 命令数({len(want)}); 多于命令数 = 重复删除")

    # ---------------- S6: 数据面只读(data_dir 只多出白名单内的文件) ----------------
    unexpected_data = sorted(data_after - DATA_ALLOWLIST)
    add(
        "S6.data_dir_unexpected", len(unexpected_data), "==", 0,
        f"data_dir 只允许 {sorted(DATA_ALLOWLIST)}; 实际 {sorted(data_after)}"
    )

    # ---------------- S7: WEB 并发只读 ----------------
    if polls:
        errs = [p for p in polls if p["code"] >= 400]
        add("S7.http_errors", len(errs), "==", 0, f"并发轮询 {len(polls)} 次, 4xx/5xx 必须 0(离线未就绪记为 code=0, 不计)")
        add("S7.requests", len(polls), ">=", 1, "否则本组判据空转")
        add("S7.p95_ms", _pct([p["ms"] for p in polls if p["code"]], 0.95), "<=", None, "WEB 只读端点 p95 耗时, 待 W4 固化基线")

    # ---------------- S8: 限速保护 ----------------
    if sim.manual_limits:
        add("S8.manual_limits_seeded", len(sim.manual_limits), ">=", 1, "否则下一条空转")
        changed = [h for h, v in sim.manual_limits.items() if h in sim.torrents and sim.torrents[h]["up_limit"] != v]
        add("S8.manual_limits_intact", len(changed), "==", 0, "手设单种限速(奇数 KiB/s)不得被改写")
        upl = sum(1 for w in writes if w["endpoint"] == "torrents/setUploadLimit")
        add("S8.set_upload_limit_writes", upl, "==", 0, "默认配置下不得改写手设限速")

    # ---------------- S5: 断连降级 ----------------
    if args.abort_after:
        st = next((r["ts"] for r in sim.events if r.get("kind") == "abort_start"), None)
        en = next((r["ts"] for r in sim.events if r.get("kind") == "abort_recover"), None)
        en = en or (time.time() if st else None)
        if st:
            during = [w for w in writes if st < w["ts"] < en]
            add("S5.writes_during_outage", len(during), "==", 0, "断连期间一个写请求都不该发出(发不出去, 更不该重试风暴)")
            # 恢复后必须靠全量轮重建快照(rid 断层被 sim 人为制造)
            if args.abort_duration:
                add(
                    "S5.full_update_after_recover", sim.stats["sync_full_rounds"], ">=",
                    max(1, len(hist_sizes)) + 1, "恢复后必须再走一次全量自愈; 否则快照停留在断连前"
                )
            add(
                "S5.outage_survived", 1 if sync["last_ts"] and sync["last_ts"] > st else 0, "==", 1,
                "断连后必须恢复同步(不得卡死/退出)"
            )

    # ---------------- D5: 批量删除 + 幂等 ----------------
    if args.redeliver_removed:
        ev_ts = None
        for r in sim.events:
            if r.get("kind") == "redeliver_removed":
                ev_ts = r["ts"]
                break
        if ev_ts and sync["last_ts"]:
            add(
                "D5.sync_after_redeliver", 1 if sync["last_ts"] > ev_ts else 0, "==", 1,
                "重复投递 torrents_removed 后必须继续正常同步(不得崩/卡死)"
            )
    # 跨进程幂等: 第二相不得重跑 execute_once=once 的规则(依 state_file 去重)
    if len(hist_sizes) >= 2:
        # ❗硬 kill 会拿不到 state.json(hist=-1), 此时不能静默跳过, 必须判红
        add("D5.state_file_present", hist_sizes[0] >= 0, "==", True, "第一相结束时 state.json 必须已落盘且可解析")
        add("D5.exec_history_seeded", hist_sizes[0], ">=", 1, "第一相必须真的命中过规则(否则下一条是空转)")
        if hist_sizes[0] >= 0 and hist_sizes[1] >= 0:
            add(
                "D5.exec_history_growth", hist_sizes[1] - hist_sizes[0], "==", 0, "第二相新增执行数; >0 = state_file 去重失效(或没落盘)"
            )
    st_path = os.path.join(sim.run_dir, "data", "state.json")
    if os.path.exists(st_path):
        try:
            json.load(open(st_path, encoding="utf-8"))
            add("D5.state_file_valid", True, "==", True, "state_file 必须是可解析 JSON(状态持久化)")
        except (json.JSONDecodeError, OSError):
            add("D5.state_file_valid", False, "==", True, "state_file 损坏")

    # D4: 外部删文件 -> 缺文件保护(组内成员必须一个不漏地全停)
    if args.delete_files:
        gi = args.delete_files[0][1]
        members = sim.groups[gi] if gi < len(sim.groups) else []
        if members:
            rate = round(sum(1 for h in members if h in stopped) / len(members), 3)
            add("D4.group_stop_rate", rate, "==", 1.0, f"辅种组 #{gi} 成员停止率; <1.0 即会向站点上传垃圾数据")

            # 响应延迟: 注入时刻 -> 最后一个成员被停的时刻, 折算 tick 数
            ev_ts = None
            for r in sim.events:
                if r.get("kind") == "delete_files":
                    ev_ts = r["ts"]
                    break
            last = max(
                (
                    w["ts"] for w in writes if w["endpoint"] in ("torrents/stop", "torrents/pause") and
                    any(h in str(w.get("params", {}).get("hashes") or "") for h in members)
                ),
                default=None
            )
            lag = round((last - ev_ts) / max(args.tick, 0.1), 2) if (ev_ts and last) else None
            add("D4.group_stop_lag_ticks", lag, "<=", 3, "从文件消失到整组停完经过的 tick 数")
    return c


def verdict_of(checks: list[dict]) -> tuple[str, list[str]]:
    fails = [x["id"] for x in checks if x["result"] == "FAIL"]
    warns = [x["id"] for x in checks if x["result"] == "WARN"]
    if fails:
        return "FAIL", fails
    if warns:
        return "WARN", warns
    return "OK", []


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="auto-qb 仿真测试驱动器")
    p.add_argument("--scenario", default="P3", help="场景 ID(仅用于标记与目录命名)")
    p.add_argument("--root", default=os.environ.get("AUTOQB_SIM_ROOT") or sim_qb.DEFAULT_ROOT)
    p.add_argument("--n", type=int, default=5000)
    p.add_argument("--beat", type=float, default=1.5)
    p.add_argument("--active", type=float, default=0.10)
    p.add_argument("--mode", choices=("churn", "steady"), default="churn")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--tick", type=float, default=2.0, help="auto-qb main_tick(写入生成的配置)")
    p.add_argument("--duration", type=float, default=60)
    p.add_argument("--dry-run", action="store_true", help="auto-qb 以 --dry-run 运行(测 S1)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=0)
    p.add_argument("--delete-files", nargs="*", default=[], help="'K:G' 第 K 拍删第 G 个辅种组文件")
    p.add_argument("--delete-torrents", nargs="*", default=[], help="'K:N[:with-files]'")
    p.add_argument("--redeliver-removed", type=int, default=0, help="第 K 拍重复投递已删 hash(D5 幂等)")
    p.add_argument("--abort-after", type=float, default=0, help="S5: N 秒后 sim 断连")
    p.add_argument("--abort-duration", type=float, default=0, help="S5: 断连持续秒数; 0=断到结束")
    p.add_argument("--web-port", type=int, default=0, help=">0 时开启 auto-qb 自带 WEB UI 并监听该端口(D3 主动删除)")
    p.add_argument("--web-delete", type=int, default=0, help="D3: 经 WEB UI 删除 N 个种子(一半带文件一半不带); 需 --web-port")
    p.add_argument("--two-phase", action="store_true", help="D5: 连跑两轮 auto-qb(共用 state_file), 验跨进程幂等")
    p.add_argument("--with-rules", action="store_true", help="注入一条 execute_once=once 的规则(D5 幂等的判据载体)")
    p.add_argument("--interval", type=int, default=60, help="config.interval(秒)")
    p.add_argument("--web-poll", type=int, default=0, help="S7: N 个线程并发只读轮询 WEB UI(需 --web-port)")
    p.add_argument("--ramp", type=int, default=0, help="P2 渐进灌入: 每拍新增种子数; 0=首轮全量")
    p.add_argument("--fs-materialize", type=int, default=-1)
    p.add_argument("--latency-ms", type=float, default=0, help="仿真 qB 每个请求的人为延迟(模拟真机负载; 见 sim_qb.py 同名参数)")
    p.add_argument("--keep-last", type=int, default=10)
    p.add_argument("--autoqb-args", default="", help="附加给 auto-qb 的参数")
    # ---- 语料回放透传(计划 §07/§12: 语料位置与回放 root 全部显式传入, 不写死) ----
    p.add_argument("--source", default="synthetic", help="synthetic(默认, 对照档) | corpus:<dir>(语料目录)")
    p.add_argument("--fs-root", default="", help="mock 层根目录; 默认 <root>/runs/<run-id>/fs")
    p.add_argument("--fs-mode", choices=("mock", "real"), default="", help="磁盘事实来源; 默认语料档 mock / 合成档 real")
    p.add_argument("--command-latency-ms", type=float, default=750.0, help="命令效果对两个端点都延后的毫秒数(默认 750 = W0 真机实测)")
    p.add_argument(
        "--maindata-lag-ms", type=float, default=0.0, help="sync/maindata 相对 torrents/info 的额外滞后(默认 0 = W0 实测)"
    )
    p.add_argument("--replay-speed", type=float, default=1.0, help="录播回放倍速(W4)")
    p.add_argument("--latency-mode", choices=("recorded", "p50", "p95", "const"), default="recorded")
    p.add_argument("--baseline", default="", help="固化阈值文件路径(默认 docs/plans/…baseline.json)")
    p.add_argument("--no-baseline", action="store_true", help="不读固化阈值(全部记 BASELINE)")
    p.add_argument("--stress", action="store_true", help="标记为压力档: 漂移等只观测不判红(否则会盖住真实稳态回归)")
    args = p.parse_args(argv)

    THRESH.clear()
    if not args.no_baseline:
        THRESH.update(load_thresholds(args.baseline or None))

    args.delete_files = sim_qb.parse_spec(args.delete_files, 2)
    args.delete_torrents = sim_qb.parse_spec(args.delete_torrents, 3)
    args.run_id = time.strftime("%Y%m%d-%H%M%S") + f"-{args.scenario}"
    args.read_only = False
    args.fs_file_size = 4096

    sim, srv = sim_qb.create_sim(args)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"[run] sim 起于 {args.host}:{port} | 种子 {len(sim.torrents)} | "
          f"辅种组 {len(sim.groups)} | run={sim.run_dir}")

    cfg = emit_config(
        sim.run_dir, sim, port, web_port=args.web_port, with_rules=args.with_rules, interval=args.interval
    )
    # 驱动器统一用 --tick 覆盖配置里的 main_tick
    text = open(cfg, encoding="utf-8").read().replace("main_tick: 2S", f"main_tick: {args.tick:g}S")
    open(cfg, "w", encoding="utf-8").write(text)

    # 负载引擎
    stop = threading.Event()
    threading.Thread(target=sim_qb.run_load_engine, args=(sim, stop), daemon=True).start()

    # D1/D2/D5 的观测通道 + D3 的命令通道: 都走 auto-qb 自带 WEB UI
    web_results: list[dict] = []
    web_th = None
    snaps: list[dict] = []
    polls: list[dict] = []
    obs_stop = threading.Event()
    quiesce = threading.Event()  # 停机前置位: 让观测/轮询先收手, 避免半截请求
    if args.web_port:
        threading.Thread(target=observe_web, args=(args.web_port, snaps, obs_stop, 1.0, quiesce), daemon=True).start()
        for _ in range(max(0, args.web_poll)):  # S7 并发只读轮询
            threading.Thread(target=poll_web, args=(args.web_port, polls, obs_stop, 0.5, quiesce), daemon=True).start()
    if args.web_delete:
        grouped: set[str] = set()
        for g in sim.groups:
            grouped.update(g)
        # 只挑非辅种组成员: 组内删除会触发缺文件保护的连锁暂停, 判据就不干净了
        cand = [h for h in sim.torrents if h not in grouped][:args.web_delete]
        targets = [(h, i >= (len(cand) + 1) // 2) for i, h in enumerate(cand)]
        print(f"[run] D3 目标: {len(targets)} 个种子(带文件 {sum(1 for _, f in targets if f)})")

        def _web_driver():
            st = wait_web_ready(args.web_port, timeout=max(5.0, min(args.duration * 0.5, 60)))
            if st is None:
                print(f"[run] WARN: auto-qb WEB UI(:{args.web_port}) 未就绪, D3 无结果", file=sys.stderr)
                return
            for h, df in targets:
                try:
                    r = post_web_cmd(args.web_port, f"/api/torrents/{h}/delete", {"delete_files": df})
                    web_results.append({"hash": h, "delete_files": df, "queued": bool(r.get("queued"))})
                except (urllib.error.URLError, OSError, ValueError) as e:
                    web_results.append({"hash": h, "delete_files": df, "queued": False, "err": str(e)})

        web_th = threading.Thread(target=_web_driver, daemon=True)

    # ❗走 sim_autoqb.py 包装启动(装 SIGBREAK 处理器), 否则只能硬 kill -> state_file 不落盘
    cmd = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "sim_autoqb.py"), cfg]
    if args.dry_run:
        cmd.append("--dry-run")
    if args.autoqb_args:
        cmd += args.autoqb_args.split()
    log_path = os.path.join(sim.run_dir, "autoqb.log")
    print(f"[run] auto-qb: {' '.join(cmd[1:])}")
    # 语料档 + mock: 把 FS mock 通过**环境变量**注入 auto-qb 子进程(不占 argv, 免得动到它的参数解析)。
    # 时间源归播放器: mock 按秒拉 GET /api/v2/_fsmock/state, 保持"播放器是唯一时间源"。
    child_env = dict(os.environ)
    if getattr(sim, "corpus_mode", False) and sim.fs_mode == "mock":
        child_env["AUTOQB_FSMOCK_ROOT"] = sim.fs_root
        child_env["AUTOQB_FSMOCK_PLAYER"] = f"http://{args.host}:{port}/api/v2/_fsmock/state"
        # 初值文件: 消除"auto-qb 首轮早于 mock 首次轮询"的竞态(否则首轮在空表上跑 => 全部文件当成缺失)
        state_file = getattr(sim, "fsmock_state_file", "")
        if state_file and os.path.isfile(state_file):
            child_env["AUTOQB_FSMOCK_STATE"] = state_file
        print(
            f"[run] FS mock: root={sim.fs_root} player={child_env['AUTOQB_FSMOCK_PLAYER']} "
            f"init={os.path.basename(state_file) if state_file else '(无)'}"
        )
    t0 = time.time()
    # Windows: 需要独立进程组才能发 CTRL_BREAK(否则只能硬 kill, 拿不到 state_file)
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    data_before = data_dir_files(sim.run_dir)  # S6: 启动前 data_dir 快照
    phases = 2 if args.two_phase else 1
    phase_dur = args.duration / phases
    hist_sizes: list[int] = []
    boundaries: list[float] = []
    rc = 0
    for i in range(phases):
        mode = "w" if i == 0 else "a"
        with open(log_path, mode, encoding="utf-8", errors="replace") as lf:
            if i:
                lf.write(f"\n===== phase {i + 1} (新进程, 复用 state_file) =====\n")
            proc = subprocess.Popen(
                cmd, stdout=lf, stderr=subprocess.STDOUT, text=True, creationflags=flags, env=child_env
            )
            if web_th and i == 0:
                web_th.start()
            try:
                proc.wait(timeout=phase_dur)
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                quiesce.set()  # 先让观测/轮询收手
                time.sleep(0.8)
                rc = graceful_stop(proc)
                quiesce.clear()
        hist_sizes.append(exec_history_size(sim.run_dir))
        boundaries.append(time.time())  # 相位切换点: 下一个间隔是重启造成的, 不计入稳态漂移
        print(f"[run] phase {i + 1}/{phases} rc={rc} exec_history={hist_sizes[-1]}")
    elapsed = time.time() - t0
    stop.set()
    srv.shutdown()
    obs_stop.set()
    if web_th:
        web_th.join(timeout=5)
    time.sleep(0.3)  # 等观测线程写完最后一批样本

    writes = collect_writes(sim.run_dir)
    sync = collect_sync_metrics(sim.run_dir, tuple(boundaries[:-1]), args.tick)
    logscan = scan_log(log_path)
    data_after = data_dir_files(sim.run_dir) - data_before
    checks = build_checks(
        sim, args, writes, sync, stopped_hashes(writes), logscan, web_results, snaps, rc, hist_sizes, polls, data_after
    )
    verdict, triggers = verdict_of(checks)

    risky = {e: sim.stats["endpoint_hits"].get(e, 0) for e in sorted(sim_qb.RISK_ENDPOINTS)}
    by_ep = dict(sorted(sim.stats["endpoint_hits"].items(), key=lambda kv: -kv[1]))
    summary = {
        "verdict": verdict,
        "triggers": triggers,
        "scenario":
            {
                "id": args.scenario,
                "n": args.n,
                "beat": args.beat,
                "active": args.active,
                "mode": args.mode,
                "tick": args.tick,
                "seed": args.seed,
                "dry_run": args.dry_run,
                "ramp": args.ramp,
                "web_poll_threads": args.web_poll,
                "duration_s": args.duration,
                "elapsed_s": round(elapsed, 1),
                "autoqb_rc": rc,
            },
        "checks": checks,
        "sync": sync,
        "writes":
            {
                "total": len(writes),
                "per_min": round(len(writes) / max(args.duration / 60, 1 / 60), 1),
                "by_endpoint": by_ep,
                "risky": risky,
            },
        "fs": sim.reconcile(),
        "log": logscan,
        "web_commands": web_results,
        "removed_torrents": len(sim.removed_all),
        "snapshot_series": snaps[-40:],
        "web_poll":
            {
                "requests": len(polls),
                "errors": sum(1 for p in polls if p["code"] >= 400),
                "p95_ms": _pct([p["ms"] for p in polls if p["code"]], 0.95) if polls else 0.0,
            },
        "data_dir_new": sorted(data_after),
        "violations": sim.violations,
        "run_dir": sim.run_dir,
        "root": args.root,
    }
    with open(os.path.join(sim.run_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 统计层文本: 一眼能判读
    lines = [
        f"verdict: {verdict}", f"scenario: {args.scenario} n={args.n} "
        f"beat={args.beat} active={args.active} mode={args.mode} seed={args.seed}",
        f"elapsed: {elapsed:.1f}s  autoqb_rc: {rc}", "", "checks:"
    ]
    for x in checks:
        th = "—" if x["threshold"] is None else x["threshold"]
        lines.append(f"  {x['result']:<8} {x['id']:<28} value={x['value']} "
                     f"{x['op']} {th}")
    lines += [
        "", f"sync: rounds={sync['rounds']} full={sim.stats['sync_full_rounds']} "
        f"avg_interval={sync['avg_interval_s']}s drift_max={sync['drift_max_s']}s "
        f"avg_bytes={sync['avg_bytes']}",
        f"writes: total={len(writes)} per_min={summary['writes']['per_min']} risky={risky}",
        f"fs: before={summary['fs']['files_before']} after={summary['fs']['files_after']} "
        f"unexpected={len(summary['fs']['unexpected_removals'])}",
        f"log: lines={logscan['lines']} tracebacks={logscan['tracebacks']} "
        f"critical={logscan['critical']} error={logscan['error']}"
    ]
    if sim.violations:
        lines += ["", "violations:"] + [f"  {v}" for v in sim.violations]
    txt = "\n".join(lines)
    with open(os.path.join(sim.run_dir, "summary.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    print("\n" + txt)
    print(f"\n[run] 产物目录: {sim.run_dir}")
    sim_qb.prune_runs(args.root, args.keep_last)
    return 0 if verdict == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
