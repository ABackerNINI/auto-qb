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
- test_model_infohash_of_prefers_index: infohash_of 索引条目优先且 v1 优先 v2(有索引就不回落)
- test_model_index_by_infohash_continue_skips_inactive_head: 反查表遇非活跃条目 continue 跳过而非 break 停表

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

### R20 展示导出变异守阵(issue 26-10-10-1108-test-hr-mutation-display, 排序口径/人话回落/字段面)
- test_lane_statuses_full_field_passthrough: LaneStatus 全字段非默认搬运(含 to_dict)—— 置 None/删实参类变异全杀
- test_lane_statuses_text_composition_exact: ls.text 与 lanes_text 逐字(全深度/声明/对不平/detail/连续失效/标记)
- test_lane_statuses_missing_lane_keeps_rest: 缺档位不 break 停表 —— 后续档位与「无」标记都在
- test_lane_statuses_unknown_status_falls_back_to_raw: 未知状态人话回落原文, 不静默丢也不变 None
- test_lane_statuses_text_condition_boundaries: text 各条件边界(全深度假/声明 None/对不平 True 与 None/detail 空/连续失效 1 与 2)
- test_duration_text_exact_tiers: 人话时长四档精确边界(恰等 86400/3600/60 与 +1s 组合)
- test_ago_text_never_suffix_and_fraction: 「从未」三形态(0/负/边界) + 「Nx前」后缀 + 小数秒
- test_stamp_text_format_zero_and_edges: 绝对时刻格式逐字 + 0/负/1 的「-」边界
- test_need_seed_text_tiers_exact: 镜像站点书写形态全档(天/时/分/秒边界 + 负值钳 0)
- test_lane_counts_counts_every_lane: 四档计数(含免罪档)逐键精确
- test_retention_text_ratio_zero_and_tails: 守恒行 ratio=0 不误判「不适用」+ 正常/WARN 两尾注
- test_entry_details_sort_none_download_tiebreak: 下载量缺失与 1 的排序次序(or 0 口径)
- test_entry_details_field_surface_nondefault: EntryDetail 全字段非默认(键名/置 None/删实参全杀)
- test_entry_details_unknown_lane_falls_back_to_raw: 未知档位 lane_text 回落原文
- test_history_lanes_skips_non_dict_keeps_rest: 脏键(非 dict)跳过不停表
- test_history_lanes_defaults_and_fallbacks: 缺键走默认(空串/0) + 未知 lane/status 回落原文 + 字段面
- test_history_rows_stable_tiebreak_and_fallbacks: 同 ts 跨站/同站保持插入序(不按 site 排) + 未知 kind/trigger 回落 + 字段面
- test_site_conf_interval_stub_objects: getattr 缺省与 or 兜底(stub conf/wave 无属性/值为 0 各形态)
- test_blocking_reason_branches_exact: 四分支文案逐字 + next_wave_at 缺省形态
- test_site_status_rich_snapshot_fields: 富快照全字段面(quota/pending/backfill/observing/keys/allow_window/blocking)
- test_site_status_stale_and_boundary: 过复用窗(含恰等 now)+「(已过)」注记 + blocking 带下次核对清单时刻
- test_site_status_no_healthy_wave: healthy_ts=0 ⇒ next_wave_at=0.0 且 fresh_text 不带下次核对段
- test_site_status_unknown_channel_text: 未知通道态回落「未启用」
- test_site_status_empty_confirmed_boundary: 对账戳 ts=1 即算已确认(>0 口径)
- test_site_status_limits_for_site_arg: limits_for 按站点取(不是 None)
- test_site_status_to_dict_field_surface: SiteStatus.to_dict 键面 = 全字段(零 no tests)
- test_build_site_statuses_reads_error_and_sites: 显式站点序 + read_error 空串/原文透出
"""
import json

from auto_qb.config.models import SiteHrCheckConfig
from auto_qb.hr import report
from auto_qb.hr.model import (
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
from auto_qb.hr.ratelimit import HrLimits, day_key
from auto_qb.hr.resolve import HrSiteView
from auto_qb.hr.status import (
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
    assert set(row) == ENTRY_ROW_KEYS, "字段面要与计划 §3 逐字对齐(多导出 = 体积浪费, 少导出 = 前端没得吃)"
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


def test_model_infohash_of_prefers_index():
    """infohash_of: 索引条目优先(且 v1 优先 v2) —— 有索引就不该回落已取记录"""
    from auto_qb.hr.model import HrDownloaded

    data = HrSiteData()
    data.index[1] = HrEntry(tid=1, infohash_v1="IDX1", infohash_v2="IDX2")
    data.downloaded[1] = HrDownloaded(tid=1, infohash_v1="DL1", infohash_v2="DL2")
    assert data.infohash_of(1) == "IDX1", "索引命中优先, 不回落已取记录"
    data.index[1] = HrEntry(tid=1, infohash_v2="IDX2")
    assert data.infohash_of(1) == "IDX2", "v1 缺失回落 v2(而不是取空)"


def test_model_index_by_infohash_continue_skips_inactive_head():
    """反查表遇非活跃条目要 continue(跳过)而非 break(整表停): 后面的活跃条目仍要收"""
    inactive = HrEntry(tid=1, name="a")
    inactive.infohash_v1 = "H1"
    inactive.active = False
    active = HrEntry(tid=2, name="b")
    active.infohash_v1 = "H2"
    data = HrSiteData()
    data.index = {1: inactive, 2: active}
    assert data.index_by_infohash() == {"H2": 2}


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
    assert set(row) == HISTORY_ROW_KEYS, "字段面要与计划 §3.4 逐字对齐(多导出 = 体积浪费, 少导出 = 前端没得吃)"
    assert set(row["lanes"][0]) == HISTORY_LANE_KEYS


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


# ---------- R20 展示导出变异守阵(issue 26-10-10-1108-test-hr-mutation-display) ----------
# 排序口径与 CLI 一致 · 人话映射未知回落原文 · 字段面冻结(置 None/删实参/键名改写全杀)


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
    assert lanes_text == "A:[x]3页4行(全)/声明5 对不平 B:-0页0行 C:-0页0行"


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
    # 注: lane_text 的 LANE_TEXTS.get(lane, lane) 回落分支在本函数不可达(遍历 FETCH_LANES 常量,
    # lane 恒 A/B/C) —— 变异 m40(get(lane, None))因此是等价; 可达的同形落在 _history_lanes,
    # 由 test_history_lanes_defaults_and_fallbacks 守。探针勿放不可达分支(空转)。


def test_lane_statuses_text_condition_boundaries():
    """text 各条件边界: 全深度假/声明 None/对不平 True 与 None/detail 空/连续失效 1 与 2"""
    data = HrSiteData()
    data.wave.lanes = {
        "A": _rich_lane(full_depth=False, count_claim=None, count_match=None, detail="", fail_streak=1),
    }
    out, lanes_text = _lane_statuses(data, 1_800_000_000.0)
    assert out[0].text == "考察中 有效: 3 页 / 4 行", "全深度假/无声明/对不平缺失/detail 空/streak=1 时无附加段"
    assert lanes_text == "A:[x]3页4行 B:无 C:无", "摘要同口径: 无 (全) 无 /声明"
    data2 = HrSiteData()
    data2.wave.lanes = {"A": _rich_lane(full_depth=False, count_claim=None, count_match=None, detail="", fail_streak=2)}
    out2, _ = _lane_statuses(data2, 1_800_000_000.0)
    assert out2[0].text.endswith(", 连续失效 2 波"), "streak=2 即标注(>1 口径, 不是 >=1)"
    data3 = HrSiteData()
    data3.wave.lanes = {"A": _rich_lane(status=LANE_FAILED, count_claim=7, count_match=True, fail_streak=0)}
    out3, lanes3 = _lane_statuses(data3, 1_800_000_000.0)
    assert out3[0].status_text == "失效" and out3[0].lane_text == "考察中"
    assert "声明 7 行" in out3[0].text and "对不平" not in out3[0].text, "count_match=True 不标对不平"
    assert lanes3 == "A:x3页4行(全)/声明7 B:无 C:无", "failed 档摘要标记 x 且不带对不平"


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
    assert snap.lanes_text == "A:[x]3页4行(全)/声明5 对不平 B:-0页0行 C:-0页0行"
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
