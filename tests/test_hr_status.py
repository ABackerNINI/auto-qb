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
"""
from auto_qb.hr import report
from auto_qb.hr.model import (
    SOURCE_EXEMPT,
    SOURCE_NOT_LISTED,
    SOURCE_SATISFIED,
    HrEntry,
    HrSiteData,
    HrVerified,
)
from auto_qb.hr.resolve import HrSiteView
from auto_qb.hr.status import (
    LaneStatus,
    QuotaStatus,
    SOURCE_TEXTS,
    blocking_reason,
    duration_text,
    entry_details,
    need_seed_text,
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
