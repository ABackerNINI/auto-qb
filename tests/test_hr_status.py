"""test_hr_status 测试计划: hr.status 种子明细导出(entry_details, 计划 26-10-01-2216 §7 阶段1)

## 测试计划(每个测试函数一条)
- test_entry_details_sort_matches_cli_order: 排序与 CLI 明细表口径一致(档位·下载量同一公式; 下载量缺失按 0)
- test_entry_details_keeps_missing_rows: 失踪行(active=False)不丢且参与同一排序 —— 全量清单一览是 issue 本意
- test_entry_details_need_seed_text_reuses_single_point: need_seed 人话确为复用单点(与 CLI 同一函数)而非另写
- test_entry_details_verified_join: verified join —— 有记录→ts+source 原值+人话 / 无记录→未核实 / v2 键也能命中
- test_entry_details_source_texts: 放行来源人话映射(D 免罪 / 未列出 / B 毕业); 未知原值回落原文不静默丢
- test_entry_details_field_surface: 导出字段面 = §3 P0+P1 全集; remain_seconds 等 P2 字段不得出现(决策点③)
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
from auto_qb.hr.status import SOURCE_TEXTS, entry_details, need_seed_text


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
    assert rows[3].verified_source == "satisfied" and rows[3].verified_source_text == "B 毕业"


def test_entry_details_source_texts():
    """放行来源人话映射钉死三键; 未知 source 回落原文(给原始值+人话的兜底, 不静默丢)"""
    assert SOURCE_TEXTS == {SOURCE_EXEMPT: "D 免罪", SOURCE_NOT_LISTED: "未列出", SOURCE_SATISFIED: "B 毕业"}
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
