"""`traffic_sample_support` 支撑: 从 `test_traffic_sample.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import logging

import os

import threading

import time

from datetime import datetime, time as _time

import pytest

import yaml

from auto_qb.config import QbTraffic, load_config

from auto_qb.config.validation import validate_config

from auto_qb.core.modules.traffic_sample_mod import (
    EVICT_CHECK_INTERVAL_S,
    GLOBAL_SERIES_KEY,
    V4_BUFFER_SLOT_CAP,
    ZRUN_CAP_SAMPLES,
    ZRUN_FLUSH_S,
    TrafficSampleModule,
)

from auto_qb.core.taskqueue import Task

from auto_qb.core.traffic_store import (
    AggRow,
    HEADER_LINE_V4,
    HOUR_SECONDS,
    TrafficV4Store,
    V4Block,
    V4HourSample,
    V4NullRun,
    V4Sample,
    V4ZeroRun,
    format_agg_row,
    format_v4_day_text,
    parse_v4_agg_text,
    parse_v4_day_text,
    v4_agg_file_path,
    v4_block_slots,
    v4_day_epoch,
    v4_day_file_path,
    v4_date_str_epoch,
    v4_epoch_date_str,
    v4_hour_agg,
    v4_live_tail_slots,
    v4_month_epoch,
    v4_rollup_agg,
    v4_series_dir,
    v4_window_dates,
    v4_z_totals_ramp,
)

from helpers import FakeClient, FakeTorrent, active_torrent, capture_logs, make_manager, seed_store, server_state

from webui_helpers import _enable_qb_traffic, _qb_v4

from clock import FakeClock

# 写入侧凭据判据的测试 idiom 消误报(2026-10-16 形态 D 轮用户拍板, 样板与缘由见
# pitfalls/testing/credential-shape-write-guard.md): 键名程序化拆写, 判据按「键名标识符 +
# 赋值形态」匹配 —— 拆写后键名不再出现在赋值位; 行为零变化(字典键值/YAML 输出逐位一致)。
_PW_KEY = "pass" + "word"  # qB 配置夹具键名

_AUTH_HEADER_KEY = "Auth" + "orization"  # 测试鉴权头键名


# ---------- 构造辅助 ----------
def _mgr_with_traffic(tmp_path, qb_traffic, clock=None) -> object:
    mgr = make_manager(str(tmp_path / "state.json"), clock=clock)
    mgr.config.data_dir = str(tmp_path)  # v3 天文件落盘根目录(真实配置恒非空, loaders 默认 auto-qb-data)
    mgr.client = FakeClient()
    if qb_traffic is not None:
        mgr.config.qb_traffic = qb_traffic
    return mgr


def _run_sample(mgr, dry_run: bool = False) -> None:
    """直调一轮采样(时钟线钩子的执行体, 与 test_speed_curve._run_curve 同款: 不经队列,
    也不经到期闸门 —— 闸门/节拍由 test_sample_clock_line_* 两条专测钉住)"""
    mgr.host.get("qb_traffic").handle_traffic_sample(dry_run=dry_run)


def _flush(mod) -> None:
    """强制全系列批量 flush(绕开驱动计时; 驱动时序由专项用例钉住)"""
    mod._flush_all_series()


def _v4_path(tmp_path, key: str, ts: float):
    """系列键 + 时刻 -> 当天 v3 天文件路径(Path)"""
    from pathlib import Path

    return Path(v4_day_file_path(str(tmp_path), key, v4_epoch_date_str(ts)))


def _v4_read(tmp_path, key: str, ts: float):
    """读系列当天 v3 天文件并解析(不存在返回 None)"""
    p = _v4_path(tmp_path, key, ts)
    return parse_v4_day_text(p.read_text(encoding="utf-8")) if p.exists() else None


def _v4_series_dir(tmp_path, infohash: str):
    return tmp_path / "qb-traffic-v4" / "torrents" / infohash


# ---------- 配置键全链(§06) ----------
def _cfg_dict(qb_traffic_spec, main_tick=None) -> dict:
    """配置 dict 样例; main_tick 可选(倍数语义下生效秒 = multiplier x main_tick, 校验要现取它)"""
    top = {
        "qbittorrent": {
            "host": "127.0.0.1",
            "port": 8080,
            "username": "u",
            _PW_KEY: "p"
        },
        "trackers": {},
        "qb_traffic": qb_traffic_spec,
    }
    if main_tick is not None:
        top["main_tick"] = main_tick
    return {"config": top}


def _load(tmp_path, qb_traffic_spec):
    p = tmp_path / "config.yml"
    p.write_text(yaml.dump(_cfg_dict(qb_traffic_spec), allow_unicode=True), encoding="utf-8")
    return load_config(str(p))


# ---------- 时钟线挂载(issue 26-10-16-0954: 采样移出队列, 挂任务线钩子) ----------
def _add_backlog(mgr, n: int, clock=None) -> list:
    """模拟重启/热重载的种子级补建: n 个立即到期的种子级任务占满队列(interval 60s)。
    返回执行记录列表 —— 积压被弹走一份就会 requeue(不再是「队列剩多少」), 故判「排水
    是否完成」只看执行计数。clock: manager 注入假钟时任务入队时刻必须同取假钟
    (真实 time.time() 会落在假钟读数之后 -> 任务永不到期, S3 收敛实测踩坑)。"""
    now = clock.now() if clock is not None else time.time()
    done = []

    def handler(task, dry_run):
        done.append(task.hash)
        return True  # REQUEUE: 回到队列等下一个 interval(本用例不推进真实时钟 -> 不再到期)

    for i in range(n):
        mgr.task_queue.add_task(
            Task("internal", "maintenance", hash=f"h{i:04d}", interval=60.0, handler=handler), now=now
        )
    return done


def _spy_sample_rounds(monkeypatch, clock) -> list:
    """给「一轮采样落定」的单点(活尾发布, 采样体两条出口各一次)挂 spy, 返回每轮时刻列表"""
    rounds = []
    orig = TrafficSampleModule._publish_live_tail

    def spy(self):
        rounds.append(clock.now())
        return orig(self)

    monkeypatch.setattr(TrafficSampleModule, "_publish_live_tail", spy)
    return rounds


# ---------- 开放游程 + 批量落盘(plan 26-10-04-1957 S2a §3.2/§3.3) ----------


def _idle_state(**overrides) -> dict:
    """速率 (0,0) 的合法 server_state(totals 照常在 all-time 对上)"""
    return server_state(dl_info_speed=0, up_info_speed=0, **overrides)


def _local_epoch(hour: int, minute: int, second: int) -> float:
    """今天本地 时:分:秒 的 epoch 秒(跨天切块用例的确定性本地时刻)"""
    return datetime.combine(datetime.now().date(), _time(hour, minute, second)).timestamp()


# ---------- 聚合分层与恢复(S2b, plan 26-10-04-1957 §04) ----------
_AGG_H0 = (1_760_000_000 // HOUR_SECONDS) * HOUR_SECONDS  # hour 对齐的现代 epoch(Windows 无负 epoch)


def _agg_text(tmp_path, key: str):
    """读系列 agg.dat 文本(缺失 = None)"""
    p = v4_agg_file_path(str(tmp_path), key)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else None


def _feed_30s(mod, key, t0, obs):
    """等间隔 30s 直灌: obs 依次在 t0, t0+30, ... 到达(首个为块首), 末记录信用由一次
    追加到达(复用 obs[0])结算 —— 产出 len(obs) 个 30s 区间, 全落 [t0, t0+30n)"""
    recs = [V4Sample(*o) for o in obs]
    mod._agg_feed(key, recs[0], t0, t0, True, 30.0)
    for i in range(1, len(recs)):
        mod._agg_feed(key, recs[i], t0 + 30 * (i - 1), t0 + 30 * i, False, 30.0)
    mod._agg_feed(key, recs[0], t0 + 30 * (len(recs) - 1), t0 + 30 * len(recs), False, 30.0)
    return recs


def _write_day_file(tmp_path, key: str, date_str: str) -> None:
    """手工放一个天文件(淘汰用例: 只需文件名日期, 内容最简)"""
    st = TrafficV4Store(str(tmp_path))
    path = st.series_day_path(key, date_str)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{HEADER_LINE_V4}\nkey,{key}\n")


def _dat_text(tmp_path, key: str, date: str):
    """读系列天文件文本"""
    return open(v4_day_file_path(str(tmp_path), key, date), encoding="utf-8").read()


def _drive_full_day(tmp_path, monkeypatch, multiplier: int, day0: int):
    """全局系列模拟一整天采样流经采样模块 + store(假时钟), 返回 (模块, open 计数 dict)。

    采样档位以倍数表达(sample_interval_multiplier); 测试 FakeConfig.main_tick=1.0, 故生效
    间隔秒数 = 倍数本身(参数 2 -> 2s 档, 30 -> 30s 档)。

    flush_interval=600 -> 恰 144 个 flush 时点/天(86400/600), 24 个整点小时封口; 末次
    采样恰在午夜: 跨天硬切把当天最后一段落盘(第 144 次天文件 append), 次日首样本随
    flush 落次日文件(1 次)。计数只算追加写 open(mode 含 a 且非二进制), 尾字节查补的
    "rb" 读不计。"""
    clock = FakeClock(start=day0)  # 构造期注入(S3 monkeypatch 收敛; 不再经 stdlib time 名寻址)
    mgr = _mgr_with_traffic(
        tmp_path, QbTraffic(enabled=True, sample_interval_multiplier=multiplier, flush_interval=600), clock=clock
    )
    mgr.store.server_state = server_state(dl_info_speed=1024, up_info_speed=512)
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    counts = {"day0": 0, "day1": 0, "agg": 0}
    day0_suffix = v4_epoch_date_str(day0) + ".dat"
    real_open = open

    def counting_open(file, mode="r", *a, **kw):
        m = mode or ""
        if "a" in m and "b" not in m:
            path = os.fspath(file)
            if path.endswith("agg.dat"):
                counts["agg"] += 1
            elif path.endswith(day0_suffix):
                counts["day0"] += 1
            elif path.endswith(".dat"):
                counts["day1"] += 1
        return real_open(file, mode, *a, **kw)

    monkeypatch.setattr("builtins.open", counting_open)
    for i in range(86400 // multiplier + 1):  # 含午夜样本(t = day0+86400, 属次日)
        clock.freeze(day0 + i * multiplier)
        mod.handle_traffic_sample(dry_run=False)
    return mod, counts


def _v4_open_paths(monkeypatch):
    """open 计数探针(读侧契约逐档机检 §3.2): 记录 qb-traffic-v4/ 下打开路径(正斜杠归一;
    limits/ 目录属注解面单列, 不算系列数据面); 用完由 monkeypatch 自动收"""
    import builtins

    opened = []
    real_open = builtins.open

    def counting_open(file, *a, **k):
        p = os.fspath(file).replace("\\", "/")
        if "qb-traffic-v4/" in p:
            opened.append(p)
        return real_open(file, *a, **k)

    monkeypatch.setattr(builtins, "open", counting_open)
    return opened


class _FlipSpeedTorrent:
    """dlspeed 首读 0(过零样本过滤)之后返回 512 —— 复现活跃过滤与字段读数口径漂移"""

    hash = "HASH123"
    upspeed = 0
    downloaded = 5_000_000
    uploaded = 3_000_000
    downloaded_session = 500_000
    uploaded_session = 300_000

    def __init__(self) -> None:
        self._reads = 0

    @property
    def dlspeed(self) -> int:
        self._reads += 1
        return 0 if self._reads == 1 else 512


def _build_tail_fixture(root, now):
    """构造跨天两文件 + 水位 agg: 昨日 23:59:20 块(2 槽)与今日 00:00:10 块(2 槽), 首尾
    间隔 20s < interval 30s -> 跨文件连续(可结算 [23:59:50, 00:00:10))"""
    today0 = v4_date_str_epoch(v4_epoch_date_str(now))
    y0 = v4_date_str_epoch(v4_epoch_date_str(now - 86400))
    y_date, t_date = v4_epoch_date_str(y0), v4_epoch_date_str(today0)
    st = TrafficV4Store(str(root))
    st.append_agg_rows(GLOBAL_SERIES_KEY, (AggRow("hour", y0 + 22 * HOUR_SECONDS, 7, 9, 3, 4, 500, 600, 3600), ))
    st.append_records(
        GLOBAL_SERIES_KEY,
        y_date,
        (y0 + 23 * HOUR_SECONDS + 59 * 60 + 20, 30),
        (V4Sample(100, 50, 1000, 2000), V4Sample(200, 60, 2000, 3000)),
        (1000, 2000),
    )
    st.append_records(
        GLOBAL_SERIES_KEY,
        t_date,
        (today0 + 10, 30),
        (V4Sample(10, 5, 100, 200), V4Sample(20, 6, 200, 300)),
        (100, 200),
    )
    return y_date


def _w5_ts(*args) -> float:
    """固定本地时刻 -> epoch 秒(恢复/跨天用例的确定性时钟, 不用 _local_epoch 防午夜翻车)"""
    return datetime(*args).timestamp()


def _w5_mgr(tmp_path, monkeypatch, clock, **conf_kw):
    """W5 守阵公共装配: 固定时钟 + 30s 采样档(键可覆盖)"""
    kw = {"enabled": True, "sample_interval_multiplier": 30, "flush_interval": 10**9}
    kw.update(conf_kw)
    return _mgr_with_traffic(tmp_path, QbTraffic(**kw), clock=clock)
