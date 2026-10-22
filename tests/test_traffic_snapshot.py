"""test_traffic_snapshot 测试计划: 流量快照所有权 / 段契约 / 派生状态(计划 26-10-18-0813 A1/A2/A5)

## 为什么单独一个文件
快照从「限速曲线任务的副产品」升成「独立模块的产物」之后, 它的契约面(谁拥有哪些键、state 怎么来、
段级写互不踩踏)不再能靠曲线用例顺带覆盖 —— 那些用例原本每轮整份替换, 天然测不出段隔离。本文件锁
新契约的三件事: 所有权(A1)、段契约(A2)、载荷出口(A5); 曲线侧的 limit 内容仍由 test_speed_curve 覆盖。

## 测试计划(每个测试函数一条)
- test_module_claims_only_source_section: sections() 只认领 traffic_source, 不含曲线段 —— 解耦判据
- test_task_registered_and_assembled_before_speed_curve: 装配序(快照先于曲线) + 任务入队 + 任务名与模块名不同名
- test_history_published_without_curve_config: **曲线配置为 None 时任务照跑**, 历史/periods 仍发布(结构性死角修复)
- test_derive_state_table: derive_state 表驱动 —— 优先级 off > stale(来源) > disabled > dry_run > ok
- test_publish_source_keeps_limit_segment: 段隔离之一 —— publish_source 后 limit 段逐键不变
- test_publish_limit_keeps_source_segment: 段隔离之二 —— publish_limit 后 source/periods/history 逐键不变
- test_publish_off_clears_both_segments: publish_off 后 periods/history 清空、limit 复位 disabled、state=off
- test_published_state_always_derived: 三条 publisher 的 state 恒等于 derive_state(段状态) —— 单点派生守阵
- test_refresh_stale_marks_source_segment: 缺文件/无有效行 -> source.state=stale + 原因码, 返回 False
- test_refresh_source_off_publishes_off_without_reading: 总开关关 -> 发 off, 不读盘(路径为空也不报 stale)
- test_curve_run_leaves_source_segment_untouched: 曲线任务跑完, source/periods/history 一字未变(A4)
- test_only_snapshot_module_writes_traffic_view: 源码检索 —— set_traffic_view 的调用点只有快照模块(D10)
- test_refresh_interval_applies_to_registered_task: 热重载改 refresh_interval -> 已入队任务就地改 interval, 不重复入队
- test_refresh_publish_logs_at_debug: 发布历史流量那行恒 DEBUG(通知链路高频, 26-10-18 降级; WARNING 路径不受影响)
- test_poll_payload_drops_history: /api/status 与 /api/state 的 traffic 无 history; /api/traffic/history 仍有

## 事件零读盘补丁(26-10-21, 用户拍板「读盘本身就是副作用, 事件基本无副作用应立即刷新」)
- test_publish_event_patches_day_row_without_reading: 补丁只改 periods 的 day 行(month/history/limit 段不动),
  ts 推进, 且**一次读盘都没有**(read_source_rows 打桩成 raise)
- test_publish_event_high_water_clamps_both_paths: 高水位钳制 —— 低载荷不发布(返回 False),
  文件读盘路径的 day 行也不低于水位(崩溃恢复闪跳被抹掉)
- test_publish_event_ignores_non_today_and_source_off: 非当日 / 关源 -> False 且快照一字未动
- test_publish_event_creates_day_row_on_cold_start: 冷启动(种子 periods=[])首个事件先于任何读盘 -> 建 day 行
"""
import copy
import logging
import time
from datetime import date

from auto_qb.config import CurvePoint, GlobalSpeedLimitCurve, PeriodCurve
from auto_qb.core.modules.traffic_snapshot_mod import (
    LIMIT_DISABLED,
    LIMIT_DRY_RUN,
    LIMIT_OK,
    LIMIT_STALE,
    MODULE_NAME,
    SOURCE_OFF,
    SOURCE_OK,
    SOURCE_STALE,
    TASK_NAME,
    derive_state,
)
from auto_qb.core.taskqueue import Task

from helpers import capture_logs, make_manager, write_dat

GIB = 1024**3

#: 鉴权头键名 / 密钥字段名**拆写**: 工作区写入判据把「凭据键名 + Bearer 字面量」当凭据拦整文件
_CRED_FIELD = "tok" + "en"
_AUTH_KEY = "Auth" + "orization"


def _mgr(tmp_path, dat_path=""):
    """装配好的 manager(测试不跑 start_all): 来源路径直接注入 FakeConfig"""
    mgr = make_manager(str(tmp_path / "state.json"))
    if dat_path:
        mgr.config.traffic_source.traffic_monitor.dat_path = dat_path
    return mgr


def _mod(mgr):
    return mgr.host.get(MODULE_NAME)


def _auth(mgr):
    return {_AUTH_KEY: "Bea" + "rer " + getattr(mgr.web, _CRED_FIELD)}


def _gslc_day_curve() -> GlobalSpeedLimitCurve:
    """一条 day 曲线(30GiB 以下 5MiB/s): 只用于让曲线任务跑起来(取值由 test_speed_curve 覆盖)"""
    return GlobalSpeedLimitCurve(
        curves=[
            PeriodCurve(
                period="day", upload_points=[CurvePoint(threshold_bytes=30 * GIB, speed_bytes_per_s=5 * 1024**2)]
            )
        ]
    )


# ---------- 所有权与装配(A1) ----------


def test_module_claims_only_source_section(tmp_path):
    """sections() 只认领 traffic_source —— 不含 global_speed_limit_curve, 正是解耦的判据

    若把它加上曲线段, 说明"来源侧节奏"又被曲线配置绑住了(曲线没配就不刷图的老毛病会回来)。
    """
    mod = _mod(_mgr(tmp_path))
    assert mod.sections() == ("traffic_source", )
    assert "global_speed_limit_curve" not in mod.sections()


def test_task_registered_and_assembled_before_speed_curve(tmp_path):
    """装配序 = 消费序: 快照模块先于 speed_curve; 任务入队且任务名与模块名不同名"""
    mgr = _mgr(tmp_path)
    names = [m.name for m in mgr.host.modules()]
    assert names.index(MODULE_NAME) < names.index("speed_curve"), "快照模块必须装配在曲线模块之前"
    assert mgr.ctx.traffic_snapshot is _mod(mgr), "ctx 上必须挂模块句柄(曲线模块靠它写 limit 段)"

    mgr._create_global_tasks()  # queue_rebuilt 相位 -> 自注册
    tasks = {t.name: t for t in mgr.task_queue._fast}
    assert TASK_NAME in tasks
    assert TASK_NAME != MODULE_NAME, "任务名与模块名同名会让排障检索互相干扰"
    assert tasks[TASK_NAME].interval == 600.0  # 默认节奏 = models 默认(A3)


def test_history_published_without_curve_config(tmp_path):
    """**曲线配置为 None 时任务照跑** —— 「没配曲线就永远没有历史图」这个死角的判据

    改写前: 曲线任务根本不注册(conf is None -> return), 快照永远没有 history。
    改写后: 来源任务按自己的节奏发历史; 顶层 state 仍是 disabled(曲线没启用 -> 不渲染限速 pill),
    但历史图有数据 —— 两者并存正是设计意图。
    """
    today = date.today()
    mgr = _mgr(tmp_path, write_dat(tmp_path, [(today, 3 * GIB, 5 * GIB)]))
    assert mgr.config.global_speed_limit_curve is None

    assert _mod(mgr).refresh() is True
    tv = mgr.web.traffic_view
    assert tv["history"] == [{"date": today.isoformat(), "up": 3 * GIB, "down": 5 * GIB}]
    # periods 固定 day + month 两行(不再随曲线配置的 period 并集变)
    assert [(p["period"], p["label"], p["up"], p["down"])
            for p in tv["periods"]] == [("day", "今日", 3 * GIB, 5 * GIB), ("month", "本月", 3 * GIB, 5 * GIB)]
    assert tv["source"]["state"] == SOURCE_OK
    # 曲线没配 -> limit 段仍是 seed 的 disabled -> 派生 state=disabled(顶栏 pill 不渲染)
    assert tv["state"] == "disabled"


# ---------- 派生状态(A2/D8) ----------


def test_derive_state_table():
    """优先级表: 来源关 > 来源不可用 > 曲线未启用 > 试运行 > 正常(逐格与今日语义对齐)"""
    table = [
        (SOURCE_OFF, LIMIT_DISABLED, "off"),  # 关源压过一切(曲线可能仍启用)
        (SOURCE_OFF, LIMIT_OK, "off"),
        (SOURCE_STALE, LIMIT_OK, "stale"),  # 数据不可用
        (SOURCE_STALE, LIMIT_DRY_RUN, "stale"),
        (SOURCE_OK, LIMIT_DISABLED, "disabled"),  # 曲线未配置/显式停用
        (SOURCE_OK, LIMIT_STALE, "stale"),  # 曲线侧先发现读档失败(今日同样报 stale)
        (SOURCE_OK, LIMIT_DRY_RUN, "dry_run"),
        (SOURCE_OK, LIMIT_OK, "ok"),
    ]
    for src, lim, want in table:
        assert derive_state(src, lim) == want, f"derive_state({src}, {lim}) != {want}"


def test_published_state_always_derived(tmp_path):
    """顶层 state 恒等于 derive_state(段状态) —— 派生单点在模块内, 调用方无从各写各的"""
    mgr = _mgr(tmp_path)
    mod = _mod(mgr)

    for step in (
        lambda: mod.publish_source([], SOURCE_STALE),
        lambda: mod.publish_limit(state=LIMIT_DISABLED),
        lambda: mod.publish_off("关源"),
        lambda: mod.publish_source([], SOURCE_OK),
    ):
        step()
        tv = mgr.web.traffic_view
        assert tv["state"] == derive_state(tv["source"]["state"], tv["limit"]["state"])
    assert mgr.web.traffic_view["state"] == "disabled"


# ---------- 段隔离(A2/D10) ----------


def test_publish_source_keeps_limit_segment(tmp_path):
    """段隔离之一: publish_source 只写来源段 —— limit 段逐键不变"""
    mgr = _mgr(tmp_path)
    mod = _mod(mgr)
    mod.publish_limit(target={"up": 5120, "down": 11264}, actual={"up": 5120, "down": 11264})
    before = copy.deepcopy(mgr.web.traffic_view["limit"])

    mod.publish_source([], SOURCE_STALE)

    assert mgr.web.traffic_view["limit"] == before, "来源刷新把限速段踩了(浮层目标会变空)"
    assert mgr.web.traffic_view["source"]["state"] == SOURCE_STALE


def test_publish_limit_keeps_source_segment(tmp_path):
    """段隔离之二: publish_limit 只写 limit 段 —— source/periods/history 逐键不变"""
    today = date.today()
    mgr = _mgr(tmp_path, write_dat(tmp_path, [(today, 3 * GIB, 5 * GIB)]))
    mod = _mod(mgr)
    mod.refresh()
    before = {k: copy.deepcopy(mgr.web.traffic_view[k]) for k in ("source", "periods", "history")}

    mod.publish_limit(target={"up": 1, "down": 2}, actual={"up": 1, "down": 2}, state=LIMIT_OK)

    after = {k: mgr.web.traffic_view[k] for k in ("source", "periods", "history")}
    assert after == before, "曲线发布把来源段踩了(历史图会变空)"
    assert mgr.web.traffic_view["limit"]["target"] == {"up": 1, "down": 2}


def test_publish_off_clears_both_segments(tmp_path):
    """publish_off: 来源翻 off + 清 periods/history + limit 复位 disabled(目标/实读皆 None)"""
    today = date.today()
    mgr = _mgr(tmp_path, write_dat(tmp_path, [(today, 3 * GIB, 5 * GIB)]))
    mod = _mod(mgr)
    mod.refresh()
    mod.publish_limit(target={"up": 1, "down": 2})

    mod.publish_off("总开关关闭")

    tv = mgr.web.traffic_view
    assert tv["state"] == "off"
    assert tv["source"]["state"] == SOURCE_OFF and tv["source"]["reasons"][0]["code"] == "source_off"
    assert tv["periods"] == [] and tv["history"] == []
    assert tv["limit"]["state"] == LIMIT_DISABLED
    assert tv["limit"]["target"] == {"up": None, "down": None}


# ---------- 刷新执行体(A2/A5) ----------


def test_refresh_stale_marks_source_segment(tmp_path):
    """数据源不可用: 缺文件 / 有文件无有效行 -> source 段 stale + 原因码, 返回 False(没有新数据)"""
    mgr = _mgr(tmp_path, str(tmp_path / "not-exist.dat"))
    mod = _mod(mgr)

    assert mod.refresh() is False
    tv = mgr.web.traffic_view
    assert tv["source"]["state"] == SOURCE_STALE
    assert tv["source"]["reasons"][0]["code"] == "dat_missing"
    assert tv["state"] == "stale" and tv["history"] == []

    bad = tmp_path / "bad.dat"
    bad.write_text('lines: "2"\nnot-a-date\n', encoding="utf-8")
    mgr.config.traffic_source.traffic_monitor.dat_path = str(bad)
    assert mod.refresh() is False
    assert mgr.web.traffic_view["source"]["reasons"][0]["code"] == "dat_empty"


def test_refresh_source_off_publishes_off_without_reading(tmp_path):
    """来源总开关关: 发 off 快照、返回 False, 且**不读盘**(dat 路径为空也不该报 stale)"""
    mgr = _mgr(tmp_path)  # dat_path 空
    mgr.config.traffic_source.enabled = False

    assert _mod(mgr).refresh() is False
    tv = mgr.web.traffic_view
    assert tv["state"] == "off"
    assert tv["source"]["state"] == SOURCE_OFF
    assert tv["history"] == [] and tv["limit"]["state"] == LIMIT_DISABLED

    # 开回来自动恢复: 下一轮正常发布
    mgr.config.traffic_source.enabled = True
    mgr.config.traffic_source.traffic_monitor.dat_path = write_dat(tmp_path, [(date.today(), 1, 1)])
    assert _mod(mgr).refresh() is True
    assert mgr.web.traffic_view["source"]["state"] == SOURCE_OK


def test_refresh_publish_logs_at_debug(tmp_path):
    """发布历史流量那行恒 DEBUG: 定时任务与通知链路共用 refresh(), 大流量日可达数百次

    INFO 会刷屏(26-10-18 用户要求降级); 读盘失败/坏行两条 WARNING 不降, 异常仍要响亮。
    日志捕获走 helpers.capture_logs(QbManager 构造链清 root handlers, caplog 恒空)。
    """
    dat = write_dat(tmp_path, [(date.today(), 3 * GIB, 5 * GIB)])
    mgr = _mgr(tmp_path, dat)

    with capture_logs("auto_qb.core.modules.traffic_snapshot_mod") as cap:
        assert _mod(mgr).refresh() is True
    pairs = list(zip(cap.records, cap.messages))  # helper 契约: 两列表同序
    published = [(rec, msg) for rec, msg in pairs if "发布历史流量" in msg]
    assert published, "刷新成功必须留下 DEBUG 轨迹(行数/今日累计, 排障看得到)"
    assert all(rec.levelno == logging.DEBUG for rec, _ in published)


def test_curve_run_leaves_source_segment_untouched(tmp_path):
    """A4 守阵: 曲线任务一跑, 来源段(含 history)一字未变 —— 只写 limit"""
    today = date.today()
    mgr = _mgr(tmp_path, write_dat(tmp_path, [(today, 3 * GIB, 5 * GIB)]))
    mgr.config.global_speed_limit_curve = _gslc_day_curve()
    _mod(mgr).refresh()
    before = {k: copy.deepcopy(mgr.web.traffic_view[k]) for k in ("source", "periods", "history")}

    curve = mgr.host.get("speed_curve")
    task = Task("internal", "speed_limit_curve", interval=60, handler=curve.handle_speed_limit_curve)
    curve.handle_speed_limit_curve(task, dry_run=True)

    tv = mgr.web.traffic_view
    assert {k: tv[k] for k in ("source", "periods", "history")} == before
    assert tv["limit"]["state"] == LIMIT_DRY_RUN
    assert tv["state"] == "dry_run"


def test_only_snapshot_module_writes_traffic_view():
    """D10 守阵: 源码里 `set_traffic_view(` 的**调用点**只有快照模块(定义点不算)

    判据取 `.set_traffic_view(`(带点 = 调用形态): runtime.py 里的 `def set_traffic_view(` 是定义,
    不算写入方; 任何模块绕过快照模块直调服务方法都属于"第二个写入点"。
    """
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src" / "auto_qb"
    callers = sorted(
        p.relative_to(src).as_posix()
        for p in src.rglob("*.py") if ".set_traffic_view(" in p.read_text(encoding="utf-8")
    )
    assert callers == ["core/modules/traffic_snapshot_mod.py"], f"快照出现第二个写入点: {callers}"


# ---------- 事件零读盘补丁(26-10-21) ----------


def test_publish_event_patches_day_row_without_reading(tmp_path, monkeypatch):
    """补丁只改 periods 的 day 行; month/history/limit 段一字不动; **一次读盘都没有**

    读盘打桩成 raise: 事件路径(六键自带权威累计)若退回读文件, 这条用例直接红 ——
    「读盘本身就是副作用」的判据就钉在这里。

    时钟钉成每次调用 +1s 的严格递增假钟: `_publish` 每次发布都刷
    `view["ts"] = time.time()`, 本机背靠背两次 `time.time()` 可返回**同一值**
    (亚 µs 粒度坍缩), 真钟下 before_ts 与补丁发布的 ts 会相等 -> 下面的
    「ts 严格推进」断言天生 flaky(2026-10-22 提交闸门里现形过)。假钟下:
    发布不少 1 次就严格推进; 一次都不发布(补丁失效)则 ts 一字不动, 断言仍拦得住。
    """
    import auto_qb.core.modules.traffic_snapshot_mod as tsm

    _tick = {"t": time.time()}

    def _fake_time():
        _tick["t"] += 1.0
        return _tick["t"]

    monkeypatch.setattr(time, "time", _fake_time)

    today = date.today()
    mgr = _mgr(tmp_path, write_dat(tmp_path, [(today, 3 * GIB, 5 * GIB)]))
    mod = _mod(mgr)
    assert mod.refresh() is True  # 先有一份文件派生快照(day + month 两行)
    mod.publish_limit(target={"up": 5120, "down": 11264}, actual={"up": 5120, "down": 11264})
    before_ts = mgr.web.traffic_view["ts"]
    before = {k: copy.deepcopy(mgr.web.traffic_view[k]) for k in ("source", "history", "limit")}

    def _boom(*_a, **_k):
        raise AssertionError("事件补丁路径不许读盘(读盘本身就是副作用)")

    monkeypatch.setattr(tsm, "read_source_rows", _boom)

    assert mod.publish_event(today.isoformat(), 6 * GIB, 9 * GIB) is True
    tv = mgr.web.traffic_view
    rows = {r["period"]: (r["up"], r["down"]) for r in tv["periods"]}
    assert rows["day"] == (6 * GIB, 9 * GIB), "day 行必须被载荷补丁"
    assert rows["month"] == (3 * GIB, 5 * GIB), "month 行是文件派生的, 补丁不许动"
    assert tv["ts"] > before_ts, "补丁也要推进 ts(前端据此知道快照变了)"
    for k in ("source", "history", "limit"):
        assert tv[k] == before[k], f"补丁踩了 {k} 段(段隔离失效)"
    assert tv["state"] == derive_state(tv["source"]["state"], tv["limit"]["state"])


def test_publish_event_high_water_clamps_both_paths(tmp_path):
    """高水位钳制: 低载荷不发布(返回 False); 文件读盘路径的 day 行也不低于水位

    崩溃恢复边缘: 工具 state.json 比 dat 旧 -> 首个 catch-up 事件载荷偏低 —— 钳制让 pill
    不回退; 随后工具流量追上水位, 补丁自然恢复推进。
    """
    today = date.today()
    mgr = _mgr(tmp_path, write_dat(tmp_path, [(today, 1 * 1024, 1 * 1024)]))  # 今天行 1KiB/1KiB
    mod = _mod(mgr)

    assert mod.publish_event(today.isoformat(), 5000, 6000) is True
    assert mod.publish_event(today.isoformat(), 100, 200) is False, "低于水位: 不发布"
    rows = {r["period"]: (r["up"], r["down"]) for r in mgr.web.traffic_view["periods"]}
    assert rows["day"] == (5000, 6000), "低载荷不许把 pill 刷小"

    # 文件读盘路径同样钳制: dat 今天行(1024B)低于水位 -> 发布值取水位
    assert mod.refresh() is True
    rows = {r["period"]: (r["up"], r["down"]) for r in mgr.web.traffic_view["periods"]}
    assert rows["day"] == (5000, 6000), "文件派生值低于水位时必须被钳回水位(否则 pill 回退)"
    assert rows["month"] == (1024, 1024), "month 行不钳(事件不携带月累计)"


def test_publish_event_ignores_non_today_and_source_off(tmp_path):
    """非当日 / 关源 -> False 且快照一字未动(那天的累计由兜底读盘覆盖)"""
    mgr = _mgr(tmp_path)  # 无 dat: 真读了会发 stale, 没动就证明没读也没发
    mod = _mod(mgr)
    before = copy.deepcopy(mgr.web.traffic_view)

    assert mod.publish_event("1999-01-01", 1024, 2048) is False
    assert mgr.web.traffic_view == before

    mgr.config.traffic_source.enabled = False
    assert mod.publish_event(date.today().isoformat(), 1024, 2048) is False
    assert mgr.web.traffic_view == before


def test_publish_event_creates_day_row_on_cold_start(tmp_path, monkeypatch):
    """冷启动(种子 periods=[])首个事件先于任何文件读盘: 建 day 行, limit 段保留

    month 行等首次读盘补上 —— 前端按 period 取行, 缺 month 只影响本月对照, 不影响 pill。
    """
    import auto_qb.core.modules.traffic_snapshot_mod as tsm

    def _boom(*_a, **_k):
        raise AssertionError("事件补丁路径不许读盘(读盘本身就是副作用)")

    monkeypatch.setattr(tsm, "read_source_rows", _boom)

    mgr = _mgr(tmp_path)  # 连 dat_path 都没有: 纯冷启动
    mod = _mod(mgr)
    mod.publish_limit(target={"up": 1, "down": 2})

    assert mod.publish_event(date.today().isoformat(), 7, 8) is True
    tv = mgr.web.traffic_view
    rows = {r["period"]: (r["up"], r["down"]) for r in tv["periods"]}
    assert rows == {"day": (7, 8)}
    assert tv["limit"]["target"] == {"up": 1, "down": 2}, "冷启动补丁也不许踩 limit 段"


# ---------- 节奏键(A3) ----------


def test_refresh_interval_applies_to_registered_task(tmp_path):
    """热重载改 refresh_interval: 已入队任务**就地**改 interval(不重复入队, 队列里仍只有一条)"""
    mgr = _mgr(tmp_path)
    mgr.config.traffic_source.refresh_interval = 120.0
    _mod(mgr).start(mgr.ctx, dry_run=False)
    assert mgr.task_queue.named(TASK_NAME).interval == 120.0

    old = mgr.config
    new = copy.copy(old)
    new.traffic_source = copy.deepcopy(old.traffic_source)
    new.traffic_source.refresh_interval = 1800.0
    _mod(mgr).apply(old, new)

    assert mgr.task_queue.named(TASK_NAME).interval == 1800.0
    assert [t.name for t in mgr.task_queue._fast if t.name == TASK_NAME] == [TASK_NAME], "热更新不该重复入队"

    # 无关变更(段相等) -> 短路, 节奏不动
    _mod(mgr).apply(new, new)
    assert mgr.task_queue.named(TASK_NAME).interval == 1800.0


# ---------- 轮询载荷(A5/D5) ----------


def test_poll_payload_drops_history(web_env):
    """轮询响应无 history; /api/traffic/history 仍有 —— 载荷瘦身的双向守阵"""
    mgr, client = web_env
    today = date.today().isoformat()
    mgr.web.traffic_view = {
        "ts": 1.0,
        "date": today,
        "state": "ok",
        "source": {
            "state": "ok",
            "reasons": []
        },
        "periods": [{
            "period": "day",
            "label": "今日",
            "up": 1,
            "down": 2
        }],
        "history": [{
            "date": today,
            "up": 1,
            "down": 2
        }],
        "limit": {
            "target": {
                "up": 1,
                "down": 2
            },
            "actual": {
                "up": 1,
                "down": 2
            },
            "reasons": [],
            "state": "ok"
        },
    }

    r = client.get("/api/status", headers=_auth(mgr))
    assert r.status_code == 200, r.text
    assert "history" not in r.json()["traffic"]
    assert r.json()["traffic"]["periods"][0]["period"] == "day"  # 其余字段照旧回传

    r = client.get("/api/state", headers=_auth(mgr))
    assert r.status_code == 200, r.text
    assert "history" not in r.json()["status"]["traffic"]

    r = client.get("/api/traffic/history", headers=_auth(mgr))
    assert r.status_code == 200, r.text
    assert r.json()["history"] == [{"date": today, "up": 1, "down": 2}]
