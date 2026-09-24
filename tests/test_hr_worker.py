"""test_hr_worker 测试计划: 取数线程与只读视图发布(计划 §8)

## 测试计划(每个测试函数一条)
- test_publisher_only_bumps_revision_on_change: 视图内容实质变化才抬 revision(否则主循环白忙)
- test_publisher_snapshot_is_consistent: 一次取到 (revision, views) 不撕裂
- test_signature_ignores_generated_at: 只有 generated_at 变(时间流逝)不算变化
- test_signature_tracks_channel_state_flip: 通道状态翻转要算变化(它改变告警与展示)
- test_run_once_refreshes_and_publishes: 一轮刷新建索引并发布视图(revision 1)
- test_run_once_keeps_revision_when_reusing: 数据仍在有效期 -> 复用 -> 视图不变 -> revision 不抬
- test_run_once_logs_no_channel_once_per_state: 无通道告警只报一次(分钟级轮询不得刷通知)
- test_run_once_warns_on_partial_refresh: 刷新不完备(疑似改版) -> WARNING(service 不报这条)
- test_pacing_is_info_not_warning_and_not_repeated: **被自己频控拦下**的 partial / 未到点 waiting 只记 INFO(
  绝不 WARNING —— 会被 notify 推成系统通知), 且同状态不逐轮刷(数字抹掉后同键)
- test_pacing_state_reminds_once_per_window: 节流态持续时按 channel_silence_warn 周期提醒一次(不静默消失)
- test_worker_does_not_repeat_alert_owned_by_producer: 已由产生处告警的事件只记 INFO(不重复 WARNING)
- test_stable_key_erases_countdowns: 状态指纹抹掉数字(倒计时变化不算状态变化)
- test_worker_refresh_forgets_pacing_memory: 完整刷新后清节流记忆(下次再卡住要重新说明白)
- test_silence_reminder_is_throttled: 通道静默按 channel_silence_warn 周期提醒一次
- test_stop_without_start_is_ok: 未启动就 stop 不得报错
- test_start_wake_and_stop: 线程能起、能被唤醒立刻干活、能停干净
- test_anchors_provider_failure_is_ignored: 主循环提供锚点失败不影响刷新
- test_no_sites_publishes_empty_view: 没有启用站点时不发布也不崩
- test_loop_survives_round_exception: 单轮异常不打死线程
- test_revision_bumps_when_data_changes: 数据实质变化(新增条目) -> revision 抬升
"""
import logging
import time

from auto_qb.hr.fetcher import NullFetcher
from auto_qb.hr.model import CHANNEL_OK, CHANNEL_SILENT
from auto_qb.hr.resolve import HrSiteView, HrViewSet
from auto_qb.hr.service import ACTION_ERROR, ACTION_NO_CHANNEL, ACTION_PARTIAL, ACTION_REFRESHED, ACTION_REUSED, \
    REASON_BUDGET, HrRefreshResult, HrRefreshService
from auto_qb.hr.worker import HrViewPublisher, HrWorker, stable_key, view_signature
from hr_helpers import EMPTY_TABLE_PAGE, REVISED_PAGE, Clock, FakeFetcher, global_conf, myhr_page, row, site_conf, \
    torrent_blob

TID_A = 313852
TID_B = 313997


def _blobs(*tids: int):
    return {tid: torrent_blob(f"t{tid}.bin") for tid in tids}


def _pages(*tids: int):
    """三个档位都给同一批行(完整刷新: 覆盖证明成立)"""
    page = myhr_page([row(tid) for tid in tids])
    return {"A": page, "B": page, "C": page}


def _service(tmp_path, fetcher, *, global_overrides=None, persist=True, allow_fetch=True, clock=None):
    return HrRefreshService(
        data_dir=str(tmp_path),
        global_conf=global_conf(**(global_overrides or {})),
        site_confs={"pt.example.com": site_conf()},
        fetcher=fetcher,
        persist=persist,
        allow_fetch=allow_fetch,
        now_fn=clock or time.time,
    )


def _view(revision=1, channel_state=CHANNEL_OK) -> HrSiteView:
    return HrSiteView(site="pt.example.com", mode="partial", revision=revision, channel_state=channel_state)


def _wait_until(pred, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.02)
    return False


# ---------- 发布器 ----------


def test_publisher_only_bumps_revision_on_change():
    publisher = HrViewPublisher()
    assert publisher.revision == 0 and publisher.latest().views == {}
    assert publisher.publish(HrViewSet(views={}, generated_at=1.0)) is False, "空视图没有可观测变化"
    assert publisher.publish(HrViewSet(views={"pt.example.com": _view()}, generated_at=1.0)) is True
    assert publisher.revision == 1
    assert publisher.publish(HrViewSet(views={"pt.example.com": _view()}, generated_at=9.0)) is False, \
        "同样的内容不抬版本(只有 generated_at 变)"
    assert publisher.revision == 1
    assert publisher.publish(HrViewSet(views={"pt.example.com": _view(revision=2)}, generated_at=9.0)) is True, \
        "站点文件 revision 变化算变化"
    assert publisher.revision == 2


def test_publisher_snapshot_is_consistent():
    publisher = HrViewPublisher()
    views = HrViewSet(views={}, generated_at=7.0)
    publisher.publish(views)
    rev, got = publisher.snapshot()
    assert rev == publisher.revision and got is publisher.latest()


def test_signature_ignores_generated_at():
    assert view_signature(HrViewSet(views={},
                                    generated_at=100.0)) == view_signature(HrViewSet(views={}, generated_at=999.0))


def test_signature_tracks_channel_state_flip():
    ok = HrViewSet(views={"pt.example.com": _view(channel_state=CHANNEL_OK)})
    silent = HrViewSet(views={"pt.example.com": _view(channel_state=CHANNEL_SILENT)})
    assert view_signature(ok) != view_signature(silent), "通道状态翻转必须抬版本(否则静默告警不会触发)"


# ---------- 取数线程 ----------


def test_run_once_refreshes_and_publishes(tmp_path):
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)))
    publisher = HrViewPublisher()
    worker = HrWorker(service=service, publisher=publisher, poll_interval=60.0)
    results = worker.run_once()
    assert [r.action for r in results] == [ACTION_REFRESHED]
    assert publisher.revision == 1
    view = publisher.latest().get("pt.example.com")
    assert view is not None
    # 反查表同时收 v1/v2(同一个种子最多两个键), 所以按 tid 集合断言而不是计数
    assert {e.tid for e in view.by_infohash.values()} == {TID_A}
    assert worker.rounds == 1 and worker.last_run_ts > 0


def test_run_once_keeps_revision_when_reusing(tmp_path):
    fetcher = FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A))
    service = _service(tmp_path, fetcher)
    publisher = HrViewPublisher()
    worker = HrWorker(service=service, publisher=publisher, poll_interval=60.0)
    worker.run_once()
    first = publisher.revision
    assert [r.action for r in worker.run_once()] == [ACTION_REUSED], "有效期内复用, 不写盘"
    assert publisher.revision == first, "数据没变化 => 版本不抬(主循环零工作)"
    assert len(fetcher.text_calls) == 3, "第二轮零请求"


def test_run_once_logs_no_channel_once_per_state(tmp_path, caplog):
    service = _service(tmp_path, NullFetcher("没通道"))
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0)
    with caplog.at_level(logging.DEBUG, logger="auto_qb.hr"):
        worker.run_once()
        worker.run_once()
        worker.run_once()
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING and "通道" in r.getMessage()]
    assert len(warnings) == 1, f"无通道只报一次(否则每分钟一条系统通知): {[w.getMessage() for w in warnings]}"
    assert [r.action for r in worker.last_results] == [ACTION_NO_CHANNEL]


def test_run_once_warns_on_partial_refresh(tmp_path, caplog):
    # 三个档位都返回「没有 HR 表」的页面: 覆盖证明不成立 => partial(疑似改版), service 不报这条
    pages = {"A": REVISED_PAGE, "B": REVISED_PAGE, "C": REVISED_PAGE}
    service = _service(tmp_path, FakeFetcher(pages=pages))
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0)
    with caplog.at_level(logging.WARNING, logger="auto_qb.hr.worker"):
        worker.run_once()
    assert [r.action for r in worker.last_results] == [ACTION_PARTIAL]
    assert any(r.levelno >= logging.WARNING for r in caplog.records), "改版信号必须告警"


def test_pacing_partial_is_info_not_warning_and_not_repeated(tmp_path, caplog):
    """被**自己频控**拦下: 只记一条 INFO(绝不 WARNING), 且 partial↔waiting 交替不刷屏

    用户实报(2026-09-24): 这两个状态本会持续几小时, 却按分钟级轮询打出 WARNING ⇒ notify 推成
    系统通知 ⇒ 弹窗淹没。去重按「被拦的根因」(间隔/配额/熔断…) 而不是「本轮返回了哪个 action」——
    同一个「等间隔」在轮次间会分别表现为 partial(首页抓到、第二页被拦)与 waiting。
    """
    clock = Clock()
    pages = {"A": myhr_page([row(TID_A)], has_next=True), "B": EMPTY_TABLE_PAGE, "C": EMPTY_TABLE_PAGE}
    service = _service(
        tmp_path,
        FakeFetcher(pages=pages, blobs=_blobs(TID_A)),
        clock=clock,
        global_overrides={"min_torrent_interval": 3600.0},
    )
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0, now_fn=clock)

    with caplog.at_level(logging.DEBUG, logger="auto_qb.hr.worker"):
        worker.run_once()  # 第一页抓到、第二页被自己的间隔拦住 => partial(budget, 根因=间隔)
        clock.advance(61.0)  # 过掉截断轮次的 60s 短暂有效期
        worker.run_once()  # 未到可取时刻 => waiting(同一根因)
        clock.advance(1.0)
        worker.run_once()  # 同上(倒计时数字变了, 抹掉后同键)

    assert not [r for r in caplog.records if r.levelno >= logging.WARNING], \
        f"频控截断不是故障, 不得 WARNING: {[(r.levelname, r.getMessage()) for r in caplog.records]}"
    notes = [r for r in caplog.records if r.levelno == logging.INFO and "节流中" in r.getMessage()]
    assert len(notes) == 1, f"一整个等间隔时期只说明白一次: {[n.getMessage() for n in notes]}"
    assert "非故障" in notes[0].getMessage()
    assert any(r.levelno == logging.DEBUG and "节流中" in r.getMessage() for r in caplog.records), \
        "被去重的轮次仍要留在 DEBUG(排障时要看得见每轮到底在等什么)"


def test_pacing_state_reminds_once_per_window(tmp_path, caplog):
    """节流态持续时按 channel_silence_warn 周期提醒一次(既不满屏也不静默消失)"""
    clock = Clock()
    pages = {"A": myhr_page([row(TID_A)], has_next=True), "B": EMPTY_TABLE_PAGE, "C": EMPTY_TABLE_PAGE}
    service = _service(
        tmp_path,
        FakeFetcher(pages=pages, blobs=_blobs(TID_A)),
        clock=clock,
        global_overrides={
            "min_torrent_interval": 3600.0,
            "channel_silence_warn": 120.0
        },
    )
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0, now_fn=clock)

    with caplog.at_level(logging.INFO, logger="auto_qb.hr.worker"):
        worker.run_once()  # partial(根因=间隔)
        clock.advance(121.0)  # 超过一个提醒窗口
        worker.run_once()  # waiting(同根因, 但到点了 => 再提醒一次)

    notes = [r for r in caplog.records if "节流中" in r.getMessage()]
    assert len(notes) == 2, f"超过一个提醒窗口后应再记一次: {[n.getMessage() for n in notes]}"


def test_worker_refresh_forgets_pacing_memory(tmp_path, caplog):
    """真有进展(完整刷新)后清掉节流记忆: 下次再卡住要重新说明白, 不能默默吞掉

    这一条直接驱 `_note`(日志策略的单测): 端到端很难在同一个小时窗口里既完成完整刷新
    又恰好再次被频控拦住(完整刷新要多次请求, 而配额就是按请求计的)。
    """
    clock = Clock()
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)), clock=clock)
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0, now_fn=clock)
    pacing = HrRefreshResult(
        site="pt.example.com", action=ACTION_PARTIAL, reason="配额/间隔受限(间隔: 还差 104s)", reason_kind=REASON_BUDGET
    )
    done = HrRefreshResult(site="pt.example.com", action=ACTION_REFRESHED, reason="")

    with caplog.at_level(logging.DEBUG, logger="auto_qb.hr.worker"):
        worker._note("pt.example.com", pacing)  # 说一次
        worker._note("pt.example.com", pacing)  # 同根因 => 不重复(DEBUG)
        worker._note("pt.example.com", done)  # 进展 => 清记忆
        worker._note("pt.example.com", pacing)  # 再卡住 => 重新说一次

    notes = [r for r in caplog.records if r.levelno == logging.INFO and "节流中" in r.getMessage()]
    assert len(notes) == 2, f"清掉记忆后应重新说明白: {[n.getMessage() for n in notes]}"


def test_worker_does_not_repeat_alert_owned_by_producer(tmp_path, caplog):
    """已由产生处告警的事件(取数失败 / 文件读坏): 状态层只记 INFO, 不再打第二条 WARNING"""
    clock = Clock()
    service = _service(tmp_path, FakeFetcher({}, {}, fail_text_at={"A": "429 Too Many Requests"}), clock=clock)
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0, now_fn=clock)

    with caplog.at_level(logging.DEBUG, logger="auto_qb.hr"):
        worker.run_once()

    assert [r.action for r in worker.last_results] == [ACTION_ERROR]
    by_level = [(r.levelname, r.getMessage()) for r in caplog.records if r.levelno >= logging.WARNING]
    assert len([1 for _lv, msg in by_level if "取数失败" in msg]) == 1, \
        f"一次超时只该有一条 WARNING(产生处那条): {by_level}"
    assert any("已在取数处告警" in r.getMessage() and r.levelno == logging.INFO for r in caplog.records), \
        "状态变化仍要留一条 INFO(排障要看得到它何时开始出错)"


def test_stable_key_erases_countdowns():
    """状态指纹抹掉数字: 倒计时变化不算状态变化(否则就是逐轮刷屏的根因)"""
    assert stable_key("未到可取时刻(间隔, 还差 104s)") == stable_key("未到可取时刻(间隔, 还差 51s)")
    assert stable_key("a") != stable_key("b")


def test_silence_reminder_is_throttled(tmp_path, caplog):
    clock = Clock()
    service = _service(
        tmp_path,
        FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)),
        clock=clock,
        global_overrides={"channel_silence_warn": 3600.0}
    )

    class _Endpoint:
        last_contact_ts = 0.0

    worker = HrWorker(
        service=service, publisher=HrViewPublisher(), endpoint=_Endpoint(), poll_interval=60.0, now_fn=clock
    )
    with caplog.at_level(logging.WARNING, logger="auto_qb.hr.worker"):
        worker.run_once()  # 刚起: 不告警
        assert not [r for r in caplog.records if "静默" in r.getMessage()]
        clock.advance(3601.0)
        worker.run_once()
        clock.advance(10.0)
        worker.run_once()  # 距上次提醒才 10s: 必须被节流
        clock.advance(3601.0)
        worker.run_once()
    quiet = [r.getMessage() for r in caplog.records if "静默" in r.getMessage()]
    assert len(quiet) == 2, f"每个 warn_gap 只提醒一次: {quiet}"


def test_stop_without_start_is_ok(tmp_path):
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)))
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0)
    assert worker.stop(timeout=0.1) is True
    assert not worker.started


def test_start_wake_and_stop(tmp_path):
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)))
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=30.0)
    worker.start()
    try:
        assert worker.started
        assert _wait_until(lambda: worker.rounds >= 1), "启动后应立刻检查一轮(不等 poll_interval)"
        worker.wake()
        assert _wait_until(lambda: worker.rounds >= 2), "wake() 要能打断等待立刻干活"
    finally:
        assert worker.stop(timeout=5.0)
    assert not worker.started


def test_anchors_provider_failure_is_ignored(tmp_path, caplog):
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)))

    def boom():
        raise RuntimeError("主循环侧取锚点失败")

    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0, anchors_fn=boom)
    with caplog.at_level(logging.WARNING, logger="auto_qb.hr.worker"):
        results = worker.run_once()
    assert results[0].action == ACTION_REFRESHED, "锚点失败不影响刷新"
    assert any("锚点" in r.getMessage() for r in caplog.records)


def test_no_sites_publishes_empty_view(tmp_path):
    service = _service(tmp_path, FakeFetcher(pages={}))
    service.site_confs["pt.example.com"] = site_conf(mode="off")
    publisher = HrViewPublisher()
    worker = HrWorker(service=service, publisher=publisher, poll_interval=60.0)
    assert worker.run_once() == []
    assert publisher.revision == 0


def test_loop_survives_round_exception(tmp_path, caplog, monkeypatch):
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)))
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=0.05)
    calls = {"n": 0}
    original = worker.run_once

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("第一轮炸了")
        return original()

    monkeypatch.setattr(worker, "run_once", flaky)
    with caplog.at_level(logging.ERROR, logger="auto_qb.hr.worker"):
        worker.start()
        try:
            assert _wait_until(lambda: calls["n"] >= 2), "单轮异常后线程要继续跑下一轮"
        finally:
            worker.stop(timeout=5.0)
    assert any("单轮异常" in r.getMessage() for r in caplog.records)


def test_revision_bumps_when_data_changes(tmp_path):
    clock = Clock()
    fetcher = FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A, TID_B))
    service = _service(tmp_path, fetcher, clock=clock)
    publisher = HrViewPublisher()
    worker = HrWorker(service=service, publisher=publisher, poll_interval=60.0, now_fn=clock)
    worker.run_once()
    assert publisher.revision == 1
    clock.advance(13 * 3600.0)  # 超过 refresh_interval: 数据过期, 必须重新抓
    fetcher.pages = _pages(TID_A, TID_B)
    worker.run_once()
    assert publisher.revision == 2, "数据实质变化(新增一条) => 版本抬升"
    assert {e.tid for e in publisher.latest().get("pt.example.com").by_infohash.values()} == {TID_A, TID_B}
