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
from typing import Dict, List, Optional, Tuple

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

    def parse_counters(self, html: str) -> Dict[str, Optional[int]]:
        """从一页 HTML 提取「本页能证到的档位声明行数」(计划 26-09-29-2036 §2.1; 默认无计数)。

        默认返回 {} = 站点未接入计数 = 与无此机制完全等价(门恒开, 现状不变)。

        覆写契约三条 —— **覆写即承诺**, 违反 = 口径校准事故 ⇒ 批量签发永久冻结:
        1. 只在本页能证到该档**总数**时才返回该键: tab / 摘要形任意页可证(计数条同页带全档);
           分页区间形只有「无下一页」的末页能证(区间终点 = 档内累计行数, 1 起含端),
           早停波拿不到总数; 空表页无标记 ⇒ 无键。
        2. 键缺 = 无证据 = None 降级: 绝不猜测, 绝不拿「目前为止的行数」冒充总数。
        3. 铁律「宁可不用, 不可错用」: 只在样张实证「计数 == 全深度翻页实抓行数」后才允许
           覆写本方法; 未实证一律保持默认返回 {}。口径校准记录(样张路径/载体形态/推导规则/
           实证日期)随覆写写进子类 docstring, 证据链留档。
        """
        return {}

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
