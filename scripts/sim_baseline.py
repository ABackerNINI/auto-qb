"""W4: 跑齐性能矩阵 P1–P7 并把基线固化到 baseline.json

一次运行 = 依次跑 SCENARIOS 里每个场景(每个都是一次完整的 sim_run), 收集统计层
`summary.json` 的关键数字, 按"实测值 × 余量系数"推出建议阈值, 写入:
    docs/plans/26-09-19-1433-sim-client-5000.baseline.json

之后 `sim_run.py` 启动时会自动读这个文件填阈值 —— 未固化时统计层记 BASELINE(不算 FAIL),
固化后同一批指标就成了硬判据, 回归时能真正变红。

用法:
    uv run python scripts/sim_baseline.py                 # 全量(约 6-8 分钟)
    uv run python scripts/sim_baseline.py --only P1,P3    # 只跑部分
    uv run python scripts/sim_baseline.py --dry           # 只打印将执行的命令
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BASELINE_PATH = os.path.join(REPO, "docs", "plans", "26-09-19-1433-sim-client-5000.baseline.json")

# 场景 -> (sim_run 参数, 采集哪些指标, 阈值余量系数)
# 余量系数只用于"越小越好"的指标; 越大越好的(如 D4 停止率)不在这里固化。
SCENARIOS: list[tuple[str, list[str], dict[str, float]]] = [
    ("P1", ["--n", "5000", "--duration", "50"], {
        "P1.first_round_s": 1.5
    }),
    ("P2", ["--n", "5000", "--duration", "50", "--ramp", "200"], {
        "P1.first_round_s": 1.5
    }),
    ("P3", ["--n", "5000", "--duration", "45", "--tick", "2"], {
        "S3.write_rate_per_min": 1.3
    }),
    ("P3b", ["--n", "5000", "--duration", "45", "--tick", "1.5"], {
        "S3.write_rate_per_min": 1.3
    }),
    ("P4", ["--n", "5000", "--duration", "45", "--mode", "steady"], {
        "S3.write_rate_per_min": 1.3
    }),
    # P6 = 真实节奏(单标签页轮询); P6x = 压力档(4 线程打满), 只观测不进阈值
    ("P6", ["--n", "5000", "--duration", "45", "--web-poll", "1"], {
        "S7.p95_ms": 2.0
    }),
    ("P6x", ["--n", "5000", "--duration", "45", "--web-poll", "4", "--stress"], {}),
    ("P7", ["--n", "3000", "--duration", "45", "--delete-torrents", "5:1500:no"], {
        "S3.write_rate_per_min": 1.3
    }),
]


def _trace_counts(run_dir: str) -> dict:
    """从 trace.jsonl 数各端点命中(看首轮灌入是否跑完: files/trackers 是否到 N)"""
    import collections
    p = os.path.join(run_dir, "trace.jsonl")
    if not os.path.exists(p):
        return {}
    c = collections.Counter()
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                c[json.loads(line).get("e")] += 1
            except json.JSONDecodeError:
                pass
    return dict(c.most_common(8))


def run_one(scen: str, extra: list[str], port: int, dry: bool) -> dict | None:
    cmd = [sys.executable, os.path.join(HERE, "sim_run.py"), "--scenario", scen] + extra
    if "--web-port" not in extra:
        cmd += ["--web-port", str(port)]
    print(f"\n{'=' * 70}\n[baseline] {' '.join(cmd[1:])}\n{'=' * 70}", flush=True)
    if dry:
        return None
    t0 = time.time()
    subprocess.run(cmd, cwd=REPO, timeout=300)
    print(f"[baseline] {scen} 用时 {time.time() - t0:.0f}s", flush=True)

    # 找本次运行的 summary.json(按目录名里的场景 ID 定位最新一个)
    root = os.environ.get("AUTOQB_SIM_ROOT") or r"R:\auto-qb-sim"
    cands = sorted(glob.glob(os.path.join(root, "runs", f"*-{scen}", "summary.json")), key=os.path.getmtime)
    if not cands:
        print(f"[baseline] WARN: 找不到 {scen} 的 summary.json", file=sys.stderr)
        return None
    with open(cands[-1], encoding="utf-8") as f:
        return json.load(f)


# 语料档场景: 静态回放(不推进游标) + 时间轴回放。两者都要开 --web-port ——
# 头号判据 CORPUS.group_exact 需要 auto-qb 自己的 WEB 端点才能取到"它实际分的组"。
CORPUS_SCENARIOS: list[tuple[str, list[str]]] = [
    ("C1", ["--replay-speed", "0"]),  # 静态回放: 与 T0 同构, 分组比对最干净
    ("C2", ["--replay-speed", "3"]),  # 时间轴回放: 验游标推进与窗口合并
]

# 语料档需要固化的指标(余量系数): 硬判据(group_exact / fs_state_match / endpoints_covered /
# stream_consumed / maindata_lag_modeled)已在 sim_run 里写死 0/1, 不需要固化。
# ❗`CORPUS.replay_timeline_aligned` **不进固化表**: 它的预算在 sim_run 里按
#   「客户端轮询间隔 × 倍速 × 2 裕度」动态算 —— 固化成常数会在换倍速 / 换轮询档时假红或假绿。
CORPUS_MARGINS: dict[str, tuple[str, float]] = {
    "P1.first_round_s": ("first_round_s", 1.5),
    "S3.write_rate_per_min": ("writes_per_min", 1.3),
    "SYNC.drift_max_s": ("drift_max_s", 1.0),
}


def run_corpus_baseline(args) -> int:
    """跑语料档场景并把 `corpus.*` 阈值合并进 baseline.json"""
    corpus = os.path.abspath(args.corpus)
    if not os.path.isfile(os.path.join(corpus, "meta.json")):
        print(f"[baseline] FATAL: 语料目录里没有 meta.json: {corpus}", file=sys.stderr)
        return 2
    # 首次固化: 把既有(合成档)基线另存一份, 两套来源一眼可分(计划 §09「旧基线另存 synthetic.*」)
    synth_copy = os.path.join(os.path.dirname(BASELINE_PATH), "26-09-19-1433-sim-client-5000.synthetic.json")
    if os.path.exists(BASELINE_PATH) and not os.path.exists(synth_copy) and not args.dry:
        with open(BASELINE_PATH, encoding="utf-8") as f:
            json.dump(json.load(f), open(synth_copy, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[baseline] 合成档基线已另存: {synth_copy}")

    port = args.port + 50  # 避开合成档场景的端口段
    obs: list[dict] = []
    for scen, extra in CORPUS_SCENARIOS:
        cmd_extra = ["--source=corpus:%s" % corpus, "--duration", "25"] + extra
        if "--web-port" not in cmd_extra:
            cmd_extra += ["--web-port", str(port)]
            port += 1
        s = run_one(scen, cmd_extra, port, args.dry)
        if s is None:
            continue
        checks = {c["id"]: c.get("value") for c in s.get("checks") or []}
        obs.append(
            {
                "verdict": s["verdict"],
                "first_round_s": s["sync"]["first_round_s"],
                "writes_per_min": s["writes"]["per_min"],
                "drift_max_s": next((c["value"] for c in s["checks"] if c["id"] == "SYNC.drift_max_s"), 0.0),
                "replay_drift_ms": checks.get("CORPUS.replay_timeline_aligned"),
                "run_dir": s["run_dir"],
            }
        )
        print(
            f"[baseline] {scen}: verdict={s['verdict']} 首轮={obs[-1]['first_round_s']}s "
            f"写={obs[-1]['writes_per_min']}/min 漂移={obs[-1]['drift_max_s']}s "
            f"游标滞后={obs[-1]['replay_drift_ms']}ms",
            flush=True
        )

    if args.dry or not obs:
        return 0
    if any(o["verdict"] != "OK" for o in obs):
        print("[baseline] WARN: 有语料档场景 verdict 非 OK, 阈值仍会固化但请先查明原因", file=sys.stderr)

    th: dict = {}
    if args.merge and os.path.exists(BASELINE_PATH):
        with open(BASELINE_PATH, encoding="utf-8") as f:
            th.update(json.load(f).get("thresholds", {}))
    for cid, (key, margin) in CORPUS_MARGINS.items():
        vals = [o.get(key) for o in obs if isinstance(o.get(key), (int, float))]
        if vals:
            th["corpus." + cid] = round(max(vals) * margin, 2)
    # 漂移再给 0.5 s 的地板(太紧会每次假红)
    if "corpus.SYNC.drift_max_s" in th:
        th["corpus.SYNC.drift_max_s"] = max(1.0, th["corpus.SYNC.drift_max_s"] + 0.5)

    scenarios: dict = {}
    if args.merge and os.path.exists(BASELINE_PATH):
        with open(BASELINE_PATH, encoding="utf-8") as f:
            scenarios.update(json.load(f).get("scenarios", {}))
    scenarios["corpus"] = {"runs": obs}

    out = {
        "_":
            {
                "说明":
                    "仿真测试性能基线。thresholds 里 `corpus.*` 是**语料档**阈值(本脚本 "
                    "--corpus 固化), 裸 id 是合成档阈值; sim_run 在语料档只查 `corpus.` 前缀, "
                    "两套不混用(计划 §09)。首次固化时旧合成档基线另存 *.synthetic.json。",
                "生成时间": time.strftime("%Y-%m-%d %H:%M:%S"),
                "语料": corpus,
            },
        "thresholds": th,
        "scenarios": scenarios,
    }
    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n[baseline] 已写入 {BASELINE_PATH}")
    print(json.dumps({k: v for k, v in th.items() if k.startswith("corpus.")}, ensure_ascii=False, indent=2))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="固化仿真测试的性能基线")
    p.add_argument("--only", default="", help="只跑指定场景, 逗号分隔(如 P1,P3)")
    p.add_argument("--port", type=int, default=18201, help="WEB 观测起始端口")
    p.add_argument("--dry", action="store_true", help="只打印命令不执行")
    p.add_argument("--merge", action="store_true", help="与已有 baseline.json 合并(只覆盖本次重跑的场景)")
    p.add_argument(
        "--corpus",
        default="",
        help="语料目录: 跑**语料档**场景并固化 `corpus.*` 阈值(与合成档两套不混用, 见计划 §09)",
    )
    args = p.parse_args(argv)

    # ---- 语料档基线(计划 W5): 两套阈值不混用 ----
    # 合成档的阈值是在合成数据上固化出来的, 拿去判语料档会同时产生假红与假绿; 故语料档
    # 单独跑、单独固化, 键名带 `corpus.` 前缀(sim_run 在语料档只查这个前缀, 不回落裸 id)。
    # 首次固化时把既有(合成档)基线**另存**一份 ...synthetic.json, 两套来源一眼可分。
    if args.corpus:
        return run_corpus_baseline(args)

    wanted = {x.strip() for x in args.only.split(",") if x.strip()}
    results: dict[str, dict] = {}
    if args.merge and os.path.exists(BASELINE_PATH):
        with open(BASELINE_PATH, encoding="utf-8") as f:
            results.update(json.load(f).get("scenarios", {}))
    port = args.port
    for scen, extra, _margin in SCENARIOS:
        if wanted and scen not in wanted:
            continue
        s = run_one(scen, extra, port, args.dry)
        port += 1
        if s is None:
            continue
        results[scen] = {
            "verdict":
                s["verdict"],
            "n":
                s["scenario"]["n"],
            "tick":
                s["scenario"]["tick"],
            "mode":
                s["scenario"]["mode"],
            "ramp":
                s["scenario"].get("ramp", 0),
            "web_poll_threads":
                s["scenario"].get("web_poll_threads", 0),
            "rounds":
                s["sync"]["rounds"],
            "trackers_requests":
                None,  # 由 trace 统计, 见 _trace_counts
            "_trace":
                _trace_counts(s["run_dir"]),
            "first_round_s":
                s["sync"]["first_round_s"],
            "avg_interval_s":
                s["sync"]["avg_interval_s"],
            # --ramp 场景的漂移记在 P2.drift_max_s 下(非稳态), 这里取得到就取
            "drift_max_s":
                next((c["value"] for c in s["checks"] if c["id"] in ("SYNC.drift_max_s", "P2.drift_max_s")), 0.0),
            "avg_bytes":
                s["sync"]["avg_bytes"],
            "max_bytes":
                s["sync"]["max_bytes"],
            "writes_total":
                s["writes"]["total"],
            "writes_per_min":
                s["writes"]["per_min"],
            "web_p95_ms":
                s.get("web_poll", {}).get("p95_ms", 0.0),
            "run_dir":
                s["run_dir"],
        }
        r = results[scen]
        print(
            f"[baseline] {scen}: verdict={r['verdict']} 首轮={r['first_round_s']}s "
            f"稳态={r['avg_interval_s']}s 漂移={r['drift_max_s']}s "
            f"写={r['writes_per_min']}/min 载荷={r['avg_bytes']}B "
            f"web_p95={r['web_p95_ms']}ms",
            flush=True
        )

    if args.dry or not results:
        return 0

    # ---- 推阈值 ----
    # ❗**常规场景**才进阈值: --ramp(P2)是渐进灌入、P6x 是人为打满的压力档,
    # 它们的数字是"要观测的现象", 拿来当阈值会把真正的稳态回归放过去。
    def normal() -> list[dict]:
        """常规场景: 非 --ramp、非压力档(x 后缀); 可以带真实节奏的 WEB 轮询"""
        return [r for k, r in results.items() if not r.get("ramp") and not k.endswith("x")]

    def steady() -> list[dict]:
        """纯主循环: 常规场景里再排除 WEB 并发轮询(漂移只反映主循环自身健康度)"""
        return [r for r in normal() if not r.get("web_poll_threads")]

    def thresh(margin: float, pick, pool=normal) -> float | None:
        vals = [v for v in (pick(r) for r in pool()) if v]
        return round(max(vals) * margin, 2) if vals else None

    thresholds = {
        "P1.first_round_s": thresh(1.5, lambda r: r["first_round_s"]),
        "S3.write_rate_per_min": thresh(1.3, lambda r: r["writes_per_min"]),
        "S7.p95_ms": thresh(2.0, lambda r: r["web_p95_ms"]),
        # 稳态漂移: 纯主循环实测最大值 + 0.5 s 余量, 且不少于 1.0 s(太紧会每次假红)
        "SYNC.drift_max_s": max(1.0, round(max([r["drift_max_s"] for r in steady()] or [0]) + 0.5, 2)),
    }

    out = {
        "_":
            {
                "说明": "仿真测试性能基线(W4 固化)。thresholds 由实测值×余量系数推出, "
                      "sim_run.py 启动时读取; 不存在时统计层对应项记 BASELINE(不算 FAIL)。",
                "生成时间": time.strftime("%Y-%m-%d %H:%M:%S"),
                "生成命令": "uv run python scripts/sim_baseline.py",
                "机器": "Windows 本机 / R 盘 / 回环 HTTP",
            },
        "thresholds": thresholds,
        "scenarios": results,
    }
    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n[baseline] 已写入 {BASELINE_PATH}")
    print(json.dumps(thresholds, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
