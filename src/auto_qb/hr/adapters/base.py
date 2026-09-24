"""站点 adapter 抽象: 「给定登录态 + 分页游标, 返回结构化 HR 种子列表」。

设计(计划 §4):
- adapter 只做**站点隔离**: URL 拼接 + 表格解析 + 数值容错; 不做频控、不抓页面、不碰状态
  —— 那些是 service/ratelimit 的职责。
- 接口按「返回 HR 种子列表」抽象, 把「站点若提供更便宜的来源(JSON 接口 / 逐种标记)」这条路留开:
  换实现不换接口, 并跳过 .torrent 下载成本。
- 「HTTP 200 但解析出 0 条」「必填字段缺失率超阈」都只是**数据质量信号**, 由 service 转成
  覆盖证明不成立 + 熔断告警, 绝不把空结果当真入库(空结果的正确语义是「该账号没有 HR 种子」)。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Tuple

from ..model import HrEntry


@dataclass(slots=True)
class ParsedScope:
    """一个 scope 一页的解析结果

    header_found 是「页面改版」与「账号确实没有 HR 种子」的**唯一区分器**:
    表头都没找到 = 页面结构变了(不可信); 表头在但 0 行 = 合法空结果。
    """

    scope: str
    entries: List[HrEntry] = field(default_factory=list)
    has_next: bool = False
    header_found: bool = False
    missing_field_rate: float = 0.0
    row_count: int = 0


class HrAdapter(ABC):
    """站点 adapter 基类: 子类只需实现 URL 拼接与一页 HTML 的解析。"""

    #: 站点名(与 trackers.<site> 的键一致)
    site: str = ""

    @property
    @abstractmethod
    def scopes(self) -> Tuple[str, ...]:
        """本次刷新要抓的 scope 集合(A 考察中 / B 已达标 / C 未达标 / 可选 D 已免罪)"""

    @abstractmethod
    def page_url(self, scope: str, page: int) -> str:
        """第 page 页(从 1 开始)的 HR 统计页地址"""

    @abstractmethod
    def parse_page(self, scope: str, html: str) -> ParsedScope:
        """解析一页 HTML -> 结构化条目(空结果 = 页面里没有数据行, 由 service 判定是否改版)"""

    @abstractmethod
    def download_url(self, tid: int) -> str:
        """.torrent 下载地址(相对站点根拼出; passkey 这类页面参数由取数通道在页面上下文补)"""

    def looks_like_login(self, html: str) -> bool:
        """页面是否像登录页/未登录(默认按 NexusPHP 通用特征; 站点可覆写)"""
        return ("takelogin.php" in html or 'name="password"' in html) and "HR编号" not in html

    def looks_like_challenge(self, html: str) -> bool:
        """页面是否像 Cloudflare 之类的挑战页(默认按通用特征)"""
        lowered = html.lower()
        return any(
            mark in lowered
            for mark in ("just a moment", "cf-chl", "__cf_chl", "attention required", "checking your browser")
        )
