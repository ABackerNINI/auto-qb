"""test_hr_worker_notes 测试计划: 取数线程与只读视图发布(计划 §8)

## 测试计划(每个测试函数一条)
- test_pacing_partial_is_info_not_warning_and_not_repeated: **被自己频控拦下**的 partial / 未到点 waiting 只记 INFO(
  绝不 WARNING —— 会被 notify 推成系统通知), 且同状态不逐轮刷(数字抹掉后同键)
- test_pacing_state_reminds_once_per_window: 节流态持续时按 channel_silence_warn 周期提醒一次(不静默消失)
- test_silence_reminder_is_throttled: 通道静默按 channel_silence_warn 周期提醒一次
- test_silence_warning_names_affected_sites: 通道静默是**端点级**事件 ⇒ 文案里要列出受影响站点(M4 四类事件)
- test_silence_is_quiet_when_nobody_watching: 无人在用 WebUI 且无被拒敲门 ⇒ 预期离线, 只进后端 log(hr_silent)
- test_silence_is_visible_when_web_active: WebUI 活跃 + 扩展未联系 ⇒ 可见告警(不静默, 口径⑤)
- test_silence_names_rejected_root_cause: 有被拒敲门(401/403) ⇒ 文案指名 token / origin 根因

### hr 首轮变异审计轮: 取数线程长尾(issue 26-10-10-1108-runtime-worker)
- test_pacing_class_unknown_and_blank: 未命中类别回落稳定指纹; 空串 -> 空串
- test_note_logs_normal_action_only_on_change: 正常动作只在变化时记一条, 缺省文案「正常」
- test_note_pacing_key_and_message: 节流键取自原因; 缺省文案「正常」; 精确文案
- test_note_pacing_separates_reason_url: 节流 INFO 中原因以 URL 结尾时, 后文括号前必须有空格
- test_note_alerted_separates_reason_url: 已告警 INFO 中原因以 URL 结尾时, 后文括号前必须有空格
- test_note_warn_gap_floor_and_exact_boundary: 非节流告警的 warn_gap 下界 60s 且「恰好到点」即再报
- test_note_pacing_reminder_fires_at_exact_gap: 节流态持续时恰好满一个 warn_gap 即再说明一次
- test_note_info_branch_message: 非告警动作走 INFO 分支并带站点与动作
- test_silence_reference_prefers_last_contact: 静默基准优先「上次联系时刻」(非启动时刻)
- test_silence_reference_defaults_when_attr_missing: 端点缺 last_contact_ts/rejected_contacts 时保守缺省
- test_silence_gap_floor_and_exact_boundary: 静默 gap 下界 60s; 恰好到点即出声
- test_silence_rejected_threshold_is_positive: 被拒计数 >0 即算被拒(不是 >1)
- test_silence_hours_value_uses_3600: 静默小时数 = 秒 / 3600(展示取整可辨)
- test_silence_event_tag_sets_domain: 静默出口挂通道层标签(hr_domain)
- test_pacing_class_separates_fetch_interval_gate
- test_silence_missing_rejected_attr_defaults_zero
- test_silence_where_after_contact_label: 「上次联系后」分支标签精确(原 test_silence_where_labels_both_branches 拆分)

### 锚点采集失败告警节流(issue 26-11-07-0527 #19)
- test_anchor_failure_warning_throttled: 状态变化沿立即报 + 持续同态按 warn_gap 周期提醒, 被去重的轮次落 DEBUG
- test_anchor_warning_rereports_on_state_change_edge: 恢复后再失败/换根因都算状态变化沿, 立即再报
"""

import logging

import threading

import time

from auto_qb.hr.fetcher import NullFetcher

from auto_qb.hr.model import CHANNEL_OK, CHANNEL_SILENT

from auto_qb.hr.resolve import HrIdentity, HrSiteView, HrViewSet, judge_record

from auto_qb.hr.service import ACTION_ERROR, ACTION_NO_CHANNEL, ACTION_PARTIAL, ACTION_REFRESHED, ACTION_REUSED, \
    ACTION_WAITING, REASON_BUDGET, HrRefreshResult

import auto_qb.hr.worker as worker_module

from auto_qb.hr import events

from auto_qb.hr.fetcher import HrFetchError, NullFetcher

from auto_qb.hr.worker import HrViewPublisher, HrWorker, pacing_class, stable_key, view_signature

from auto_qb.infra.logging import DOMAIN_ATTR

from helpers import capture_logs

from clock import wait_until

from hr_helpers import EMPTY_TABLE_PAGE, REVISED_PAGE, FakeFetcher, global_conf, make_service, myhr_page, row, \
    site_conf, torrent_blob
from clock import FakeClock

from hr_worker_support import (
    TID_A,
    _blobs,
    _pages,
    _service,
    _silence_worker,
)


def test_pacing_partial_is_info_not_warning_and_not_repeated(tmp_path, caplog):
    """被**自己频控**拦下: 只记一条 INFO(绝不 WARNING), 且 partial↔waiting 交替不刷屏

    用户实报(2026-09-24): 这两个状态本会持续几小时, 却按分钟级轮询打出 WARNING ⇒ notify 推成
    系统通知 ⇒ 弹窗淹没。去重按「被拦的根因」(间隔/配额/熔断…) 而不是「本轮返回了哪个 action」——
    同一个「等间隔」在轮次间会分别表现为 partial(首页抓到、第二页被拦)与 waiting。
    """
    clock = FakeClock()
    service = _service(tmp_path, FakeFetcher(pages={}, blobs={}), clock=clock)
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0, now_fn=clock.now)
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
    clock = FakeClock()
    service = _service(tmp_path, FakeFetcher(pages={}, blobs={}), clock=clock)
    worker = HrWorker(service=service, publisher=HrViewPublisher(), poll_interval=60.0, now_fn=clock.now)
    pacing = HrRefreshResult(
        site="pt.example.com", action=ACTION_PARTIAL, reason="配额/间隔受限(间隔: 还差 104s)", reason_kind=REASON_BUDGET
    )

    with caplog.at_level(logging.INFO, logger="auto_qb.hr.worker"):
        worker._note("pt.example.com", pacing)  # 说一次
        clock.advance(6 * 3600 + 1)  # 超过一个提醒窗口(v3 常量 CHANNEL_SILENCE_WARN = 6H)
        worker._note("pt.example.com", pacing)  # 同根因但到点了 => 再提醒一次

    notes = [r for r in caplog.records if "节流中" in r.getMessage()]
    assert len(notes) == 2, f"超过一个提醒窗口后应再记一次: {[n.getMessage() for n in notes]}"


def test_silence_reminder_is_throttled(tmp_path, caplog, monkeypatch):
    clock = FakeClock()
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
        now_fn=clock.now,
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
    clock = FakeClock()
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
        now_fn=clock.now,
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
    clock = FakeClock()
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
        now_fn=clock.now,
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
    clock = FakeClock()
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
        now_fn=clock.now,
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
    clock = FakeClock()
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
        now_fn=clock.now,
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


def test_pacing_class_separates_fetch_interval_gate():
    """「拉取间隔」闸门的等待原因进入节流类别且与 min_interval 的「间隔」区分(不刷屏 + 根因可辨)"""
    from auto_qb.hr.worker import pacing_class
    assert pacing_class("未到拉取时刻(拉取间隔, 还差 104s)") == "拉取间隔"
    assert pacing_class("未到拉取时刻(拉取间隔, 还差 51s)") == "拉取间隔", "倒计时变化不换类别(去重)"
    assert pacing_class("未到可取时刻(间隔, 还差 104s)") == "间隔", "min_interval 是另一类"


def test_pacing_class_unknown_and_blank():
    assert pacing_class("") == ""
    assert pacing_class(None) == ""
    assert pacing_class("未知状态") == "未知状态"


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
    assert "HR 站点 pt.example.com | waiting: 未到可取时刻(间隔, 还差 5s) (节流中, 非故障)" in cap.messages, cap.messages
    assert "HR 站点 pt.example.com | waiting: 正常 (节流中, 非故障)" in cap.messages, cap.messages


def test_note_pacing_separates_reason_url(tmp_path):
    """原因以 URL 结尾时, `(节流中, 非故障)` 前必须有空格(编辑器点击不吞括号)"""
    worker = HrWorker(
        service=_service(tmp_path, FakeFetcher(pages={})), publisher=HrViewPublisher(), poll_interval=60.0
    )
    url = "https://pt.example.com/myhr.php?hrtype=A"
    waiting = HrRefreshResult(
        site="pt.example.com", action=ACTION_WAITING, reason=f"本波取数被叫停: {url}", reason_kind=REASON_BUDGET
    )
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        worker._note("pt.example.com", waiting)
    assert any(f"{url} (节流中, 非故障)" in m for m in cap.messages), cap.messages


def test_note_alerted_separates_reason_url(tmp_path):
    """已由产生处告警的原因以 URL 结尾时, `(已在取数处告警)` 前必须有空格"""
    worker = HrWorker(
        service=_service(tmp_path, FakeFetcher(pages={})), publisher=HrViewPublisher(), poll_interval=60.0
    )
    url = "https://pt.example.com/myhr.php?hrtype=A"
    result = HrRefreshResult(
        site="pt.example.com", action=ACTION_ERROR, reason=f"等待浏览器扩展取数超时(180s): {url}", alerted=True
    )
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        worker._note("pt.example.com", result)
    assert any(f"{url} (已在取数处告警)" in m for m in cap.messages), cap.messages


def test_note_warn_gap_floor_and_exact_boundary(tmp_path, monkeypatch):
    """非节流告警: warn_gap 下界 60s; 同 action 恰好到点即再报"""
    clock = FakeClock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 0.0)
    worker = HrWorker(
        service=_service(tmp_path, FakeFetcher(pages={}), clock=clock),
        publisher=HrViewPublisher(),
        poll_interval=60.0,
        now_fn=clock.now,
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
    clock = FakeClock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)
    worker = HrWorker(
        service=_service(tmp_path, FakeFetcher(pages={}), clock=clock),
        publisher=HrViewPublisher(),
        poll_interval=60.0,
        now_fn=clock.now,
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


def test_silence_reference_prefers_last_contact(tmp_path, monkeypatch):
    clock = FakeClock()
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
    clock = FakeClock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)

    class _BareEndpoint:
        pass

    worker = _silence_worker(tmp_path, clock, _BareEndpoint(), web_active=False)
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        worker._check_channel_silence()
    assert cap.messages == [], cap.messages


def test_silence_missing_rejected_attr_defaults_zero(tmp_path, monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)

    class _NoRejected:
        last_contact_ts = 5.0

    worker = _silence_worker(tmp_path, clock, _NoRejected(), web_active=False)
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        worker._check_channel_silence()
    assert len(cap.messages) == 1 and "端点未收到任何联系" in cap.messages[0], cap.messages


def test_silence_where_after_contact_label(tmp_path, monkeypatch):
    clock = FakeClock()
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
    clock = FakeClock()
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
    clock = FakeClock()
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
    clock = FakeClock()
    monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", 3600.0)

    class _Endpoint:
        last_contact_ts = clock.now() - 650000.0
        rejected_contacts = 0

    worker = _silence_worker(tmp_path, clock, _Endpoint(), web_active=True)
    with capture_logs("auto_qb.hr.worker", logging.INFO) as cap:
        worker._check_channel_silence()
    assert any("180.6h" in m for m in cap.messages), cap.messages


def test_silence_event_tag_sets_domain(tmp_path, monkeypatch):
    clock = FakeClock()
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


def test_anchor_failure_warning_throttled(tmp_path, caplog):
    """锚点采集失败的 WARNING 节流(issue 26-11-07-0527 #19): 状态变化沿立即报, 持续同态按
    channel_silence_warn 周期提醒, 被去重的轮次落 DEBUG —— 取数线程每 poll 一轮都试一次,
    不节流就是分钟级系统通知(模块 docstring 自述要避免的弹窗轰炸)"""
    clock = FakeClock()
    service = _service(tmp_path, FakeFetcher(pages={}, blobs={}), clock=clock)

    def boom():
        raise RuntimeError("主循环侧取锚点失败(还差 42s)")

    worker = HrWorker(
        service=service, publisher=HrViewPublisher(), poll_interval=60.0, now_fn=clock.now, anchors_fn=boom
    )
    with caplog.at_level(logging.DEBUG, logger="auto_qb.hr.worker"):
        worker._collect_anchors()  # 首次失败: 立即 WARNING
        clock.advance(1.0)
        worker._collect_anchors()  # 同态持续: 只落 DEBUG
        clock.advance(6 * 3600 + 1)  # 超过一个提醒窗口(CHANNEL_SILENCE_WARN = 6H)
        worker._collect_anchors()  # 周期提醒一次
        clock.advance(1.0)
        worker._collect_anchors()  # 又是同态: DEBUG
    warns = [r for r in caplog.records if r.levelno == logging.WARNING and "锚点" in r.getMessage()]
    assert len(warns) == 2, f"变化沿一次 + 周期提醒一次: {[(r.levelname, r.getMessage()) for r in caplog.records]}"
    debugs = [r for r in caplog.records if r.levelno == logging.DEBUG and "锚点" in r.getMessage()]
    assert len(
        debugs
    ) == 2, f"被去重的轮次仍要留在 DEBUG(排障要看得见每轮在败什么): {[(r.levelname, r.getMessage()) for r in caplog.records]}"


def test_anchor_warning_rereports_on_state_change_edge(tmp_path, caplog):
    """恢复后再失败 = 状态变化沿: 立即报(不吃 warn_gap 冷启动); 同态持续中换根因(指纹变化)同样立即报"""
    clock = FakeClock()
    service = _service(tmp_path, FakeFetcher(pages={}, blobs={}), clock=clock)
    behavior = {"on": False, "mode": "runtime"}

    def provider():
        if not behavior["on"]:
            return {}
        if behavior["mode"] == "runtime":
            raise RuntimeError("锚点提供者崩了")
        raise TimeoutError("锚点通道超时")

    worker = HrWorker(
        service=service, publisher=HrViewPublisher(), poll_interval=60.0, now_fn=clock.now, anchors_fn=provider
    )

    def warns():
        return [r for r in caplog.records if r.levelno == logging.WARNING and "锚点" in r.getMessage()]

    with caplog.at_level(logging.DEBUG, logger="auto_qb.hr.worker"):
        behavior["on"] = True
        worker._collect_anchors()  # 失败: WARNING 1
        behavior["on"] = False
        worker._collect_anchors()  # 成功: 清失败指纹, 无告警
        behavior["on"] = True
        worker._collect_anchors()  # 恢复后再失败: 变化沿 -> 立即 WARNING(距上次告警 0s, 不吃 gap)
        assert len(warns()) == 2, "成功后再失败是状态变化沿, 不得被节流吞掉"
        behavior["mode"] = "timeout"
        worker._collect_anchors()  # 换根因: 指纹变化 -> 立即 WARNING
        assert len(warns()) == 3, "根因变化算状态变化, 不吃节流"
        assert "锚点通道超时" in warns()[-1].getMessage(), "新根因的告警要能看出换了病因"
