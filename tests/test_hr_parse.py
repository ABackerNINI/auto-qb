"""test_hr_parse 测试计划: HR 统计页解析(栈式表格抽取 + 数值容错 + NexusPHP adapter)

## 测试计划(每个测试函数一条)
- test_parse_size: "27.34 GB" / "0.00 KB" / 十进制与二进制单位 / 认不出返回 None
- test_parse_duration: "H:MM:SS" / "MM:SS" / "X天HH:MM:SS" 与非法形态
- test_parse_ratio_and_datetime: 分享率与完成时间解析(认不出返回 None, 不猜)
- test_extract_table_handles_nested_wrapper: HR 表被 <td class="embedded"> 再套一层 table, 仍能锚定表头与数据行
- test_extract_table_missing_header: 页面改版(无表头) -> columns 为空
- test_has_next_page_requires_real_link: 灰色不可点的「下一页」不算有下一页(覆盖证明的翻页到底判据)
- test_adapter_parse_first_page: 首屏两行全字段解析正确(含嵌套包裹表与免罪链接)
- test_adapter_parse_last_page: 末页一行 + has_next=False
- test_adapter_empty_table_is_not_revision: 表头在但 0 行 = 合法空结果(不是改版)
- test_adapter_revised_page_reports_header_missing: 表头找不到 = 疑似改版
- test_adapter_reports_missing_field_rate: 必填列缺失计入缺失率
- test_adapter_urls: page_url 首屏不带翻页参数/第二页带, download_url 按模板拼绝对地址
- test_adapter_detects_login_and_challenge: 登录页与挑战页特征识别
- test_page_javascript_marks: 页脚区间与 maxpage/currentpage 脚本标记(报告用)
"""
import pytest

from auto_qb.hr.adapters import build_adapter
from auto_qb.hr.adapters.nexusphp import REQUIRED_COLUMNS
from auto_qb.hr.parse import (
    cell_text,
    column_index,
    extract_table,
    has_next_page,
    parse_datetime,
    parse_duration,
    parse_ratio,
    parse_size,
    page_bounds,
    page_javascript_marks,
)
from hr_helpers import (
    CHALLENGE_PAGE,
    EMPTY_TABLE_PAGE,
    LOGIN_PAGE,
    REVISED_PAGE,
    load_fixture,
    site_conf,
)

PAGE1 = "nexusphp_myhr_page1.html"
LAST = "nexusphp_myhr_last.html"


def _adapter(**overrides):
    conf = site_conf(**overrides)
    adapter = build_adapter("btschool", conf)
    assert adapter is not None
    return adapter


# ---------- 数值容错 ----------


@pytest.mark.parametrize(
    "text,want",
    [
        ("27.34 GB", int(27.34 * 1024**3)),
        ("0.00 KB", 0),
        ("451.88 GB", int(451.88 * 1024**3)),
        ("1.5 GiB", int(1.5 * 1024**3)),
        ("2 TB", 2 * 1024**4),
        ("", None),
        ("--", None),
    ],
)
def test_parse_size(text, want):
    """大小串解析(GB 按 1024 进制, 与站点展示习惯一致); 认不出返回 None"""
    assert parse_size(text) == want


@pytest.mark.parametrize(
    "text,want",
    [
        ("2:42:17", 2 * 3600 + 42 * 60 + 17),
        ("9天06:05:11", 9 * 86400 + 6 * 3600 + 5 * 60 + 11),
        ("06:05:11", 6 * 3600 + 5 * 60 + 11),
        ("10:00", 10 * 60),
        ("0:00:00", 0),
        ("", None),
        ("未知", None),
        ("1:2:3:4", None),
    ],
)
def test_parse_duration(text, want):
    """时长解析: 天数前缀 + 时分秒两种形态; 非法形态返回 None"""
    assert parse_duration(text) == want


def test_parse_ratio_and_datetime():
    """分享率与完成时间解析(认不出返回 None, 新鲜度闸门依赖完成时间故不能猜)"""
    assert parse_ratio("0.000") == 0.0
    assert parse_ratio("6.212") == 6.212
    assert parse_ratio("∞") is None
    assert parse_datetime("2026-09-22 04:34:25") == "2026-09-22 04:34:25"
    assert parse_datetime("2026-09-22") == "2026-09-22 00:00:00"
    assert parse_datetime("昨天") is None
    assert parse_datetime("") is None


# ---------- 表格抽取 ----------


def test_extract_table_handles_nested_wrapper():
    """HR 表被 <td class="embedded"> 再套一层 table, 仍能锚定表头与数据行"""
    html = load_fixture(PAGE1)
    table = extract_table(html, "HR编号")
    assert table.columns[0] == "HR编号"
    assert len(table.columns) == 9
    assert "20000魔力值免罪" in table.columns
    assert column_index(table.columns, "剩余达标时间") == 7
    assert column_index(table.columns, "不存在的列") == -1
    # 数据行: 前两行是数据, 后续是页脚/分页
    first = table.rows[0]
    assert cell_text(first[0]) == "313852"
    assert cell_text(first[1]).startswith("EXAMPLE SHOW S01")


def test_extract_table_missing_header():
    """页面改版(无表头) -> columns 为空(调用方据此判改版而不是把空结果当真)"""
    assert extract_table(REVISED_PAGE, "HR编号").columns == ()


def test_has_next_page_requires_real_link():
    """灰色不可点的「下一页」不算有下一页 —— 这是覆盖证明的翻页到底判据"""
    assert has_next_page(load_fixture(PAGE1)) is True
    assert has_next_page(load_fixture(LAST)) is False


# ---------- adapter ----------


def test_adapter_parse_first_page():
    """首屏两行全字段解析正确(含嵌套包裹表与免罪链接)"""
    adapter = _adapter()
    parsed = adapter.parse_page("A", load_fixture(PAGE1))
    assert parsed.header_found is True
    assert parsed.has_next is True
    assert parsed.row_count == 2
    assert parsed.missing_field_rate == 0.0
    first, second = parsed.entries
    assert first.tid == 313852
    assert first.lane == "A"
    assert first.name.startswith("EXAMPLE SHOW S01")
    assert first.uploaded_bytes == 0
    assert first.downloaded_bytes == int(27.34 * 1024**3)
    assert first.ratio == 0.0
    assert first.need_seed_seconds == 2 * 3600 + 42 * 60 + 17
    assert first.done_iso == "2026-09-22 04:34:25"
    assert first.remain_seconds == 9 * 86400 + 6 * 3600 + 5 * 60 + 11
    assert second.tid == 313997
    assert second.ratio == 1.234
    # 站点侧达标判据(计划 §9「站点数据是权威」): 档位 B 或剩余为 0
    assert first.satisfied_by_site is False
    assert parsed.entries[0].infohash_v1 == ""


def test_adapter_parse_last_page():
    """末页一行 + has_next=False(灰色「下一页」)"""
    parsed = _adapter().parse_page("A", load_fixture(LAST))
    assert parsed.header_found is True
    assert parsed.has_next is False
    assert parsed.row_count == 1
    assert parsed.entries[0].tid == 314011


def test_adapter_empty_table_is_not_revision():
    """表头在但 0 行 = 合法空结果(「该账号没有 HR 种子」), 与改版必须可区分"""
    parsed = _adapter().parse_page("A", EMPTY_TABLE_PAGE)
    assert parsed.header_found is True
    assert parsed.row_count == 0
    assert parsed.entries == []
    assert parsed.has_next is False


def test_adapter_revised_page_reports_header_missing():
    """表头找不到 = 疑似改版 -> header_found False(覆盖证明据此拒绝产生放行)"""
    parsed = _adapter().parse_page("A", REVISED_PAGE)
    assert parsed.header_found is False
    assert parsed.row_count == 0


def test_adapter_reports_missing_field_rate():
    """必填列缺失计入缺失率(改版防护的第二个信号)"""
    html = load_fixture(PAGE1).replace(">3天00:00:00<", "><")
    parsed = _adapter().parse_page("A", html)
    assert parsed.row_count == 2
    assert parsed.missing_field_rate == pytest.approx(0.5)
    assert REQUIRED_COLUMNS == ("种子名称", "还需做种时间", "剩余达标时间")


def test_adapter_urls():
    """page_url 首屏不带翻页参数 / 第二页带; download_url 按模板拼绝对地址"""
    adapter = _adapter()
    assert adapter.page_url("A", 1) == "https://pt.example.com/myhr.php?hrtype=A"
    assert adapter.page_url("C", 2) == "https://pt.example.com/myhr.php?hrtype=C&page=2"
    assert adapter.download_url(313852) == "https://pt.example.com/download.php?id=313852"
    assert adapter.scopes == ("A", "B", "C")


def test_adapter_detects_login_and_challenge():
    """登录页与挑战页特征识别(命中即熔断告警, 不重试轰炸)"""
    adapter = _adapter()
    assert adapter.looks_like_login(LOGIN_PAGE) is True
    assert adapter.looks_like_login(load_fixture(PAGE1)) is False
    assert adapter.looks_like_challenge(CHALLENGE_PAGE) is True
    assert adapter.looks_like_challenge(load_fixture(PAGE1)) is False


def test_page_javascript_marks():
    """页脚区间与 maxpage/currentpage 脚本标记(报告与翻页确认用)"""
    html = load_fixture(PAGE1)
    assert page_bounds(html) == (1, 2)
    marks = page_javascript_marks(html)
    assert marks["maxpage"] == 1
    assert marks["currentpage"] == 0
    assert page_javascript_marks(REVISED_PAGE) == {}
