"""NexusPHP 系站点 adapter —— HR 名单来源 = `myhr.php` (首批站点 BTSchool 即此形态)。

页面事实(2026-09-22 样张核对, 样本见 D:/Projects/站点页面/BTSchool):
- `myhr.php` 表头九列: HR编号 | 种子名称 | 上传量 | 下载量 | 分享率 | 还需做种时间 | 完成时间 |
  剩余达标时间 | 20000魔力值免罪
- HR 表被包在 `<td class="embedded">` 内再套一层 `<table>`, 解析器须容忍嵌套(parse.TableTree 已做)
- 页面**没有** download.php 链接, 按 NexusPHP 惯例拼 `/download.php?id={tid}`
- 状态过滤: `?hrtype=A`(考察中, 默认页) / `B`(已达标) / `C`(未达标) / `D`(已免罪)
- 时间形态: 还需做种 "H:MM:SS"; 剩余达标 "X天HH:MM:SS"; 完成时间 "YYYY-MM-DD HH:MM:SS"
- 灰色不可点的「下一页」是无 `<a>` 的 `<font><b>`, 故 has_next_page 不会误判到底

待在线实测(计划 §13 M0, 不阻塞离线管道): `?page=N` 的真实参数名与形态。
"""
from typing import Dict, List, Tuple
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

_COLUMNS = (COL_TID, COL_NAME, COL_UPLOADED, COL_DOWNLOADED, COL_RATIO, COL_NEED_SEED, COL_DONE, COL_REMAIN)

#: 这些列任一为空即计一次「字段缺失」—— 用于改版防护(HTTP 200 但字段大面积读不到)
REQUIRED_COLUMNS = (COL_NAME, COL_NEED_SEED, COL_REMAIN)


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
    ) -> None:
        self.site = site
        self._hr_page_url = hr_page_url
        self._download_path = download_path
        self._scopes = tuple(scopes)
        self._page_param = page_param
        parsed = urlparse(hr_page_url)
        self._root = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else ""

    # ---------- URL ----------

    @property
    def scopes(self) -> Tuple[str, ...]:
        return self._scopes

    def page_url(self, scope: str, page: int) -> str:
        """第 page 页地址; page <= 1 不带翻页参数(站点默认即第一页)"""
        url = f"{self._hr_page_url}?hrtype={scope}"
        if page > 1:
            url += f"&{self._page_param}={page}"
        return url

    def download_url(self, tid: int) -> str:
        return f"{self._root}{self._download_path.format(id=tid)}"

    # ---------- 解析 ----------

    def parse_page(self, scope: str, html: str) -> ParsedScope:
        table = extract_table(html, HEADER_KEY)
        if not table.columns:
            return ParsedScope(scope=scope)
        idx = {name: column_index(table.columns, name) for name in _COLUMNS}
        if idx[COL_TID] < 0:
            return ParsedScope(scope=scope)  # 表头在但缺 HR 编号列 = 改版, 交由覆盖证明拒绝

        entries: List[HrEntry] = []
        missing = 0
        for cells in table.rows:
            i_tid = idx[COL_TID]
            if i_tid >= len(cells):
                break
            tid_text = cell_text(cells[i_tid])
            if not tid_text.isdigit():
                break  # 数据区结束(页脚 / 分页区)
            entries.append(self._map_row(scope, cells, idx))
            if any(_is_blank(cells, idx[name]) for name in REQUIRED_COLUMNS):
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
        def text(name: str) -> str:
            i = idx[name]
            return cell_text(cells[i]) if 0 <= i < len(cells) else ""

        return HrEntry(
            tid=int(text(COL_TID)),
            name=text(COL_NAME),
            lane=scope,
            uploaded_bytes=parse_size(text(COL_UPLOADED)),
            downloaded_bytes=parse_size(text(COL_DOWNLOADED)),
            ratio=parse_ratio(text(COL_RATIO)),
            need_seed_seconds=parse_duration(text(COL_NEED_SEED)),
            done_iso=parse_datetime(text(COL_DONE)),
            remain_seconds=parse_duration(text(COL_REMAIN)),
        )


def _is_blank(cells, index: int) -> bool:
    """列缺失(下标越界)或单元格为空 —— 两者都算字段缺失"""
    return index < 0 or index >= len(cells) or not cell_text(cells[index])
