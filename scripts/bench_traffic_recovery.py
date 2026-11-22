"""Benchmark harness for traffic startup recovery (plan 26-11-21-1546 S0 stage).

为什么存在
----------
计划 26-11-21-1546 的 S0 阶段要求: 用同一 harness 钉死「现行实现」的恢复成本矩阵
(3 形态 x 3 场景 x 5000 系列 + 236 生产形态对照), 并在 P1/P2(游程级重建重写 + acc
快照账本)落地后**重跑同一 harness 回填矩阵**。因此本 harness 的硬约束是:

1. 计时走**真实恢复入口**: 构造真实 ``TrafficSampleModule`` + ``AppContext``, 经
   ``module.start(ctx, dry_run=False)`` 驱动 ``_recover_aggregates``(与生产 start()
   钩子同一路径), 不复刻任何恢复逻辑; 模块源码零改动。
2. 语料用**项目自身编解码函数**生成真实格式 v4 天文件(V4Block/V4Sample/V4ZeroRun +
   format_v4_day_text), 三种形态与计划 §02.2 基准同口径。
3. 可重入: 语料一次生成多场景复用; 每 cell 结果实时落 JSON(按 cell 键合并, 同键
   重跑覆盖, 换 impl_tag 追加), 中途失败不丢已完成进度。

场景语义(现行实现 = B1 后, 如实标注)
------------------------------
现行实现下崩溃与优雅重启同路(累计器不落盘, 恢复一律从 raw 重建), 三场景只差
agg.dat 水位形态:
- fresh  水位新鲜: agg 含当日 00:00..18:00 整点 hour 行(相位 19:45 -> 最后封口小时
         18h), 读集 = 水位当日 1 个天文件; B1(plan 26-11-21-1546 S1)后现行实现走
         字节级块定位 + 开放段限定解析 + 记账入口水位过滤 —— 只解析/入账含保留槽位
         的开放段(上下文块整块解析供 tail 接力, 封口块零解析零入账), 计划 §02.1
         缺陷 1 的"过滤后置"已修。
- stale  水位陈旧至昨日: agg 的 hour 行止于昨日 23:00, 读集 = 昨日+今日 2 个天文件。
- fallback 无水位/全量兜底(D4/D5 语义): agg.dat 仅头行+key 行(无可用水位), 读集
         下界 = now - rollup_window(30d), 实际读到语料里存在的全部天文件。
崩溃模拟与优雅重启共用同一语义(如实标注, 不单独设 cell)。

S0 数字口径与回填纪律(评审 P1b-4)
----------------------------------
本 harness 记录的 S0 矩阵数字(计划 §02.2/§03.2 引用)为 **pre-B1 全量口径**(当时实现
= 全文件解析 + 全槽入账 + 尾部丢弃)。B1 落地后回填重跑**必须换新 impl_tag**(如
b1-open-segment)—— 结果按 cell@impl_tag 键追加不覆盖, pre-B1 与 B1 口径的数字不得
混写同键。slots 字段已随 B1 由「slots_credited(入账槽, 全量口径)」更名
「slots_processed(处理槽, B1 开放段口径: 实际解析/记账走过的块槽位, 封口块不计)」,
并在 cell JSON 带 slots_semantics 字段; 旧结果 JSON 里的 slots_credited 是 pre-B1
全量口径, 跨口径对照时注意。

相位口径(与计划 §02.2 相位披露同源)
------------------------------------
语料内容按"生成时刻的当日 19:45 相位"固定: 当日天文件覆盖 [当日 00:00, 19:45),
昨日及更早天文件覆盖整日; cell 运行时的**真实挂钟**只影响 (a) 哪些幸存小时被判
完结(进 catch-up append)哪些进 pending, (b) 裁剪判据 -- 两者都不触及本矩阵计时的
主成本段(读集解析 + 逐槽展开 + 入账)。跨零点重跑 cell 亦内部自洽(读集由水位驱动,
不由挂钟驱动); 相位依赖如实披露, 见计划 §02.2 先例。

语料布局
--------
<out>/qb-traffic-v4/global/<YYYY-MM-DD>.dat + torrents/<40hex sha1>/<YYYY-MM-DD>.dat
天文件行型与生产逐字节同源(项目 codec 序列化); agg.dat 不在 gen 产出(由 run 的
场景准备步骤按 cell 写入, 天文件永不被恢复路径改写, 多场景安全复用)。

子命令
------
gen            生成语料(gen --shape rheavy|zheavy|mixed|prod236 --label L --series N --days D)
run            跑单个 cell(run --corpus <data_dir> --scenario fresh|stale|fallback)
run-matrix     顺序跑一批 cell(逐 cell 进度行 + JSON 实时落盘; 供后台整批执行)
snapshot-stats 只读统计一个真实 v4 存储库(系列/天文件尺寸分布/槽位/日期范围/间隔分布)

用法示例(从仓库根, uv run):
    uv run python scripts/bench_traffic_recovery.py gen --out R:/aqb-traffic-bench/<ts>/corpus-mixed \
        --shape mixed --series 5000 --days 4 --interval 4.0
    uv run python scripts/bench_traffic_recovery.py run-matrix --bench-root R:/aqb-traffic-bench/<ts> \
        --labels mixed,rheavy,zheavy --scenarios fresh,stale,fallback --impl-tag current
    uv run python scripts/bench_traffic_recovery.py snapshot-stats --root "R:/Download/qb-traffic-v4" \
        --out R:/aqb-traffic-bench/<ts>/snapshot-stats.json --emit-spec R:/aqb-traffic-bench/<ts>/prod-spec.json
"""
import argparse
import hashlib
import json
import logging
import os
import random
import sys
import time
from types import SimpleNamespace

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_REPO, os.path.join(_REPO, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from auto_qb.config.models import QbTraffic  # noqa: E402
from auto_qb.core.module import AppContext  # noqa: E402
from auto_qb.core.modules.traffic_sample_mod import TrafficSampleModule  # noqa: E402
from auto_qb.core.traffic_store_paths import v4_acc_ledger_path  # noqa: E402
from auto_qb.core.traffic_store import (  # noqa: E402
    AggRow,
    TrafficV4Store,
    V4Block,
    V4Sample,
    V4ZeroRun,
    format_agg_row,
    format_v4_day_text,
    parse_v4_day_text,
    v4_block_slots,
    v4_date_str_epoch,
    v4_day_epoch,
    v4_day_file_date,
    v4_epoch_date_str,
    v4_series_dir,
)

#: 合成基准的目标"混合构成"日均天文件尺寸(计划 §02.2 mixed 口径 165KB/天文件均值)
MIXED_TARGET_MEAN_DAY_BYTES = 165 * 1024

#: 相位缺省: 当日内容覆盖 [00:00, 19:45) —— 计划 §02.2 "当日 19-20h 相位"口径
DEFAULT_PHASE_HOURS = 19.75

#: fallback 场景 agg.dat 内容(仅头行 + key 行: 无可用水位 -> D5 全量兜底)
FALLBACK_AGG_HEADER_ONLY = True

#: 活跃系列 r 行取值带宽(位宽对齐生产 ~34B/行量级, 见 §02.2 162MB/470 万行)
RATE_DL_BAND = (1_000_000, 9_999_999)
RATE_UP_BAND = (100_000, 999_999)
INC_DL_BAND = (500_000, 9_999_999)
INC_UP_BAND = (50_000, 999_999)

#: 空闲系列 totals 快照(恒定常量, delta 全 0; 取值不影响计时面)
IDLE_TOTALS = (54_321_098_765_432, 8_765_432_109_876)


def _now_ts() -> float:
    return time.time()


def _series_list(series: int, seed: int) -> list:
    """系列键表: global 恒在(首位) + (series-1) 个 torrent:<40hex sha1>(确定性派生)。"""
    keys = ["global"]
    for i in range(series - 1):
        h = hashlib.sha1(f"bench:{seed}:{i}".encode("utf-8")).hexdigest()
        keys.append(f"torrent:{h}")
    return keys


def _active_flags(keys: list, active_frac: float) -> list:
    """逐系列活跃旗标: global 恒活跃; 其余按 deterministic 顺序前 active_n 个活跃。"""
    n_torrent = len(keys) - 1
    n_active = int(round(active_frac * n_torrent))
    return [True] + [i < n_active for i in range(n_torrent)]


def _active_day_blocks(
    day0: int, span_s: float, interval: float, flush_s: float, totals: list, rng: random.Random
) -> list:
    """活跃日块序列: 每 flush_s 一块(块内 r 行按 interval 铺满, 末块可截断), totals 单调
    递增(块基线 = 块首快照, delta 恒非负 —— 与写侧关块状态机同构)。"""
    blocks = []
    t = 0.0
    while t < span_s:
        b_len = min(flush_s, span_s - t)
        rows = int(b_len // interval)
        if rows < 1:
            break
        dl_base, up_base = totals[0], totals[1]
        recs = []
        for _j in range(rows):
            totals[0] += rng.randint(*INC_DL_BAND)
            totals[1] += rng.randint(*INC_UP_BAND)
            recs.append(
                V4Sample(
                    dl_rate=rng.randint(*RATE_DL_BAND),
                    up_rate=rng.randint(*RATE_UP_BAND),
                    dl_total=totals[0],
                    up_total=totals[1],
                )
            )
        blocks.append(
            V4Block(
                start_epoch=day0 + int(t), interval_s=interval, dl_base=dl_base, up_base=up_base, records=tuple(recs)
            )
        )
        t += flush_s
    return blocks


def _idle_day_blocks(day0: int, span_s: float, interval: float, start_off: float = 0.0) -> list:
    """空闲段块序列: 单块单条 z 游程占满 span(显式退化末端对 = 开启快照)。
    start_off > 0 时块头 = day0 + start_off(用于 r-share 混合日的 z 后缀段)。"""
    n = max(1, int(round(span_s / interval)))
    rec = V4ZeroRun(
        run_len=n,
        dl_total=IDLE_TOTALS[0],
        up_total=IDLE_TOTALS[1],
        dl_total_end=IDLE_TOTALS[0],
        up_total_end=IDLE_TOTALS[1],
    )
    return [
        V4Block(
            start_epoch=day0 + int(start_off),
            interval_s=interval,
            dl_base=IDLE_TOTALS[0],
            up_base=IDLE_TOTALS[1],
            records=(rec, )
        )
    ]


def _shared_day_blocks(
    day0: int, span_s: float, interval: float, flush_s: float, r_share: float, totals: list, rng: random.Random
) -> list:
    """r-share 混合日块序列: [z 前缀 | r 活跃窗(块化) | z 后缀], r 槽占比 ~= r_share
    (槽位守恒: 三段槽和 ~= span/interval, 与单一形态同量级 —— prod236 生产构成锚)。
    r_share >= 1.0 退化为纯活跃日; <= 0 退化为纯空闲日。"""
    if r_share >= 1.0:
        return _active_day_blocks(day0, span_s, interval, flush_s, totals, rng)
    if r_share <= 0.0:
        return _idle_day_blocks(day0, span_s, interval)
    active_s = span_s * r_share
    idle_a = round((span_s - active_s) / 2.0 / interval) * interval  # z 前缀长(对齐 interval 栅格)
    blocks = []
    if idle_a >= interval:
        blocks.extend(_idle_day_blocks(day0, idle_a, interval))
    win0 = idle_a
    blocks.extend(_active_day_blocks(day0 + int(win0), active_s, interval, flush_s, totals, rng))
    tail0 = win0 + active_s
    tail_s = span_s - tail0
    if tail_s >= interval:
        blocks.extend(_idle_day_blocks(day0, tail_s, interval, start_off=tail0))
    return blocks


def _calibrate_mixed_frac(interval: float, flush_s: float, span_s: float) -> float:
    """按 §02.2 mixed 口径(165KB/天文件均值)反推活跃占比: 生成一个活跃日 + 一个空闲日
    样本文本, 解 f = (target - z_bytes) / (r_bytes - z_bytes), 钳到 [0.01, 1.0]。"""
    day0 = 0
    rng = random.Random(7)
    totals = [500_000_000_000_000, 90_000_000_000_000]
    r_bytes = len(
        format_v4_day_text("global", _active_day_blocks(day0, span_s, interval, flush_s, totals, rng)).encode("utf-8")
    )
    z_bytes = len(format_v4_day_text("global", _idle_day_blocks(day0, span_s, interval)).encode("utf-8"))
    f = (MIXED_TARGET_MEAN_DAY_BYTES - z_bytes) / max(1, (r_bytes - z_bytes))
    return min(1.0, max(0.01, f))


def cmd_gen(args: argparse.Namespace) -> int:
    """生成 v4 天文件语料(逐系列逐文件即写盘, 不积内存; 不写 agg.dat)。"""
    t0 = time.perf_counter()
    interval = float(args.interval)
    flush_s = float(args.flush_s)
    phase_s = float(args.phase_hours) * 3600.0
    day_s = 86400.0
    today0 = v4_day_epoch(_now_ts())
    day_dates = [v4_epoch_date_str(today0 - (args.days - 1 - k) * day_s) for k in range(args.days)]
    day0s = {d: v4_date_str_epoch(d) for d in day_dates}

    active_frac = args.active_frac
    r_share = args.r_share  # None = 按形态缺省(见下); prod236 从快照实测派生
    if args.shape == "zheavy":
        active_frac, r_share = 0.0, 0.0
    elif args.shape == "rheavy":
        active_frac, r_share = 1.0, 1.0
    elif args.shape == "mixed" and active_frac is None:
        active_frac = _calibrate_mixed_frac(interval, flush_s, day_s)
        r_share = 1.0  # mixed = §02.2 口径: 系列级二元混合(活跃系列全天 r 行)
    elif args.shape == "prod236":
        if not args.prod_spec:
            print("prod236 形态须 --prod-spec <json>(由 snapshot-stats --emit-spec 产出)")
            return 1
        with open(args.prod_spec, "r", encoding="utf-8") as f:
            spec = json.load(f)
        interval = float(spec.get("interval_s") or interval)
        active_frac = float(spec.get("active_frac", 0.24))
        # 生产构成锚: 全库 r 行槽位占比(rows/slots)按活跃系列折算到逐系列 r-share
        rs_total = float(spec.get("r_share_total") or 0.0)
        r_share = min(1.0, rs_total / max(active_frac, 1e-6)) if rs_total > 0 else (args.r_share or 1.0)
        print(
            f"prod236 参数取自快照实测: interval_s={interval:g} active_frac={active_frac:.3f} "
            f"r_share_total={rs_total:.4f} -> 逐系列 r_share={r_share:.4f}"
        )
    if r_share is None:
        r_share = 1.0

    keys = _series_list(args.series, args.seed)
    flags = _active_flags(keys, active_frac)
    if args.shape == "zheavy":
        flags[0] = False  # 全空闲形态: global 也走 z 游程日(生产语义 global 恒采, 此处按形态纯度豁免)
    rng = random.Random(args.seed)

    store_root = os.path.join(args.out, "qb-traffic-v4")
    os.makedirs(os.path.join(store_root, "global"), exist_ok=True)
    os.makedirs(os.path.join(store_root, "torrents"), exist_ok=True)

    # 逐系列 totals 跨天单调推进(活跃系列); 空闲系列恒 IDLE_TOTALS
    per_series_totals = {}
    files_written = 0
    bytes_total = 0
    for i, key in enumerate(keys):
        if key == "global":
            series_dir = os.path.join(store_root, "global")
        else:
            series_dir = os.path.join(store_root, "torrents", key[len("torrent:"):])
        os.makedirs(series_dir, exist_ok=True)
        totals = per_series_totals.setdefault(key, [500_000_000_000_000, 90_000_000_000_000])
        for d in day_dates:
            span_s = day_s if d != day_dates[-1] else phase_s  # 末日 = 相位截断
            if flags[i]:
                blocks = _shared_day_blocks(day0s[d], span_s, interval, flush_s, r_share, totals, rng)
            else:
                blocks = _idle_day_blocks(day0s[d], span_s, interval)
            text = format_v4_day_text(key, tuple(blocks))
            path = os.path.join(series_dir, d + ".dat")
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            files_written += 1
            bytes_total += os.path.getsize(path)
        if (i + 1) % 500 == 0 or i + 1 == len(keys):
            el = time.perf_counter() - t0
            print(
                f"[gen {args.label}] {i + 1}/{len(keys)} 系列, {files_written} 文件, {bytes_total / 1e6:.1f}MB, {el:.1f}s",
                flush=True
            )

    manifest = {
        "label": args.label,
        "shape": args.shape,
        "series": len(keys),
        "days": args.days,
        "day_dates": day_dates,
        "interval_s": interval,
        "flush_s": flush_s,
        "phase_s": phase_s,
        "phase_hours": args.phase_hours,
        "active_frac": active_frac,
        "r_share": r_share,
        "seed": args.seed,
        "gen_now": _now_ts(),
        "gen_date": day_dates[-1],
        "files": files_written,
        "bytes_total": bytes_total,
        "mean_day_bytes": bytes_total / files_written,
        "keys_sample": keys[:3],
    }
    with open(os.path.join(args.out, "bench_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    print(
        f"[gen {args.label}] 完成: {len(keys)} 系列 x {args.days} 天 = {files_written} 文件, "
        f"{bytes_total / 1e9:.2f}GB, 均值 {bytes_total / files_written / 1024:.1f}KB/天文件, "
        f"active_frac={active_frac:.3f}, 耗时 {time.perf_counter() - t0:.1f}s",
        flush=True,
    )
    return 0


# ----------------------------------------------------------------------
# 场景 agg.dat 准备(天文件不动, 只写 agg.dat; 每 cell 前重写保证可重入)
# ----------------------------------------------------------------------


def _agg_row_values(rng: random.Random) -> tuple:
    """合成 agg 行值(值域量级贴近生产; 计时面只吃行数与字节数)。"""
    return (
        rng.randint(*RATE_DL_BAND) // 10,
        rng.randint(*RATE_DL_BAND),
        rng.randint(*RATE_UP_BAND) // 10,
        rng.randint(*RATE_UP_BAND),
        rng.randint(10**11, 10**13),
        rng.randint(10**10, 10**12),
        3600,
    )


def _scenario_agg_rows(manifest: dict, scenario: str) -> list:
    """场景 agg 行集(§4.3 水位形态): 30d hour 历史 + 场景尾段 + day/month 行。

    fresh: + 当日 00:00..(phase 整点-1) hour 行 -> 水位 = 当日 18h(19:45 相位);
    stale: 止于昨日 23:00 -> 水位 = 昨日 23h(重建两日);
    fallback: 空行集(仅头行 + key 行) -> 无可用水位 -> now - rollup_window 全量兜底。
    """
    if scenario == "fallback":
        return []
    rng = random.Random(11)
    gen_today0 = v4_date_str_epoch(manifest["gen_date"])
    phase_s = float(manifest["phase_s"])
    rows = []
    # 30d hour 历史: [today-30d, today) 逐整点(720 行, 贴近生产 rollup_window=30d 的 agg 体量)
    hist_lo = gen_today0 - 30 * 86400
    for h in range(hist_lo, gen_today0, 3600):
        rows.append(AggRow("hour", h, *_agg_row_values(rng)))
    if scenario == "fresh":
        sealed_hours = int(phase_s // 3600)  # 19:45 相位 -> 当日 0..18 共 19 行
        for k in range(sealed_hours):
            rows.append(AggRow("hour", gen_today0 + k * 3600, *_agg_row_values(rng)))
    # day 行: [today-30d, today-1d] 逐日 30 行
    for k in range(30, 0, -1):
        d0 = gen_today0 - k * 86400
        v = _agg_row_values(rng)
        rows.append(AggRow("day", d0, v[0] * 24, v[1], v[2] * 24, v[3], v[4], v[5], 86400))
    # month 行: 覆盖 30d 历史里"已完结自然月"(epoch 早于本月 1 日)
    seen_months = set()
    for k in range(30, 0, -1):
        d0 = gen_today0 - k * 86400
        m0 = _month_start(d0)
        if m0 < _month_start(gen_today0) and m0 not in seen_months:
            seen_months.add(m0)
            v = _agg_row_values(rng)
            rows.append(AggRow("month", m0, v[0] * 720, v[1], v[2] * 720, v[3], v[4] * 30, v[5] * 30, 30 * 86400))
    rows.sort(key=lambda r: (0 if r.kind == "hour" else (1 if r.kind == "day" else 2), r.epoch))
    return rows


def _month_start(ts: int) -> int:
    import datetime as _dt
    d = _dt.datetime.fromtimestamp(ts)
    return int(_dt.datetime(d.year, d.month, 1).timestamp())


def prepare_scenario_agg(corpus: str, manifest: dict, scenario: str) -> dict:
    """清空全部 agg.dat 后按场景重写(可重入保证: 恢复路径会向 agg 追加 catch-up 行)。"""
    store = TrafficV4Store(corpus)
    keys = store.series_keys()
    rows = _scenario_agg_rows(manifest, scenario)
    bytes_total = 0
    for key in keys:
        series_dir = v4_series_dir(corpus, key)
        os.makedirs(series_dir, exist_ok=True)
        payload = f"# auto-qb qb-traffic v4\nkey,{key}\n"
        if rows:
            payload += "\n".join(format_agg_row(r) for r in rows) + "\n"
        path = os.path.join(series_dir, "agg.dat")
        if os.path.exists(path):
            os.remove(path)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(payload)
        bytes_total += os.path.getsize(path)
    return {
        "series": len(keys),
        "agg_bytes_total": bytes_total,
        "hour_rows_per_series": sum(1 for r in rows if r.kind == "hour"),
        "scenario": scenario,
    }


# ----------------------------------------------------------------------
# 真实恢复入口计时
# ----------------------------------------------------------------------


def run_recovery_cell(corpus: str, manifest: dict, scenario: str, impl_tag: str, log_path: str) -> dict:
    """走真实恢复入口计时: module.start(ctx, dry_run=False) -> _recover_aggregates()。

    与生产 start() 钩子的唯一差异 = ctx/config 用最小装配(AppContext + SimpleNamespace
    config + 真实 QbTraffic 默认值), 恢复代码路径(_recover_aggregates/_recover_series/
    _agg_credit_day_file/_agg_append/_agg_trim)全部为生产原码零改动。
    """
    # 场景准备 + 记录准备体量(不在计时内; 生产里 agg.dat 是既有状态)
    prep = prepare_scenario_agg(corpus, manifest, scenario)

    logging.getLogger().setLevel(logging.INFO)
    for h in list(logging.getLogger().handlers):
        logging.getLogger().removeHandler(h)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.getLogger().addHandler(fh)

    conf = QbTraffic()
    conf.enabled = True  # 其余字段用配置缺省(rollup_window=30D / flush=600s)
    # S3(plan 26-11-21-1546)后 start() 尾部 spawn 真 daemon 清理, raw_window 缺省 24H 的
    # 保留下界 = 语料最旧日 + 0 余量 —— 语料是 harness 复用资产, 跨日复用时最旧语料日会被
    # 静默删。放大到 30d(不新增键): 语料自身保留不受清理影响, 清理 daemon 照跑零删除。
    conf.raw_window = 30 * 86400
    ctx = AppContext(SimpleNamespace(data_dir=corpus, qb_traffic=conf, main_tick=2.0))

    # 快照列编排(S2 快路语义接缝, 接缝终审发现 2 收编入库): impl_tag 以 -snap 结尾 =
    # 两阶段走真实入口 —— 阶段一(不计时): 删 acc.dat -> start 全量重建(B1+B2) -> stop
    # 终态行自举账本; 阶段二(计时): 新模块实例真实 start = 纯快路(指纹匹配零读直采)。
    # 零业务逻辑复刻, 与 S5 现场 s5snap.py 编排同构(该编排自此可由本 harness 复跑)。
    snap_mode = impl_tag.endswith("-snap")
    if snap_mode:
        acc_path = v4_acc_ledger_path(corpus)
        if os.path.exists(acc_path):
            os.remove(acc_path)
        boot = TrafficSampleModule(ctx)
        boot.start(ctx, dry_run=False)
        boot.stop()
        del boot

    mod = TrafficSampleModule(ctx)

    t0 = time.perf_counter()
    wall0 = _now_ts()
    mod.start(ctx, dry_run=False)  # 真实入口: 置 persistence_on 后调 _recover_aggregates()
    elapsed = time.perf_counter() - t0

    stats = dict(mod.recovery_stats or {})
    reads = mod.recovery_reads or {}
    bound_counts: dict = {}
    day_file_counts: dict = {}
    for info in reads.values():
        b = info.get("bound")
        bound_counts[b] = bound_counts.get(b, 0) + 1
        n = len(info.get("day_dates") or ())
        day_file_counts[n] = day_file_counts.get(n, 0) + 1
    # 机检断言(评审 26-11-21-1650 #12): cell 结果面与场景定义不自洽 = 该 cell 立即 FAIL,
    # 不静默记 None/空 bound_counts(fail-fast 机检形态)。-snap 快路 cell 走快路面机检
    # (source 全 ledger / slots=0 / fastpath=系列数; 重建面 bound 断言不适用)。
    expect_bound = "fallback" if scenario == "fallback" else "watermark"
    problems = []
    if stats.get("series") != manifest["series"]:
        problems.append(f"series {stats.get('series')!r} != manifest {manifest['series']}")
    if snap_mode:
        ledger_hits = sum(1 for info in reads.values() if info.get("source") == "ledger")
        if ledger_hits != stats.get("series"):
            problems.append(f"快路面 source 分布不符: ledger {ledger_hits}/{stats.get('series')}")
        if stats.get("slots"):
            problems.append(f"快路面 slots_processed = {stats.get('slots')!r}(应为 0)")
        if stats.get("ledger_fastpath") != stats.get("series"):
            problems.append(f"ledger_fastpath {stats.get('ledger_fastpath')!r} != series {stats.get('series')}")
    else:
        if not stats.get("slots"):
            problems.append(f"slots_processed = {stats.get('slots')!r}(应为正)")
        if bound_counts.get(expect_bound) != stats.get("series"):
            problems.append(f"bound 分布 {bound_counts} 与场景 {scenario} 不符(期望 {manifest['series']} 个系列全部 {expect_bound})")
    if problems:
        raise AssertionError("recovery cell 机检失败: " + "; ".join(problems))
    return {
        "cell": f"{manifest['label']}/{scenario}",
        "label": manifest["label"],
        "shape": manifest["shape"],
        "scenario": scenario,
        "impl_tag": impl_tag,
        "series": stats.get("series"),
        "day_files": stats.get("day_files"),
        "new_hours": stats.get("hours"),
        "slots_processed": stats.get("slots"),
        "slots_semantics": "处理槽(B1 开放段口径: 实际解析/记账走过的块槽位, 封口块不计; "
                           "pre-B1 旧结果 JSON 的 slots_credited = 全量口径, 评审 P1b-4)",
        "elapsed_perf_s": round(elapsed, 3),
        "module_elapsed_s": round(float(stats.get("elapsed_s") or 0.0), 3),
        "wall_started": v4_epoch_date_str(wall0) + " " + time.strftime("%H:%M:%S", time.localtime(wall0)),
        "wall_finished": time.strftime("%Y-%m-%d %H:%M:%S"),
        "bound_counts": bound_counts,
        "day_file_counts": dict(sorted(day_file_counts.items())),
        "ledger_fastpath": stats.get("ledger_fastpath"),
        "ledger_fallback": stats.get("ledger_fallback"),
        "agg_prepare": prep,
        "corpus":
            {
                "path": corpus,
                "interval_s": manifest["interval_s"],
                "days": manifest["days"],
                "phase_s": manifest["phase_s"],
                "active_frac": manifest["active_frac"],
                "mean_day_bytes": manifest["mean_day_bytes"],
                "gen_date": manifest["gen_date"],
                "raw_bytes_total": manifest["bytes_total"],
            },
        "notes":
            "现行实现(B1 后): 字节级开放段限定解析 + 记账入口水位过滤(封口块不解析"
            "不入账); 崩溃与优雅同路(累计器不落盘); 场景差异仅在 agg 水位形态。"
            "S2(P2b, 26-11-21-1546)起 acc 快照账本接线已上: 非 -snap cell 本 harness "
            "语料不含 acc.dat -> 全体系列走 fallback 重建(ledger_fastpath=0), 恢复埋"
            "点新增 ledger_fastpath/ledger_fallback 计数字段(旧字段语义不变); acc 行"
            "只在 flush/stop 写。" + (
                "-snap cell: boot 阶段已自举 acc.dat 并驱动真实 stop, 计时面 = 纯快路"
                "(接缝终审发现 2 收编入库, S5 现场编排可由本 harness 复跑)" if snap_mode else ""
            ),
    }


def _merge_cell(results_path: str, cell: dict) -> None:
    """按 cell 键合并写回 JSON(同键覆盖 = 幂等重跑; 换 impl_tag 键不同 = 追加)。"""
    data = {"meta": {}, "cells": {}}
    if os.path.exists(results_path):
        with open(results_path, "r", encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except (ValueError, OSError):
                data = {"meta": {}, "cells": {}}
    data.setdefault("meta", {})["harness"] = "scripts/bench_traffic_recovery.py"
    data["meta"]["plan"] = "26-11-21-1546 S0"
    data["meta"]["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    data.setdefault("cells", {})[cell["cell"] + "@" + cell["impl_tag"]] = cell
    tmp = results_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, results_path)


def cmd_run(args: argparse.Namespace) -> int:
    corpus = args.corpus
    with open(os.path.join(corpus, "bench_manifest.json"), "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    log_path = args.log_file or os.path.join(corpus, f"recovery-{args.scenario}.log")
    print(
        f"[run] {manifest['label']}/{args.scenario} 开始(系列 {manifest['series']}, 读集场景 = {args.scenario})...", flush=True
    )
    cell = run_recovery_cell(corpus, manifest, args.scenario, args.impl_tag, log_path)
    _merge_cell(args.out, cell)
    print(
        f"[run] {cell['cell']} 完成: {cell['elapsed_perf_s']}s (模块内 {cell['module_elapsed_s']}s) "
        f"读入天文件 {cell['day_files']} 个 / 补算小时 {cell['new_hours']} / 处理槽 {cell['slots_processed']}",
        flush=True,
    )
    return 0


def cmd_run_matrix(args: argparse.Namespace) -> int:
    """顺序跑一批 cell: 逐 cell 进度行 + 每_cell 落一次 JSON(防中途失败丢全部进度)。"""
    labels = [s.strip() for s in args.labels.split(",") if s.strip()]
    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    results_path = args.out
    log_dir = os.path.dirname(os.path.abspath(results_path))
    total = len(labels) * len(scenarios)
    k = 0
    for label in labels:
        corpus = os.path.join(args.bench_root, f"corpus-{label}")
        with open(os.path.join(corpus, "bench_manifest.json"), "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
        for scenario in scenarios:
            k += 1
            print(f"[matrix {k}/{total}] {label}/{scenario} 开始...", flush=True)
            t0 = time.perf_counter()
            cell = run_recovery_cell(
                corpus, manifest, scenario, args.impl_tag, os.path.join(log_dir, f"recovery-{label}-{scenario}.log")
            )
            _merge_cell(results_path, cell)
            print(
                f"[matrix {k}/{total}] {cell['cell']} 完成: {cell['elapsed_perf_s']}s "
                f"(模块内 {cell['module_elapsed_s']}s, 天文件 {cell['day_files']}, "
                f"处理槽 {cell['slots_processed']})",
                flush=True,
            )
    print(f"[matrix] 全部 {total} cell 完成, 结果 = {results_path}", flush=True)
    return 0


# ----------------------------------------------------------------------
# 只读快照统计(S0 尺寸预算实测的数据源)
# ----------------------------------------------------------------------


def _pct(values: list, q: float) -> float:
    if not values:
        return 0.0
    vs = sorted(values)
    idx = min(len(vs) - 1, int(round(q * (len(vs) - 1))))
    return vs[idx]


def _dist(values: list) -> dict:
    if not values:
        return {"n": 0, "mean": 0.0, "median": 0.0, "p90": 0.0, "max": 0.0}
    return {
        "n": len(values),
        "mean": sum(values) / len(values),
        "median": _pct(values, 0.5),
        "p90": _pct(values, 0.9),
        "max": max(values),
    }


def _reject_output_under_root(root: str, out_path: str, flag: str) -> None:
    """只读守卫(评审 26-11-21-1650 #13): snapshot-stats 的输出路径绝不允许落在 --root
    之下 —— 生产快照的只读承诺由工具自身机器保证, 不靠人记得。out 为空跳过;
    两侧先 os.path.normcase(os.path.abspath(...)) 归一(评审复评 #1: win32 大小写
    不敏感, 不归一则 --out 与 --root 仅大小写不同即绕过), 再判相等与前缀;
    命中即拒跑(SystemExit, rc != 0)。"""
    if not out_path:
        return
    r = os.path.normcase(os.path.abspath(root))
    o = os.path.normcase(os.path.abspath(out_path))
    if o == r or o.startswith(r + os.sep):
        raise SystemExit(f"[guard] {flag} 输出路径落在只读 --root 之下, 拒跑: {o}(root = {r})")


def cmd_snapshot_stats(args: argparse.Namespace) -> int:
    """只读统计一个 v4 存储库(绝不写 root 下任何文件; 只 listdir + open("r"))。"""
    _reject_output_under_root(args.root, args.out, "--out")
    _reject_output_under_root(args.root, args.emit_spec, "--emit-spec")
    t0 = time.perf_counter()
    root = args.root
    keys = []
    global_dir = os.path.join(root, "global")
    torrents_dir = os.path.join(root, "torrents")
    if os.path.isdir(global_dir):
        keys.append(("global", global_dir))
    if os.path.isdir(torrents_dir):
        for name in sorted(os.listdir(torrents_dir)):
            d = os.path.join(torrents_dir, name)
            if os.path.isdir(d):
                keys.append((name, d))

    per_series = []
    sizes_global, sizes_torrents = [], []
    slots_total = 0
    rows_total = 0
    blocks_total = 0
    interval_counts: dict = {}
    dates_all = []
    per_date: dict = {}  # 日期 -> {files, bytes, slots}(读集规模按日分解)
    span_stats = []  # 逐系列最新日期文件的槽位跨度(相位证据; 全量 v4_block_slots 仅此抽样)
    parse_errors = 0
    for s_key, sdir in keys:
        files = sorted(n for n in os.listdir(sdir) if v4_day_file_date(n) is not None)
        sizes = []
        slots_series = 0
        for name in files:
            dates_all.append(v4_day_file_date(name))
            path = os.path.join(sdir, name)
            fsize = os.path.getsize(path)
            sizes.append(fsize)
            dstat = per_date.setdefault(v4_day_file_date(name), {"files": 0, "bytes": 0, "slots": 0})
            dstat["files"] += 1
            dstat["bytes"] += fsize
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    parsed = parse_v4_day_text(fh.read())
            except OSError:
                parse_errors += 1
                continue
            for b in parsed.blocks:
                blocks_total += 1
                interval_counts[repr(b.interval_s)] = interval_counts.get(repr(b.interval_s), 0) + 1
                b_slots = sum(1 if isinstance(rec, V4Sample) else rec.run_len for rec in b.records)
                dstat["slots"] += b_slots
                for rec in b.records:
                    rows_total += 1
                    if isinstance(rec, V4Sample):
                        slots_series += 1
                    else:
                        slots_series += rec.run_len
            # 抽样: 每系列只对最新日期文件精确展开槽位跨度(末日相位证据)
            if files and name == files[-1] and parsed.blocks:
                first = float(parsed.blocks[0].start_epoch)
                last_ts = first
                for b in parsed.blocks:
                    sl = v4_block_slots(b)
                    if sl:
                        last_ts = sl[-1].ts
                span_stats.append(
                    {
                        "key": s_key,
                        "date": v4_day_file_date(name),
                        "span_s": round(last_ts - first, 1),
                        "span_hours": round((last_ts - first) / 3600.0, 2)
                    }
                )
        sizes_total = sum(sizes)
        if s_key == "global":
            sizes_global.extend(sizes)
        else:
            sizes_torrents.extend(sizes)
        per_series.append({"key": s_key, "day_files": len(files), "bytes": sizes_total, "slots": slots_series})
        slots_total += slots_series

    series_day_means = [s["bytes"] / s["day_files"] for s in per_series if s["day_files"]]
    active_threshold = 4096
    n_active = sum(1 for m in series_day_means if m > active_threshold)
    out = {
        "root": root,
        "measured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "series_total": len(keys),
        "series_global": 1 if any(k == "global" for k, _ in keys) else 0,
        "series_torrents": len(keys) - (1 if any(k == "global" for k, _ in keys) else 0),
        "day_files_total": sum(s["day_files"] for s in per_series),
        "date_min": min(dates_all) if dates_all else None,
        "date_max": max(dates_all) if dates_all else None,
        "bytes_total": sum(s["bytes"] for s in per_series),
        "slots_total": slots_total,
        "rows_total": rows_total,
        "blocks_total": blocks_total,
        "slots_per_series": _dist([s["slots"] for s in per_series]) if per_series else {},
        "day_file_bytes_global": _dist(sizes_global),
        "day_file_bytes_torrents": _dist(sizes_torrents),
        "series_mean_day_bytes": _dist(series_day_means),
        "active_frac_est": n_active / max(1, len(series_day_means)),
        "active_threshold_bytes": active_threshold,
        "interval_counts_top": sorted(interval_counts.items(), key=lambda kv: -kv[1])[:8],
        "per_date": {
            k: per_date[k]
            for k in sorted(per_date)
        },
        "latest_file_span_samples": span_stats[:16],
        "parse_errors": parse_errors,
        "elapsed_s": round(time.perf_counter() - t0, 2),
    }
    payload = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload)
        print(f"snapshot-stats 已写 {args.out}", flush=True)
    else:
        print(payload)
    if args.emit_spec:
        spec = {
            "interval_s": _median_interval(interval_counts),
            "active_frac": out["active_frac_est"],
            "r_share_total": round(rows_total / max(1, slots_total), 6),
            "mean_day_bytes": out["series_mean_day_bytes"]["mean"],
            "source_root": root,
        }
        with open(args.emit_spec, "w", encoding="utf-8") as fh:
            json.dump(spec, fh, ensure_ascii=False, indent=2)
        print(f"prod-spec 已写 {args.emit_spec}: {spec}", flush=True)
    return 0


def _median_interval(interval_counts: dict) -> float:
    """按块头频次的众数间隔(字符串键 -> float)。"""
    if not interval_counts:
        return 4.0
    top, _cnt = max(interval_counts.items(), key=lambda kv: kv[1])
    try:
        return float(top.strip("'"))
    except ValueError:
        return 4.0


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="traffic recovery benchmark harness (plan 26-11-21-1546 S0)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("gen", help="生成 v4 天文件语料")
    p.add_argument("--out", required=True, help="语料 data_dir(内建 qb-traffic-v4/)")
    p.add_argument("--shape", required=True, choices=["rheavy", "zheavy", "mixed", "prod236"])
    p.add_argument("--label", default=None, help="语料标识(缺省 = shape; cell 键用它)")
    p.add_argument("--series", type=int, default=5000)
    p.add_argument("--days", type=int, default=4)
    p.add_argument("--interval", type=float, default=4.0, help="采样间隔秒(块头 interval_s)")
    p.add_argument("--flush-s", type=float, default=600.0, help="块宽(= flush 窗)秒")
    p.add_argument("--phase-hours", type=float, default=DEFAULT_PHASE_HOURS, help="当日内容相位(小时)")
    p.add_argument("--active-frac", type=float, default=None, help="活跃占比(mixed 缺省按 165KB 口径自校准)")
    p.add_argument("--r-share", type=float, default=None, help="活跃系列日内 r 行槽位占比(prod236 从快照实测派生)")
    p.add_argument("--prod-spec", default=None, help="prod236 参数 json(interval_s/active_frac/r_share_total)")
    p.add_argument("--seed", type=int, default=42)
    p.set_defaults(fn=cmd_gen)

    p = sub.add_parser("run", help="跑单个恢复 cell(真实入口计时)")
    p.add_argument("--corpus", required=True)
    p.add_argument("--scenario", required=True, choices=["fresh", "stale", "fallback"])
    p.add_argument("--impl-tag", default="current", help="实现标签(口径变更后重跑必须换新 tag —— 结果按 cell@tag 追加不覆盖)")
    p.add_argument("--out", required=True, help="结果 JSON(按 cell 键合并)")
    p.add_argument("--log-file", default=None)
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("run-matrix", help="顺序跑一批 cell(逐 cell 进度 + JSON 实时落盘)")
    p.add_argument("--bench-root", required=True, help="语料根(<bench-root>/corpus-<label>)")
    p.add_argument("--labels", required=True, help="逗号分隔语料标识")
    p.add_argument("--scenarios", required=True, help="逗号分隔场景(fresh,stale,fallback)")
    p.add_argument("--impl-tag", default="current", help="实现标签(口径变更后重跑必须换新 tag —— 结果按 cell@tag 追加不覆盖)")
    p.add_argument("--out", required=True, help="结果 JSON")
    p.set_defaults(fn=cmd_run_matrix)

    p = sub.add_parser("snapshot-stats", help="只读统计真实 v4 存储库")
    p.add_argument("--root", required=True, help="v4 存储根(只读, 绝不写入)")
    p.add_argument("--out", default=None, help="统计 JSON 输出路径")
    p.add_argument("--emit-spec", default=None, help="同时产出 prod236 gen 参数 json")
    p.set_defaults(fn=cmd_snapshot_stats)

    args = ap.parse_args(argv)
    if hasattr(args, "label"):
        args.label = args.label or getattr(args, "shape", None)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
