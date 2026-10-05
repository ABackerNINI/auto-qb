"""test_hr_parse 测试计划: HR 统计页解析(栈式表格抽取 + 数值容错 + NexusPHP adapter)

## 测试计划(每个测试函数一条)
- test_parse_size: "27.34 GB" / "0.00 KB" / 十进制与二进制单位 / 认不出返回 None
- test_parse_size_unknown_unit_returns_none: 表外字母缩写单位("2.5T"/"800M") -> None, 不当 1 字节静默算错
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
- test_carpt_adapter_urls: CarPT 变体的 status 状态参数 / 档位映射 / 翻页 / 下载地址
- test_carpt_adapter_parse_first_page: CarPT 表头形态(十列 td.colhead)数据行全字段解析正确
- test_carpt_adapter_empty_table: 真实样张的空表结构 = 合法空结果, 不是改版
- test_carpt_adapter_revised_page_reports_header_missing: CarPT 页改版(无 H&R ID 表头) -> header_found False
- test_carpt_adapter_detects_login: 登录页识别按 CarPT 表头锚点(基类锚的是标准「HR编号」)
- test_header_hr_numbers_btschool_carrier: BTSchool 页头计数条原文形态, 红 span 的 style 属性带数字不误采
- test_header_hr_numbers_carpt_carrier: CarPT 页头计数条原文形态([] 包裹 + 中间位红字)按序取出 3 数
- test_header_hr_numbers_absent_returns_none: 无计数条 / 标签被改 = None(无证据降级)
- test_carpt_parse_counters_maps_survey_and_unsatisfied: CarPT 3 数 = A 考察中 / C 未达标, 上限位不采
- test_carpt_parse_counters_wrong_arity_degrades: 位数与钉死值不符 = 空 dict 降级(铁律)
- test_btschool_parse_counters_maps_two_numbers: BTSchool 2 数 = A 考察中 / C 未达标
- test_btschool_parse_counters_missing_bar_degrades: BTSchool 页无计数条 = 空 dict 降级
- test_default_nexusphp_adapter_has_no_counters: 未实证站点(默认 nexusphp)一律无计数
- test_order_violations_desc_holds: 完成时间倒序整列成立 -> 0 违反
- test_order_violations_single_inversion_is_flagged: 页内逆序 1 处即记违反 + 首处位置
- test_order_violations_direction_flip_counts_as_violation: 方向翻转视同逆序
- test_order_violations_asc_also_valid: 方向不预设(校验单调稳定, 不是必须倒序)
- test_order_violations_missing_fields_not_compared: 缺字段行不计入比较但计入 total
- test_order_violations_insufficient_evidence: 可比行 < 2 = 证据不足不判
- test_order_violations_all_equal_no_direction: 全相等不算违反但方向推不出
- test_cross_page_violation_desc_and_asc: 跨页证据判据(desc/asc/方向未知/上页空)
"""
import pytest

from auto_qb.hr.adapters import build_adapter
from auto_qb.hr.adapters.nexusphp import REQUIRED_COLUMNS, NexusPhpMyhrAdapter, header_hr_numbers
import auto_qb.hr.adapters.nexusphp as hr_nexusphp
from auto_qb.hr.parse import (
    cell_text,
    flat_rows,
    column_index,
    cross_page_violation,
    extract_table,
    has_next_page,
    order_violations,
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
    btschool_counter_bar,
    carpt_counter_bar,
    load_fixture,
    myhr_page,
    row,
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
    # 标准 NexusPHP: H&R 编号与种子 id 同空间(dl_id == tid), 回落路径不改变行为
    assert first.dl_id == 313852
    # 站点侧达标结论(计划 §9 v3.0: 档位即结论): A 考察中 / C 未达标 ⇒ False, B 已达标 ⇒ True
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
    """登录页与挑战页特征识别

    命中登录页 ⇒ service 抛 `HrLoginExpired`(**不计失败、不推熔断**, 只报一次让人去登录 —— 重试无用);
    命中挑战页 ⇒ 普通取数失败(走退避熔断)。两者分开的判据见 `events.LABELS` 的四类事件。
    """
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


# ---------- CarPT 变体(myhr 表格 + status 参数 + H&R ID 表头) ----------

CARPT_PAGE1 = "carpt_myhr_page1.html"
CARPT_EMPTY = "carpt_myhr_empty.html"


def _carpt_adapter(**overrides):
    conf = site_conf(
        adapter="carpt",
        hr_page_url="https://carpt.net/myhr.php",
        **overrides,
    )
    adapter = build_adapter("carpt", conf)
    assert adapter is not None
    return adapter


def test_carpt_adapter_urls():
    """CarPT 的档位映射(status: 1考察中/2已达标/3未达标/4已免罪)与翻页 / 下载地址"""
    adapter = _carpt_adapter()
    assert adapter.page_url("A", 1) == "https://carpt.net/myhr.php?status=1"
    assert adapter.page_url("B", 1) == "https://carpt.net/myhr.php?status=2"
    assert adapter.page_url("D", 2) == "https://carpt.net/myhr.php?status=4&page=2"
    assert adapter.download_url(40001) == "https://carpt.net/download.php?id=40001"
    assert adapter.scopes == ("A", "B", "C"), "v3: 恒抓 A/B/C, D 已免罪不翻(计划 §4.1)"


def test_carpt_adapter_parse_first_page():
    """CarPT 表头形态(十列 td.colhead)数据行全字段解析正确(列名差异: 下载完成时间/剩余考察时间)"""
    parsed = _carpt_adapter().parse_page("A", load_fixture(CARPT_PAGE1))
    assert parsed.header_found is True
    assert parsed.has_next is True
    assert parsed.row_count == 2
    assert parsed.missing_field_rate == 0.0
    first, second = parsed.entries
    assert first.tid == 40001
    assert first.lane == "A"
    assert first.name.startswith("EXAMPLE MOVIE")
    # CarPT 实证(2026-09-27 已达标样张): H&R ID 与种子 id 是两个 id 空间 ——
    # 名称列详情链接的 id 必须提取进 dl_id(取 .torrent 用), 不能混用 tid
    assert first.dl_id == 173107
    assert first.dl_id != first.tid
    assert first.uploaded_bytes == 0
    assert first.downloaded_bytes == int(27.34 * 1024**3)
    assert first.ratio == 0.0
    assert first.need_seed_seconds == 2 * 3600 + 42 * 60 + 17
    # 样张完成时间无秒("2026-09-25 04:34"), parse_datetime 补齐秒
    assert first.done_iso == "2026-09-25 04:34:00"
    assert first.remain_seconds == 9 * 86400 + 6 * 3600 + 5 * 60 + 11
    assert second.tid == 40002
    assert second.dl_id == 198349
    assert second.ratio == 1.234


def test_carpt_adapter_empty_table():
    """真实样张的空表结构(表头在但 0 行) = 合法空结果, 不是改版"""
    parsed = _carpt_adapter().parse_page("A", load_fixture(CARPT_EMPTY))
    assert parsed.header_found is True
    assert parsed.row_count == 0
    assert parsed.entries == []
    assert parsed.has_next is False


def test_carpt_adapter_revised_page_reports_header_missing():
    """CarPT 页改版(无 H&R ID 表头) -> header_found False(覆盖证明据此拒绝产生放行)"""
    parsed = _carpt_adapter().parse_page("A", REVISED_PAGE)
    assert parsed.header_found is False
    assert parsed.row_count == 0


def test_carpt_adapter_detects_login():
    """登录页识别按 CarPT 表头锚点(基类锚的是标准「HR编号」, CarPT 页面没有这个词)"""
    adapter = _carpt_adapter()
    assert adapter.looks_like_login(LOGIN_PAGE) is True
    assert adapter.looks_like_login(load_fixture(CARPT_PAGE1)) is False


# ---------- 页头 H&R 计数条(计划 26-09-29-2036 §2.1 摘要形; M2 两站启用) ----------


def test_header_hr_numbers_btschool_carrier():
    """BTSchool 样张原文形态(标签在 <a> 内): 未达标红 span 的 style 属性带数字不得误采"""
    assert header_hr_numbers(btschool_counter_bar(1, 0)) == [1, 0]


def test_header_hr_numbers_carpt_carrier():
    """CarPT 样张原文形态(标签在 <a> 外、[] 包裹、中间位红字): 3 个数按序取出"""
    assert header_hr_numbers(carpt_counter_bar(0, 0, 20)) == [0, 0, 20]


def test_header_hr_numbers_absent_returns_none():
    """无计数条 / 标签被改(改版) -> None = 无证据, 调用方按降级处理"""
    assert header_hr_numbers(myhr_page([row(1)])) is None
    assert header_hr_numbers(REVISED_PAGE) is None


def test_carpt_parse_counters_maps_survey_and_unsatisfied():
    """CarPT: 3 数 = A 考察中 / C 未达标; 第 3 位是处罚上限不是档位行数不采, B 无声明不猜"""
    page = myhr_page([row(40001)], counter_bar_html=carpt_counter_bar(2, 1, 20))
    assert _carpt_adapter().parse_counters(page) == {"A": 2, "C": 1}


def test_carpt_parse_counters_wrong_arity_degrades():
    """位数与钉死的 3 不符(载体变了) -> 空 dict = 无证据降级, 绝不猜(铁律: 宁可不用)"""
    page = myhr_page([row(1)], counter_bar_html=btschool_counter_bar(2, 1))
    assert _carpt_adapter().parse_counters(page) == {}


def test_btschool_parse_counters_maps_two_numbers():
    """BTSchool: 2 数 = A 考察中 / C 未达标(校准实证: 考察中样例 页头 1 == A 档实抓 1 行)"""
    page = myhr_page([row(90001)], counter_bar_html=btschool_counter_bar(1, 0))
    adapter = build_adapter("btschool", site_conf(adapter="btschool"))
    assert adapter is not None
    assert adapter.parse_counters(page) == {"A": 1, "C": 0}


def test_btschool_parse_counters_missing_bar_degrades():
    """BTSchool 页没有计数条(改版 / 形态变) -> 空 dict, 行为退回无计数现状"""
    adapter = build_adapter("btschool", site_conf(adapter="btschool"))
    assert adapter is not None
    assert adapter.parse_counters(myhr_page([row(1)])) == {}
    assert adapter.parse_counters(REVISED_PAGE) == {}


def test_default_nexusphp_adapter_has_no_counters():
    """默认 nexusphp 形态不启用计数 —— 未实证站点一律无计数(基类默认空 dict 恒成立)"""
    adapter = build_adapter("nexusphp", site_conf())
    assert adapter is not None
    page = myhr_page([row(1)], counter_bar_html=btschool_counter_bar(1, 0))
    assert adapter.parse_counters(page) == {}


# ---------- 排序校验(计划 26-09-27-1815 §2 1.1) ----------


def test_order_violations_desc_holds():
    """完成时间倒序(降序)整列成立 -> 0 违反, 方向 desc"""
    check = order_violations([1000.0, 900.0, 800.0, 700.0])
    assert check.ok is True
    assert check.direction == "desc"
    assert check.inversions == 0
    assert check.first_at == -1
    assert check.comparable == 4


def test_order_violations_single_inversion_is_flagged():
    """页内逆序哪怕 1 处也记违反, 且给出首处位置(乱序行序号)"""
    check = order_violations([1000.0, 900.0, 950.0, 800.0])
    assert check.ok is False
    assert check.direction == "desc"
    assert check.inversions == 1
    assert check.first_at == 2  # 950 > 900 的乱序行


def test_order_violations_direction_flip_counts_as_violation():
    """方向翻转视同逆序: 先升后降(或反向)记违反"""
    check = order_violations([100.0, 200.0, 300.0, 250.0])
    assert check.ok is False
    assert check.direction == "asc"
    assert check.inversions == 1


def test_order_violations_asc_also_valid():
    """方向不预设: 升序整列同样成立(校验的是「单调稳定」, 不是「必须倒序」)"""
    check = order_violations([100.0, 200.0, 300.0])
    assert check.ok is True
    assert check.direction == "asc"


def test_order_violations_missing_fields_not_compared():
    """缺字段行不计入比较(避免重复算违反), 但计入 total 供证据判断"""
    check = order_violations([1000.0, None, 900.0, 800.0])
    assert check.ok is True
    assert check.comparable == 3
    assert check.total == 4


def test_order_violations_insufficient_evidence():
    """可比行 < 2 = 证据不足: 不判违反、方向为空(判定前置条件, 2026-09-26 用户定稿)"""
    for values in ([], [None, None], [100.0]):
        check = order_violations(values)
        assert check.insufficient is True
        assert check.direction == ""
        assert check.inversions == 0


def test_order_violations_all_equal_no_direction():
    """全相等: 单调恒成立不算违反, 但方向推不出(跨页校验没有基准)"""
    check = order_violations([100.0, 100.0, 100.0])
    assert check.ok is False
    assert check.direction == ""
    assert check.inversions == 0


def test_cross_page_violation_desc_and_asc():
    """跨页证据: desc 下本页最大 > 上页最小 = 乱序; asc 反之; 方向未知不判"""
    assert cross_page_violation([900.0, 800.0], [750.0, 700.0], "desc") is False
    assert cross_page_violation([900.0, 800.0], [850.0, 700.0], "desc") is True  # 850 > 800 比上页最老行还新
    assert cross_page_violation([100.0, 200.0], [250.0, 300.0], "asc") is False
    assert cross_page_violation([100.0, 200.0], [150.0, 300.0], "asc") is True  # 150 < 200 比上页最小行还小
    assert cross_page_violation([900.0], [950.0], "") is False  # 方向未知 = 证据不足不判
    assert cross_page_violation([], [950.0], "desc") is False  # 上页没有可比行


# ==================== P1 覆盖率提升轮: 解析容错长尾 ====================


def test_parse_size_malformed_number_returns_none():
    """数值段含多个小数点(float 拒收) -> None, 不猜(逗号按千分位剥除, 不算畸形)"""
    assert parse_size("1.2.3 GB") is None


def test_parse_size_unknown_unit_returns_none():
    """表外字母缩写单位("2.5T" / "800M", T/M 不在 _SIZE_UNITS 表内) -> None, 不当 1 字节
    静默算错(与 parse_duration「认不出不猜」同款纪律, issue 26-10-06-0028)"""
    assert parse_size("2.5T") is None
    assert parse_size("800M") is None
    assert parse_size("12 Bytes") is None  # 归一后不在表内(表只收 B/KB/.../KiB/...)
    assert parse_size("3 ZB") is None


def test_parse_duration_days_only():
    """只有天数前缀("3天") -> 3 天的秒数"""
    assert parse_duration("3天") == 3 * 86400
    assert parse_duration("2d") == 2 * 86400


def test_parse_ratio_malformed_returns_none():
    """多小数点形态(float 抛 ValueError) -> None"""
    assert parse_ratio("1.2.3") is None


def test_table_tree_anchor_without_href_is_ignored():
    """<a> 无 href 属性不进 hrefs(页内锚点不误当链接)"""
    rows = flat_rows("<table><tr><td><a name=\"anchor\">text</a></td></tr></table>")
    assert len(rows) == 1
    assert rows[0].cells[0].hrefs == []
    assert cell_text(rows[0].cells[0]) == "text"


def test_extract_table_header_not_first_row():
    """表头行前面还有其它行(页面前言) -> 循环跳过直到锚定表头"""
    html = (
        "<table><tbody>"
        "<tr><td>页面说明文字</td></tr>"
        "<tr><td>HR编号</td><td>种子名称</td></tr>"
        "<tr><td>7</td><td>Show.7</td></tr>"
        "</tbody></table>"
    )
    table = extract_table(html, "HR编号")
    assert table.columns == ("HR编号", "种子名称")
    assert len(table.rows) == 1 and cell_text(table.rows[0][1]) == "Show.7"


def test_page_bounds_no_match_returns_none():
    """页脚区间 "N - M</b>" 找不到(或被锚定失败) -> None"""
    assert page_bounds("<p>没有分页</p>") is None
    assert page_bounds("完成时间 2026-09-21 - 2026-09-22(不在 <b> 里)") is None


def test_order_violations_records_only_first_inversion_position():
    """多处逆序只记第一处(first_at), 后续违反继续累加 inversions"""
    check = order_violations([3.0, 1.0, 4.0, 2.0, 5.0, 0.0])
    assert check.direction == "desc" and check.inversions == 2
    assert check.first_at == 2, "只记第一处违反的行号, 后续违反只累加计数"


def test_adapter_row_without_links_falls_back_to_tid():
    """行内没有任何可认下载链接 -> dl_id None(调用方回落 tid)"""
    adapter = NexusPhpMyhrAdapter(
        "example", hr_page_url="https://pt.example.com/myhr.php", download_path="/download.php?id={id}", scopes=("A", )
    )
    parsed = adapter.parse_page(
        "A",
        "<table><tbody>"
        "<tr><td>HR编号</td><td>种子名称</td><td>还需做种时间</td><td>剩余达标时间</td></tr>"
        "<tr><td>11</td><td>Plain.Row</td><td>1:00:00</td><td>2天00:00:00</td></tr>"
        "</tbody></table>",
    )
    assert parsed.entries[0].dl_id is None


def test_adapter_row_missing_tid_cell_breaks():
    """tid 列下标越界的残行(表头在, 行没格子) -> 数据区直接结束"""
    adapter = NexusPhpMyhrAdapter(
        "example", hr_page_url="https://pt.example.com/myhr.php", download_path="/download.php?id={id}", scopes=("A", )
    )
    parsed = adapter.parse_page(
        "A",
        "<table><tbody>"
        "<tr><td>HR编号</td><td>种子名称</td></tr>"
        "<tr></tr>"
        "</tbody></table>",
    )
    assert parsed.entries == [] and parsed.header_found


def test_adapter_non_digit_tid_ends_data_region():
    """tid 列非纯数字(页脚/分页区) -> 数据区结束, 不产出行"""
    adapter = NexusPhpMyhrAdapter(
        "example", hr_page_url="https://pt.example.com/myhr.php", download_path="/download.php?id={id}", scopes=("A", )
    )
    parsed = adapter.parse_page(
        "A",
        "<table><tbody>"
        "<tr><td>HR编号</td><td>种子名称</td><td>还需做种时间</td><td>剩余达标时间</td></tr>"
        "<tr><td>11</td><td>Show</td><td>1:00:00</td><td>2天00:00:00</td></tr>"
        "<tr><td>下一页</td><td></td><td></td><td></td></tr>"
        "</tbody></table>",
    )
    assert [e.tid for e in parsed.entries] == [11]


def test_adapter_parse_page_without_tid_column_degrades(monkeypatch):
    """表头在但列集里没有 HR 编号列 -> 空 ParsedScope(交由覆盖证明拒绝)"""
    from auto_qb.hr.parse import HtmlTable

    adapter = NexusPhpMyhrAdapter(
        "example", hr_page_url="https://pt.example.com/myhr.php", download_path="/download.php?id={id}", scopes=("A", )
    )
    monkeypatch.setattr(hr_nexusphp, "extract_table", lambda html, key: HtmlTable(columns=("种子名称", ), rows=((), )))
    parsed = adapter.parse_page("A", "<table></table>")
    assert parsed.entries == [] and parsed.header_found is False
