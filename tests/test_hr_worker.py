"""test_hr_worker 测试计划: 取数线程与只读视图发布(计划 §8)

## 测试计划(每个测试函数一条)
- test_publisher_only_bumps_revision_on_change: 视图内容实质变化才抬 revision(否则主循环白忙)
- test_publisher_snapshot_is_consistent: 一次取到 (revision, views) 不撕裂
- test_signature_ignores_generated_at: 只有 generated_at 变(时间流逝)不算变化
- test_signature_tracks_channel_state_flip: 通道状态翻转要算变化(它改变告警与展示)
- test_run_once_refreshes_and_publishes: 一轮刷新建索引并发布视图(revision 1)
- test_start_publishes_disk_views_before_first_wave: 冷启动先把**磁盘既有结论**发布出去(不得留判定真空期)
- test_run_once_keeps_revision_when_reusing: 数据仍在有效期 -> 复用 -> 视图不变 -> revision 不抬
- test_run_once_logs_no_channel_once_per_state: 无通道告警只报一次(分钟级轮询不得刷通知)
- test_run_once_warns_on_parse_breakdown: 全档「没有 HR 表」(疑似改版) -> error + 告警(service 不报这条)
- test_pacing_partial_is_info_not_warning_and_not_repeated: **被自己频控拦下**的 partial / 未到点 waiting 只记 INFO(
  绝不 WARNING —— 会被 notify 推成系统通知), 且同状态不逐轮刷(数字抹掉后同键)
- test_pacing_state_reminds_once_per_window: 节流态持续时按 channel_silence_warn 周期提醒一次(不静默消失)
- test_worker_does_not_repeat_alert_owned_by_producer: 已由产生处告警的事件只记 INFO(不重复 WARNING)
- test_stable_key_erases_countdowns: 状态指纹抹掉数字(倒计时变化不算状态变化)
- test_worker_refresh_forgets_pacing_memory: 完整刷新后清节流记忆(下次再卡住要重新说明白)
- test_silence_reminder_is_throttled: 通道静默按 channel_silence_warn 周期提醒一次
- test_silence_warning_names_affected_sites: 通道静默是**端点级**事件 ⇒ 文案里要列出受影响站点(M4 四类事件)
- test_silence_is_quiet_when_nobody_watching: 无人在用 WebUI 且无被拒敲门 ⇒ 预期离线, 只进后端 log(hr_silent)
- test_silence_is_visible_when_web_active: WebUI 活跃 + 扩展未联系 ⇒ 可见告警(不静默, 口径⑤)
- test_silence_names_rejected_root_cause: 有被拒敲门(401/403) ⇒ 文案指名 token / origin 根因
- test_stop_without_start_is_ok: 未启动就 stop 不得报错
- test_start_wake_and_stop: 线程能起、能被唤醒立刻干活、能停干净
- test_anchors_provider_failure_is_ignored: 主循环提供锚点失败不影响刷新
- test_no_sites_publishes_empty_view: 没有启用站点时不发布也不崩
- test_loop_survives_round_exception: 单轮异常不打死线程
- test_revision_bumps_when_data_changes: 数据实质变化(新增条目) -> revision 抬升

### hr 首轮变异审计轮: 取数线程长尾(issue 26-10-10-1108-runtime-worker)
- test_stable_key_blank_and_none_inputs: 空串/None 输入 -> 空串(不落 "XXXX")
- test_pacing_class_unknown_and_blank: 未命中类别回落稳定指纹; 空串 -> 空串
- test_view_signature_rounds_healthy_ts_to_three_places: 指纹里的健康时刻按 3 位取整
- test_worker_init_defaults: 线程名 / poll 下界 / 各初始计数位
- test_start_message_and_thread_props: 启动 INFO 报间隔与站点(多站), 线程名/daemon/起始位
- test_start_message_no_sites_placeholder: 无启用站点 -> 「站点: (无)」
- test_stop_cancels_fetch_channel_with_reason: stop 先叫停取数通道并带上原因串
- test_stop_clean_reports_and_clears_handle: 干净退出: 留 INFO + 清线程句柄
- test_stop_keeps_thread_handle_when_not_exited: 未退出: 留句柄 + ERROR 说明
- test_stop_default_timeout_is_ten_seconds: stop 缺省等待上限 10s(契约)
- test_wake_increments_sequence: wake 递增唤醒序号(每次 +1)
- test_request_refresh_accumulates_and_bumps_seq: 受理累加(不覆盖) + 唤醒序号递增
- test_request_refresh_logs_accepted_sites: 受理日志精确报出站点清单
- test_run_once_hands_site_anchors_three_state: 锚点三态交接(None / 映射 / 缺键 {})
- test_run_once_records_note_under_site: _note 以站点为键记账
- test_build_views_prefers_memory_snapshot: 本轮结果的内存快照覆盖已落盘视图; generated_at 取现读时钟
- test_note_logs_normal_action_only_on_change: 正常动作只在变化时记一条, 缺省文案「正常」
- test_note_pacing_key_and_message: 节流键取自原因; 缺省文案「正常」; 精确文案
- test_note_warn_gap_floor_and_exact_boundary: 非节流告警的 warn_gap 下界 60s 且「恰好到点」即再报
- test_note_pacing_reminder_fires_at_exact_gap: 节流态持续时恰好满一个 warn_gap 即再说明一次
- test_note_warn_message_names_site_and_action: 改版告警文案点名站点与动作
- test_note_info_branch_message: 非告警动作走 INFO 分支并带站点与动作
- test_silence_reference_prefers_last_contact: 静默基准优先「上次联系时刻」(非启动时刻)
- test_silence_reference_defaults_when_attr_missing: 端点缺 last_contact_ts/rejected_contacts 时保守缺省
- test_silence_where_labels_both_branches: 「启动以来」/「上次联系后」两分支各自精确
- test_silence_gap_floor_and_exact_boundary: 静默 gap 下界 60s; 恰好到点即出声
- test_silence_rejected_threshold_is_positive: 被拒计数 >0 即算被拒(不是 >1)
- test_silence_hours_value_uses_3600: 静默小时数 = 秒 / 3600(展示取整可辨)
- test_silence_event_tag_sets_domain: 静默出口挂通道层标签(hr_domain)
"""
import logging
import threading
import time

from auto_qb.hr.fetcher import NullFetcher
from auto_qb.hr.model import CHANNEL_OK, CHANNEL_SILENT
from auto_qb.hr.resolve import HrIdentity, HrSiteView, HrViewSet, judge_record
from auto_qb.hr.service import ACTION_ERROR, ACTION_NO_CHANNEL, ACTION_PARTIAL, ACTION_REFRESHED, ACTION_REUSED, \
    ACTION_WAITING, REASON_BUDGET, HrRefreshResult, HrRefreshService
import auto_qb.hr.worker as worker_module
from auto_qb.hr import events
from auto_qb.hr.fetcher import HrFetchError, NullFetcher
from auto_qb.hr.worker import HrViewPublisher, HrWorker, pacing_class, stable_key, view_signature
from auto_qb.infra.logging import DOMAIN_ATTR
from helpers import capture_logs
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
    return HrSiteView(site="pt.example.com", listing="list", revision=revision, channel_state=channel_state)


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


class _BlockingFetcher:
    """永远卡在取数上的假通道: 让第一轮波次跑不完, 用来证明「发布不依赖第一轮跑完」"""
    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()

    def get_text(self, url: str) -> str:
        self.entered.set()
        self.release.wait(10.0)
        return EMPTY_TABLE_PAGE

    def get_bytes(self, url: str) -> bytes:
        return self.get_text(url).encode()


def test_start_publishes_disk_views_before_first_wave(tmp_path):
    """冷启动先把**磁盘既有结论**发布出去 —— 第一波跑完前不得出现「判定真空期」

    2026-09-29 实报: 重启后 `view_revision` 仍为 0(第一波受站点最小间隔约束要跑数小时, 待回填的
    .torrent 越积越久), 108 个种子 `hr_state` **全是空串** ⇒ 界面全回落本地兜底; 而站点文件里
    B 档命中与放行记录都在。修复 = `_loop` 在首轮取数**之前**先发布一次 `build_views()`。
    """
    clock = Clock()
    first = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)), clock=clock)
    HrWorker(service=first, publisher=HrViewPublisher(), poll_interval=60.0).run_once()
    data, _err = first.store("pt.example.com").read_unlocked()
    h = data.index[TID_A].infohash_v1
    assert h, "第一轮应已登记身份(否则本用例前提不成立)"
    clock.advance(13 * 3600)  # 越过复用窗: 第二轮必须真的去取数

    stuck = _BlockingFetcher()
    service = _service(tmp_path, stuck, clock=clock)
    publisher = HrViewPublisher()
    worker = HrWorker(service=service, publisher=publisher, poll_interval=60.0, now_fn=clock)
    assert publisher.revision == 0
    worker.start()
    try:
        assert stuck.entered.wait(3.0), "用例前提: 第一轮应已卡进取数(波次确实没跑完)"
        assert publisher.revision >= 1, "第一轮跑完前就必须发布磁盘既有结论"
        view = publisher.latest().get("pt.example.com")
        assert view is not None and h in view.lane_terminal, "磁盘上的终态命中要进视图"
        judged = judge_record(view, (h, ), now=clock())
        assert judged is not None and judged.identity is HrIdentity.RELEASED, "判定侧立刻可用"
    finally:
        stuck.release.set()
        worker.stop()


def test_run_once_refreshes_and_publishes(tmp_path):
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)))
    publisher = HrViewPublisher()
    worker = HrWorker(service=service, publisher=publisher, poll_interval=60.0)
    results = worker.run_once()
    assert [r.action for r in results] == [ACTION_REFRESHED]
    assert publisher.revision == 1
    view = publisher.latest().get("pt.example.com")
    assert view is not None
    # 行同时在 A/B/C 三档页出现 → 波内逐档覆盖, 最终档位取最后一次见到(C, 终态)
    assert {e.tid for e in view.lane_terminal.values()} == {TID_A}
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


def test_run_once_warns_on_parse_breakdown(tmp_path, caplog):
    # 三个档位都返回「没有 HR 表」的页面: 全档失效 => error(疑似改版), service 侧已告警一次
    pages = {"A": REVISED_PAGE, "B": REVISED_PAGE, "C": REVISED_PAGE}
    service = _service(tmp_path, FakeFetcher(pages=pages))
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0)
    with caplog.at_level(logging.WARNING, logger="auto_qb.hr"):
        worker.run_once()
    assert [r.action for r in worker.last_results] == [ACTION_ERROR]
    assert any(r.levelno >= logging.WARNING for r in caplog.records), "改版信号必须告警"


def test_pacing_partial_is_info_not_warning_and_not_repeated(tmp_path, caplog):
    """被**自己频控**拦下: 只记一条 INFO(绝不 WARNING), 且 partial↔waiting 交替不刷屏

    用户实报(2026-09-24): 这两个状态本会持续几小时, 却按分钟级轮询打出 WARNING ⇒ notify 推成
    系统通知 ⇒ 弹窗淹没。去重按「被拦的根因」(间隔/配额/熔断…) 而不是「本轮返回了哪个 action」——
    同一个「等间隔」在轮次间会分别表现为 partial(首页抓到、第二页被拦)与 waiting。
    """
    clock = Clock()
    service = _service(tmp_path, FakeFetcher(pages={}, blobs={}), clock=clock)
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0, now_fn=clock)
    pacing = HrRefreshResult(
        site="pt.example.com", action=ACTION_PARTIAL, reason="配额/间隔受限(间隔: 还差 104s)", reason_kind=REASON_BUDGET
    )
    waiting = HrRefreshResult(
        site="pt.example.com", action=ACTION_WAITING, reason="未到可取时刻(间隔, 还差 51s)", reason_kind=REASON_BUDGET
    )

    with caplog.at_level(logging.DEBUG, logger="auto_qb.hr.worker"):
        worker._note("pt.example.com", pacing)  # partial(根因=间隔)
        worker._note("pt.example.com", waiting)  # waiting(同一根因)
        clock.advance(1.0)
        worker._note("pt.example.com", waiting)  # 倒计时数字变了, 抹掉后同键

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
    service = _service(tmp_path, FakeFetcher(pages={}, blobs={}), clock=clock)
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0, now_fn=clock)
    pacing = HrRefreshResult(
        site="pt.example.com", action=ACTION_PARTIAL, reason="配额/间隔受限(间隔: 还差 104s)", reason_kind=REASON_BUDGET
    )

    with caplog.at_level(logging.INFO, logger="auto_qb.hr.worker"):
        worker._note("pt.example.com", pacing)  # 说一次
        clock.advance(6 * 3600 + 1)  # 超过一个提醒窗口(v3 常量 CHANNEL_SILENCE_WARN = 6H)
        worker._note("pt.example.com", pacing)  # 同根因但到点了 => 再提醒一次

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


def test_silence_reminder_is_throttled(tmp_path, caplog, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)), clock=clock)

    class _Endpoint:
        last_contact_ts = 0.0
        rejected_contacts = 0

    # web_active=True ⇒ 走**可见**档(WARNING), 这样节流本身才看得见; 静默档走 INFO(见
    # test_silence_is_quiet_when_nobody_watching)
    worker = HrWorker(
        service=service,
        publisher=HrViewPublisher(),
        endpoint=_Endpoint(),
        poll_interval=60.0,
        now_fn=clock,
        web_active_fn=lambda: True,
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


def test_silence_warning_names_affected_sites(tmp_path, caplog, monkeypatch):
    """通道静默是**端点级**事件 ⇒ 文案里要列出受影响站点(只有它能判断后果)

    只说「通道静默」而不说「哪些站点的数据在变旧」, 用户没法判断该不该管它。
    """
    clock = Clock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)), clock=clock)

    class _Endpoint:
        last_contact_ts = 0.0
        rejected_contacts = 0

    worker = HrWorker(
        service=service,
        publisher=HrViewPublisher(),
        endpoint=_Endpoint(),
        poll_interval=60.0,
        now_fn=clock,
        web_active_fn=lambda: True,
    )
    with caplog.at_level(logging.WARNING, logger="auto_qb.hr.worker"):
        clock.advance(3601.0)
        worker.run_once()

    warns = [r.getMessage() for r in caplog.records if "[HR 通道静默]" in r.getMessage()]
    assert len(warns) == 1, f"静默告警要用事件标签前缀: {warns}"
    assert "受影响站点: pt.example.com" in warns[0], "端点级事件必须点出谁受影响"


def test_silence_is_quiet_when_nobody_watching(tmp_path, caplog, monkeypatch):
    """无人在用 WebUI 且无被拒敲门 ⇒ 「预期离线」: 只进后端 log(hr_silent), 不进前端错误历史

    这正是用户实报的那一类(关浏览器过夜) —— 它不该出现在错误历史里(计划 §03.2 / D2①)。
    """
    clock = Clock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)), clock=clock)

    class _Endpoint:
        last_contact_ts = 0.0
        rejected_contacts = 0

    worker = HrWorker(
        service=service,
        publisher=HrViewPublisher(),
        endpoint=_Endpoint(),
        poll_interval=60.0,
        now_fn=clock,
        web_active_fn=lambda: False,
    )
    with caplog.at_level(logging.INFO, logger="auto_qb.hr.worker"):
        clock.advance(3601.0)
        worker.run_once()
    recs = [r for r in caplog.records if "[HR 通道静默]" in r.getMessage()]
    assert len(recs) == 1
    assert recs[0].levelno == logging.INFO, "没人在用 = 预期离线 ⇒ 只进后端 log"
    assert getattr(recs[0], "hr_silent", False) is True, "必须打 silent 标, 否则出口滤不掉"
    assert "浏览器可能未运行" in recs[0].getMessage()


def test_silence_is_visible_when_web_active(tmp_path, caplog, monkeypatch):
    """WebUI 活跃但扩展未联系 ⇒ **可见告警, 不静默**(用户口径⑤)

    只陈述「有人在看 WebUI, 而扩展没在联系」; **不**推断「扩展离线」, 也**不**判断是否同机 / 同源。
    """
    clock = Clock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)), clock=clock)

    class _Endpoint:
        last_contact_ts = 0.0
        rejected_contacts = 0

    worker = HrWorker(
        service=service,
        publisher=HrViewPublisher(),
        endpoint=_Endpoint(),
        poll_interval=60.0,
        now_fn=clock,
        web_active_fn=lambda: True,
    )
    with caplog.at_level(logging.WARNING, logger="auto_qb.hr.worker"):
        clock.advance(3601.0)
        worker.run_once()
    recs = [r for r in caplog.records if "[HR 通道静默]" in r.getMessage()]
    assert len(recs) == 1 and recs[0].levelno == logging.WARNING
    assert getattr(recs[0], "hr_silent", False) is False, "可见档不得标 silent(否则出口会滤掉)"
    assert "有人在看 WebUI" in recs[0].getMessage()


def test_silence_names_rejected_root_cause(tmp_path, caplog, monkeypatch):
    """有被拒敲门(401/403) ⇒ 文案**指名根因**(token / origin), 不让人猜「浏览器是否在运行」

    「有人在敲门但被拒」是后端唯一能证明「不是浏览器离线」的证据(计划 §03.6 / P4)。
    """
    clock = Clock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)), clock=clock)

    class _Endpoint:
        last_contact_ts = 0.0
        rejected_contacts = 3

    worker = HrWorker(
        service=service,
        publisher=HrViewPublisher(),
        endpoint=_Endpoint(),
        poll_interval=60.0,
        now_fn=clock,
        web_active_fn=lambda: False,
    )
    with caplog.at_level(logging.WARNING, logger="auto_qb.hr.worker"):
        clock.advance(3601.0)
        worker.run_once()
    recs = [r for r in caplog.records if "[HR 通道静默]" in r.getMessage()]
    assert len(recs) == 1 and recs[0].levelno == logging.WARNING
    msg = recs[0].getMessage()
    assert "被拒" in msg and "token" in msg, f"被拒敲门要指名根因: {msg}"
    assert getattr(recs[0], "hr_silent", False) is False


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
    service.site_confs["pt.example.com"] = site_conf(enabled=False)
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
    view = publisher.latest().get("pt.example.com")
    assert {e.tid for e in view.lane_terminal.values()} == {TID_A, TID_B}


# ---------------- 立即拉取的 force 通路(计划 26-09-30-0240) ----------------


def test_request_refresh_consumed_once_and_not_left_behind(tmp_path):
    """request_refresh 置旗 → 下一轮消费(force 越过复用窗) → 即时清空不残留(旗标一次性)"""
    fetcher = FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A))
    service = _service(tmp_path, fetcher)
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0)
    worker.run_once()  # 建立数据: 下一轮正常会 REUSED
    requested = worker.request_refresh()
    assert requested == ["pt.example.com"]
    assert [r.action for r in worker.run_once()] == [ACTION_REFRESHED], "force: 复用窗内也应真取数"
    assert [r.action for r in worker.run_once()] == [ACTION_REUSED], "旗标已消费, 不能残留到下一轮"
    assert len(fetcher.text_calls) == 6, "第三轮回零请求(前两轮各 3 页)"


def test_request_refresh_targets_only_named_site(tmp_path):
    """按站触发只影响该站: 未点名的站点仍走正常调度(复用窗内 → REUSED)"""
    fetcher = FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A))
    site_confs = {"alpha": site_conf(), "beta": site_conf()}
    service = HrRefreshService(
        data_dir=str(tmp_path),
        global_conf=global_conf(),
        site_confs=site_confs,
        fetcher=fetcher,
        persist=True,
        allow_fetch=True,
    )
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0)
    worker.run_once()
    assert worker.request_refresh(["alpha", "ghost"]) == ["alpha"], "未启用的站点不受理"
    actions = {r.site: r.action for r in worker.run_once()}
    assert actions["alpha"] == ACTION_REFRESHED, "被点名的站点 force 开波"
    assert actions["beta"] == ACTION_REUSED, "未点名的站点照常复用"
    assert len(fetcher.text_calls) == 9, "首轮两站各 3 页(6) + alpha 第二轮 3 页(3) —— beta 第二轮零请求"


def test_pacing_class_separates_fetch_interval_gate():
    """「拉取间隔」闸门的等待原因进入节流类别且与 min_interval 的「间隔」区分(不刷屏 + 根因可辨)"""
    from auto_qb.hr.worker import pacing_class
    assert pacing_class("未到拉取时刻(拉取间隔, 还差 104s)") == "拉取间隔"
    assert pacing_class("未到拉取时刻(拉取间隔, 还差 51s)") == "拉取间隔", "倒计时变化不换类别(去重)"
    assert pacing_class("未到可取时刻(间隔, 还差 104s)") == "间隔", "min_interval 是另一类"


# ==================== P1 覆盖率提升轮: 取数线程长尾 ====================


class _BoomPublisher:
    """publish 必炸的发布器(验证启动期发布失败不打死取数线程)"""
    revision = 0

    def publish(self, views):
        raise RuntimeError("发布炸了")


def test_start_twice_is_idempotent(tmp_path):
    """start 幂等: 线程已在跑时不重复起(否则会出现两个取数线程抢同一把站点锁)"""
    fetcher = FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A))
    service = _service(tmp_path, fetcher, clock=Clock())
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0)
    worker.start()
    first_thread = worker._thread
    worker.start()
    assert worker._thread is first_thread, "第二次 start 复用同一线程"
    assert worker.stop(), "正常关停"


def test_stop_timeout_reports_error(tmp_path):
    """线程超时未退出 -> stop 返回 False 并 ERROR(可能仍在等扩展回传)"""
    fetcher = FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A))
    service = _service(tmp_path, fetcher, clock=Clock())
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=3600.0)
    stuck = threading.Thread(target=time.sleep, args=(30, ), name="stuck-hr-worker", daemon=True)
    stuck.start()  # join 需要线程已启动
    worker._thread = stuck  # 注入一个不退出的线程, 验证超时分支的判定与返回值
    assert worker.stop(timeout=0.05) is False
    worker._thread = None


def test_request_refresh_site_filtering(tmp_path):
    """request_refresh: 未点名站点 = 全部启用站点; 点名未启用站点 = 空受理(不告警)"""
    fetcher = FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A))
    service = _service(tmp_path, fetcher, clock=Clock())
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0)
    assert worker.request_refresh(["ghost"]) == [], "未启用站点不受理"
    assert worker._force in (set(), None) or not worker._force, "空受理不残留旗标"
    assert worker.request_refresh(["pt.example.com"]) == ["pt.example.com"]


def test_loop_survives_startup_publish_failure(tmp_path, monkeypatch):
    """冷启动发布既有视图失败(读盘异常) -> ERROR 但线程照常进入取数循环"""
    fetcher = FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A))
    clock = Clock()
    service = _service(tmp_path, fetcher, clock=clock)
    worker = HrWorker(service=service, publisher=_BoomPublisher(), poll_interval=60.0, now_fn=clock)

    calls = []

    def fake_run_once():
        calls.append(1)
        with worker._cond:
            worker._stopped = True  # 跑一轮就停(测试内联驱动 _loop)
        raise RuntimeError("单轮也炸")

    monkeypatch.setattr(worker, "run_once", fake_run_once)
    worker._loop()  # 内联跑: 发布炸 -> 记 ERROR -> run_once 炸 -> 记 ERROR -> 收敛退出
    assert len(calls) == 1
    monkeypatch.undo()


def test_record_status_warns_on_partial_and_error(tmp_path):
    """刷新不完备(partial/error)且产生处未告警 -> 取数线程补一条 WARNING(改版让放行证明不成立)"""
    fetcher = FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A))
    service = _service(tmp_path, fetcher, clock=Clock())
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0)
    with worker_log() as messages:
        result = HrRefreshResult(site="pt.example.com", action=ACTION_PARTIAL, reason="页面取数失败", alerted=False)
        worker._note("pt.example.com", result)
        assert any("页面取数失败" in m for m in messages), "partial 未告警 -> 线程补 WARNING"
        # 状态不变 + 节流窗口内: 不重复
        worker._note("pt.example.com", result)
        assert sum("页面取数失败" in m for m in messages) == 1, "同状态节流期内不重复记"


class _ListLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


class worker_log:
    """挂在 auto_qb.hr.worker 模块 logger 上的自足采集(pitfalls/testing/log-capture: 禁 caplog)"""
    def __init__(self, level=logging.DEBUG):
        self._handler = _ListLogHandler()
        self._logger = logging.getLogger("auto_qb.hr.worker")
        self._level = level

    def __enter__(self):
        self._old_level, self._old_propagate = self._logger.level, self._logger.propagate
        self._logger.addHandler(self._handler)
        self._logger.setLevel(self._level)
        self._logger.propagate = False
        return self._handler.messages

    def __exit__(self, *exc):
        self._logger.removeHandler(self._handler)
        self._logger.setLevel(self._old_level)
        self._logger.propagate = self._old_propagate
        return False


# ==================== hr 首轮变异审计轮: 取数线程长尾 ====================


def test_stable_key_blank_and_none_inputs():
    assert stable_key("") == ""
    assert stable_key(None) == ""
    assert stable_key("还差 104s") == "还差 #s"


def test_pacing_class_unknown_and_blank():
    assert pacing_class("") == ""
    assert pacing_class(None) == ""
    assert pacing_class("未知状态") == "未知状态"


def test_view_signature_rounds_healthy_ts_to_three_places():
    def sig(ts):
        view = HrSiteView(site="s", listing="list", healthy_ts=ts)
        return view_signature(HrViewSet(views={"s": view}))[0][4]

    assert sig(1.2349) == round(1.2349, 3)
    assert sig(1.5) == round(1.5, 3)
    assert sig(2.0) == round(2.0, 3)


def test_worker_init_defaults(tmp_path):
    service = _service(tmp_path, FakeFetcher(pages={}))
    worker = HrWorker(service=service, publisher=HrViewPublisher())
    assert worker._name == "auto-qb-hr-fetch"
    assert worker.poll_interval == 60.0
    assert worker._wake_seq == 0
    assert worker._stopped is False
    assert worker.last_run_ts == 0.0
    assert worker.last_results == []
    assert worker._silence_warned_at == 0.0, "「从未提醒过」的哨兵值"
    assert HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=1.0).poll_interval == 1.0, \
        "下界是 max(1.0, ...): 1s 不该被抬"


def test_start_message_and_thread_props(tmp_path):
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)))
    service.site_confs["pt2.example.com"] = site_conf()
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=30.0)
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        worker.start()
        try:
            assert worker._thread.name == "auto-qb-hr-fetch"
            assert worker._thread.daemon is True
            assert worker._stopped is False
            assert worker._started_at is not None
            assert worker.last_run_ts > 0
        finally:
            worker.stop(timeout=5.0)
    assert any(
        m.startswith("HR 取数线程已启动: 每 30s 自唤醒检查一次站点(与主循环节拍无关); 站点: pt.example.com, pt2.example.com") for m in cap.messages
    ), cap.messages


def test_start_message_no_sites_placeholder(tmp_path):
    service = _service(tmp_path, FakeFetcher(pages={}))
    service.site_confs["pt.example.com"] = site_conf(enabled=False)
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=30.0)
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        worker.start()
        try:
            pass
        finally:
            worker.stop(timeout=5.0)
    assert any("站点: (无)" in m for m in cap.messages), cap.messages
    assert not any("XX" in m for m in cap.messages), cap.messages


class _CancelQueue:
    def __init__(self):
        self.reason = ""

    def cancel_all(self, reason):
        self.reason = reason


class _FetcherWithQueue:
    def __init__(self):
        self.queue = _CancelQueue()

    def get_text(self, url):
        raise HrFetchError("无")

    def get_bytes(self, url):
        raise HrFetchError("无")


def test_stop_cancels_fetch_channel_with_reason(tmp_path):
    fetcher = _FetcherWithQueue()
    worker = HrWorker(service=_service(tmp_path, fetcher), publisher=HrViewPublisher(), poll_interval=60.0)
    assert worker.stop(timeout=0.1) is True
    assert fetcher.queue.reason == "HR 取数线程正在停止"


def test_stop_clean_reports_and_clears_handle(tmp_path):
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)))
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0)
    worker.start()
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        assert worker.stop(timeout=5.0) is True
    assert "HR 取数线程已停止" in cap.messages, cap.messages
    assert worker._thread is None, "干净退出后句柄要清掉"
    assert worker.started is False


def test_stop_keeps_thread_handle_when_not_exited(tmp_path, monkeypatch):
    service = _service(tmp_path, FakeFetcher(pages={}))
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0)
    release = threading.Event()
    entered = threading.Event()

    def blocking():
        entered.set()
        release.wait(5.0)

    monkeypatch.setattr(worker, "run_once", blocking)
    worker.start()
    try:
        assert entered.wait(10.0), "用例前提: 线程已进到阻塞的一轮里"
        with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
            assert worker.stop(timeout=0.05) is False, "线程还阻塞着 -> 未退出"
        assert worker._thread is not None and worker.started, "没退出就得留着句柄(否则再也停不掉)"
        assert any("未退出" in m for m in cap.messages), cap.messages
    finally:
        release.set()
        worker.stop(timeout=5.0)


def test_stop_default_timeout_is_ten_seconds():
    """契约: stop 的缺省等待上限是 10s(改它等于改关停行为)"""
    import inspect

    assert inspect.signature(HrWorker.stop).parameters["timeout"].default == 10.0


def test_wake_increments_sequence(tmp_path):
    worker = HrWorker(
        service=_service(tmp_path, FakeFetcher(pages={})), publisher=HrViewPublisher(), poll_interval=60.0
    )
    assert worker._wake_seq == 0
    worker.wake()
    assert worker._wake_seq == 1
    worker.wake()
    assert worker._wake_seq == 2


def test_request_refresh_accumulates_and_bumps_seq(tmp_path):
    service = _service(tmp_path, FakeFetcher(pages={}))
    service.site_confs["pt2.example.com"] = site_conf()
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0)
    assert worker.request_refresh(["pt.example.com"]) == ["pt.example.com"]
    assert worker._wake_seq == 1
    assert worker.request_refresh(["pt2.example.com"]) == ["pt2.example.com"]
    assert worker._wake_seq == 2
    assert worker._force == {"pt.example.com", "pt2.example.com"}, "受理要累加(不是覆盖)"


def test_request_refresh_logs_accepted_sites(tmp_path):
    service = _service(tmp_path, FakeFetcher(pages={}))
    service.site_confs["pt2.example.com"] = site_conf()
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0)
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        worker.request_refresh(["pt.example.com", "pt2.example.com"])
    assert cap.messages == ["HR 收到立即拉取请求: pt.example.com, pt2.example.com(取数线程将跳过复用窗与拉取间隔, 频控仍生效)"], cap.messages


def test_run_once_hands_site_anchors_three_state(tmp_path):
    """锚点三态交接: 映射原样直通 / 采集失败(None) 直通 / 该站键缺失 -> {}"""
    service = _service(tmp_path, FakeFetcher(pages={}))
    captured = []

    def spy(site, anchors, *, force=False):
        captured.append((site, anchors, force))
        return HrRefreshResult(site=site, action=ACTION_WAITING, reason="未到可取时刻", reason_kind=REASON_BUDGET)

    service.refresh_site = spy
    mapping = {"pt.example.com": {"h1": "anchor"}}

    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0, anchors_fn=lambda: mapping)
    worker.run_once()
    assert captured == [("pt.example.com", {"h1": "anchor"}, False)]
    assert "pt.example.com" in worker._last_action, "_note 以站点为键记账"

    captured.clear()
    HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0).run_once()
    assert captured == [("pt.example.com", None, False)], "采集失败(None) 原样直通"

    captured.clear()
    HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0, anchors_fn=lambda: {}).run_once()
    assert captured == [("pt.example.com", {}, False)], "确认该站零锚点 -> {}"


def test_build_views_prefers_memory_snapshot(tmp_path):
    service = _service(tmp_path, FakeFetcher(pages={}))
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0, now_fn=lambda: 123.0)
    service.build_view_for = lambda site, data: ("built", site, data)
    snapshot = object()
    views = worker._build_views([HrRefreshResult(site="pt.example.com", action=ACTION_REFRESHED, snapshot=snapshot)])
    assert views.views["pt.example.com"] == ("built", "pt.example.com", snapshot), "本轮内存快照优先"
    assert views.generated_at == 123.0


def test_note_logs_normal_action_only_on_change(tmp_path):
    worker = HrWorker(
        service=_service(tmp_path, FakeFetcher(pages={})), publisher=HrViewPublisher(), poll_interval=60.0
    )
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        worker._note("pt.example.com", HrRefreshResult(site="pt.example.com", action=ACTION_REFRESHED, reason="正常"))
        worker._note("pt.example.com", HrRefreshResult(site="pt.example.com", action=ACTION_REFRESHED, reason="正常"))
        worker._note("pt2.example.com", HrRefreshResult(site="pt2.example.com", action=ACTION_REUSED, reason=""))
    assert cap.messages.count("HR 站点 pt.example.com | refreshed: 正常") == 1, cap.messages
    assert "HR 站点 pt2.example.com | reused: 正常" in cap.messages, cap.messages


def test_note_pacing_key_and_message(tmp_path):
    worker = HrWorker(
        service=_service(tmp_path, FakeFetcher(pages={})), publisher=HrViewPublisher(), poll_interval=60.0
    )
    waiting = HrRefreshResult(
        site="pt.example.com", action=ACTION_WAITING, reason="未到可取时刻(间隔, 还差 5s)", reason_kind=REASON_BUDGET
    )
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        worker._note("pt.example.com", waiting)
        assert worker._pacing_key["pt.example.com"] == pacing_class(waiting.reason), "节流键取自原因"
        worker._note(
            "pt.example.com",
            HrRefreshResult(site="pt.example.com", action=ACTION_WAITING, reason="", reason_kind=REASON_BUDGET)
        )
    assert "HR 站点 pt.example.com | waiting: 未到可取时刻(间隔, 还差 5s)(节流中, 非故障)" in cap.messages, cap.messages
    assert "HR 站点 pt.example.com | waiting: 正常(节流中, 非故障)" in cap.messages, cap.messages


def test_note_warn_gap_floor_and_exact_boundary(tmp_path, monkeypatch):
    """非节流告警: warn_gap 下界 60s; 同 action 恰好到点即再报"""
    clock = Clock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 0.0)
    worker = HrWorker(
        service=_service(tmp_path, FakeFetcher(pages={}), clock=clock),
        publisher=HrViewPublisher(),
        poll_interval=60.0,
        now_fn=clock,
    )
    err = HrRefreshResult(site="pt.example.com", action=ACTION_ERROR, reason="表头缺失")
    with capture_logs("auto_qb.hr.worker", logging.WARNING) as cap:
        worker._note("pt.example.com", err)
        worker._note("pt.example.com", err)
        clock.advance(60.0)
        worker._note("pt.example.com", err)
    assert len(cap.messages) == 2, cap.messages
    assert "站点 pt.example.com" in cap.messages[-1] and f"| {ACTION_ERROR}:" in cap.messages[-1], cap.messages[-1]


def test_note_pacing_reminder_fires_at_exact_gap(tmp_path, monkeypatch):
    """节流态持续: 恰好满一个 warn_gap 就要再说明白一次(不是「超过」才说)"""
    clock = Clock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)
    worker = HrWorker(
        service=_service(tmp_path, FakeFetcher(pages={}), clock=clock),
        publisher=HrViewPublisher(),
        poll_interval=60.0,
        now_fn=clock,
    )
    waiting = HrRefreshResult(
        site="pt.example.com", action=ACTION_WAITING, reason="未到可取时刻(间隔, 还差 5s)", reason_kind=REASON_BUDGET
    )
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        worker._note("pt.example.com", waiting)
        worker._note("pt.example.com", waiting)
        clock.advance(3600.0)
        worker._note("pt.example.com", waiting)
    assert len(cap.messages) == 2, cap.messages


def test_note_info_branch_message(tmp_path):
    worker = HrWorker(
        service=_service(tmp_path, FakeFetcher(pages={})), publisher=HrViewPublisher(), poll_interval=60.0
    )
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        worker._note("pt.example.com", HrRefreshResult(site="pt.example.com", action=ACTION_NO_CHANNEL, reason="通道不可用"))
    assert "HR 站点 pt.example.com | no-channel: 通道不可用" in cap.messages, cap.messages


def _silence_worker(tmp_path, clock, endpoint, *, web_active):
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)), clock=clock)
    return HrWorker(
        service=service,
        publisher=HrViewPublisher(),
        endpoint=endpoint,
        poll_interval=60.0,
        now_fn=clock,
        web_active_fn=lambda: web_active,
    )


def test_silence_reference_prefers_last_contact(tmp_path, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)

    class _Endpoint:
        last_contact_ts = 5.0
        rejected_contacts = 0

    worker = _silence_worker(tmp_path, clock, _Endpoint(), web_active=True)
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        worker._check_channel_silence()
    assert any("上次联系后" in m for m in cap.messages), cap.messages


def test_silence_reference_defaults_when_attr_missing(tmp_path, monkeypatch):
    """端点缺 last_contact_ts -> 缺省 0.0 = 视为刚启动, 不告警"""
    clock = Clock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)

    class _BareEndpoint:
        pass

    worker = _silence_worker(tmp_path, clock, _BareEndpoint(), web_active=False)
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        worker._check_channel_silence()
    assert cap.messages == [], cap.messages


def test_silence_missing_rejected_attr_defaults_zero(tmp_path, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)

    class _NoRejected:
        last_contact_ts = 5.0

    worker = _silence_worker(tmp_path, clock, _NoRejected(), web_active=False)
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        worker._check_channel_silence()
    assert len(cap.messages) == 1 and "端点未收到任何联系" in cap.messages[0], cap.messages


def test_silence_where_started_label(tmp_path, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)

    class _Fresh:
        last_contact_ts = 0.0
        rejected_contacts = 0

    worker = _silence_worker(tmp_path, clock, _Fresh(), web_active=True)
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        clock.advance(3601.0)
        worker._check_channel_silence()
    assert any("(启动以来扩展未联系端点)" in m for m in cap.messages), cap.messages


def test_silence_where_after_contact_label(tmp_path, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)

    class _Contacted:
        last_contact_ts = 5.0
        rejected_contacts = 0

    class _Recent:
        last_contact_ts = 0.5
        rejected_contacts = 0

    for endpoint in (_Contacted(), _Recent()):
        worker = _silence_worker(tmp_path, clock, endpoint, web_active=True)
        with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
            worker._check_channel_silence()
        assert any("(上次联系后扩展未联系端点)" in m for m in cap.messages), cap.messages


def test_silence_gap_floor_and_exact_boundary(tmp_path, monkeypatch):
    """静默 gap 下界 60s; 恰好到点即出声(不是「超过」才出声)"""
    clock = Clock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 0.0)

    class _Fresh:
        last_contact_ts = 0.0
        rejected_contacts = 0

    worker = _silence_worker(tmp_path, clock, _Fresh(), web_active=True)
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        clock.advance(60.0)
        worker._check_channel_silence()
        clock.advance(60.0)
        worker._check_channel_silence()
    assert len(cap.messages) == 2, cap.messages


def test_silence_rejected_threshold_is_positive(tmp_path, monkeypatch):
    """被拒计数 >0 即算「有人在敲门」"""
    clock = Clock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)

    class _Endpoint:
        last_contact_ts = 0.0
        rejected_contacts = 1

    worker = _silence_worker(tmp_path, clock, _Endpoint(), web_active=False)
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        clock.advance(3601.0)
        worker._check_channel_silence()
    assert any("被拒" in m for m in cap.messages), cap.messages


def test_silence_hours_value_uses_3600(tmp_path, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)

    class _Endpoint:
        last_contact_ts = clock() - 650000.0
        rejected_contacts = 0

    worker = _silence_worker(tmp_path, clock, _Endpoint(), web_active=True)
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        worker._check_channel_silence()
    assert any("180.6h" in m for m in cap.messages), cap.messages


def test_silence_event_tag_sets_domain(tmp_path, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)

    class _Endpoint:
        last_contact_ts = 0.0
        rejected_contacts = 0

    worker = _silence_worker(tmp_path, clock, _Endpoint(), web_active=True)
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        clock.advance(3601.0)
        worker._check_channel_silence()
    recs = [r for r in cap.records if "[HR 通道静默]" in r.getMessage()]
    assert len(recs) == 1
    assert getattr(recs[0], DOMAIN_ATTR) == events.DOMAIN_CHANNEL


def test_loop_startup_publish_failure_logs_traceback(tmp_path, monkeypatch):
    service = _service(tmp_path, FakeFetcher(pages={}))
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=0.05)

    def boom(_results):
        raise RuntimeError("读盘失败")

    monkeypatch.setattr(worker, "_build_views", boom)

    def stop_after_one():
        with worker._cond:
            worker._stopped = True
        return []

    monkeypatch.setattr(worker, "run_once", stop_after_one)
    with capture_logs("auto_qb.hr.worker", logging.ERROR) as cap:
        worker._loop()
    assert any("启动时发布既有视图失败" in m for m in cap.messages), cap.messages
    assert all(isinstance(r.exc_info, tuple) for r in cap.records), "要带堆栈(exc_info=True)"


def test_loop_round_exception_logs_traceback(tmp_path, monkeypatch):
    service = _service(tmp_path, FakeFetcher(pages={}))
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=0.05)

    def boom():
        with worker._cond:
            worker._stopped = True
        raise RuntimeError("单轮炸了")

    monkeypatch.setattr(worker, "run_once", boom)
    with capture_logs("auto_qb.hr.worker", logging.ERROR) as cap:
        worker._loop()
    assert any("单轮异常" in m for m in cap.messages), cap.messages
    assert all(isinstance(r.exc_info, tuple) for r in cap.records), "要带堆栈(exc_info=True)"


def test_loop_waits_for_poll_interval(tmp_path):
    """没被唤醒就不该多跑 —— 等待谓词若失效会退化成忙等(rounds 疯涨)"""
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)))
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0)
    worker.start()
    try:
        assert _wait_until(lambda: worker.rounds >= 1, timeout=10.0)
        time.sleep(0.4)
        assert worker.rounds == 1, "poll_interval=60s, 0.4s 内不该再跑"
    finally:
        worker.stop(timeout=5.0)
