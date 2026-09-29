"""CarPT (carpt.net) 的 myhr.php 变体 adapter。

页面事实(2026-09-27 两份样张核对, 样本见用户提供: C:/Users/11059/Desktop/Projects/PT页/CarPT/HR,
含空表页与 status=2 已达标页 17 行数据):
- HR 表仍在 `myhr.php`, 但状态参数是 `?status=N` 而非标准 `?hrtype=X`:
  1 考察中 / 2 已达标 / 3 未达标 / 4 已免罪(tab 文字逐一核对)
- 表头锚点首列是「H&R ID」(非标准「HR编号」), 表头格为 `<td class="colhead">`(十列):
  H&R ID | 种子名称 | 上传量 | 下载量 | 分享率 | 还需做种时间 | 下载完成时间 | 剩余考察时间 |
  备注 | 操作 —— 末尾比标准多两列, 解析按表头名取列不受影响
- 列名差异: 「下载完成时间」(标准: 完成时间) / 「剩余考察时间」(标准: 剩余达标时间);
  完成时间形态 "YYYY-MM-DD HH:MM"(无秒, parse_datetime 已认)
- !**H&R ID 与种子 id 是两个 id 空间**(已达标页实证: H&R ID=8017746 的行, 名称列详情链接是
  details.php?id=173107) ⇒ 取 .torrent 必须用行内链接里的种子 id(基类 `_dl_id_of` 提取,
  download.php 优先 / details.php 兜底), 走 `HrEntry.dl_id`; 操作列在已达标页为空, 无站内下载链接
- B/C 档「还需做种时间/剩余考察时间」显示 `---`(非空白 ⇒ 不计字段缺失, parse 成 None = 展示层不显示)
- 分页仍是 nexus-pagination 形态, 翻页参数 `?page=N`; 服务端渲染, 无异步取数

计数载体(2026-09-29 样张核对, 计划 26-09-29-2036 §2.1 摘要形; 样本: C:/Users/11059/Desktop/Projects/PT页/CarPT/HR):
- 页头状态栏每页都带 `<font class="color_bonus">H&amp;R: </font> [<a href="myhr.php">考察中/<font color="red">未达标</font>/上限</a>]` —— 3 个数字, 与分页完全解耦
- 口径(用户拍板 26-09-29): 3 个数 = 考察中 / 未达标 / 上限(达到上限受处罚); 上限是处罚阈值不是
  档位行数不采, 已达标位页头没有 ⇒ B 档无声明(不猜)
- 校准实证(项目 parser 实抓): 考核中样例 页头第 1 位 0 == A 档实抓 0 行 [x]; 已达标样例 17 行,
  页头无已达标位(B 无声明的直接证据); 第 1/2 位语义来自用户拍板, 样张里恒 0 且无未达标档样张
- 未实证前(2026-09-27 存档)曾按「分页区间形」设计(末页 `1 - 17` 终点 = 档内总数) —— 样张定形改走
  页头摘要形: 区间终点在早停页 == 已抓行数, 对「翻页标记失效」这一目标失效模式无保护, 页头计数才有

配置写法: trackers.carpt.hr_check.adapter = "carpt", 其余同 nexusphp。
"""
from typing import Dict, Optional

from .nexusphp import NexusPhpMyhrAdapter, header_hr_numbers

#: 档位字母 -> CarPT status 参数值(样张 tab 核对: 1 考察中 / 2 已达标 / 3 未达标 / 4 已免罪)
SCOPE_STATUS = {"A": "1", "B": "2", "C": "3", "D": "4"}

#: 页头计数条位数与档位映射(样张钉死): 3 个数 = 考察中(A) / 未达标(C) / 上限(不采)
COUNTER_ARITY = 3
COUNTER_LANES = ("A", "C")

HEADER_KEY = "H&R ID"

COLUMN_NAMES = {
    "tid": "H&R ID",
    "name": "种子名称",
    "uploaded": "上传量",
    "downloaded": "下载量",
    "ratio": "分享率",
    "need_seed": "还需做种时间",
    "done": "下载完成时间",
    "remain": "剩余考察时间",
}


class CarPtMyhrAdapter(NexusPhpMyhrAdapter):
    """CarPT 形态: 标准 myhr 表格 + status 参数 + 变体表头名 + 页头 H&R 计数条(3 数)"""
    def parse_counters(self, html: str) -> Dict[str, Optional[int]]:
        """页头摘要形计数(载体与校准证据见模块 docstring): 3 数 = A 考察中 / C 未达标, 上限不采。"""
        nums = header_hr_numbers(html)
        if nums is None or len(nums) != COUNTER_ARITY:
            return {}  # 位数不对 = 载体变了 = 无证据降级(铁律: 宁可不用, 不可错用)
        return {lane: nums[i] for i, lane in enumerate(COUNTER_LANES)}

    def looks_like_login(self, html: str) -> bool:
        # 基类用标准表头「HR编号」排除误判, CarPT 页面没有这个词, 换本站表头锚点
        return ("takelogin.php" in html or 'name="password"' in html) and HEADER_KEY not in html


__all__ = [
    "CarPtMyhrAdapter",
    "COLUMN_NAMES",
    "COUNTER_ARITY",
    "COUNTER_LANES",
    "HEADER_KEY",
    "SCOPE_STATUS",
]
