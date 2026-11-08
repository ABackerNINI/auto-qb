"""test_hr_status_entry 测试计划: hr.status 种子明细导出(entry_details, 计划 26-10-01-2216 §7 阶段1)

## 测试计划(每个测试函数一条)
- test_entry_details_sort_matches_cli_order: 排序与 CLI 明细表口径一致(档位·下载量同一公式; 下载量缺失按 0)
- test_entry_details_keeps_missing_rows: 失踪行(active=False)不丢且参与同一排序 —— 全量清单一览是 issue 本意
- test_entry_details_need_seed_text_reuses_single_point: need_seed 人话确为复用单点(与 CLI 同一函数)而非另写
- test_entry_details_verified_join: verified join —— 有记录→ts+source 原值+人话 / 无记录→未核实 / v2 键也能命中
- test_entry_details_source_texts: 放行来源人话映射(D 免罪 / 未列出 / 已达标); 未知原值回落原文不静默丢
- test_entry_details_field_surface: 导出字段面 = §3 P0+P1 全集; remain_seconds 等 P2 字段不得出现(决策点③)
- test_mark_local_present_v1_hit: 本地库存在(v1 命中) -> local_present=True
- test_mark_local_present_absent: 本地不存在 -> local_present=False(未做种)
- test_mark_local_present_v2_only_hit: 仅 v2 命中(v1 未命中) -> local_present=True
- test_mark_local_present_case_insensitive_hit: 大小写差异命中(站点清单与 qB hash 书写形态不同) -> local_present=True
- test_mark_local_present_empty_hash_skipped: 空 infohash 不探测(空串 casefold 进集合也不误命中)

### P1 覆盖率提升轮: 展示层与模型长尾
- test_model_lane_predicates_and_done_epoch_edges: lane_is_satisfied/exempt + done_epoch 空值与坏值不猜
- test_model_infohash_of_falls_back_to_downloaded: infohash_of 回落永久层(v1 优先, 缺失回落 v2)
- test_model_from_json_drops_invalid_verified_records: 放行记录脏数据(无 hash/无时刻)不入账
- test_model_infohash_of_prefers_index: infohash_of 索引条目优先且 v1 优先 v2(有索引就不回落)

### 拉取历史导出(history_rows, 计划 26-10-04-0312 §3.4)
- test_history_rows_merges_sites_desc_and_site_column: 多站合并成一条时间轴, ts 降序, 行带 site 归属
- test_history_rows_limit_truncates_newest: limit 截最新的 N 条; limit<=0 回空表(上限钳制是调用方的参数卫生)
- test_history_rows_badge_mapping: 结果徽章六态查表 + confirm_empty 特判优先 + defer 走 waiting 映射
  (拦下 dim, kind_text 区分「取数波被拦/立即拉取被拦」) + 未知 action 回落原值不静默丢
- test_history_rows_plain_texts_and_lanes: 人话字段取值 —— ts_text/elapsed_text 复用单点, kind/trigger
  人话映射, lanes 附 lane_text/status_text(取 LANE_TEXTS/LANE_STATUS_TEXTS 单点), 计数字段透传
- test_history_rows_field_surface: 行键面 = §3.4 全集; lane 子键面钉死(前端只消费后端算好字段的契约面)

### 稳态降频展示同步(计划 26-10-05-0555 S3 + 拍板 D1)

### R20 展示导出变异守阵(issue 26-10-10-1108-test-hr-mutation-display, 排序口径/人话回落/字段面)
- test_entry_details_sort_none_download_tiebreak: 下载量缺失与 1 的排序次序(or 0 口径)
- test_entry_details_field_surface_nondefault: EntryDetail 全字段非默认(键名/置 None/删实参全杀)
- test_entry_details_unknown_lane_falls_back_to_raw: 未知档位 lane_text 回落原文
- test_history_lanes_skips_non_dict_keeps_rest: 脏键(非 dict)跳过不停表
- test_history_lanes_defaults_and_fallbacks: 缺键走默认(空串/0) + 未知 lane/status 回落原文 + 字段面
- test_history_rows_stable_tiebreak_and_fallbacks: 同 ts 跨站/同站保持插入序(不按 site 排) + 未知 kind/trigger 回落 + 字段面
- test_history_lanes_dirty_numeric_values_do_not_raise: lanes 内层 pages/rows 脏值(非数字串/容器/inf/1e999/NaN)按 _as_int 口径兜 0 不抛, 合法值语义不变(issue 26-11-07-0527 #15; 26-11-08-0827)
- test_history_rows_dirty_lane_values_do_not_raise: 表3 端到端 —— history lanes 内层脏计数经 history_rows 不整体抛错(#15 失败场景)

### 通道病因可见化(计划 26-10-29-0147 W3/D6)
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


def test_entry_details_sort_matches_cli_order():
    """排序与 CLI 明细表口径一致: key = (档位, -下载量)(report._print_status_rows 同一公式)"""
    data = _site(
        [
            _entry(1, lane="C", down=100),
            _entry(2, lane="A", down=500),
            _entry(3, lane="A", down=900),
            _entry(4, lane="B", down=10),
            _entry(5, lane="D", down=999),
            _entry(6, lane="A", down=None),  # 下载量缺失按 0 计, 落 A 档末位
        ]
    )
    rows = entry_details(data)
    assert [(r.tid, r.lane) for r in rows] == [(3, "A"), (2, "A"), (6, "A"), (4, "B"), (1, "C"), (5, "D")]


def test_entry_details_keeps_missing_rows():
    """失踪行不丢: active=False 也导出, 且与活跃行按同一 key 排序(前端靠状态列弱化)"""
    data = _site([
        _entry(1, lane="A", down=10),
        _entry(2, lane="A", down=99, active=False, missing_streak=2),
    ])
    rows = entry_details(data)
    assert [r.tid for r in rows] == [2, 1], "失踪行下载量更大, 按同一口径排前面; 但绝不能被丢弃"
    assert rows[0].active is False and rows[0].missing_streak == 2
    assert rows[1].active is True and rows[1].missing_streak == 0


def test_entry_details_need_seed_text_reuses_single_point():
    """need_seed 人话复用单点: 与 CLI 明细表是**同一个函数**(上收 report._need_seed_text 后再导入),
    且导出值与 CLI 行单元格逐点相等 —— 另写第二份即红"""
    assert need_seed_text is report.need_seed_text, "CLI 侧与导出侧必须指向同一实现(口径单点)"
    entry = _entry(7, need=3661)
    data = _site([entry, _entry(8, need=None)])
    rows = {r.tid: r for r in entry_details(data)}
    assert rows[7].need_seed_text == report._status_row_cells(entry)[5], "与 CLI 明细表的「还需做种」列同文"
    assert rows[8].need_seed_text == "-"


def test_entry_details_verified_join():
    """verified join: 有记录→verified_ts + source 原值 + 人话; 无记录→未核实(0 / "" / "未核实");
    v1 没有记录时落 v2 命中(观察期出口只写主键的存量形态)"""
    data = _site(
        [
            _entry(1, ih1="aaaa1111", ih2="aaaa2222"),
            _entry(2, ih1="bbbb1111"),
            _entry(3, ih1="dddd1111", ih2="dddd2222"),
        ]
    )
    data.verified["aaaa1111"] = HrVerified(infohash="aaaa1111", tid=1, verified_ts=1759000000.0, source=SOURCE_EXEMPT)
    data.verified["dddd2222"] = HrVerified(
        infohash="dddd2222", tid=3, verified_ts=1759000001.0, source=SOURCE_SATISFIED
    )
    rows = {r.tid: r for r in entry_details(data)}
    assert rows[1].verified_ts == 1759000000.0
    assert rows[1].verified_source == "absent" and rows[1].verified_source_text == "D 免罪"
    assert rows[2].verified_ts == 0.0 and rows[2].verified_source == "" and rows[2].verified_source_text == "未核实"
    assert rows[3].verified_ts == 1759000001.0
    assert rows[3].verified_source == "satisfied" and rows[3].verified_source_text == "已达标"


def test_entry_details_source_texts():
    """放行来源人话映射钉死三键; 未知 source 回落原文(给原始值+人话的兜底, 不静默丢)"""
    assert SOURCE_TEXTS == {SOURCE_EXEMPT: "D 免罪", SOURCE_NOT_LISTED: "未列出", SOURCE_SATISFIED: "已达标"}
    data = _site([_entry(9, ih1="eeee1111")])
    data.verified["eeee1111"] = HrVerified(infohash="eeee1111", tid=9, verified_ts=1.0, source="weird")
    row = entry_details(data)[0]
    assert row.verified_source == "weird" and row.verified_source_text == "weird"


def test_entry_details_field_surface():
    """导出字段面 = 计划 §3 的 P0+P1 全集; remain_seconds 与 P2 字段(已取/失败/本地对照)不得出现"""
    entry = HrEntry(
        tid=101,
        dl_id=173107,
        name="EXAMPLE 101",
        lane="A",
        uploaded_bytes=1,
        downloaded_bytes=2,
        ratio=0.5,
        need_seed_seconds=3600,
        done_iso="2026-09-20 10:00:00",
        remain_seconds=7200,
        infohash_v1="aaaa1111",
        first_seen=111.0,
        last_seen=222.0,
        missing_streak=1,
    )
    row = entry_details(_site([entry]))[0].to_dict()
    assert set(row) == ENTRY_ROW_KEYS, "字段面要与计划 §3 逐字对齐(多导出 = 体积浪费, 少导出 = 前端没得吃)"
    assert "remain_seconds" not in row, "决策点③: 考核窗口倒计时不得进表(2026-09-25 误读教训)"
    assert row["dl_id"] == 173107 and row["done_iso"] == "2026-09-20 10:00:00"
    assert row["lane_text"] == "考察中" and row["first_seen"] == 111.0 and row["last_seen"] == 222.0


def test_model_lane_predicates_and_done_epoch_edges():
    """model 判定谓词与完成时间解析边界(空值/坏值不猜)"""
    from auto_qb.hr.model import lane_is_exempt, lane_is_satisfied

    assert lane_is_satisfied("B") and not lane_is_satisfied("A")
    assert lane_is_exempt("D") and not lane_is_exempt("B")
    entry = HrEntry(tid=1, name="x", done_iso="")
    assert entry.done_epoch is None, "无完成时间 -> None"
    entry.done_iso = "not-a-date"
    assert entry.done_epoch is None, "解析不了 -> None(不猜)"


def test_model_infohash_of_falls_back_to_downloaded():
    """infohash_of: 索引无该 tid 时回落永久层已取记录"""
    from auto_qb.hr.model import HrDownloaded

    data = HrSiteData()
    assert data.infohash_of(9) == "", "两处都没有 -> 空串"
    data.downloaded[9] = HrDownloaded(tid=9, infohash_v1="V1", infohash_v2="V2")
    assert data.infohash_of(9) == "V1"
    data.downloaded[9] = HrDownloaded(tid=9, infohash_v1="", infohash_v2="V2")
    assert data.infohash_of(9) == "V2", "v1 缺失回落 v2"


def test_model_infohash_of_prefers_index():
    """infohash_of: 索引条目优先(且 v1 优先 v2) —— 有索引就不该回落已取记录"""
    from auto_qb.hr.model import HrDownloaded

    data = HrSiteData()
    data.index[1] = HrEntry(tid=1, infohash_v1="IDX1", infohash_v2="IDX2")
    data.downloaded[1] = HrDownloaded(tid=1, infohash_v1="DL1", infohash_v2="DL2")
    assert data.infohash_of(1) == "IDX1", "索引命中优先, 不回落已取记录"
    data.index[1] = HrEntry(tid=1, infohash_v2="IDX2")
    assert data.infohash_of(1) == "IDX2", "v1 缺失回落 v2(而不是取空)"


def test_model_from_json_drops_invalid_verified_records():
    """from_json: 无 infohash / 无时刻的放行记录不入账(脏数据不装进内存)"""
    raw = {
        "verified":
            [
                {
                    "infohash": "OK",
                    "tid": 1,
                    "verified_ts": 5.0
                },
                {
                    "infohash": "",
                    "tid": 2,
                    "verified_ts": 5.0
                },
                {
                    "infohash": "BAD",
                    "tid": 3,
                    "verified_ts": 0.0
                },
            ]
    }
    data = HrSiteData.from_json(raw)
    assert set(data.verified) == {"OK"}


def _rows_with_hashes(**kwargs):
    """构造明细行并就地跑 mark_local_present, 返回 (行按 tid 索引, 本地库 hash 集)

    kwargs = 本地库的 hash 表(by_hash 形态, 值随意 —— join 只看键)。
    """
    from auto_qb.webui.server.routes.hr import mark_local_present

    entries = [
        _entry(1, ih1="aaaa1111", ih2="aaaa2222"),
        _entry(2, ih1="bbbb1111", ih2="bbbb2222"),
        _entry(3, ih1="cccc1111", ih2="cccc2222"),
        _entry(4, ih1="", ih2=""),
    ]
    rows = [r.to_dict() for r in entry_details(_site(entries))]
    mark_local_present(rows, kwargs)
    return {r["tid"]: r for r in rows}


def test_mark_local_present_v1_hit():
    """本地存在(v1 命中) -> True; 完全不在本地库 -> False(未做种, 含本地从未下载的清单行)"""
    rows = _rows_with_hashes(**{"aaaa1111": object()})
    assert rows[1]["local_present"] is True, "v1 命中即算本地存在"
    assert rows[2]["local_present"] is False, "本地不存在 = 未做种(不区分 state 细类, 不存在即 False)"


def test_mark_local_present_absent():
    """本地库为空(空 by_hash) -> 全部行 local_present=False, 端点响应层不抛"""
    rows = _rows_with_hashes()
    assert all(r["local_present"] is False for r in rows.values())


def test_mark_local_present_v2_only_hit():
    """仅 v2 命中(v1 未收录) -> True: 终态冻结给 v1/v2 各写一条, 任一键命中即算"""
    rows = _rows_with_hashes(**{"bbbb2222": object()})
    assert rows[2]["local_present"] is True, "v1 不在、v2 在 -> 本地存在"


def test_mark_local_present_case_insensitive_hit():
    """大小写差异命中: 站点清单与 qB hash 书写形态可能不同, hex 语义等价 -> True"""
    rows = _rows_with_hashes(**{"CCCC1111": object()})
    assert rows[3]["local_present"] is True, "本地库大写、清单小写也必须命中(大小写无关口径)"


def test_mark_local_present_empty_hash_skipped():
    """空 infohash 不探测: 无 hash 行(取数通道刚接通未回填)恒 False, 且空串不误命中本地库的空键"""
    rows = _rows_with_hashes(**{"": object(), "cccc1111": object()})
    assert rows[4]["local_present"] is False, "空 hash 行恒不在本地库(空串不得因集合含空键而误命中)"
    assert rows[3]["local_present"] is True, "空串键不影响有 hash 行的正常探测"
    assert rows[1]["local_present"] is False and rows[2]["local_present"] is False, "不在本地库的行照常回 False"


def _hist(ts: float, *, kind: str = "wave", trigger: str = "auto", action: str = "refreshed", **kw) -> HrHistoryEvent:
    """最小历史事件: 只填被测面用到的字段, 其余走 dataclass 缺省"""
    return HrHistoryEvent(ts=ts, kind=kind, trigger=trigger, action=action, **kw)


def _datas(**sites) -> dict:
    """{站点: 事件表} -> {站点: HrSiteData}(history 字段直挂; 合并/排序的被测面都在这)"""
    return {site: HrSiteData(history=list(events)) for site, events in sites.items()}


def test_history_rows_merges_sites_desc_and_site_column():
    """多站合并成一条时间轴: 按 ts 降序交错排列, 行带 site 归属(前端站点 chips 的过滤键)"""
    datas = _datas(
        alpha=[_hist(100.0), _hist(300.0)],
        beta=[_hist(200.0, trigger="manual", action="partial")],
    )
    rows = history_rows(datas, 10, 999.0)
    assert [(r.site, r.ts) for r in rows] == [("alpha", 300.0), ("beta", 200.0), ("alpha", 100.0)], \
        "跨站 ts 降序, 站点归属逐行带出"


def test_history_rows_limit_truncates_newest():
    """limit 截最新的 N 条; limit<=0 回空表(端点层钳到 [1, HISTORY_CAP], 这里守函数本体的底)"""
    datas = _datas(alpha=[_hist(100.0), _hist(200.0), _hist(300.0)])
    assert [r.ts for r in history_rows(datas, 2, 999.0)] == [300.0, 200.0]
    assert history_rows(datas, 0, 999.0) == []


def test_history_rows_badge_mapping():
    """结果徽章映射(单点在 HISTORY_RESULT_BADGES): 六态查表 + confirm_empty 特判优先 +
    defer 走 action=waiting 映射(拦下 dim, 语义区分靠 kind_text) + 未知 action 回落原值"""
    cases = [
        ("refreshed", "完成", "ok"),
        ("partial", "部分·截断", "warn"),
        ("waiting", "拦下·未到时刻", "dim"),
        ("no-channel", "通道不可用", "err"),
        ("error", "失败", "err"),
        ("skipped-locked", "锁忙", "dim"),
    ]
    for action, text, tone in cases:
        row = history_rows(_datas(alpha=[_hist(1.0, action=action)]), 10, 9.0)[0]
        assert (row.result_text, row.result_tone) == (text, tone), f"徽章映射漂移: {action}"
    row = history_rows(
        _datas(alpha=[_hist(1.0, kind="confirm_empty", trigger="confirm", action="confirm-empty")]), 10, 9.0
    )[0]
    assert (row.result_text, row.result_tone) == ("对账", "blue"), "confirm_empty 特判优先于查表(计划 §3.4)"
    row = history_rows(_datas(alpha=[_hist(1.0, kind="defer", trigger="manual", action="waiting")]), 10, 9.0)[0]
    assert (row.result_text, row.result_tone) == ("拦下·未到时刻", "dim"), "defer 复用 waiting 的拦下映射"
    assert (row.kind, row.kind_text) == ("defer", "立即拉取被拦"), "与自动波被拦的语义区分靠 kind_text"
    row = history_rows(_datas(alpha=[_hist(1.0, action="disabled")]), 10, 9.0)[0]
    assert (row.result_text, row.result_tone) == ("disabled", "dim"), "未知 action 回落原值(原值+人话并给, 不静默丢)"


def test_history_rows_plain_texts_and_lanes():
    """人话字段取值: ts_text/elapsed_text 复用既有单点, kind/trigger 人话映射, lanes 附
    lane_text/status_text(取 LANE_TEXTS/LANE_STATUS_TEXTS 单点), 计数与过程字段原样透传"""
    ev = _hist(
        1759000000.0,
        reason="达到单波页数上限(6), A 档截断",
        reason_kind="budget",
        pages=6,
        rows=214,
        torrents_ok=3,
        torrents_fail=1,
        verified=2,
        elapsed_s=42.6,
        lanes=[{
            "lane": "A",
            "status": "ok",
            "pages": 3,
            "rows": 96,
            "detail": "截断于第 4 页"
        }],
        notes=["n1", "n2"],
        by="abcd12",
    )
    row = history_rows(_datas(alpha=[ev]), 10, 9.0)[0]
    assert row.ts_text == stamp_text(1759000000.0), "绝对时刻复用 stamp_text 单点"
    assert row.elapsed_text == duration_text(42.6), "耗时人话复用 duration_text 单点"
    assert (row.kind, row.kind_text) == ("wave", "取数波")
    assert (row.trigger, row.trigger_text) == ("auto", "自动")
    assert (row.reason, row.reason_kind) == ("达到单波页数上限(6), A 档截断", "budget")
    assert (row.pages, row.rows, row.torrents_ok, row.torrents_fail, row.verified) == (6, 214, 3, 1, 2)
    lane = row.lanes[0]
    assert (lane.lane_text, lane.status_text) == (LANE_TEXTS["A"], LANE_STATUS_TEXTS["ok"]), "档位人话取单点"
    assert (lane.pages, lane.rows, lane.detail) == (3, 96, "截断于第 4 页")
    assert row.notes == ["n1", "n2"] and row.by == "abcd12"


def test_history_rows_field_surface():
    """行键面 = 计划 §3.4 全集; lane 子键面钉死 —— 前端只消费后端算好字段, 键面漂移即红"""
    row = history_rows(_datas(alpha=[_hist(1.0, lanes=[{"lane": "B", "status": "ok"}])]), 10, 9.0)[0].to_dict()
    assert set(row) == HISTORY_ROW_KEYS, "字段面要与计划 §3.4 逐字对齐(多导出 = 体积浪费, 少导出 = 前端没得吃)"
    assert set(row["lanes"][0]) == HISTORY_LANE_KEYS


def test_entry_details_sort_none_download_tiebreak():
    """下载量缺失按 0 计(or 0 口径): None 与 1 的次序 —— 变 or 1 会错序"""
    data = _site([_entry(1, lane="A", down=None), _entry(2, lane="A", down=1)])
    rows = entry_details(data)
    assert [r.tid for r in rows] == [2, 1], "下载量 1 的排在缺失(按 0)前面"


def test_entry_details_field_surface_nondefault():
    """EntryDetail 全字段非默认: 置 None / 删实参 / 键名改写全部可杀"""
    data = _site([_entry(1, lane="A", down=100, up=200, ratio=0.5, need=3661, ih1="a" * 40)])
    data.verified["a" * 40] = HrVerified(infohash="a" * 40, tid=1, verified_ts=1_800_000_000.0, source=SOURCE_SATISFIED)
    (d, ) = entry_details(data)
    assert d.tid == 1 and d.name == "EXAMPLE 1" and d.lane == "A" and d.lane_text == "考察中"
    assert d.uploaded_bytes == 200 and d.downloaded_bytes == 100 and d.ratio == 0.5
    assert d.need_seed_seconds == 3661 and d.need_seed_text == "01:01:01"
    assert d.infohash_v1 == "a" * 40 and d.infohash_v2 == ""
    assert d.verified_ts == 1_800_000_000.0 and d.verified_source == SOURCE_SATISFIED
    assert d.verified_source_text == "已达标" and d.done_iso is None and d.active is True
    assert d.missing_streak == 0 and d.first_seen == 111.0 and d.last_seen == 222.0


def test_entry_details_unknown_lane_falls_back_to_raw():
    """未知档位 lane_text 回落原文: 不静默丢也不变 None"""
    data = _site([_entry(1, lane="Z")])
    (d, ) = entry_details(data)
    assert d.lane_text == "Z"


def test_history_lanes_skips_non_dict_keeps_rest():
    """脏键(非 dict)跳过不停表: break 变异会丢掉后续合法行"""
    rows = _history_lanes(["not-a-dict", {"lane": "A", "status": "ok"}, None, {"lane": "B", "status": "failed"}])
    assert [r.lane for r in rows] == ["A", "B"]


def test_history_lanes_defaults_and_fallbacks():
    """缺键走默认(空串/0) + 未知 lane/status 回落原文 + 字段面"""
    rows = _history_lanes([{"lane": "A", "status": "ok"}, {"lane": "Z", "status": "weird"}])
    assert rows[0].lane == "A" and rows[0].lane_text == "考察中"
    assert rows[0].status_text == "有效" and rows[0].pages == 0 and rows[0].rows == 0 and rows[0].detail == ""
    assert rows[1].lane_text == "Z", "未知档位回落原文"
    assert rows[1].status_text == "weird", "未知状态回落原文"
    rich = _history_lanes([{"lane": "C", "status": "failed", "pages": 2, "rows": 9, "detail": "d"}])[0]
    assert (rich.lane, rich.lane_text, rich.status, rich.status_text) == ("C", "未达标", "failed", "失效")
    assert (rich.pages, rich.rows, rich.detail) == (2, 9, "d")
    assert set(rich.to_dict()) == HISTORY_LANE_KEYS
    # 整条缺 lane/status 键: 兜空串(or 右侧占位文本会进展示行)
    empty = _history_lanes([{}])[0]
    assert (empty.lane, empty.lane_text, empty.status, empty.status_text) == ("", "", "", "-"), "缺键兜空串/人话表空串键(不是占位)"


def test_history_lanes_dirty_numeric_values_do_not_raise():
    """lanes 内层 pages/rows 脏值按 _as_int 口径兜 0 不抛(issue 26-11-07-0527 #15): lanes 经
    HrHistoryEvent.from_json 原样透传, 手改坏的站点文件不得让展示层抛 ValueError; 合法值
    (int/数字串)语义与旧 int() 直转一致(_as_int 既有口径, 不另造); inf/1e999/NaN 同兜 0
    (issue 26-11-08-0827: _as_int except 元组补 OverflowError)"""
    rows = _history_lanes(
        [
            {
                "lane": "A",
                "status": "ok",
                "pages": "abc",
                "rows": "not-a-number"
            },
            {
                "lane": "B",
                "status": "ok",
                "pages": "3",
                "rows": "12"
            },
            {
                "lane": "C",
                "status": "ok",
                "pages": 2,
                "rows": 9
            },
            {
                "lane": "D",
                "status": "ok",
                "pages": [],
                "rows": {}
            },
            {
                "lane": "E",
                "status": "ok",
                "pages": float("inf"),
                "rows": 1e999
            },
            {
                "lane": "F",
                "status": "ok",
                "pages": float("nan"),
                "rows": float("-inf")
            },
        ]
    )
    assert [(r.pages, r.rows) for r in rows] == [(0, 0), (3, 12), (2, 9), (0, 0), (0, 0), (0, 0)]


def test_history_rows_dirty_lane_values_do_not_raise():
    """表3 端到端(#15 失败场景): history 事件 lanes 内层脏计数经 history_rows 不得整体抛错"""
    data = HrSiteData()
    data.history = [_ev(1.0, ts=100.0, lanes=[{"lane": "A", "status": "ok", "pages": "oops", "rows": "4"}])]
    rows = history_rows({"s1": data}, 10, 999.0)
    assert [(lane.pages, lane.rows) for lane in rows[0].lanes] == [(0, 4)]


def _ev(site_ts: float, *, kind="wave", trigger="auto", action="refreshed", ts=None, **kw) -> HrHistoryEvent:
    ev = HrHistoryEvent(ts=ts if ts is not None else site_ts, kind=kind, trigger=trigger, action=action)
    for k, v in kw.items():
        setattr(ev, k, v)
    return ev


def test_history_rows_stable_tiebreak_and_fallbacks():
    """同 ts 保持插入序(不按 site 字典序重排) + 未知 kind/trigger 回落原文 + 字段面"""
    datas = {
        "s1": _site([]),
        "s2": _site([]),
    }
    datas["s1"].history = [_ev(1.0, ts=100.0), _ev(1.0, ts=50.0)]
    datas["s2"].history = [_ev(1.0, ts=100.0)]
    rows = history_rows(datas, 10)
    assert [r.site for r in rows] == ["s1", "s2", "s1"], "同 ts 跨站保持站点遍历序; 组内降序"
    same = {"s1": _site([])}
    same["s1"].history = [_ev(1.0, ts=100.0, action="first"), _ev(1.0, ts=100.0, action="second")]
    rows2 = history_rows(same, 10)
    assert [r.action for r in rows2] == ["first", "second"], "同站同 ts 保持写入序(稳定排序)"
    weird = {"s1": _site([])}
    weird["s1"].history = [_ev(1.0, kind="zz", trigger="qq", action="mystery")]
    (r, ) = history_rows(weird, 10)
    assert r.kind_text == "zz" and r.trigger_text == "qq", "未知 kind/trigger 回落原文"
    assert (r.result_text, r.result_tone) == ("mystery", "dim"), "未知 action 回落原值 + dim(不静默丢)"
    rich = {"s1": _site([])}
    rich["s1"].history = [
        _ev(
            1.0,
            elapsed_s=65.0,
            pages=2,
            rows=3,
            torrents_ok=4,
            torrents_fail=5,
            verified=6,
            by="abc123",
            notes=["n"],
            lanes=[{
                "lane": "A"
            }]
        )
    ]
    (rr, ) = history_rows(rich, 10)
    assert rr.ts == 1.0 and rr.ts_text == stamp_text(1.0)
    assert rr.elapsed_s == 65.0 and rr.elapsed_text == "1m5s"
    assert (rr.pages, rr.rows, rr.torrents_ok, rr.torrents_fail, rr.verified) == (2, 3, 4, 5, 6)
    assert rr.by == "abc123" and rr.notes == ["n"] and rr.lanes[0].lane_text == "考察中"
