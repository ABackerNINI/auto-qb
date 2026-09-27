"""NexusPHP 系站点 adapter —— HR 名单来源 = `myhr.php` (首批站点 BTSchool 即此形态)。

页面事实(2026-09-22 样张核对, 样本见 D:/Projects/站点页面/BTSchool):
- `myhr.php` 表头九列: HR编号 | 种子名称 | 上传量 | 下载量 | 分享率 | 还需做种时间 | 完成时间 |
  剩余达标时间 | 20000魔力值免罪
- HR 表被包在 `<td class="embedded">` 内再套一层 `<table>`, 解析器须容忍嵌套(parse.TableTree 已做)
- 页面**没有** download.php 链接, 按 NexusPHP 惯例拼 `/download.php?id={tid}`
- 状态过滤: `?hrtype=A`(考察中, 默认页) / `B`(已达标) / `C`(未达标) / `D`(已免罪)
- 时间形态: 还需做种 "H:MM:SS"; 剩余达标 "X天HH:MM:SS"; 完成时间 "YYYY-MM-DD HH:MM:SS"
- 灰色不可点的「下一页」是无 `<a>` 的 `<font><b>`, 故 has_next_page 不会误判到底

myhr 表格形态但状态参数 / 表头名不同的变体站点, 经构造参数注入(scope_param / scope_values /
header_key / column_names), 不另写解析逻辑 —— 见 carpt.py。

待在线实测(计划 §13 M0, 不阻塞离线管道): `?page=N` 的真实参数名与形态。
"""
from typing import Dict, List, Optional, Tuple
import re
from urllib.parse import urlparse

from ..model import HrEntry
from ..parse import (
    cell_text,
    column_index,
    extract_table,
    has_next_page,
    parse_datetime,
    parse_duration,
    parse_ratio,
    parse_size,
)
from .base import HrAdapter, ParsedScope

HEADER_KEY = "HR编号"
COL_TID = "HR编号"
COL_NAME = "种子名称"
COL_UPLOADED = "上传量"
COL_DOWNLOADED = "下载量"
COL_RATIO = "分享率"
COL_NEED_SEED = "还需做种时间"
COL_DONE = "完成时间"
COL_REMAIN = "剩余达标时间"

#: 语义列名 -> 标准表头名。变体站点(见 carpt.py)只换表头名, 语义列不变
STANDARD_COLUMNS = {
    "tid": COL_TID,
    "name": COL_NAME,
    "uploaded": COL_UPLOADED,
    "downloaded": COL_DOWNLOADED,
    "ratio": COL_RATIO,
    "need_seed": COL_NEED_SEED,
    "done": COL_DONE,
    "remain": COL_REMAIN,
}

#: 这些语义列任一为空即计一次「字段缺失」—— 用于改版防护(HTTP 200 但字段大面积读不到)
REQUIRED_KEYS = ("name", "need_seed", "remain")

#: 档位字母 -> 状态参数值(标准 NexusPHP: hrtype=A/B/C/D, 值与字母一致)
STANDARD_SCOPE_VALUES = {"A": "A", "B": "B", "C": "C", "D": "D"}

#: 行内链接里提取「下载用种子 id」: download.php 优先, details.php 兜底(CarPT 等站点
#: H&R ID 与种子 id 是两个空间, 实证见 carpt.py 模块 docstring; 顺序即优先级)
_DL_ID_RES = (
    re.compile(r"download\.php\?id=(\d+)"),
    re.compile(r"details\.php\?id=(\d+)"),
)

#: 兼容历史导入(标准形态的必填列名)
REQUIRED_COLUMNS = tuple(STANDARD_COLUMNS[k] for k in REQUIRED_KEYS)


class NexusPhpMyhrAdapter(HrAdapter):
    """NexusPHP `myhr.php` 形态的 HR 统计页 adapter"""
    def __init__(
        self,
        site: str,
        *,
        hr_page_url: str,
        download_path: str,
        scopes: Tuple[str, ...],
        page_param: str = "page",
        scope_param: str = "hrtype",
        scope_values: Optional[Dict[str, str]] = None,
        header_key: str = HEADER_KEY,
        column_names: Optional[Dict[str, str]] = None,
    ) -> None:
        self.site = site
        self._hr_page_url = hr_page_url
        self._download_path = download_path
        self._scopes = tuple(scopes)
        self._page_param = page_param
        self._scope_param = scope_param
        self._scope_values = dict(scope_values) if scope_values else dict(STANDARD_SCOPE_VALUES)
        self._header_key = header_key
        self._columns = dict(STANDARD_COLUMNS if column_names is None else column_names)
        self._required = tuple(self._columns[k] for k in REQUIRED_KEYS)
        parsed = urlparse(hr_page_url)
        self._root = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else ""

    # ---------- URL ----------

    @property
    def scopes(self) -> Tuple[str, ...]:
        return self._scopes

    def page_url(self, scope: str, page: int) -> str:
        """第 page 页地址; page <= 1 不带翻页参数(站点默认即第一页)

        档位不在映射表里按字母原样传(校验层已把 hr_page_scopes 锁在 A/B/C/D)。
        """
        value = self._scope_values.get(scope, scope)
        url = f"{self._hr_page_url}?{self._scope_param}={value}"
        if page > 1:
            url += f"&{self._page_param}={page}"
        return url

    def download_url(self, tid: int) -> str:
        return f"{self._root}{self._download_path.format(id=tid)}"

    # ---------- 解析 ----------

    def parse_page(self, scope: str, html: str) -> ParsedScope:
        table = extract_table(html, self._header_key)
        if not table.columns:
            return ParsedScope(scope=scope)
        idx = {name: column_index(table.columns, name) for name in self._columns.values()}
        i_tid = idx[self._columns["tid"]]
        if i_tid < 0:
            return ParsedScope(scope=scope)  # 表头在但缺 HR 编号列 = 改版, 交由覆盖证明拒绝

        entries: List[HrEntry] = []
        missing = 0
        for cells in table.rows:
            if i_tid >= len(cells):
                break
            tid_text = cell_text(cells[i_tid])
            if not tid_text.isdigit():
                break  # 数据区结束(页脚 / 分页区)
            entries.append(self._map_row(scope, cells, idx))
            if any(_is_blank(cells, idx[name]) for name in self._required):
                missing += 1
        count = len(entries)
        return ParsedScope(
            scope=scope,
            entries=entries,
            has_next=has_next_page(html),
            header_found=True,
            missing_field_rate=(missing / count) if count else 0.0,
            row_count=count,
        )

    def _map_row(self, scope: str, cells, idx: Dict[str, int]) -> HrEntry:
        col = self._columns

        def text(key: str) -> str:
            i = idx[col[key]]
            return cell_text(cells[i]) if 0 <= i < len(cells) else ""

        return HrEntry(
            tid=int(text("tid")),
            dl_id=_dl_id_of(cells),
            name=text("name"),
            lane=scope,
            uploaded_bytes=parse_size(text("uploaded")),
            downloaded_bytes=parse_size(text("downloaded")),
            ratio=parse_ratio(text("ratio")),
            need_seed_seconds=parse_duration(text("need_seed")),
            done_iso=parse_datetime(text("done")),
            remain_seconds=parse_duration(text("remain")),
        )


def _dl_id_of(cells) -> Optional[int]:
    """行内链接提取「下载用种子 id」; 没有任何可认链接返回 None(调用方回落 tid)"""
    for pattern in _DL_ID_RES:
        for cell in cells:
            for href in cell.hrefs:
                m = pattern.search(href)
                if m:
                    return int(m.group(1))
    return None


def _is_blank(cells, index: int) -> bool:
    """列缺失(下标越界)或单元格为空 —— 两者都算字段缺失"""
    return index < 0 or index >= len(cells) or not cell_text(cells[index])
