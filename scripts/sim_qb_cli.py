"""sim_qb CLI 装配: 参数 / 运行目录 / 配置生成 / 引擎启动(从 sim_qb.py 原样搬迁)"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import threading
import time

from sim_qb_core import *  # noqa: F401,F403
from sim_qb_model import SimQb
from sim_qb_server import SimServer, fallback_root, prepare_root

# ---------- CLI ----------


def parse_spec(s: list[str] | None, arity: int) -> list[tuple]:
    """--delete-torrents 'K:N[:with-files]' / --delete-files 'K:G'"""
    out = []
    for item in (s or []):
        parts = str(item).split(":")
        if len(parts) < arity:
            raise SystemExit(f"格式错误: {item}")
        if arity == 3:
            out.append((int(parts[0]), int(parts[1]), str(parts[2]).lower() in ("1", "true", "yes")))
        else:
            out.append((int(parts[0]), int(parts[1])))
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="qBittorrent WebUI 仿真客户端")
    p.add_argument("--root", default=os.environ.get("AUTOQB_SIM_ROOT") or DEFAULT_ROOT)
    p.add_argument("--run-id", default="")
    p.add_argument("--n", type=int, default=5000)
    p.add_argument("--beat", type=float, default=1.5)
    p.add_argument("--active", type=float, default=0.10)
    p.add_argument("--mode", choices=("churn", "steady"), default="churn")
    p.add_argument("--ramp", type=int, default=0, help="每拍新增种子数; 0=首轮全量")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=0, help="0=随机端口")
    p.add_argument("--duration", type=float, default=0, help="运行秒数; 0=不限")
    p.add_argument("--read-only", action="store_true", help="写端点回 403 但仍记账(dry-run 硬断言)")
    p.add_argument("--abort-after", type=float, default=0, help="N 秒后断连(测重连自愈)")
    p.add_argument("--abort-duration", type=float, default=0, help="断连持续秒数; 0=一直断。到点自动恢复并把 rid 断层(逼客户端走全量自愈)")
    p.add_argument("--delete-torrents", nargs="*", default=[], help="'K:N[:with-files]'")
    p.add_argument("--delete-files", nargs="*", default=[], help="'K:G' 第 K 拍删第 G 个辅种组文件")
    p.add_argument(
        "--redeliver-removed", type=int, default=0, help="第 K 拍把已删 hash 重新投递一次(测幂等: 重复 torrents_removed 不得炸)"
    )
    p.add_argument(
        "--latency-ms",
        type=float,
        default=0,
        help="每个请求的人为延迟(模拟真机上有负载的 qB)。默认 0 —— 本地请求 ~0.5ms 时主循环永远"
        "不饱和, '命令排队 wait_ms' 恒为 0, 真机上'点了要等 2-4s'这类缺陷复现不出来",
    )
    p.add_argument("--fs-materialize", type=int, default=-1, help="-1=全量(默认); 0=不建树")
    p.add_argument("--fs-file-size", type=int, default=4096)
    p.add_argument("--keep-last", type=int, default=10)
    p.add_argument("--emit-config", action="store_true", help="在 run 目录生成匹配的 config.yml")
    # ---- 语料回放(计划 26-09-21-0024 §07/§12: 语料位置与回放 root 全部参数化, 不写死) ----
    p.add_argument(
        "--source",
        default="synthetic",
        help="synthetic(默认, 保留为对照档) | corpus:<dir>(语料目录; 位置显式传入, 不写死)",
    )
    p.add_argument(
        "--fs-mode",
        choices=("mock", "real"),
        default="",
        help="磁盘事实来源: mock(默认, 进程内 FS mock, 不物化任何文件) | real(真建文件树, 仅用于复核 mock)",
    )
    p.add_argument("--fs-root", default="", help="mock 层根目录; 默认 <root>/runs/<run-id>/fs")
    p.add_argument(
        "--command-latency-ms",
        type=float,
        default=750.0,
        help="命令效果对**两个端点**都延后的毫秒数。默认 750 = W0 真机实测(mean 733 / median 751, n=12); "
        "真机实测 Δ(torrents/info − sync/maindata) = +1 ms, 即滞后是 qB 命令处理延迟、两端共享",
    )
    p.add_argument(
        "--maindata-lag-ms",
        type=float,
        default=0.0,
        help="sync/maindata 相对 torrents/info 的**额外**滞后(默认 0 = W0 实测)。"
        "计划原文默认 1500 并假设 info 更快, W0 实测推翻了该前提; 调大它可做'直查更快'的受控实验(红验落点)",
    )
    p.add_argument("--replay-speed", type=float, default=1.0, help="录播回放倍速(W4)")
    p.add_argument(
        "--latency-mode",
        choices=("recorded", "p50", "p95", "const"),
        default="recorded",
        help="延迟注入方式: recorded(默认, 用录到的真实 rtt) | p50/p95 | const:N(--latency-ms)",
    )
    p.add_argument("--self-test", action="store_true", help="跑内置自检(真实 qbittorrent-api 往返)")
    return p


def make_run_dir(root: str, run_id: str) -> str:
    if not run_id:
        run_id = time.strftime("%Y%m%d-%H%M%S") + "-run"
    d = os.path.join(root, "runs", run_id)
    os.makedirs(d, exist_ok=True)
    return d


def prune_runs(root: str, keep: int) -> int:
    runs = os.path.join(root, "runs")
    if not os.path.isdir(runs) or keep <= 0:
        return 0
    items = sorted(os.listdir(runs))
    removed = 0
    for name in items[:-keep]:
        p = os.path.join(runs, name)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
            removed += 1
    return removed


CONFIG_TMPL = """---
config:
    interval: {interval}S
    main_tick: {tick}S
    max_tasks_per_tick: {max_tasks}
    state_file: "{state_file}"
    remove_similar_tags: false
    skip_checking_tag: {skip_checking_tag}
    hr:
        add_tag: ""
        add_category: "!!HR${{required_seeding_time}}!!"
        overwrite_category: false
        add_tag_for_satisfied: ""
        add_category_for_satisfied: --HR${{required_seeding_time}}--
        overwrite_category_for_satisfied: false
    grouping:
        enabled: true
        missing_tag: {missing_tag}
        check_missing_files: true
    qbittorrent:
        host: "{host}"
        port: "{port}"
        username: "{user}"
        password: "{password}"
    log:
        level: INFO
        file: "{log_file}"
        max_bytes: 50MiB
{web}{rules}    trackers:
{trackers}
"""

WEB_TMPL = """    web:
        enabled: true
        host: "127.0.0.1"
        port: {web_port}
        token: "sim-token"
        skip_local_verify: true
"""

# D5 幂等用: execute_once=once 的规则 + 无副作用的 print_torrent_details 动作。
# 它会在 state.json 的 exec_history 里给每个命中种子留一条记录 —— 第二相(新进程)必须
# 靠这条记录跳过, 一个都不许重跑。state 若没落盘, 第二相就会全部重跑 -> 判据立刻变红。
# !规则块必须落在 config: **之内**且键名以 _rules 结尾 —— validate_config 的
# rules_config = {k: v for k, v in cfg.items() if k.endswith("_rules")}; 根节点只认 config。
# (test_stop.yml 里那种顶层写法是旧格式, 现在会被判"根节点未知键")
RULES_TMPL = """    sim_once_rules:
        rule:
            enabled: true
            trigger: interval
            interval: 15S
            execute_once: once
            cooldown: 0S
            conditions:
                - trackers:
                      - ptfans_cc
            actions:
                - print_torrent_details: true
"""

TRACKER_RULES_TMPL = """            rules:
                - "@sim_once_rules.rule"
"""

SYNTHETIC_TRACKERS = """        ptfans_cc:
            domains:
                - ptfans.cc
            tags:
                - PTFans
{rules}        hhanclub:
            domains:
                - tracker.hhanclub.net
            tags:
                - HHan
"""

# 非站点标签(自动生成的通用标签), 派生"站点标签"时要排除掉
_GENERIC_TAG_HINTS = ("MISSING", "zSkipChecked", "辅种", "R")


def corpus_tracker_section(sim: SimQb) -> str:
    """按语料里的真实数据派生 tracker 段(计划 §12 / W3)

    为什么必须派生: 语料里的 tracker 域名已被脱敏成 `site-N.example`、标签也已伪名化。
    若沿用合成档写死的 `ptfans.cc` / `hhanclub`, auto-qb 的站点匹配会全部落空 ⇒
    `tracker_name` 解析不出来 ⇒ 依赖站点的规则与日志全是空转。

    站点标签的推断 —— 取"**对该 host 最专有**"的那个标签: score = 该站出现次数 / 全局出现次数。
    真机上站点标签几乎只出现在本站的种子上(score→1), 而通用标签(MISSING / zSkipChecked / 辅种)
    散布在全库(score 很小)。⇒ 不能按"出现最多"挑, 那会被通用标签抢走。
    (WARN: 标签在语料里已伪名化, 所以**不能**用原始字面量 "MISSING" 之类去排除 —— 只能靠这个统计判据。)

    WARN: 首选 `meta.sanitize_map.tracker_tags`: 抓取端拿用户 config 的 trackers 段算出来的**权威**
    伪域名 ↔ 伪标签映射; 取不到才退回上面的统计派生。两者都只产出**已脱敏**的两侧。
    """
    # !`or {}`: 老语料 / 无映射时 `.get()` 返回 None, 后面再 .get() 会直接 AttributeError
    _corpus = getattr(sim, "corpus", None)
    smap = ((_corpus.meta.get("sanitize_map") or {}) if _corpus else {}) or {}
    auth = smap.get("tracker_tags") or {}
    host_tags: dict[str, dict[str, int]] = {}
    tag_global: dict[str, int] = {}
    for h, t in sim.torrents.items():
        tags = [x.strip() for x in str(t.get("tags") or "").split(",") if x.strip()]
        for tag in tags:
            tag_global[tag] = tag_global.get(tag, 0) + 1
        for tr in (t.get("_trackers_raw") or []):
            url = str(tr.get("url") or "")
            if "://" not in url:
                continue
            host = url.split("://", 1)[1].split("/", 1)[0].split(":", 1)[0]
            if not host:
                continue
            slot = host_tags.setdefault(host, {})
            for tag in tags:
                slot[tag] = slot.get(tag, 0) + 1

    # ---- 输出: 权威映射优先, 覆盖不到的域名退回统计派生, 且只输出语料里真出现过的域名 ----
    # !**不能只信权威映射**: 用户 config 的 `domains:` 字面量与 tracker URL 的 **host 不一定相等**
    #   (auto-qb 的站点匹配是**后缀**匹配, 而这里按 host 精确对表)。实测该映射漏掉了语料里最大的
    #   站点(35 个种子) ⇒ 那些种子因"未匹配 tracker 配置"被 `continue` 跳过(qbmanager.py:685-690),
    #   **连带不参与归组** ⇒ 头号判据 group_exact 从 0 变成 34(真值 63 组只分出 29 组)。
    # !也**不能只信统计**: 站点混用标签时统计会挑错。故**两者合并**: 有权威就用, 没有才统计。
    stat_tag: dict[str, str] = {}
    for host in host_tags:
        counts = host_tags[host]
        best, best_score = None, -1.0
        for tag, n in sorted(counts.items()):
            score = n / max(tag_global.get(tag, 1), 1)
            if score > best_score or (score == best_score and best is not None and n > counts.get(best, 0)):
                best, best_score = tag, score
        if best:
            stat_tag[host] = best
    if not stat_tag and not auth:
        return SYNTHETIC_TRACKERS.format(rules="")
    lines = []
    for host in sorted(stat_tag):
        tag = None
        if host in auth:
            cand = [t for t in (auth[host] or []) if t]
            if cand:
                tag = cand[0]
        if tag is None:
            tag = stat_tag[host]
        key = host.replace(".", "_").replace("-", "_")
        lines.append(
            f"""        {key}:
            domains:
                - {host}
            tags:
                - {tag}
"""
        )
    return "".join(lines) if lines else SYNTHETIC_TRACKERS.format(rules="")


def emit_config(
    run_dir: str, sim: SimQb, port: int, web_port: int = 0, with_rules: bool = False, interval: int = 60
) -> str:
    """生成与仿真端匹配的 auto-qb 配置

    web_port > 0 时开启 auto-qb 自带 WEB UI(D3: 测 auto-qb 主动删除的唯一真实路径;
    skip_local_verify=true 让 loopback 免密钥, 驱动器可直接投递命令)。默认不开 ——
    保持"默认配置不额外开面"的保守默认。

    with_rules 时注入一条 execute_once=once 的规则, 供 D5 验跨进程幂等(默认不注入,
    免得给性能场景掺进规则求值成本)。
    """
    data_dir = os.path.join(run_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    p = os.path.join(run_dir, "config.yml")
    # 语料档: tracker 段必须按语料里的实际域名/标签派生(域已脱敏成 site-N.example), 否则站点匹配全落空
    if getattr(sim, "corpus_mode", False):
        trackers = corpus_tracker_section(sim)
    else:
        trackers = SYNTHETIC_TRACKERS.format(rules=TRACKER_RULES_TMPL if with_rules else "")
    # 语料档: auto-qb 自有标签字面量(MISSING / zSkipChecked)在语料里**已被伪名化**,
    # 必须换成对应伪名 —— 否则跳检/缺文件的行为与真机不一致(该跳的没跳, 判据全绿也是假的)。
    known = {}
    if getattr(sim, "corpus_mode", False) and sim.corpus is not None:
        known = (sim.corpus.meta.get("sanitize_map") or {}).get("known_tags") or {}
    with open(p, "w", encoding="utf-8") as f:
        f.write(
            CONFIG_TMPL.format(
                interval=interval,
                tick=2,
                max_tasks=20,
                state_file=os.path.join(data_dir, "state.json").replace("\\", "/"),
                host=sim.args.host,
                port=port,
                user="sim",
                password="sim",
                log_file=os.path.join(data_dir, "autoqb.log").replace("\\", "/"),
                web=WEB_TMPL.format(web_port=web_port) if web_port else "",
                rules=RULES_TMPL if with_rules else "",
                trackers=trackers,
                skip_checking_tag=known.get("zSkipChecked", "zSkipChecked"),
                missing_tag=known.get("MISSING", "MISSING"),
            )
        )
    return p


def run_load_engine(sim: SimQb, stop: threading.Event):
    """按 beat 变异; abort-after 到点后置 _abort 断连"""
    start = time.time()
    while not stop.is_set():
        stop.wait(sim.args.beat)
        if stop.is_set():
            break
        sim.pump()
        a = sim.args
        if not a.abort_after:
            continue
        if not sim._abort and not sim._abort_done and time.time() - start >= a.abort_after:
            sim._abort = True
            sim._abort_done = True
            sim._abort_until = time.time() + (a.abort_duration or 1e9)
            sim._event("abort_start", {"duration_s": a.abort_duration})
        elif sim._abort and time.time() >= sim._abort_until:
            sim._abort = False
            # !恢复时把 rid 断层(模拟 qB 重启): 客户端手上的旧 rid 必然失配 -> 走全量自愈。
            # 不这么做的话 rid 只是暂停推进, 恢复后仍是增量, 测不到"全量重建"这条路径。
            sim.rid += 1000
            sim._event("abort_recover", {"rid": sim.rid})
    return


def create_sim(args) -> tuple[SimQb, SimServer]:
    """构造仿真端(供 sim_qb 主流程与 sim_run 驱动器共用)"""
    root, why = prepare_root(args.root)
    fallback = None
    if root is None:
        root = fallback_root()
        fallback = why
    args.root = root
    args.run_dir = make_run_dir(root, args.run_id)
    sim = SimQb(args)
    if fallback:
        sim.violations.append(f"ROOT_FALLBACK: {fallback}")
        print(f"[WARN] {fallback} -> {root}", file=sys.stderr)
    return sim, SimServer((args.host, args.port), sim)
