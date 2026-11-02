"""test_hr_status_status 测试计划: hr.status 种子明细导出(entry_details, 计划 26-10-01-2216 §7 阶段1)

## 测试计划(每个测试函数一条)

### P1 覆盖率提升轮: 展示层与模型长尾
- test_duration_text_tiers: 人话时长四档(天/时/分/秒) + 负数钳 0
- test_lane_and_quota_status_to_dict_roundtrip_keys: LaneStatus/QuotaStatus 的 to_dict = asdict
- test_blocking_reason_stale_with_next_wave_text: 过复用窗的兜底文案(带/不写下次核对清单时刻)

### 拉取历史导出(history_rows, 计划 26-10-04-0312 §3.4)

### 稳态降频展示同步(计划 26-10-05-0555 S3 + 拍板 D1)
- test_site_status_steady_uses_idle_interval_everywhere: 稳态期(落盘旗标 idle_mode=True)—— 单点换算
  返回 idle_refresh_interval, next_wave_at / refresh_interval / fresh_text 全链跟随 + 「(稳态降频)」注记;
  idle_mode 旗标透出视图(D1 前端 kv 行数据源, 同 stale/(已过) 先例)
- test_site_status_normal_period_keeps_refresh_interval: 常态期(旗标 False)—— next_at / 视图字段仍是
  refresh_interval, 稳态注记不出现
- test_legacy_site_file_without_idle_key_reads_as_false: 存量站点文件兼容 —— 旧 JSON 波次段无 idle_mode
  键读入仍 False, 展示走常态间隔不误降频

### R20 展示导出变异守阵(issue 26-10-10-1108-test-hr-mutation-display, 排序口径/人话回落/字段面)
- test_lane_statuses_full_field_passthrough: LaneStatus 全字段非默认搬运(含 to_dict)—— 置 None/删实参类变异全杀
- test_lane_statuses_text_composition_exact: ls.text 与 lanes_text 逐字(全深度/声明/对不平/detail/连续失效/标记)
- test_lane_statuses_missing_lane_keeps_rest: 缺档位不 break 停表 —— 后续档位与「无」标记都在
- test_lane_statuses_unknown_status_falls_back_to_raw: 未知状态人话回落原文, 不静默丢也不变 None
- test_lane_statuses_text_condition_boundaries: text 各条件边界(全深度假/声明 None/对不平 True 与 None/detail 空/连续失效 1 与 2)
- test_lanes_summary_parity_between_service_and_status: service._lanes_summary_from 与 status._lane_statuses
  parts 同波次逐字相等(tag/深度/计数三部件读 model 单点, issue 26-10-29-1327); 未知状态两侧同透传
- test_duration_text_exact_tiers: 人话时长四档精确边界(恰等 86400/3600/60 与 +1s 组合)
- test_ago_text_never_suffix_and_fraction: 「从未」三形态(0/负/边界) + 「Nx前」后缀 + 小数秒
- test_stamp_text_format_zero_and_edges: 绝对时刻格式逐字 + 0/负/1 的「-」边界
- test_need_seed_text_tiers_exact: 镜像站点书写形态全档(天/时/分/秒边界 + 负值钳 0)
- test_lane_counts_counts_every_lane: 四档计数(含免罪档)逐键精确
- test_retention_text_ratio_zero_and_tails: 守恒行 ratio=0 不误判「不适用」+ 正常/WARN 两尾注
- test_site_conf_interval_stub_objects: getattr 缺省与 or 兜底(stub conf/wave 无属性/值为 0 各形态)
- test_blocking_reason_branches_exact: 四分支文案逐字 + next_wave_at 缺省形态
- test_site_status_rich_snapshot_fields: 富快照全字段面(quota/pending/backfill/observing/keys/allow_window/blocking)
- test_site_status_stale_and_boundary: 过复用窗(含恰等 now)+「(已过)」注记 + blocking 带下次核对清单时刻
- test_site_status_no_healthy_wave: healthy_ts=0 ⇒ next_wave_at=0.0 且 fresh_text 不带下次核对段
- test_site_status_unknown_channel_text: 未知通道态回落「未启用」
- test_site_status_empty_confirmed_boundary: 对账戳 ts=1 即算已确认(>0 口径)
- test_site_status_to_dict_field_surface: SiteStatus.to_dict 键面 = 全字段(零 no tests)
- test_build_site_statuses_reads_error_and_sites: 显式站点序 + read_error 空串/原文透出
- test_site_status_empty_index_backfill
- test_site_status_observing_counts_only_positive_streak

### 通道病因可见化(计划 26-10-29-0147 W3/D6)
- test_channel_texts_carry_the_next_action: 两个新通道态人话逐字且**带动作**(用户看这行时正在问
  「为什么一个都没取到」); 视图直取 CHANNEL_TEXTS 单点不另写第二份
- test_blocking_reason_channel_cause_precedes_data_symptoms: 通道病因排在整条判定链最前 ——
  缺权限/网络不通时既不劝人去「先跑一轮取数」也不劝人「--hr-confirm-empty」; 无病因时旧文案照旧
- test_channel_state_stale_trace_ignored: `ts <= healthy_ts` 的陈旧痕不生效(恢复后旧痕不许把站点
  卡标红), 且未知 kind / 坏 ts 不猜
"""

import json

from types import SimpleNamespace

from auto_qb.config.models import SiteHrCheckConfig

from auto_qb.hr import report

from auto_qb.hr.model import (
    CHANNEL_NETWORK,
    CHANNEL_NO_PERMISSION,
    CHANNEL_OK,
    LANE_FAILED,
    LANE_IDLE,
    LANE_OK,
    SOURCE_EXEMPT,
    SOURCE_NOT_LISTED,
    SOURCE_SATISFIED,
    HrEntry,
    HrHistoryEvent,
    HrLaneState,
    HrSiteData,
    HrVerified,
    HrWaveMeta,
)

from auto_qb.hr.service import _lanes_summary_from

from auto_qb.hr.ratelimit import HrLimits, day_key

from auto_qb.hr.resolve import HrSiteView

from auto_qb.hr.status import (
    CHANNEL_TEXTS,
    LANE_STATUS_TEXTS,
    LANE_TEXTS,
    LaneStatus,
    QuotaStatus,
    SOURCE_TEXTS,
    SiteStatus,
    _history_lanes,
    _lane_statuses,
    _retention_text,
    ago_text,
    blocking_reason,
    build_site_statuses,
    duration_text,
    entry_details,
    history_rows,
    lane_counts,
    need_seed_text,
    site_conf_interval,
    site_status,
    stamp_text,
)

from webui_helpers import (  # 键面单点(与 test_web_hr 同引, issue 26-10-21-0502)
    ENTRY_ROW_KEYS,
    HISTORY_LANE_KEYS,
    HISTORY_ROW_KEYS,
    SITE_STATUS_KEYS,
)

from hr_status_support import (
    _entry,
    _site,
)


def test_duration_text_tiers():
    """人话时长四档(天/时/分/秒) —— 报告与界面共用一处口径"""
    assert duration_text(2 * 86400 + 3 * 3600) == "2d3h"
    assert duration_text(3 * 3600 + 4 * 60) == "3h4m"
    assert duration_text(5 * 60 + 6) == "5m6s"
    assert duration_text(7) == "7s"
    assert duration_text(-5) == "0s", "负数钳到 0"


def test_lane_and_quota_status_to_dict_roundtrip_keys():
    """两个展示 dataclass 的 to_dict = asdict(WebUI JSON 友好口径)"""
    lane = LaneStatus(lane="A", status="ok", pages=2, rows=5, text="x")
    assert lane.to_dict()["lane"] == "A" and lane.to_dict()["pages"] == 2
    quota = QuotaStatus(day=3, day_max=240, left=237, text="y")
    assert quota.to_dict()["day"] == 3 and quota.to_dict()["left"] == 237


def test_blocking_reason_stale_with_next_wave_text():
    """数据过复用窗时的兜底文案: 有下次核对清单时刻带时刻, 没有则省略(2026-10-03 修 B2 换词)"""
    view = HrSiteView(site="s", lane_a={"H": HrEntry(tid=1, name="x")})
    data = HrSiteData()
    data.wave.releases_enabled = True
    assert "下次核对清单" in blocking_reason(view, data, stale=True, next_wave_at=1234.5)
    assert "立即拉取" in blocking_reason(view, data, stale=True, next_wave_at=0.0)
    assert blocking_reason(view, data, stale=False) == ""


class _StatusSvc:
    """site_status 的最小 service 依赖(配置 + 频控 + 路径) —— 本文件保持纯 status 测试, 不起引擎"""
    def __init__(self, conf: SiteHrCheckConfig):
        self.site_confs = {"s": conf}
        self.limits = HrLimits(min_interval=2.0, max_requests_per_day=100)

    def limits_for(self, site: str) -> HrLimits:
        return self.limits

    def site_path(self, site: str) -> str:
        return "s.json"


def _status_snapshot(conf: SiteHrCheckConfig, wave: HrWaveMeta):
    """固定锚点的站点快照: 空 view(通道/判定文案不影响被测面), now 取一个真实可格式化的时刻"""
    data = HrSiteData()
    data.wave = wave
    return site_status("s", data, HrSiteView(site="s"), _StatusSvc(conf), 1_800_000_000.0)


def test_site_status_steady_uses_idle_interval_everywhere():
    """稳态期(落盘旗标 idle_mode=True): 单点换算回 idle_refresh_interval, next_wave_at / 视图字段 /
    fresh_text 全链跟随(计划 26-10-05-0555 §2.6), 并带拍板 D1 的「(稳态降频)」注记"""
    conf = SiteHrCheckConfig(refresh_interval=3600.0, idle_refresh_interval=86400.0)
    assert site_conf_interval(conf, HrWaveMeta(idle_mode=True)) == 86400.0, "单点换算: 旗标真 -> idle 间隔"
    snap = _status_snapshot(conf, HrWaveMeta(healthy_ts=1_000_000.0, idle_mode=True))
    assert snap.next_wave_at == 1_000_000.0 + 86400.0, "「下次核对清单」稳态期按 idle 间隔倒计时(与闸门同算法)"
    assert snap.refresh_interval == 86400.0, "视图字段 refresh_interval 同步跟随(前端契约面)"
    assert snap.idle_mode is True, "旗标透出视图: D1 前端 kv 行注记的数据源(只读落盘旗标, 不重算判据)"
    assert f"下次核对清单 {stamp_text(1_000_000.0 + 86400.0)}" in snap.fresh_text
    assert snap.fresh_text.endswith("(稳态降频)"), "D1: 稳态期注记, 24H 倒计时不空降无解释"


def test_site_status_normal_period_keeps_refresh_interval():
    """常态期(旗标 False): 展示不变 —— next_at / 视图字段仍是 refresh_interval, 稳态注记不出现"""
    conf = SiteHrCheckConfig(refresh_interval=3600.0, idle_refresh_interval=86400.0)
    assert site_conf_interval(conf, HrWaveMeta(idle_mode=False)) == 3600.0
    snap = _status_snapshot(conf, HrWaveMeta(healthy_ts=1_000_000.0))
    assert snap.next_wave_at == 1_000_000.0 + 3600.0
    assert snap.refresh_interval == 3600.0
    assert snap.idle_mode is False
    assert f"下次核对清单 {stamp_text(1_000_000.0 + 3600.0)}" in snap.fresh_text
    assert "(稳态降频)" not in snap.fresh_text, "D1: 常态期注记不出现"


def test_legacy_site_file_without_idle_key_reads_as_false():
    """存量站点文件兼容(§2.4 旗标缺省 False): 旧 JSON 波次段无 idle_mode 键, 读入仍 False ——
    展示走常态间隔, 不把存量文件误显示成稳态降频"""
    conf = SiteHrCheckConfig(refresh_interval=3600.0, idle_refresh_interval=86400.0)
    legacy = json.loads(json.dumps(HrSiteData().to_json()))
    legacy["wave"].pop("idle_mode", None)  # 模拟 S2 之前落盘的站点文件
    legacy["wave"]["healthy_ts"] = 1_000_000.0
    data = HrSiteData.from_json(legacy)
    assert data.wave.idle_mode is False
    snap = _status_snapshot(conf, data.wave)
    assert snap.next_wave_at == 1_000_000.0 + 3600.0
    assert snap.refresh_interval == 3600.0
    assert "(稳态降频)" not in snap.fresh_text


def _rich_lane(**kw) -> HrLaneState:
    """全字段非默认的档位态(字段面守阵的源值)"""
    base = dict(
        lane="A",
        wave_ts=1_700_000_000.0,
        status=LANE_OK,
        pages=3,
        rows=4,
        cutoff_done=123.5,
        full_depth=True,
        detail="预算截断",
        fail_streak=3,
        count_claim=5,
        count_match=False,
    )
    base.update(kw)
    return HrLaneState(**base)


def test_lane_statuses_full_field_passthrough():
    """LaneStatus 全字段非默认搬运: 每个字段逐一钉死(置 None / 删实参 / 键名改写全部可杀)"""
    data = HrSiteData()
    st = _rich_lane()
    data.wave.lanes = {"A": st, "B": HrLaneState(lane="B"), "C": HrLaneState(lane="C")}
    out, _ = _lane_statuses(data, 1_800_000_000.0)
    a = out[0]
    assert a.lane == "A" and a.status == LANE_OK
    assert a.status_text == "有效" and a.lane_text == "考察中"
    assert a.wave_ts == 1_700_000_000.0 and a.pages == 3 and a.rows == 4
    assert a.cutoff_done == 123.5 and a.full_depth is True and a.fail_streak == 3
    assert a.count_claim == 5 and a.count_match is False and a.detail == "预算截断"
    assert set(a.to_dict()) == {
        "lane",
        "status",
        "status_text",
        "lane_text",
        "wave_ts",
        "pages",
        "rows",
        "cutoff_done",
        "full_depth",
        "fail_streak",
        "count_claim",
        "count_match",
        "detail",
        "text",
    }, "to_dict 键面 = LaneStatus 全字段(asdict 单点)"


def test_lane_statuses_text_composition_exact():
    """ls.text 与 lanes_text 逐字: 全深度/声明/对不平/detail/连续失效与 [x] 标记各就位"""
    data = HrSiteData()
    data.wave.lanes = {"A": _rich_lane(), "B": HrLaneState(lane="B"), "C": HrLaneState(lane="C")}
    out, lanes_text = _lane_statuses(data, 1_800_000_000.0)
    assert out[0].text == "考察中 有效: 3 页 / 4 行(全深度) / 声明 5 行 对不平, 预算截断, 连续失效 3 波"
    assert lanes_text == "A:[x]3页4行(全深度)/声明5 对不平 B:-0页0行 C:-0页0行"


def test_lane_statuses_missing_lane_keeps_rest():
    """缺档位只记「无」不停表: break 变异会让后续档位整段消失"""
    data = HrSiteData()
    data.wave.lanes = {"A": _rich_lane()}
    out, lanes_text = _lane_statuses(data, 1_800_000_000.0)
    assert [ls.lane for ls in out] == ["A"], "缺的档位不进 out(前端按 lanes 键面消费)"
    assert "B:无" in lanes_text and "C:无" in lanes_text, "缺档位在摘要里如实标「无」, 且后续档位不被 break 吞掉"


def test_lane_statuses_unknown_status_falls_back_to_raw():
    """未知状态人话回落原文: 不静默丢也不变 None(前端要能显示原始状态排障)"""
    data = HrSiteData()
    data.wave.lanes = {"A": _rich_lane(status="weird-status")}
    out, _ = _lane_statuses(data, 1_800_000_000.0)
    assert out[0].status_text == "weird-status"
    assert out[0].text.startswith("考察中 weird-status:"), "回落值进 text, 不是 None"


def test_lane_statuses_text_condition_boundaries():
    """text 各条件边界: 全深度假/声明 None/对不平 True 与 None/detail 空/连续失效 1 与 2"""
    data = HrSiteData()
    data.wave.lanes = {
        "A": _rich_lane(full_depth=False, count_claim=None, count_match=None, detail="", fail_streak=1),
    }
    out, lanes_text = _lane_statuses(data, 1_800_000_000.0)
    assert out[0].text == "考察中 有效: 3 页 / 4 行", "全深度假/无声明/对不平缺失/detail 空/streak=1 时无附加段"
    assert lanes_text == "A:[x]3页4行 B:无 C:无", "摘要同口径: 无 (全深度) 无 /声明"
    data2 = HrSiteData()
    data2.wave.lanes = {"A": _rich_lane(full_depth=False, count_claim=None, count_match=None, detail="", fail_streak=2)}
    out2, _ = _lane_statuses(data2, 1_800_000_000.0)
    assert out2[0].text.endswith(", 连续失效 2 波"), "streak=2 即标注(>1 口径, 不是 >=1)"
    data3 = HrSiteData()
    data3.wave.lanes = {"A": _rich_lane(status=LANE_FAILED, count_claim=7, count_match=True, fail_streak=0)}
    out3, lanes3 = _lane_statuses(data3, 1_800_000_000.0)
    assert out3[0].status_text == "失效" and out3[0].lane_text == "考察中"
    assert "声明 7 行" in out3[0].text and "对不平" not in out3[0].text, "count_match=True 不标对不平"
    assert lanes3 == "A:x3页4行(全深度)/声明7 B:无 C:无", "failed 档摘要标记 x 且不带对不平"


def test_lanes_summary_parity_between_service_and_status():
    """同一波次两套摘要逐字相等(issue 26-10-29-1327 验证①): service._lanes_summary_from 与
    status._lane_statuses 的 parts 在 tag/深度/计数三部件上读同一 model 单点, 排版模板一致
    ⇒ 整串相等; 缺档与未知状态回落也同口径(透传原值不静默降级)"""
    data = HrSiteData()
    data.wave.lanes = {"A": _rich_lane(), "B": HrLaneState(lane="B"), "C": HrLaneState(lane="C")}
    _, lanes_text = _lane_statuses(data, 1_800_000_000.0)
    assert _lanes_summary_from(data.wave.lanes) == lanes_text
    assert lanes_text == "A:[x]3页4行(全深度)/声明5 对不平 B:-0页0行 C:-0页0行"
    # 未知档位状态: 两侧同走 LANE_TAGS.get(status, status) 透传, 不各自回落
    data2 = HrSiteData()
    data2.wave.lanes = {"A": _rich_lane(status="weird-status")}
    _, lanes_text2 = _lane_statuses(data2, 1_800_000_000.0)
    assert _lanes_summary_from(data2.wave.lanes) == lanes_text2
    assert lanes_text2.startswith("A:weird-status3页4行"), "未知状态透传原文, 不是 -"


def test_duration_text_exact_tiers():
    """人话时长四档精确边界: 恰等 86400/3600/60 归上档, +1s 组合逐位"""
    assert duration_text(0) == "0s" and duration_text(-5) == "0s", "负数钳 0"
    assert duration_text(7) == "7s" and duration_text(59) == "59s"
    assert duration_text(60) == "1m0s" and duration_text(61) == "1m1s"
    assert duration_text(3599) == "59m59s" and duration_text(3600) == "1h0m"
    assert duration_text(3601) == "1h0m" and duration_text(3660) == "1h1m"
    assert duration_text(86399) == "23h59m" and duration_text(86400) == "1d0h"
    assert duration_text(86400 + 3600) == "1d1h" and duration_text(90065) == "1d1h"


def test_ago_text_never_suffix_and_fraction():
    """「从未」三形态 + 「Nx前」后缀 + 小数秒(int 截断)"""
    now = 1_800_000_000.0
    assert ago_text(0, now) == "从未" and ago_text(-5, now) == "从未"
    assert ago_text(0.5, now) == f"{duration_text(now - 0.5)}前", "0<ts 即算有过(不是从未)"
    assert ago_text(now - 30, now) == "30s前" and ago_text(now - 90, now) == "1m30s前"
    assert ago_text(now - 7200, now) == "2h0m前"


def test_stamp_text_format_zero_and_edges():
    """绝对时刻格式逐字(%m-%d %H:%M:%S) + 0/负/1 的「-」边界"""
    assert stamp_text(0) == "-" and stamp_text(-1) == "-"
    import time as _time
    assert stamp_text(1) == _time.strftime("%m-%d %H:%M:%S", _time.localtime(1))
    assert stamp_text(1_800_000_000.0) == _time.strftime("%m-%d %H:%M:%S", _time.localtime(1_800_000_000.0))


def test_need_seed_text_tiers_exact():
    """镜像站点书写形态全档: None/-、HH:MM:SS、N天HH:MM:SS 与负值钳 0"""
    assert need_seed_text(None) == "-"
    assert need_seed_text(0) == "00:00:00" and need_seed_text(-5) == "00:00:00"
    assert need_seed_text(1) == "00:00:01" and need_seed_text(59) == "00:00:59"
    assert need_seed_text(60) == "00:01:00" and need_seed_text(3599) == "00:59:59"
    assert need_seed_text(3600) == "01:00:00" and need_seed_text(86399) == "23:59:59"
    assert need_seed_text(86400) == "1天00:00:00" and need_seed_text(90065) == "1天01:01:05"


def test_lane_counts_counts_every_lane():
    """四档计数(含免罪档 D)逐键精确; 同档多条目累加"""
    data = _site(
        [
            _entry(1, lane="A"),
            _entry(2, lane="A"),
            _entry(3, lane="B"),
            _entry(4, lane="C"),
            _entry(5, lane="D"),
            _entry(6, lane="D"),
        ]
    )
    assert lane_counts(data) == {"A": 2, "B": 1, "C": 1, "D": 2}


def test_retention_text_ratio_zero_and_tails():
    """守恒行: ratio=0 是「有上波但零留存」不是「不适用」; 正常/WARN 两尾注逐字"""
    data = HrSiteData()
    data.wave.retention_ratio = 0.0
    data.wave.retention_ok = True
    data.wave.prev_a_tids = {1: "a", 2: "b", 3: "c"}
    assert _retention_text(data) == "上波 A 档 3 行, 本波留存率 0%, 正常"
    data.wave.retention_ok = False
    assert _retention_text(data) == "上波 A 档 3 行, 本波留存率 0%, WARN: 不达标(批量未列出签发已冻结)"
    data.wave.retention_ratio = 0.5
    assert _retention_text(data) == "上波 A 档 3 行, 本波留存率 50%, WARN: 不达标(批量未列出签发已冻结)"
    data.wave.retention_ratio = -1.0
    assert _retention_text(data) == "不适用(上波无 A 档行)"


def test_site_conf_interval_stub_objects():
    """getattr 缺省与 or 兜底各形态: stub conf/wave 缺属性/值为 0 都可观测"""
    class _Wave:
        def __init__(self, idle):
            self.idle_mode = idle

    class _Conf:
        def __init__(self, refresh, idle=None):
            if refresh is not None:
                self.refresh_interval = refresh
            if idle is not None:
                self.idle_refresh_interval = idle

    # 稳态期: idle 间隔为 0 也要如实回 0.0(or 兜底成 1.0 会被杀)
    assert site_conf_interval(_Conf(3600.0, 0.0), _Wave(True)) == 0.0
    # 稳态期但 conf 没配 idle 键: 回落 0.0(删缺省 → AttributeError; 缺省改 1.0 会被杀)
    assert site_conf_interval(_Conf(3600.0), _Wave(True)) == 0.0
    # 常态期: refresh 间隔为 0 如实回 0.0
    assert site_conf_interval(_Conf(0.0, 86400.0), _Wave(False)) == 0.0
    # 常态期但 conf 没配 refresh 键: 回落 0.0(删缺省 → AttributeError; 缺省改 1.0 会被杀)
    assert site_conf_interval(_Conf(None, 86400.0), _Wave(False)) == 0.0

    # 旗标缺省/为 None 都按常态(存量对象无该属性的兼容形态)
    class _Bare:
        pass

    assert site_conf_interval(_Conf(60.0), _Bare()) == 60.0, "wave 无 idle_mode 属性 → 常态(缺省改 True 会被杀)"
    assert site_conf_interval(_Conf(60.0, 10.0), _Wave(None)) == 60.0, "旗标 None 按常态"


def test_blocking_reason_branches_exact():
    """四分支文案逐字 + next_wave_at 缺省形态(默认 0.0 ⇒ 不带下次核对时刻)"""
    empty = HrSiteView(site="s")
    data = HrSiteData()
    assert blocking_reason(empty, data, False) == "索引里还没有任何可判数据(先让浏览器扩展跑一轮取数)"
    only_terminal = HrSiteView(site="s", lane_terminal={"h": None})
    assert blocking_reason(
        only_terminal, data, False
    ) == "本波未全部档位有效(截断/失效): 命中照常, 批量「未列出」待下波续判", "lane_terminal 非空即可判数据, 走放行分支"
    data.wave.zero_rows = True
    data.wave.lanes = {"A": HrLaneState(lane="A")}  # count_claim=None ⇒ 未计数自证
    assert blocking_reason(only_terminal, data, False) == "结构完好但清单为 0: 不签发放行 —— 需 --hr-confirm-empty 人工对账一次"
    data.wave.zero_rows = False
    assert blocking_reason(only_terminal, data, False) == "本波未全部档位有效(截断/失效): 命中照常, 批量「未列出」待下波续判"
    data.wave.releases_enabled = True
    assert blocking_reason(only_terminal, data, True) == "数据已过复用窗,(可点『立即拉取』提前)", "next_wave_at 缺省(0.0)不带下次核对时刻"
    assert blocking_reason(only_terminal, data, True, next_wave_at=1_800_000_000.0
                          ) == (f"数据已过复用窗, 下次核对清单 {stamp_text(1_800_000_000.0)}(可点『立即拉取』提前)")
    assert blocking_reason(only_terminal, data, False) == "", "全部就绪不拦"


class _RichSvc:
    """site_status 富快照依赖: 按站点返回不同频控(钉 limits_for(site) 实参)"""
    def __init__(self, conf: SiteHrCheckConfig):
        self.site_confs = {"s": conf, "other": conf, "empty": conf}
        self._by_site = {
            "s": HrLimits(min_interval=2.0, max_requests_per_day=100, allow_window="09:00-18:00"),
            "empty": HrLimits(min_interval=2.0, max_requests_per_day=100, allow_window=""),
            None: HrLimits(min_interval=99.0, max_requests_per_day=999, allow_window="xx"),
        }

    def limits_for(self, site: str) -> HrLimits:
        return self._by_site.get(site, self._by_site[None])

    def site_path(self, site: str) -> str:
        return f"/data/hr/{site}.json"


def _rich_data(now: float) -> HrSiteData:
    """三活跃一失踪 + 部分回填 + 观察期的富站点数据"""
    data = HrSiteData()
    data.revision = 9
    data.fetched_at = now - 60
    data.expires_at = now + 100
    data.writer_instance = "writer-1"
    data.writer_heartbeat = now - 10
    data.index = {
        1: _entry(1, lane="A", down=1000, up=200, ratio=0.5, need=3661, ih1="a" * 40, missing_streak=1),
        2: _entry(2, lane="A", missing_streak=2),
        3: _entry(3, lane="B", ih2="b" * 40, missing_streak=5),
        4: _entry(4, lane="D", active=False),
    }
    data.downloaded = {1: object()}
    data.fails = {2: object()}
    data.verified = {"a" * 40: HrVerified(infohash="a" * 40, tid=1, verified_ts=now - 100)}
    data.wave.lanes = {"A": _rich_lane(), "B": HrLaneState(lane="B"), "C": HrLaneState(lane="C")}
    data.wave.healthy_ts = now - 3600
    data.wave.releases_enabled = True
    data.wave.retention_ratio = 0.5
    data.wave.retention_ok = True
    data.wave.prev_a_tids = {1: "a" * 40}
    data.wave.notes = "本波备注"
    data.rate.day_window = day_key(now)
    data.rate.day_count = 7
    data.rate.last_fetch_ts = now - 30
    return data


def _rich_view(**kw) -> HrSiteView:
    base = dict(
        site="s",
        listing="list",
        channel_state=CHANNEL_OK,
        generated_at=1_800_000_000.0,
        healthy_ts=1_800_000_000.0 - 3600,
        lane_a={"a" * 40: _entry(1, ih1="a" * 40)},
        lane_terminal={"b" * 40: _entry(3, ih2="b" * 40)},
        verified={},
    )
    base.update(kw)
    return HrSiteView(**base)


NOW = 1_800_000_000.0


def test_site_status_rich_snapshot_fields():
    """富快照全字段面: quota/pending/backfill/observing/keys/allow_window/blocking 逐一钉死"""
    conf = SiteHrCheckConfig(enabled=True, listing="list", refresh_interval=3600.0, idle_refresh_interval=86400.0)
    snap = site_status("s", _rich_data(NOW), _rich_view(), _RichSvc(conf), NOW)
    assert snap.site == "s" and snap.enabled is True and snap.listing == "list" and snap.now == NOW
    assert snap.channel_state == CHANNEL_OK and snap.channel_text == "正常"
    assert snap.revision == 9 and snap.file_path == "/data/hr/s.json" and snap.read_error == ""
    assert snap.fetched_at == NOW - 60 and snap.healthy_ts == NOW - 3600 and snap.expires_at == NOW + 100
    assert snap.next_wave_at == NOW and snap.refresh_interval == 3600.0
    assert snap.idle_mode is False and snap.stale is False
    assert snap.fresh_text == (
        f"上次取波 {ago_text(NOW - 60, NOW)} · 最近健康波 {ago_text(NOW - 3600, NOW)}"
        f" · 复用窗至 {stamp_text(NOW + 100)} · 下次核对清单 {stamp_text(NOW)}"
    )
    assert snap.lanes_text == "A:[x]3页4行(全深度)/声明5 对不平 B:-0页0行 C:-0页0行"
    assert snap.releases_enabled is True and snap.zero_rows is False
    assert snap.empty_confirmed is False and snap.count_attested_empty is False
    assert snap.retention_text == "上波 A 档 1 行, 本波留存率 50%, 正常"
    assert snap.notes == "本波备注" and snap.writer_instance == "writer-1" and snap.writer_heartbeat == NOW - 10
    assert snap.index_total == 4 and snap.index_active == 3
    assert snap.lane_counts == {"A": 2, "B": 1, "D": 1}
    assert snap.pending_infohash == 1, "仅 v1 或仅 v2 都不算待回填(and 口径)"
    assert snap.backfill_ratio == 2 / 3
    assert snap.managed == 1 and snap.keys == 2
    assert snap.downloaded == 1 and snap.fails == 1 and snap.verified == 1
    assert snap.observing == 2, "A 档且 missing_streak>0 计观察期(B 档 streak 不计; streak=1 也计, >1 口径)"
    assert snap.quota.day == 7 and snap.quota.day_max == 100, "limits_for 按站点实参取(不是 None)"
    assert snap.quota.left == 93 and snap.quota.last_fetch_ts == NOW - 30 and snap.quota.min_interval == 2.0
    assert snap.quota.next_reset > 0
    assert snap.quota.text == "今天 7/100(零点重置) · 还能取 93 次 · 最近请求 30s前 · 最小间隔 2s"
    assert snap.allow_window == "09:00-18:00"
    assert snap.blocking == "", "数据就绪不拦"
    # listing 从站点配置透传(dataclass 默认恰是 list, 删实参会静默回落 —— 全站型站点即失真)
    conf_none = SiteHrCheckConfig(enabled=True, listing="none", refresh_interval=3600.0, idle_refresh_interval=86400.0)
    snap_none = site_status("s", _rich_data(NOW), _rich_view(), _RichSvc(conf_none), NOW)
    assert snap_none.listing == "none", "listing 透传站点配置(不吃 dataclass 默认值)"
    # allow_window 空值兜空串(or "XXXX" 占位会被前端当配置展示)
    snap_empty = site_status("empty", _rich_data(NOW), _rich_view(), _RichSvc(conf), NOW)
    assert snap_empty.allow_window == "", "allow_window 空值兜空串(不是占位文本)"


def test_site_status_observing_counts_only_positive_streak():
    """观察期只计 missing_streak>0 的 A 档: streak=0(新进清单)不计(>=0 口径会把它们也算进去)"""
    conf = SiteHrCheckConfig(enabled=True, listing="list", refresh_interval=3600.0, idle_refresh_interval=86400.0)
    data = _rich_data(NOW)
    data.index[5] = _entry(5, lane="A", missing_streak=0)  # 活跃, 尚未连续失效
    snap = site_status("s", data, _rich_view(), _RichSvc(conf), NOW)
    assert snap.observing == 2, "streak=0 的 A 档不进观察期计数"


def test_site_status_stale_and_boundary():
    """过复用窗: 「(已过)」注记 + blocking 带下次核对清单时刻; 恰等 now 不算过"""
    conf = SiteHrCheckConfig(refresh_interval=3600.0, idle_refresh_interval=86400.0)
    stale_data = _rich_data(NOW)
    stale_data.expires_at = NOW - 100
    snap = site_status("s", stale_data, _rich_view(), _RichSvc(conf), NOW)
    assert snap.stale is True
    assert f"复用窗至 {stamp_text(NOW - 100)}(已过)" in snap.fresh_text, "过期注记逐字"
    assert snap.blocking == f"数据已过复用窗, 下次核对清单 {stamp_text(NOW)}(可点『立即拉取』提前)"
    edge = _rich_data(NOW)
    edge.expires_at = NOW
    assert site_status("s", edge, _rich_view(), _RichSvc(conf), NOW).stale is False, "恰等 now 不算过(> 口径)"


def test_site_status_no_healthy_wave():
    """healthy_ts=0 ⇒ next_wave_at=0.0(or True 变异会算出间隔值)且 fresh_text 不带下次核对段"""
    conf = SiteHrCheckConfig(refresh_interval=3600.0, idle_refresh_interval=86400.0)
    data = _rich_data(NOW)
    data.wave.healthy_ts = 0.0
    snap = site_status("s", data, _rich_view(), _RichSvc(conf), NOW)
    assert snap.next_wave_at == 0.0 and snap.healthy_ts == 0.0
    assert "下次核对清单" not in snap.fresh_text


def test_site_status_unknown_channel_text():
    """未知通道态回落「未启用」: 不静默丢也不变 None"""
    conf = SiteHrCheckConfig(refresh_interval=3600.0, idle_refresh_interval=86400.0)
    snap = site_status("s", _rich_data(NOW), _rich_view(channel_state="zzz"), _RichSvc(conf), NOW)
    assert snap.channel_state == "zzz" and snap.channel_text == "未启用"


def test_site_status_empty_confirmed_boundary():
    """对账戳 ts=1 即算已确认(>0 口径; >1 会把 1 误判未确认)"""
    conf = SiteHrCheckConfig(refresh_interval=3600.0, idle_refresh_interval=86400.0)
    data = _rich_data(NOW)
    data.empty_confirmed_at = 1.0
    assert site_status("s", data, _rich_view(), _RichSvc(conf), NOW).empty_confirmed is True


def test_site_status_empty_index_backfill():
    """空索引: backfill 回落 0.0(else 1.0 会被杀), 各计数为 0"""
    conf = SiteHrCheckConfig(refresh_interval=3600.0, idle_refresh_interval=86400.0)
    data = HrSiteData()
    data.wave.healthy_ts = NOW - 100
    snap = site_status("s", data, HrSiteView(site="s"), _RichSvc(conf), NOW)
    assert snap.index_total == 0 and snap.index_active == 0
    assert snap.pending_infohash == 0 and snap.backfill_ratio == 0.0
    assert snap.lane_counts == {} and snap.managed == 0 and snap.keys == 0


def test_site_status_to_dict_field_surface():
    """SiteStatus.to_dict 键面 = 全字段(asdict 单点; 零 no tests)"""
    conf = SiteHrCheckConfig(refresh_interval=3600.0, idle_refresh_interval=86400.0)
    snap = site_status("s", _rich_data(NOW), _rich_view(), _RichSvc(conf), NOW)
    keys = set(snap.to_dict())
    assert keys == SITE_STATUS_KEYS, "字段面与 WebUI 契约逐字对齐"
    assert set(snap.to_dict()["quota"]) == set(QuotaStatus().to_dict())


class _StubStore:
    def __init__(self, result):
        self._result = result

    def read_unlocked(self):
        return self._result


class _StubSvc:
    def __init__(self, results):
        self._results = results
        self.site_confs = {name: SiteHrCheckConfig() for name in results}
        self.limits = HrLimits(min_interval=0.0, max_requests_per_day=10)

    def enabled_sites(self):
        # 刻意与显式 sites 不同序: 恒定 enabled_sites(忽略实参)的变异必须被显式序断言杀
        return list(reversed(self._results))

    def limits_for(self, site: str) -> HrLimits:
        return self.limits

    def site_path(self, site: str) -> str:
        return f"/data/hr/{site}.json"

    def store(self, site):
        return _StubStore(self._results[site])

    def build_view_for(self, site, data):
        return HrSiteView(site=site)


def test_build_site_statuses_reads_error_and_sites():
    """显式站点序 + read_error 空串/原文透出(读坏不抛, 如实带出)"""
    good = (HrSiteData(), None)
    bad = (HrSiteData(), "坏 JSON")
    svc = _StubSvc({"a": good, "b": bad})
    out = build_site_statuses(svc, NOW, sites=["a", "b"])
    assert [s.site for s in out] == ["a", "b"], "显式站点表按序(不回落 enabled_sites)"
    assert out[0].read_error == "" and out[1].read_error == "坏 JSON"
    assert all(isinstance(s, SiteStatus) for s in out)
    default_out = build_site_statuses(svc, NOW)
    assert [s.site for s in default_out] == ["b", "a"], "不传站点回落 enabled_sites(其序)"


def test_channel_texts_carry_the_next_action():
    """两个新通道态的人话逐字且**带动作**: 用户看到这一行时正在问「为什么一个都没取到」,
    只说现象等于把排障整段留给人(2026-10-28 那次 12h 里, 界面只会说「静默」)"""
    assert CHANNEL_TEXTS[CHANNEL_NO_PERMISSION] == "扩展未授权该站点(去扩展选项页授权)"
    assert CHANNEL_TEXTS[CHANNEL_NETWORK] == "扩展连不上站点网络(查浏览器网络/代理)"
    assert "授权" in CHANNEL_TEXTS[CHANNEL_NO_PERMISSION]
    assert "代理" in CHANNEL_TEXTS[CHANNEL_NETWORK]
    conf = SiteHrCheckConfig(refresh_interval=3600.0, idle_refresh_interval=86400.0)
    for state in (CHANNEL_NO_PERMISSION, CHANNEL_NETWORK):
        snap = site_status("s", _rich_data(NOW), _rich_view(channel_state=state), _RichSvc(conf), NOW)
        assert snap.channel_state == state, "原值透出(前端按态上色, 不靠文案猜)"
        assert snap.channel_text == CHANNEL_TEXTS[state], "视图直取单点, 另写第二份文案即红"


def test_blocking_reason_channel_cause_precedes_data_symptoms():
    """通道病因排在整条判定链最前(计划 D6): 取数根本没发生时, 后面几句描述的都是「没取到之后
    的样子」, 说出来只会把人引向错的动作"""
    data = HrSiteData()
    data.wave.zero_rows = True
    data.wave.lanes = {"A": HrLaneState(lane="A")}  # count_claim=None ⇒ 未计数自证
    data.wave.releases_enabled = True
    empty = HrSiteView(site="s")  # 索引全空: 「先让扩展跑一轮取数」本该命中
    only_terminal = HrSiteView(site="s", lane_terminal={"h": None})
    # 阴性对照: 没有通道病因时两句旧文案照旧 —— 证明下面的断言不是「恒返回第一句」
    assert "先让浏览器扩展跑一轮取数" in blocking_reason(empty, data, False)
    assert "--hr-confirm-empty" in blocking_reason(only_terminal, data, False)

    for view in (
        HrSiteView(site="s", channel_state=CHANNEL_NO_PERMISSION),
        HrSiteView(site="s", channel_state=CHANNEL_NO_PERMISSION, lane_terminal={"h": None}),
    ):
        text = blocking_reason(view, data, False)
        assert "授权" in text, "缺权限要说清动作(去扩展选项页勾选)"
        assert "先让浏览器扩展跑一轮取数" not in text, "那正是当前做不成的事"
        assert "--hr-confirm-empty" not in text, "零行对账是数据症状, 不是病因"
    net = blocking_reason(HrSiteView(site="s", channel_state=CHANNEL_NETWORK, lane_terminal={"h": None}), data, False)
    assert "代理" in net and "--hr-confirm-empty" not in net


def _channel_state_of(data: HrSiteData, *, enabled: bool = True, now: float = NOW) -> str:
    """借真 service 的 channel_state 判据(不 new 引擎): 它只读 global_conf.channel / data / _now
    三样, 故用探针 self 就能在纯展示测试里守它的口径"""
    from auto_qb.hr.service import HrRefreshService

    class _Probe:
        global_conf = SimpleNamespace(channel=SimpleNamespace(enabled=enabled))

        def _now(self):
            return now

    return HrRefreshService.channel_state(_Probe(), "s", data)


def test_channel_state_stale_trace_ignored():
    """`ts <= healthy_ts` 的陈旧痕不生效: 站点恢复后旧痕不许把卡片一直标红(展示层撒谎比不展示更糟)"""
    data = HrSiteData()
    data.wave.healthy_ts = NOW - 60
    data.channel_last_error = {"kind": CHANNEL_NO_PERMISSION, "detail": "x", "ts": NOW - 3600}
    assert _channel_state_of(data) == CHANNEL_OK, "痕迹早于最近健康波 ⇒ 已经不是它的事了"
    data.channel_last_error = {"kind": CHANNEL_NO_PERMISSION, "detail": "x", "ts": NOW - 30}
    assert _channel_state_of(data) == CHANNEL_NO_PERMISSION, "健康波之后的痕迹才算数"
    data.channel_last_error = {"kind": CHANNEL_NO_PERMISSION, "detail": "x", "ts": NOW - 60}
    assert _channel_state_of(data) == CHANNEL_OK, "恰等 healthy_ts 也不算(> 口径): 同一刻的健康波已解释掉它"
    # 只认两种「要人处置」的形态: 别的 kind 落在这里只说明分类写错了, 不许顶替通道态
    data.channel_last_error = {"kind": "ext-quota", "ts": NOW}
    assert _channel_state_of(data) == CHANNEL_OK
    data.channel_last_error = {"kind": CHANNEL_NETWORK, "ts": "not-a-number"}
    assert _channel_state_of(data) == CHANNEL_OK, "坏 ts 按 0 处理(不猜, 也就永远比不过健康波)"
    data.channel_last_error = {}
    assert _channel_state_of(data) == CHANNEL_OK, "空痕(恢复点清空后的常态)不生效"
