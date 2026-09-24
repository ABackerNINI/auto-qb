"""HR 统计页解析的通用件: 栈式表格抽取 + 数值容错。

站点差异(表头名、列语义、分页形态)在 adapters/ 里隔离; 本模块只提供与站点无关的两件事:
1. `TableTree` —— 用标准库 html.parser 建 `<tr>/<td>` 两级树, **容忍包裹表嵌套**
   (NexusPHP 的 HR 表落在 `<td class="embedded">` 里再套一层 `<table>`);
2. 数值容错 —— 站点的 "27.34 GB" / "2:42:17" / "9天06:05:11" / "0.000" 等形态转成结构化值。

零新依赖: 标准库 html.parser 已实证够用(实验脚本在 BTSchool 样张上全字段解析正确),
不再考虑引入第三方解析器。
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple

# ---------- 数值容错 ----------

_SIZE_UNITS = {
    "B": 1,
    "KB": 1024,
    "MB": 1024**2,
    "GB": 1024**3,
    "TB": 1024**4,
    "PB": 1024**5,
    "KIB": 1024,
    "MIB": 1024**2,
    "GIB": 1024**3,
    "TIB": 1024**4,
    "PIB": 1024**5,
}

_SIZE_RE = re.compile(r"([\d.,]+)\s*([A-Za-z]+)")


def parse_size(text: str) -> Optional[int]:
    """"27.34 GB" -> 字节数; 认不出返回 None(不猜)。"""
    m = _SIZE_RE.search(text or "")
    if not m:
        return None
    try:
        value = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    return int(value * _SIZE_UNITS.get(m.group(2).upper(), 1))


_DURATION_DIGITS_RE = re.compile(r"^[\d:.\s]+$")


def parse_duration(text: str) -> Optional[int]:
    """"2:42:17" -> 9721; "9天06:05:11" -> 799511; 返回秒。

    天数前缀(中文 "天" / 英文 "d")与 "HH:MM:SS" / "MM:SS" 两种时分形态都认。
    """
    if not text:
        return None
    t = text.strip()
    days = 0
    dm = re.match(r"^(\d+)\s*(?:天|d|D)\s*", t)
    if dm:
        days = int(dm.group(1))
        t = t[dm.end():]
    if not t:
        return days * 86400 if days else None
    if not _DURATION_DIGITS_RE.match(t):
        return None
    parts = t.split(":")
    if len(parts) > 3 or len(parts) < 2 or not all(p.strip().isdigit() for p in parts):
        return None  # 段数不对就不猜(站点形态只有 H:MM:SS / MM:SS)
    nums = [int(p) for p in parts]
    while len(nums) < 3:
        nums.insert(0, 0)
    h, m, s = nums[-3:]
    return days * 86400 + h * 3600 + m * 60 + s


_RATIO_RE = re.compile(r"-?[\d.]+")


def parse_ratio(text: str) -> Optional[float]:
    """"0.000" -> 0.0; "∞" 等不可解析形态返回 None。"""
    m = _RATIO_RE.search(text or "")
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


_DT_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


def parse_datetime(text: str) -> Optional[str]:
    """完成时间 -> ISO 字符串(秒精度); 认不出返回 None(不猜 —— 新鲜度闸门依赖它)。"""
    t = (text or "").strip()
    if not t:
        return None
    for fmt in _DT_FORMATS:
        try:
            return datetime.strptime(t, fmt).isoformat(sep=" ")
        except ValueError:
            continue
    return None


# ---------- 栈式表格抽取 ----------


@dataclass
class Cell:
    """一个 `<td>/<th>`: 文本 + 其中的链接 + 嵌套行"""

    text: str = ""
    hrefs: List[str] = field(default_factory=list)
    rows: List["Row"] = field(default_factory=list)


@dataclass
class Row:
    """一个 `<tr>`: 单元格序列"""

    cells: List[Cell] = field(default_factory=list)


class _TableTree(HTMLParser):
    """建 `<tr>/<td>` 两级树。cell 内的嵌套 table 归到该 cell 的 rows, 与兄弟行不混。"""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root: List[Row] = []
        self._cell_stack: List[Cell] = []
        self._row_stack: List[Row] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "tr":
            row = Row()
            if self._cell_stack:
                self._cell_stack[-1].rows.append(row)
            else:
                self.root.append(row)
            self._row_stack.append(row)
        elif tag in ("td", "th") and self._row_stack:
            cell = Cell()
            self._row_stack[-1].cells.append(cell)
            self._cell_stack.append(cell)
        elif tag == "a" and self._cell_stack:
            href = dict(attrs).get("href")
            if href:
                self._cell_stack[-1].hrefs.append(href)

    def handle_data(self, data: str) -> None:
        if self._cell_stack:
            # 直接累积到字符串, 避免每段文本都建一个 list 元素(大页面下明显)
            cell = self._cell_stack[-1]
            cell.text += data

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._cell_stack:
            self._cell_stack.pop()
        elif tag == "tr" and self._row_stack:
            self._row_stack.pop()


def flat_rows(html: str) -> List[Row]:
    """全部「叶子行」(其单元格不含嵌套行)按文档顺序展开 —— 表头与数据行都在其中。"""
    parser = _TableTree()
    parser.feed(html)
    out: List[Row] = []

    def walk(rows: List[Row]) -> None:
        for row in rows:
            if all(not c.rows for c in row.cells):
                out.append(row)
            for c in row.cells:
                walk(c.rows)

    walk(parser.root)
    return out


def cell_text(cell: Cell) -> str:
    """单元格文本(去首尾空白; 内部空白折叠为单空格, 让 "0.00 KB" 这种形态稳定)"""
    return " ".join(cell.text.split())


@dataclass
class HtmlTable:
    """按表头锚定的表格: columns 为表头文本, rows 为数据行(单元格原样保留链接)"""

    columns: Tuple[str, ...] = ()
    rows: Tuple[Tuple[Cell, ...], ...] = ()


def extract_table(html: str, header_key: str, header_column: int = 0) -> HtmlTable:
    """以「首列文本 == header_key」的行锚定表头, 同容器内其后的行即数据行。

    数据区结束判据由调用方给定(见 adapters: 首列不再是纯数字即停) —— 本函数返回锚点
    之后同容器的**全部**行(含页脚/分页), 由调用方截断。
    """
    rows = flat_rows(html)
    columns: Optional[Tuple[str, ...]] = None
    start = -1
    for i, row in enumerate(rows):
        if len(row.cells) > header_column and cell_text(row.cells[header_column]) == header_key:
            columns = tuple(cell_text(c) for c in row.cells)
            start = i
            break
    if columns is None:
        return HtmlTable()
    return HtmlTable(columns=columns, rows=tuple(tuple(r.cells) for r in rows[start + 1:]))


def column_index(columns: Tuple[str, ...], name: str) -> int:
    """表头名 -> 列下标; 缺失返回 -1(调用方据此计缺失率, 不静默取错列)"""
    try:
        return columns.index(name)
    except ValueError:
        return -1


_NEXT_PAGE_RE_TEMPLATE = r'<a[^>]+href="[^"]*{page}[^"]*"[^>]*>\s*(?:<b>)?\s*下一页'


def has_next_page(html: str, page_file: str = "myhr.php") -> bool:
    """分页区是否存在**真实链接**的「下一页」

    灰色不可点的「下一页」在 NexusPHP 里是无 `<a>` 的 `<font><b>下一页…` , 不会误判 ——
    这是「翻页是否到底」的判据, 直接决定覆盖证明是否成立。
    """
    pattern = _NEXT_PAGE_RE_TEMPLATE.format(page=re.escape(page_file))
    return re.search(pattern, html, re.IGNORECASE) is not None


def page_bounds(html: str) -> Optional[Tuple[int, int]]:
    """分页页脚里的 "N - M" 区间(拿不到返回 None), 仅作报告用。

    必须锚定在页脚的 `<b>` 里 —— 完成时间 "2026-09-21" 也含「数字-数字」, 松正则会误匹配。
    """
    normalized = html.replace("&nbsp;", " ")
    m = re.search(r"(\d+)\s*-\s*(\d+)\s*</b>", normalized)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def page_javascript_marks(html: str) -> Dict[str, int]:
    """页面脚本里的 `var maxpage=N; var currentpage=M;`(NexusPHP 常见), 供确认翻页进度"""
    out: Dict[str, int] = {}
    for key in ("maxpage", "currentpage"):
        m = re.search(rf"var\s+{key}\s*=\s*(\d+)", html)
        if m:
            out[key] = int(m.group(1))
    return out
