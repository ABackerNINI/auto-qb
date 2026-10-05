"""test_hr_status 测试计划: hr.status 种子明细导出(entry_details, 计划 26-10-01-2216 §7 阶段1)

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
- test_duration_text_tiers: 人话时长四档(天/时/分/秒) + 负数钳 0
- test_lane_and_quota_status_to_dict_roundtrip_keys: LaneStatus/QuotaStatus 的 to_dict = asdict
- test_blocking_reason_stale_with_next_wave_text: 过复用窗的兜底文案(带/不写下次核对清单时刻)
- test_model_lane_predicates_and_done_epoch_edges: lane_is_satisfied/exempt + done_epoch 空值与坏值不猜
- test_model_infohash_of_falls_back_to_downloaded: infohash_of 回落永久层(v1 优先, 缺失回落 v2)
- test_model_index_by_infohash_skips_inactive_and_empty: 反查表跳过非活跃与空 hash
- test_model_from_json_drops_invalid_verified_records: 放行记录脏数据(无 hash/无时刻)不入账

### 拉取历史导出(history_rows, 计划 26-10-04-0312 §3.4)
- test_history_rows_merges_sites_desc_and_site_column: 多站合并成一条时间轴, ts 降序, 行带 site 归属
- test_history_rows_limit_truncates_newest: limit 截最新的 N 条; limit<=0 回空表(上限钳制是调用方的参数卫生)
- test_history_rows_badge_mapping: 结果徽章六态查表 + confirm_empty 特判优先 + defer 走 waiting 映射
  (拦下 dim, kind_text 区分「取数波被拦/立即拉取被拦」) + 未知 action 回落原值不静默丢
- test_history_rows_plain_texts_and_lanes: 人话字段取值 —— ts_text/elapsed_text 复用单点, kind/trigger
  人话映射, lanes 附 lane_text/status_text(取 LANE_TEXTS/LANE_STATUS_TEXTS 单点), 计数字段透传
- test_history_rows_field_surface: 行键面 = §3.4 全集; lane 子键面钉死(前端只消费后端算好字段的契约面)

### 稳态降频展示同步(计划 26-10-05-0555 S3 + 拍板 D1)
- test_site_status_steady_uses_idle_interval_everywhere: 稳态期(落盘旗标 idle_mode=True)—— 单点换算
  返回 idle_refresh_interval, next_wave_at / refresh_interval / fresh_text 全链跟随 + 「(稳态降频)」注记;
  idle_mode 旗标透出视图(D1 前端 kv 行数据源, 同 stale/(已过) 先例)
- test_site_status_normal_period_keeps_refresh_interval: 常态期(旗标 False)—— next_at / 视图字段仍是
  refresh_interval, 稳态注记不出现
- test_legacy_site_file_without_idle_key_reads_as_false: 存量站点文件兼容 —— 旧 JSON 波次段无 idle_mode
  键读入仍 False, 展示走常态间隔不误降频
"""
import json

from auto_qb.config.models import SiteHrCheckConfig
from auto_qb.hr import report
from auto_qb.hr.model import (
    SOURCE_EXEMPT,
    SOURCE_NOT_LISTED,
    SOURCE_SATISFIED,
    HrEntry,
    HrHistoryEvent,
    HrSiteData,
    HrVerified,
    HrWaveMeta,
)
from auto_qb.hr.ratelimit import HrLimits
from auto_qb.hr.resolve import HrSiteView
from auto_qb.hr.status import (
    LANE_STATUS_TEXTS,
    LANE_TEXTS,
    LaneStatus,
    QuotaStatus,
    SOURCE_TEXTS,
    blocking_reason,
    duration_text,
    entry_details,
    history_rows,
    need_seed_text,
    site_conf_interval,
    site_status,
    stamp_text,
)


def _site(entries) -> HrSiteData:
    """最小站点数据: 只填索引(verified join 与排序的被测面都在这)"""
    data = HrSiteData()
    for e in entries:
        data.index[e.tid] = e
    return data


def _entry(
    tid: int,
    *,
    lane: str = "A",
    down=None,
    up=None,
    ratio=None,
    need=None,
    active: bool = True,
    missing_streak: int = 0,
    ih1: str = "",
    ih2: str = "",
) -> HrEntry:
    return HrEntry(
        tid=tid,
        name=f"EXAMPLE {tid}",
        lane=lane,
        uploaded_bytes=up,
        downloaded_bytes=down,
        ratio=ratio,
        need_seed_seconds=need,
        infohash_v1=ih1,
        infohash_v2=ih2,
        active=active,
        missing_streak=missing_streak,
        first_seen=111.0,
        last_seen=222.0,
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
    expected = {
        "tid",
        "dl_id",
        "name",
        "lane",
        "lane_text",
        "uploaded_bytes",
        "downloaded_bytes",
        "ratio",
        "need_seed_seconds",
        "need_seed_text",
        "infohash_v1",
        "infohash_v2",
        "verified_ts",
        "verified_source",
        "verified_source_text",
        "done_iso",
        "active",
        "missing_streak",
        "first_seen",
        "last_seen",
    }
    assert set(row) == expected, "字段面要与计划 §3 逐字对齐(多导出 = 体积浪费, 少导出 = 前端没得吃)"
    assert "remain_seconds" not in row, "决策点③: 考核窗口倒计时不得进表(2026-09-25 误读教训)"
    assert row["dl_id"] == 173107 and row["done_iso"] == "2026-09-20 10:00:00"
    assert row["lane_text"] == "考察中" and row["first_seen"] == 111.0 and row["last_seen"] == 222.0


# ==================== P1 覆盖率提升轮: 展示层与模型长尾 ====================


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


def test_model_index_by_infohash_skips_inactive_and_empty():
    """反查表: 非活跃条目与空 hash 都不收"""
    active = HrEntry(tid=1, name="a")
    active.infohash_v1 = "HA"
    inactive = HrEntry(tid=2, name="b")
    inactive.infohash_v1 = "HB"
    inactive.active = False
    nohash = HrEntry(tid=3, name="c")
    data = HrSiteData()
    data.index = {1: active, 2: inactive, 3: nohash}
    assert data.index_by_infohash() == {"HA": 1}


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


# ==================== local_present 本地库 join(计划 26-10-02-1936 §3.3, 决策点③a) ====================


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


# ==================== 拉取历史导出(history_rows, 计划 26-10-04-0312 §3.4) ====================


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
    assert set(row) == {
        "ts",
        "ts_text",
        "site",
        "kind",
        "kind_text",
        "trigger",
        "trigger_text",
        "action",
        "result_text",
        "result_tone",
        "reason",
        "reason_kind",
        "pages",
        "rows",
        "torrents_ok",
        "torrents_fail",
        "verified",
        "elapsed_s",
        "elapsed_text",
        "lanes",
        "notes",
        "by",
    }, "字段面要与计划 §3.4 逐字对齐(多导出 = 体积浪费, 少导出 = 前端没得吃)"
    assert set(row["lanes"][0]) == {"lane", "lane_text", "status", "status_text", "pages", "rows", "detail"}


# ---------- 稳态降频展示同步(计划 26-10-05-0555 S3 + 拍板 D1) ----------


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
