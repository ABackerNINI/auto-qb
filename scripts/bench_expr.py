"""规则条件表达式性能基准(dev-only): 把"表达式条件到底多贵"从感觉变成数字

三层测量(口径见 docs/plans/26-09-20-2225-rule-conditions-expression-plan.html 第 07 节):

  ① **编译**   M 条规则的 parse + 语义校验总耗时 —— 只在启动时做一次, 不在热路径
  ② **单次求值** 按复杂度分档各跑 K 次取**中位数**(不取平均: 平均会被 GC/调度尖刺带跑)
  ③ **一轮总耗时** N 种子 × M 规则跑完整一轮条件评估 —— 决定「能不能用 interval: 0S」的数字

关键前提(不守这三条, 测出来的数字没有意义)
------------------------------------------
- **freespace() 必须打桩**: 否则测到的是磁盘 I/O, 不是表达式
- **昂贵值有 ctx 缓存**: 同一个 ctx 里第二次 freespace 命中缓存, 所以一轮里的
  首轮与稳态不是一个数 —— 脚本直接给"一轮"的实测(生产就是每个规则新建 ctx)
- **RuleContext 构造单独计一行基线**: 生产每条规则执行都会新建 ctx, 这部分开销与
  表达式无关, 单列出来才能看出净增量

不做什么
--------
- **时间断言不进单测**: 本机与 CI、Windows 与 WSL 之间必然 flaky(项目已栽过一次) ——
  基准是给人看的; 「缓存/短路有没有生效」由 test_expr_eval.py 的**计数断言**钉住(确定性)
- 不连真实 qB(合成种子 + FakeClient), 不碰生产配置

用法
----
    uv run python scripts/bench_expr.py --torrents 3000 --rules 20
    uv run python scripts/bench_expr.py --rules 4 --repeat 5000 --json bench.json

参数
----
    --torrents N   合成种子数(默认 3000)
    --rules M      规则数(默认 20)
    --repeat K     单次求值分档的重复次数(默认 2000)
    --json PATH    额外把结果写成 JSON(供计划文档引用)
"""
import argparse
import json
import os
import platform
import shutil
import statistics
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from auto_qb.rules.base import RuleContext  # noqa: E402
from auto_qb.rules.conditions import (  # noqa: E402
    SeedtimeCondition,
    SizeCondition,
    StateCondition,
    UploadRatioCondition,
)
from auto_qb.rules.expr import compile_expr, evaluate, validate  # noqa: E402
from auto_qb.torrents import TorrentRecord  # noqa: E402
from tests.helpers import FakeClient, make_manager  # noqa: E402

_GIB = 1024**3

# 分档: (名字, 表达式)。t2 含 freespace(打桩后仍走缓存与短路逻辑)
TIERS = (
    ("单比较", "tor.size >= 10GiB"),
    ("四层括号", "(((tor.size >= 100MiB) and (tor.seeding_time < 24H)) and (tor.ratio > 1.5)) and (tor.is_uploading)"),
    ("含盘空间", "(freespace(tor.save_path) < 200GiB) and (tor.size > 50GiB)"),
    ("含时间", "(sys.dow <= 5) and ((sys.time_of_day >= 22:30) or (sys.time_of_day <= 7:00))"),
    ("含全局计数", "(sys.torrent_count > 1) and (tor.uploaded > 10GiB)"),
)

# 旧条件基线: 4 个条件插件 == 上面"四层括号"那条表达式的能力
LEGACY = (
    SizeCondition(">=100MiB"),
    SeedtimeCondition("<24H"),
    UploadRatioCondition(">1.5"),
    StateCondition("is_uploading"),
)
LEGACY_EXPR = TIERS[1][1]


def _stub_disk():
    """给 freespace 打桩: 固定返回 500GiB 剩余, 并计数(顺带验证缓存生效)"""
    calls = []

    def fake_usage(path):
        calls.append(path)
        return shutil._ntuple_diskusage(500 * _GIB, 100 * _GIB, 400 * _GIB)

    shutil.disk_usage = fake_usage
    return calls


def _make_torrents(n: int):
    """合成种子(真 TorrentRecord: 与生产同一取值路径)"""
    recs = []
    for i in range(n):
        rec = TorrentRecord(
            hash=f"h{i}",
            name=f"Torrent {i}",
            size=(i % 50 + 1) * _GIB,
            total_size=(i % 50 + 1) * _GIB,
            state="uploading",
            uploaded=(i % 20) * _GIB,
            downloaded=(i % 20) * _GIB,
            ratio=1.0 + (i % 30) / 10,
            seeding_time=(i % 10) * 86400,
            tags="a,b" if i % 3 else "c",
            category="cat",
            save_path="/data",
            content_path=f"/data/Torrent {i}",
            added_on=0,
            last_activity=0,
        )
        recs.append(rec)
    return recs


def _new_ctx(mgr, tor, client):
    ctx = RuleContext(mgr, client, mgr.config, tor.hash, dry_run=True)
    ctx.manager.store.by_hash.setdefault(tor.hash, tor)
    return ctx


def _bench_compile(rules: int) -> dict:
    exprs = [TIERS[i % len(TIERS)][1] for i in range(rules)]
    start = time.perf_counter()
    for text in exprs:
        validate(compile_expr(text).root)
    total_ms = (time.perf_counter() - start) * 1000
    return {"rules": rules, "total_ms": round(total_ms, 3), "per_rule_us": round(total_ms * 1000 / max(1, rules), 1)}


def _bench_single(mgr, tor, client, repeat: int) -> list:
    rows = []
    for name, text in TIERS:
        root = compile_expr(text).root
        validate(root)
        ctx = _new_ctx(mgr, tor, client)
        for _ in range(50):  # warmup
            evaluate(root, ctx)
        samples = []
        for _ in range(repeat):
            ctx = _new_ctx(mgr, tor, client)  # 每次新 ctx: 与生产一致(缓存不复用)
            t0 = time.perf_counter()
            evaluate(root, ctx)
            samples.append((time.perf_counter() - t0) * 1e6)
        rows.append(
            {
                "tier": name,
                "median_us": round(statistics.median(samples), 3),
                "p95_us": round(sorted(samples)[int(len(samples) * 0.95)], 3),
            }
        )
    return rows


def _bench_round(mgr, torrents, client, rules: int) -> dict:
    """一轮: N 种子 × M 规则(每条规则新建 ctx, 与生产一致)"""
    exprs = [compile_expr(TIERS[i % len(TIERS)][1]).root for i in range(rules)]
    for e in exprs:
        validate(e)

    start = time.perf_counter()
    for tor in torrents:
        for root in exprs:
            evaluate(root, _new_ctx(mgr, tor, client))
    expr_ms = (time.perf_counter() - start) * 1000

    # 基线一: 只构造 ctx 不求值(这部分开销与表达式无关)
    start = time.perf_counter()
    for tor in torrents:
        for _ in exprs:
            _new_ctx(mgr, tor, client)
    ctx_ms = (time.perf_counter() - start) * 1000

    # 基线二: 等价的旧条件(4 个插件 == 一条四层括号表达式)
    legacy_root = compile_expr(LEGACY_EXPR).root
    start = time.perf_counter()
    for tor in torrents:
        ctx = _new_ctx(mgr, tor, client)
        for _ in range(rules):
            all(c.match(ctx) for c in LEGACY)
    legacy_ms = (time.perf_counter() - start) * 1000

    count = len(torrents) * rules
    return {
        "evals": count,
        "expr_total_ms": round(expr_ms, 2),
        "ctx_only_ms": round(ctx_ms, 2),
        "expr_net_ms": round(expr_ms - ctx_ms, 2),
        "us_per_eval": round((expr_ms - ctx_ms) * 1000 / max(1, count), 3),
        "legacy_total_ms": round(legacy_ms, 2),
        "legacy_us_per_eval": round(legacy_ms * 1000 / max(1, count), 3),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="规则条件表达式性能基准(dev-only)")
    ap.add_argument("--torrents", type=int, default=3000, help="合成种子数(默认 3000)")
    ap.add_argument("--rules", type=int, default=20, help="规则数(默认 20)")
    ap.add_argument("--repeat", type=int, default=2000, help="单次求值重复次数(默认 2000)")
    ap.add_argument("--json", default="", help="额外把结果写成 JSON")
    args = ap.parse_args()

    disk_calls = _stub_disk()
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        torrents = _make_torrents(args.torrents)
        for tor in torrents:
            mgr.store.by_hash[tor.hash] = tor

        result = {
            "env": {
                "python": platform.python_version(),
                "platform": platform.platform(),
            },
            "params": {
                "torrents": args.torrents,
                "rules": args.rules,
                "repeat": args.repeat
            },
            "compile": _bench_compile(args.rules),
            "single": _bench_single(mgr, torrents[0], client, args.repeat),
            "round": _bench_round(mgr, torrents, client, args.rules),
            "disk_calls": len(disk_calls),
        }

    env, params = result["env"], result["params"]
    print(f"\n环境: Python {env['python']} / {env['platform']}")
    print(f"参数: {params['torrents']} 种子 × {params['rules']} 规则, 单次重复 {params['repeat']} 次\n")

    c = result["compile"]
    print("① 编译(启动期一次)")
    print(f"    {c['rules']} 条规则共 {c['total_ms']} ms   单条 {c['per_rule_us']} µs\n")

    print("② 单次求值(每次新建 ctx, 中位数 / p95)")
    for row in result["single"]:
        print(f"    {row['tier']:<10} {row['median_us']:>8.3f} µs   p95 {row['p95_us']:>8.3f} µs")
    print()

    r = result["round"]
    print("③ 一轮总耗时")
    print(f"    求值次数            {r['evals']}")
    print(f"    表达式总耗时        {r['expr_total_ms']} ms")
    print(f"    其中 ctx 构造基线   {r['ctx_only_ms']} ms")
    print(f"    净表达式耗时        {r['expr_net_ms']} ms   ({r['us_per_eval']} µs/次)")
    print(f"    旧条件(4 插件)对照  {r['legacy_total_ms']} ms   ({r['legacy_us_per_eval']} µs/次)")
    print(f"    freespace 打桩调用  {result['disk_calls']} 次(缓存生效则应远小于求值次数)\n")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"已写出 {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
